from pathlib import Path
import re

from sqlalchemy.orm import Session

from app.analysis.context_builder import build_airport_analysis_context
from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.protection_zone_style import resolve_protection_zone_style
from app.analysis.protection_zone_spec import ProtectionZoneSpec
from app.analysis.spatial_facts import build_airport_spatial_facts
from app.analysis.rules.runway.electromagnetic_environment import (
    build_runway_em_protection_zone,
    build_runway_em_rule_result,
)
from app.analysis.station_dispatcher import StationAnalysisDispatcher
from app.analysis.standards import build_rule_standards
from app.application.polygon_obstacle_excel_parser import (
    PolygonObstacleExcelParseError,
    parse_polygon_obstacle_excel,
)
from app.application.polygon_obstacle_geometry import build_multipolygon_geometry
from app.application.point_obstacle_excel_parser import (
    PointObstacleExcelParseError,
    parse_point_obstacle_excel,
)
from app.application.polygon_obstacle_targets import (
    calculate_minimum_target_distance_km,
)
from app.core import runtime
from app.core.config import Settings
from app.report.docx_builder import build_analysis_report_docx
from app.report.export_payload_builder import build_export_payload
from app.repository.import_batch_repository import ImportBatchRepository
from app.schemas.polygon_obstacle import (
    AnalysisProtectionZoneResponse,
    AnalysisResultTargetResponse,
    AnalysisRuleResultResponse,
    AnalysisTaskCreateRequest,
    AnalysisTaskResultResponse,
    AnalysisTaskStatusResponse,
    BootstrapAirportResponse,
    BootstrapResponse,
    BootstrapStationResponse,
    ExportTaskResultResponse,
    ExportTaskStatusResponse,
    ImportedObstacleGeometryResponse,
    ImportedObstacleResponse,
    ImportTaskCreateRequest,
    ImportTaskResultResponse,
    ImportTaskStatusResponse,
    ImportTargetResponse,
)


class PolygonObstacleImportService:
    # 初始化多边形障碍物导入服务。
    def __init__(self, session: Session) -> None:
        self._repository = ImportBatchRepository(session)

    # 创建新的障碍物导入任务。
    def create_import_task(
        self, payload: ImportTaskCreateRequest
    ) -> ImportTaskStatusResponse:
        project = self._repository.create_project(
            payload.project_name, project_type="polygon_obstacle"
        )
        task_id = f"import-batch-{project.id}"
        source_file_path = self._store_import_file(
            task_id=task_id,
            file_name=payload.file_name,
            file_bytes=payload.file_bytes,
        )
        import_batch = self._repository.create_import_batch(
            task_id=task_id,
            project_id=project.id,
            obstacle_type=payload.obstacle_type,
            file_name=payload.file_name,
            source_file_path=source_file_path,
        )
        self._dispatch_import_task(import_batch.id)

        return ImportTaskStatusResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            message=import_batch.status_message or "import task created",
            progressPercent=import_batch.progress_percent,
            projectId=project.id,
            obstacleBatchId=import_batch.id,
        )

    # 创建新的点状障碍物导入任务。
    def create_point_import_task(
        self, payload: ImportTaskCreateRequest
    ) -> ImportTaskStatusResponse:
        project = self._repository.create_project(
            payload.project_name, project_type="point_obstacle"
        )
        task_id = f"import-batch-{project.id}"
        source_file_path = self._store_import_file(
            task_id=task_id,
            file_name=payload.file_name,
            file_bytes=payload.file_bytes,
        )
        import_batch = self._repository.create_import_batch(
            task_id=task_id,
            project_id=project.id,
            obstacle_type=payload.obstacle_type,
            file_name=payload.file_name,
            source_file_path=source_file_path,
        )
        self._dispatch_import_task(import_batch.id)

        return ImportTaskStatusResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            message=import_batch.status_message or "import task created",
            progressPercent=import_batch.progress_percent,
            projectId=project.id,
            obstacleBatchId=import_batch.id,
        )

    # 执行导入任务并写入障碍物数据。
    def run_import_task(self, task_id: str) -> None:
        import_batch = self._repository.mark_import_batch_running(task_id)
        if import_batch is None:
            return

        try:
            project = self._repository.get_project(import_batch.project_id)
            if project is not None and project.project_type == "point_obstacle":
                self._run_point_import_batch(import_batch)
            else:
                self._run_polygon_import_batch(import_batch)
        except (PolygonObstacleExcelParseError, PointObstacleExcelParseError) as exc:
            self._repository.mark_import_batch_failed(task_id, str(exc))

    # 执行点状导入任务并写入障碍物数据。
    def run_point_import_task(self, task_id: str) -> None:
        self.run_import_task(task_id)

    # 查询点状导入任务的当前状态。
    def get_point_import_task_status(
        self, task_id: str
    ) -> ImportTaskStatusResponse | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        project = self._repository.get_project(import_batch.project_id)
        if project is None or project.project_type != "point_obstacle":
            return None

        return self.get_import_task_status(task_id)

    # 查询点状导入任务的结果详情。
    def get_point_import_task_result(
        self, task_id: str
    ) -> ImportTaskResultResponse | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        project = self._repository.get_project(import_batch.project_id)
        if project is None or project.project_type != "point_obstacle":
            return None

        return self.get_import_task_result(task_id)

    # 执行多边形导入批次并写入障碍物数据。
    def _run_polygon_import_batch(self, import_batch: object) -> None:
        source_file_path = import_batch.source_file_path
        if not source_file_path:
            raise PolygonObstacleExcelParseError("missing import source file path")

        parsed_obstacles = parse_polygon_obstacle_excel(
            Path(source_file_path).read_bytes()
        )
        obstacle_payloads = []
        for obstacle in parsed_obstacles:
            built_geometry = build_multipolygon_geometry(obstacle)
            obstacle_payloads.append(
                {
                    "name": obstacle.name,
                    "top_elevation": obstacle.top_elevation,
                    "source_row_numbers": [point.row_number for point in obstacle.points],
                    "geometry_wkt": built_geometry.wkt,
                    "raw_payload": {
                        "sourceRowNumbers": [
                            point.row_number for point in obstacle.points
                        ],
                        "geometry": {
                            "type": "MultiPolygon",
                            "coordinates": built_geometry.coordinates,
                        },
                        "points": [
                            {
                                "rowNumber": point.row_number,
                                "longitudeText": point.longitude_text,
                                "latitudeText": point.latitude_text,
                                "longitudeDecimal": point.longitude_decimal,
                                "latitudeDecimal": point.latitude_decimal,
                            }
                            for point in obstacle.points
                        ],
                    },
                }
            )

        self._repository.create_obstacles(
            project_id=import_batch.project_id,
            obstacle_type=import_batch.import_type or "",
            source_batch_id=import_batch.id,
            obstacles=obstacle_payloads,
        )
        self._repository.mark_import_batch_succeeded(import_batch.id)

    # 执行点状导入批次并写入障碍物数据。
    def _run_point_import_batch(self, import_batch: object) -> None:
        source_file_path = import_batch.source_file_path
        if not source_file_path:
            raise PointObstacleExcelParseError("missing import source file path")

        parsed_obstacles = parse_point_obstacle_excel(Path(source_file_path).read_bytes())
        obstacle_payloads = []
        for obstacle in parsed_obstacles:
            obstacle_payloads.append(
                {
                    "name": obstacle.name,
                    "top_elevation": obstacle.top_elevation,
                    "source_row_numbers": [obstacle.row_number],
                    "geometry_wkt": (
                        f"POINT ({obstacle.longitude_decimal} {obstacle.latitude_decimal})"
                    ),
                    "raw_payload": {
                        "sourceRowNumbers": [obstacle.row_number],
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                obstacle.longitude_decimal,
                                obstacle.latitude_decimal,
                            ],
                        },
                        "point": {
                            "rowNumber": obstacle.row_number,
                            "longitudeText": obstacle.longitude_text,
                            "latitudeText": obstacle.latitude_text,
                            "longitudeDecimal": obstacle.longitude_decimal,
                            "latitudeDecimal": obstacle.latitude_decimal,
                        },
                    },
                }
            )

        self._repository.create_obstacles(
            project_id=import_batch.project_id,
            obstacle_type=import_batch.import_type or "",
            source_batch_id=import_batch.id,
            obstacles=obstacle_payloads,
        )
        self._repository.mark_import_batch_succeeded(import_batch.id)

    # 查询导入任务的当前状态。
    def get_import_task_status(self, task_id: str) -> ImportTaskStatusResponse | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        return ImportTaskStatusResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            message=import_batch.status_message or "import task created",
            progressPercent=import_batch.progress_percent,
            projectId=import_batch.project_id,
            obstacleBatchId=import_batch.id,
        )

    # 查询导入任务的结果详情。
    def get_import_task_result(self, task_id: str) -> ImportTaskResultResponse | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        obstacles = self._repository.list_obstacles_by_batch_id(import_batch.id)

        return ImportTaskResultResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            projectId=import_batch.project_id,
            obstacleBatchId=import_batch.id,
            importedCount=len(obstacles),
            failedCount=0,
            boundingBox=None,
            obstacles=[
                self._build_imported_obstacle_response(obstacle)
                for obstacle in obstacles
            ],
        )

    # 返回初始化页面所需的机场和历史障碍物数据。
    def get_bootstrap(self) -> BootstrapResponse:
        airports = self._repository.list_airports_with_coordinates()
        obstacles = self._repository.list_all_obstacles()

        return BootstrapResponse(
            airports=[
                BootstrapAirportResponse(
                    id=airport.id,
                    name=airport.name,
                    longitude=float(airport.longitude),
                    latitude=float(airport.latitude),
                    stations=[
                        BootstrapStationResponse(
                            id=station.id,
                            name=station.name,
                            stationType=station.station_type,
                            longitude=float(station.longitude),
                            latitude=float(station.latitude),
                            altitude=(
                                float(station.altitude)
                                if station.altitude is not None
                                else None
                            ),
                        )
                        for station in self._repository.list_stations_by_airport_id(
                            airport.id
                        )
                        if station.longitude is not None
                        and station.latitude is not None
                    ],
                )
                for airport in airports
            ],
            historicalObstacles=[
                self._build_imported_obstacle_response(obstacle)
                for obstacle in obstacles
            ],
        )

    # 查询导入任务关联的候选机场列表。
    def get_import_targets(self, task_id: str) -> list[ImportTargetResponse] | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        obstacles = self._repository.list_obstacles_by_batch_id(import_batch.id)
        obstacle_geometries: list[dict[str, object]] = []
        for obstacle in obstacles:
            raw_payload = (
                obstacle["raw_payload"]
                if isinstance(obstacle, dict)
                else obstacle.raw_payload
            )
            obstacle_geometries.append(raw_payload["geometry"])

        targets: list[ImportTargetResponse] = []
        for airport in self._repository.list_airports():
            if airport.longitude is None or airport.latitude is None:
                continue

            station_points = [
                (float(station.longitude), float(station.latitude))
                for station in self._repository.list_stations_by_airport_id(airport.id)
                if station.longitude is not None and station.latitude is not None
            ]

            distance_km = calculate_minimum_target_distance_km(
                station_points=station_points,
                obstacle_geometries=obstacle_geometries,
            )
            targets.append(
                ImportTargetResponse(
                    id=airport.id,
                    name=airport.name,
                    category="机场",
                    distance=distance_km,
                    distanceUnit="km",
                )
            )

        return sorted(targets, key=lambda target: (target.distance, target.id))

    # 投递导入异步任务到运行时调度器。
    def _dispatch_import_task(self, task_id: str) -> None:
        if runtime.dispatch_import_task is not None:
            runtime.dispatch_import_task(task_id)

    # 将上传的导入文件保存到任务目录。
    def _store_import_file(
        self,
        *,
        task_id: str,
        file_name: str,
        file_bytes: bytes,
    ) -> str:
        if runtime.settings is None:
            raise RuntimeError("application settings are not initialized")

        storage_dir = runtime.settings.import_storage_dir
        task_directory = storage_dir / task_id
        task_directory.mkdir(parents=True, exist_ok=True)
        sanitized_name = self._sanitize_file_name(file_name)
        file_path = task_directory / sanitized_name
        file_path.write_bytes(file_bytes)
        return str(file_path.resolve())

    # 清洗上传文件名以避免非法路径字符。
    def _sanitize_file_name(self, file_name: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", file_name).strip("._")
        return sanitized or "import.xlsx"

    # 创建新的障碍物分析任务。
    def create_analysis_task(
        self, payload: AnalysisTaskCreateRequest
    ) -> AnalysisTaskStatusResponse | None:
        import_batch = self._repository.get_import_batch(payload.import_task_id)
        if import_batch is None:
            return None

        analysis_task_id = self._build_analysis_task_id()
        analysis_task = self._repository.create_analysis_task(
            task_id=analysis_task_id,
            import_batch_id=import_batch.id,
            selected_target_ids=payload.target_ids,
        )
        self._dispatch_analysis_task(analysis_task.id)

        return AnalysisTaskStatusResponse(
            analysisTaskId=analysis_task_id,
            status=analysis_task.status,
            message=analysis_task.status_message,
            progressPercent=analysis_task.progress_percent,
            importTaskId=import_batch.id,
            targetIds=payload.target_ids,
        )

    # 执行分析任务并生成最小分析结果。
    def run_analysis_task(self, task_id: str) -> None:
        analysis_task = self._repository.mark_analysis_task_running(task_id)
        if analysis_task is None:
            return

        try:
            selected_airports = self._repository.list_airports_by_ids(
                analysis_task.selected_target_ids
            )
            selected_targets = [
                {"id": airport.id, "name": airport.name, "category": "机场"}
                for airport in selected_airports
            ]
            contexts = build_airport_analysis_context(
                repository=self._repository,
                airport_ids=analysis_task.selected_target_ids,
                import_batch_id=analysis_task.import_batch_id,
            )
            airport_facts = [
                self._build_airport_analysis_result(context) for context in contexts
            ]
            protection_zones = [
                self._build_protection_zone_payload(
                    airport_id=context.airport.id,
                    airport_name=context.airport.name,
                    projector=AirportLocalProjector(
                        float(context.airport.longitude),
                        float(context.airport.latitude),
                    ),
                    station_altitude_by_id={
                        station.id: float(station.altitude or 0.0)
                        for station in context.stations
                    },
                    station_name_by_id={station.id: station.name for station in context.stations},
                    station_coordinates_by_id={
                        station.id: (
                            float(station.longitude),
                            float(station.latitude),
                        )
                        for station in context.stations
                        if station.longitude is not None and station.latitude is not None
                    },
                    runway_name_by_id={
                        runway.id: runway.run_number or str(runway.id)
                        for runway in context.runways
                    },
                    protection_zone=protection_zone,
                )
                for context, airport_fact in zip(contexts, airport_facts, strict=False)
                for protection_zone in airport_fact.get("protectionZones", [])
            ]
            obstacle_count = len(
                self._repository.list_obstacles_by_batch_id(
                    analysis_task.import_batch_id
                )
            )
            self._repository.mark_analysis_task_succeeded(
                task_id,
                {
                    "selectedTargets": selected_targets,
                    "obstacleCount": obstacle_count,
                    "summary": "已完成局部坐标系与最小空间事实计算。",
                    "ruleResults": [
                        self._build_public_rule_result_payload(rule_result)
                        for airport_fact in airport_facts
                        for rule_result in airport_fact.get("ruleResults", [])
                    ],
                    "protectionZones": protection_zones,
                },
            )
        except Exception as exc:
            self._repository.mark_analysis_task_failed(task_id, str(exc))

    # 构建单个机场的分析结果载荷。
    def _build_airport_analysis_result(self, context: object) -> dict[str, object]:
        airport_facts = build_airport_spatial_facts(context)
        airport_facts.pop("stationCount", None)
        airport_facts.pop("stations", None)
        airport = context.airport
        projector = AirportLocalProjector(
            float(airport.longitude), float(airport.latitude)
        )
        dispatcher = StationAnalysisDispatcher()
        runway_contexts = self._build_runway_contexts(
            projector=projector,
            runways=context.runways,
        )
        rule_results: list[dict[str, object]] = []
        protection_zones: list[ProtectionZoneSpec] = []

        for station in context.stations:
            if station.longitude is None or station.latitude is None:
                continue

            station_point = projector.project_point(
                float(station.longitude),
                float(station.latitude),
            )
            station_results = dispatcher.analyze_station(
                station=station,
                obstacles=airport_facts["obstacles"],
                station_point=station_point,
                runways=runway_contexts,
            )
            rule_results.extend(
                [
                    self._build_rule_result_payload(
                        result=result,
                        station_name=station.name,
                    )
                    for result in station_results.rule_results
                ]
            )
            protection_zones.extend(station_results.protection_zones)

        # === 跑道级分析：机场电磁环境保护区 ===
        for rw_ctx in runway_contexts:
            pz_spec = build_runway_em_protection_zone(projector, rw_ctx)
            if pz_spec is None:
                continue
            protection_zones.append(pz_spec)
            for obs in airport_facts["obstacles"]:
                rr = build_runway_em_rule_result(obs, pz_spec)
                rule_results.append(
                    self._build_rule_result_payload(
                        result=rr,
                        station_name=f"跑道-{rw_ctx.get('runNumber', '')}",
                    )
                )

        airport_facts["ruleResults"] = rule_results
        airport_facts["protectionZones"] = protection_zones
        return airport_facts

    # 构建机场下全部 LOC 规则所需的跑道上下文。
    def _build_runway_contexts(
        self,
        *,
        projector: AirportLocalProjector,
        runways: list[object],
    ) -> list[dict[str, object]]:
        runway_contexts: list[dict[str, object]] = []
        for runway in runways:
            if (
                runway.longitude is None
                or runway.latitude is None
                or runway.direction is None
                or runway.length is None
            ):
                continue

            runway_contexts.append(
                {
                    "runwayId": runway.id,
                    "runNumber": runway.run_number,
                    "localCenterPoint": projector.project_point(
                        float(runway.longitude),
                        float(runway.latitude),
                    ),
                    "directionDegrees": float(runway.direction),
                    "lengthMeters": float(runway.length),
                    "widthMeters": float(runway.width or 0.0),
                    "maximumAirworthiness": (
                        float(runway.maximum_airworthiness)
                        if runway.maximum_airworthiness is not None
                        else None
                    ),
                    "runwayCodeB": getattr(runway, "runway_code_b", None),
                    "altitude": float(getattr(runway, "altitude", 0) or 0.0),
                }
            )
        return runway_contexts

    # 将规则结果序列化为 analysis API 输出项。
    def _build_rule_result_payload(
        self,
        *,
        result: object,
        station_name: str,
    ) -> dict[str, object]:
        standards = build_rule_standards(
            station_type=result.station_type,
            rule_name=str(result.standards_rule_code or result.rule_code),
            region_code=result.region_code,
        )
        return {
            "stationId": result.station_id,
            "stationName": station_name,
            "stationType": result.station_type,
            "obstacleId": result.obstacle_id,
            "obstacleName": result.obstacle_name,
            "rawObstacleType": result.raw_obstacle_type,
            "globalObstacleCategory": result.global_obstacle_category,
            "ruleCode": result.rule_code,
            "ruleName": result.rule_name,
            "zoneCode": result.zone_code,
            "zoneName": result.zone_name,
            "regionCode": result.region_code,
            "regionName": result.region_name,
            "isApplicable": result.is_applicable,
            "isCompliant": result.is_compliant,
            "message": result.message,
            "metrics": result.metrics,
            "standardsRuleCode": result.standards_rule_code,
            "overDistanceMeters": result.over_distance_meters,
            "azimuthDegrees": result.azimuth_degrees,
            "maxHorizontalAngleDegrees": result.max_horizontal_angle_degrees,
            "minHorizontalAngleDegrees": result.min_horizontal_angle_degrees,
            "relativeHeightMeters": result.relative_height_meters,
            "isInRadius": result.is_in_radius,
            "isInZone": result.is_in_zone,
            "details": result.details,
            "standards": {
                "gb": (
                    [
                        {
                            "code": s.code,
                            "text": s.text,
                            "isCompliant": result.is_compliant,
                        }
                        for s in standards.gb
                    ]
                    if standards.gb
                    else None
                ),
                "mh": (
                    [
                        {
                            "code": s.code,
                            "text": s.text,
                            "isCompliant": result.is_compliant,
                        }
                        for s in standards.mh
                    ]
                    if standards.mh
                    else None
                ),
            },
        }

    # 将内部规则结果裁剪为对外 analysis API 输出项。
    def _build_public_rule_result_payload(
        self, rule_result: dict[str, object]
    ) -> dict[str, object]:
        return {
            key: value
            for key, value in rule_result.items()
            if key != "standardsRuleCode"
        }

    # 将保护区规格转换为对外 analysis API 输出项。
    def _build_protection_zone_payload(
        self,
        *,
        airport_id: int,
        airport_name: str,
        projector: AirportLocalProjector,
        station_altitude_by_id: dict[int, float],
        station_name_by_id: dict[int, str],
        station_coordinates_by_id: dict[int, tuple[float, float]],
        runway_name_by_id: dict[int, str] | None = None,
        protection_zone: ProtectionZoneSpec,
    ) -> dict[str, object]:
        is_runway_zone = protection_zone.runway_id is not None
        if is_runway_zone:
            runway_id = protection_zone.runway_id
            station_name = (
                f"跑道-{runway_name_by_id.get(runway_id, str(runway_id))}"
                if runway_name_by_id
                else f"跑道-{runway_id}"
            )
            station_altitude = 0.0
            station_wgs84 = None
        else:
            station_name = station_name_by_id.get(
                protection_zone.station_id,
                f"station-{protection_zone.station_id}",
            )
            station_altitude = station_altitude_by_id.get(
                protection_zone.station_id,
                0.0,
            )
            station_wgs84 = station_coordinates_by_id.get(protection_zone.station_id)
        zone_id_prefix = (
            f"airport-{airport_id}-runway-{protection_zone.runway_id}"
            if is_runway_zone
            else f"airport-{airport_id}-station-{protection_zone.station_id}"
        )
        return {
            "id": (
                f"{zone_id_prefix}-"
                f"zone-{protection_zone.zone_code}-region-{protection_zone.region_code}"
            ),
            "airportId": airport_id,
            "airportName": airport_name,
            "stationId": protection_zone.station_id,
            "stationName": station_name,
            "stationType": protection_zone.station_type,
            "ruleCode": protection_zone.rule_code,
            "ruleName": protection_zone.rule_name,
            "zoneCode": protection_zone.zone_code,
            "zoneName": protection_zone.zone_name,
            "regionCode": protection_zone.region_code,
            "regionName": protection_zone.region_name,
            "style": resolve_protection_zone_style(
                zone_code=protection_zone.zone_code,
                region_code=protection_zone.region_code,
            ),
            "properties": {
                "label": (
                    f"{station_name} {protection_zone.zone_name} "
                    f"{protection_zone.region_name}"
                )
            },
            "geometry": self._build_public_protection_zone_geometry_payload(
                projector=projector,
                geometry_definition=protection_zone.geometry_definition,
            ),
            "vertical": self._build_public_protection_zone_vertical_payload(
                projector=projector,
                vertical_definition=protection_zone.vertical_definition,
                station_altitude_meters=station_altitude,
                station_wgs84=station_wgs84,
            ),
            "renderGeometry": protection_zone.render_geometry,
        }

    # 将规则侧局部 multipolygon 几何反投影为对外 WGS84 坐标。
    def _build_public_protection_zone_geometry_payload(
        self,
        *,
        projector: AirportLocalProjector,
        geometry_definition: dict[str, object],
    ) -> dict[str, object]:
        if geometry_definition.get("shapeType") != "multipolygon":
            raise ValueError("protection zone geometry must be multipolygon")
        coordinates = geometry_definition.get("coordinates")
        if not isinstance(coordinates, list):
            raise ValueError("protection zone geometry coordinates must be a list")

        return {
            "shapeType": "multipolygon",
            "coordinates": [
                [
                    [
                        [float(longitude), float(latitude)]
                        for longitude, latitude in (
                            projector.unproject_point(float(point[0]), float(point[1]))
                            for point in ring
                        )
                    ]
                    for ring in polygon
                ]
                for polygon in coordinates
            ],
        }

    # 将内部保护区垂向结构转换为对外 API 稳定结构。
    def _build_public_protection_zone_vertical_payload(
        self,
        *,
        projector: AirportLocalProjector,
        vertical_definition: dict[str, object],
        station_altitude_meters: float,
        station_wgs84: tuple[float, float] | None = None,
    ) -> dict[str, object]:
        if vertical_definition.get("mode") != "analytic_surface":
            payload = vertical_definition.copy()
            if payload.get("mode") != "flat":
                raise ValueError("unsupported protection zone vertical mode")
            base_reference = payload.get("baseReference", "station")
            base_height_meters = payload.get("baseHeightMeters")
            if (
                base_reference == "station"
                and base_height_meters in (None, 0, 0.0)
            ):
                payload["baseHeightMeters"] = float(station_altitude_meters)
            else:
                payload["baseHeightMeters"] = float(base_height_meters or 0.0)
            return payload

        surface = vertical_definition.get("surface")
        if not isinstance(surface, dict):
            raise ValueError("analytic surface definition must contain surface")

        surface_type = str(surface.get("type") or "")
        if surface_type == "loc_building_restriction_zone_region_3":
            station_point = self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=surface.get("stationPoint"),
                field_name="stationPoint",
            )
            apex_point = self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=surface.get("apexPoint"),
                field_name="apexPoint",
            )
            root_left_point = self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=surface.get("rootLeftPoint"),
                field_name="rootLeftPoint",
            )
            root_right_point = self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=surface.get("rootRightPoint"),
                field_name="rootRightPoint",
            )
            arc_points = self._build_public_protection_zone_surface_points_payload(
                projector=projector,
                points=surface.get("arcPoints"),
                field_name="arcPoints",
            )
            return {
                "mode": "analytic_surface",
                "baseReference": vertical_definition.get("baseReference", "station"),
                "baseHeightMeters": float(
                    vertical_definition.get("baseHeightMeters", 0.0)
                ),
                "surface": {
                    "type": surface_type,
                    "arcHeightMeters": float(surface.get("arcHeightMeters", 0.0)),
                    "alphaDegrees": float(surface.get("alphaDegrees", 0.0)),
                    "stationPoint": station_point,
                    "apexPoint": apex_point,
                    "rootLeftPoint": root_left_point,
                    "rootRightPoint": root_right_point,
                    "arcRadiusMeters": float(surface.get("arcRadiusMeters", 0.0)),
                    "arcPoints": arc_points,
                },
            }

        distance_source = surface.get("distanceSource")
        clamp_range = surface.get("clampRange")
        height_model = surface.get("heightModel")
        if (
            not isinstance(distance_source, dict)
            or not isinstance(clamp_range, dict)
            or not isinstance(height_model, dict)
        ):
            raise ValueError("analytic surface definition is incomplete")

        distance_source_kind = str(distance_source.get("kind") or "point")
        height_model_type = str(height_model.get("type") or "")
        if distance_source_kind == "front_reference_line":
            front_reference_line_points = (
                self._build_public_front_reference_line_distance_source_points_payload(
                    projector=projector,
                    station_wgs84=station_wgs84,
                    front_left_point=distance_source.get("frontLeftPoint"),
                    front_right_point=distance_source.get("frontRightPoint"),
                )
            )
            return {
                "mode": "analytic_surface",
                "baseReference": vertical_definition.get("baseReference", "station"),
                "baseHeightMeters": float(
                    vertical_definition.get("baseHeightMeters", 0.0)
                ),
                "surface": {
                    "type": self._resolve_public_analytic_surface_type(surface),
                    "distanceSource": {
                        "kind": "front_reference_line",
                        **front_reference_line_points,
                    },
                    "distanceMetric": "axial_from_reference_line",
                    "planarControl": {
                        "frontOffsetMeters": float(
                            clamp_range.get("startMeters", 0.0)
                            + height_model.get("distanceOffsetMeters", 0.0)
                            + 360.0
                        ),
                        "halfAngleDegrees": 8.0,
                        "radiusMeters": float(
                            clamp_range.get("endMeters", 0.0)
                            + clamp_range.get("startMeters", 0.0)
                            + height_model.get("distanceOffsetMeters", 0.0)
                            + 360.0
                        ),
                    },
                    "clampRange": {
                        "startMeters": float(clamp_range.get("startMeters", 0.0)),
                        "endMeters": float(clamp_range.get("endMeters", 0.0)),
                    },
                    "heightModel": {
                        "type": "angle_linear_rise",
                        "angleDegrees": float(height_model.get("angleDegrees", 0.0)),
                        "distanceOffsetMeters": float(
                            height_model.get("distanceOffsetMeters", 0.0)
                        ),
                    },
                },
            }

        if height_model_type == "radar_site_protection_mask_angle":
            return {
                "mode": "analytic_surface",
                "baseReference": vertical_definition.get("baseReference", "station"),
                "baseHeightMeters": float(vertical_definition.get("baseHeightMeters", 0.0)),
                "surface": {
                    "type": self._resolve_public_analytic_surface_type(surface),
                    "distanceSource": {
                        "kind": distance_source_kind,
                        "point": distance_source.get("point"),
                    },
                    "distanceMetric": "radial",
                    "clampRange": {
                        "startMeters": float(clamp_range.get("startMeters", 0.0)),
                        "endMeters": float(clamp_range.get("endMeters", 0.0)),
                    },
                    "heightModel": {
                        "type": "radar_site_protection_mask_angle",
                        "maskAngleDegrees": float(height_model.get("maskAngleDegrees", 0.0)),
                        "distanceOffsetMeters": float(
                            height_model.get("distanceOffsetMeters", 0.0)
                        ),
                        "distanceKilometersCorrectionDivisor": float(
                            height_model.get("distanceKilometersCorrectionDivisor", 16970.0)
                        ),
                    },
                },
            }

        return {
            "mode": "analytic_surface",
            "baseReference": vertical_definition.get("baseReference", "station"),
            "baseHeightMeters": float(vertical_definition.get("baseHeightMeters", 0.0)),
            "surface": {
                "type": self._resolve_public_analytic_surface_type(surface),
                "distanceSource": {
                    "kind": distance_source_kind,
                    "point": distance_source.get("point"),
                },
                "distanceMetric": "radial",
                "clampRange": {
                    "startMeters": float(clamp_range.get("startMeters", 0.0)),
                    "endMeters": float(clamp_range.get("endMeters", 0.0)),
                },
                "heightModel": {
                    "type": "angle_linear_rise",
                    "angleDegrees": float(height_model.get("angleDegrees", 0.0)),
                    "distanceOffsetMeters": float(
                        height_model.get("distanceOffsetMeters", 0.0)
                    ),
                },
            },
        }

    # 统一解析对外 analytic surface 类型，避免各分支漂移。
    def _resolve_public_analytic_surface_type(
        self,
        surface: dict[str, object],
    ) -> str:
        if surface.get("type") == "radial_cone_surface":
            return "radial_cone_surface"
        return "distance_parameterized"

    # 将局部平面控制点反投影为对外 WGS84 点坐标。
    def _build_public_protection_zone_surface_point_payload(
        self,
        *,
        projector: AirportLocalProjector,
        point: object,
        field_name: str,
    ) -> list[float]:
        if (
            not isinstance(point, (list, tuple))
            or len(point) != 2
        ):
            raise ValueError(f"{field_name} must contain two coordinates")
        longitude, latitude = projector.unproject_point(
            float(point[0]),
            float(point[1]),
        )
        return [float(longitude), float(latitude)]

    # 将 GP 前参考线控制点转换为对外稳定展示点位。
    def _build_public_front_reference_line_distance_source_points_payload(
        self,
        *,
        projector: AirportLocalProjector,
        station_wgs84: tuple[float, float] | None,
        front_left_point: object,
        front_right_point: object,
    ) -> dict[str, list[float]]:
        left_local_point = self._validate_surface_local_point(
            point=front_left_point,
            field_name="frontLeftPoint",
        )
        right_local_point = self._validate_surface_local_point(
            point=front_right_point,
            field_name="frontRightPoint",
        )
        center_local_point = (
            (left_local_point[0] + right_local_point[0]) / 2.0,
            (left_local_point[1] + right_local_point[1]) / 2.0,
        )

        if station_wgs84 is None:
            left_point = self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=left_local_point,
                field_name="frontLeftPoint",
            )
            right_point = self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=right_local_point,
                field_name="frontRightPoint",
            )
            center_point = [
                float((left_point[0] + right_point[0]) / 2.0),
                float((left_point[1] + right_point[1]) / 2.0),
            ]
            return {
                "stationPoint": center_point,
                "centerPoint": center_point,
                "leftPoint": left_point,
                "rightPoint": right_point,
            }

        station_local_x, station_local_y = projector.project_point(*station_wgs84)
        center_latitude = self._build_public_front_reference_line_axis_latitude(
            station_latitude=station_wgs84[1],
            local_y=center_local_point[1] - station_local_y,
        )
        return {
            "stationPoint": [float(station_wgs84[0]), float(station_wgs84[1])],
            "centerPoint": self._build_public_front_reference_line_axis_point(
                station_wgs84=station_wgs84,
                local_point=center_local_point,
                station_local_x=station_local_x,
                center_latitude=center_latitude,
            ),
            "leftPoint": self._build_public_front_reference_line_axis_point(
                station_wgs84=station_wgs84,
                local_point=left_local_point,
                station_local_x=station_local_x,
                center_latitude=center_latitude,
            ),
            "rightPoint": self._build_public_front_reference_line_axis_point(
                station_wgs84=station_wgs84,
                local_point=right_local_point,
                station_local_x=station_local_x,
                center_latitude=center_latitude,
            ),
        }

    # 将 GP 前参考线局部点转换为展示用 WGS84 点。
    def _build_public_front_reference_line_axis_point(
        self,
        *,
        station_wgs84: tuple[float, float],
        local_point: tuple[float, float],
        station_local_x: float,
        center_latitude: float,
    ) -> list[float]:
        longitude = round(
            station_wgs84[0] + (local_point[0] - station_local_x) / 99800.0,
            6,
        )
        return [float(longitude), float(center_latitude)]

    # 计算 GP 前参考线展示点共用纬度。
    def _build_public_front_reference_line_axis_latitude(
        self,
        *,
        station_latitude: float,
        local_y: float,
    ) -> float:
        return float(round(station_latitude + local_y / 111180.0, 6))

    # 校验并标准化局部平面控制点。
    def _validate_surface_local_point(
        self,
        *,
        point: object,
        field_name: str,
    ) -> tuple[float, float]:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"{field_name} must contain two coordinates")
        return float(point[0]), float(point[1])

    # 将局部平面控制点列表反投影为对外 WGS84 点坐标列表。
    def _build_public_protection_zone_surface_points_payload(
        self,
        *,
        projector: AirportLocalProjector,
        points: object,
        field_name: str,
    ) -> list[list[float]]:
        if not isinstance(points, list):
            raise ValueError(f"{field_name} must be a list")
        return [
            self._build_public_protection_zone_surface_point_payload(
                projector=projector,
                point=point,
                field_name=field_name,
            )
            for point in points
        ]

    # 查询分析任务的当前状态。
    def get_analysis_task_status(
        self, task_id: str
    ) -> AnalysisTaskStatusResponse | None:
        analysis_task = self._repository.get_analysis_task(task_id)
        if analysis_task is None:
            return None

        return AnalysisTaskStatusResponse(
            analysisTaskId=analysis_task.id,
            status=analysis_task.status,
            message=analysis_task.status_message,
            progressPercent=analysis_task.progress_percent,
            importTaskId=analysis_task.import_batch_id,
            targetIds=analysis_task.selected_target_ids,
        )

    # 查询分析任务的结果详情。
    def get_analysis_task_result(
        self, task_id: str
    ) -> AnalysisTaskResultResponse | None:
        analysis_task = self._repository.get_analysis_task(task_id)
        if analysis_task is None:
            return None

        result_payload = analysis_task.result_payload or {}
        rule_results = []
        for item in result_payload.get("ruleResults", []):
            rule_results.append(
                self._compat_rule_result_payload(item)
            )
        return AnalysisTaskResultResponse(
            analysisTaskId=analysis_task.id,
            status=analysis_task.status,
            importTaskId=analysis_task.import_batch_id,
            targetIds=analysis_task.selected_target_ids,
            selectedTargets=[
                AnalysisResultTargetResponse(**target)
                for target in result_payload.get("selectedTargets", [])
            ],
            obstacleCount=result_payload.get("obstacleCount", 0),
            summary=result_payload.get("summary", ""),
            ruleResults=[
                AnalysisRuleResultResponse(**item)
                for item in rule_results
            ],
            protectionZones=[
                AnalysisProtectionZoneResponse(**item)
                for item in result_payload.get("protectionZones", [])
            ],
        )

    # 兼容历史 payload 中旧版字段格式。
    def _compat_rule_result_payload(
        self, item: dict
    ) -> dict:
        result = dict(item)
        result.setdefault("overDistanceMeters", 0.0)
        result.setdefault("azimuthDegrees", 0.0)
        result.setdefault("maxHorizontalAngleDegrees", 0.0)
        result.setdefault("minHorizontalAngleDegrees", 0.0)
        result.setdefault("relativeHeightMeters", 0.0)
        result.setdefault("isInRadius", False)
        result.setdefault("isInZone", False)
        result.setdefault("details", "")
        standards = result.get("standards")
        if not isinstance(standards, dict):
            return result
        compat_standards: dict[str, object] = {}
        for key in ("gb", "mh"):
            value = standards.get(key)
            if isinstance(value, dict):
                compat_standards[key] = [value]
            elif isinstance(value, list):
                compat_standards[key] = value
            else:
                compat_standards[key] = None
        result["standards"] = compat_standards
        return result

    # 投递分析异步任务到运行时调度器。
    def _dispatch_analysis_task(self, task_id: str) -> None:
        if runtime.dispatch_analysis_task is not None:
            runtime.dispatch_analysis_task(task_id)

    # 创建新的分析报告导出任务。
    def create_export_task(
        self, analysis_task_id: str
    ) -> ExportTaskStatusResponse | None:
        analysis_task = self._repository.get_analysis_task(analysis_task_id)
        if analysis_task is None:
            return None
        if analysis_task.status != "succeeded":
            raise ValueError("analysis task is not ready for export")

        export_task_id = self._build_export_task_id()
        report_export = self._repository.create_report_export(
            task_id=export_task_id,
            analysis_task_id=analysis_task_id,
        )
        self._dispatch_export_task(report_export.id)
        return ExportTaskStatusResponse(
            exportTaskId=report_export.id,
            analysisTaskId=analysis_task_id,
            status=report_export.status,
            message=report_export.status_message,
            progressPercent=report_export.progress_percent,
        )

    # 执行导出任务并生成报告文件。
    def run_export_task(self, task_id: str) -> None:
        report_export = self._repository.mark_report_export_running(task_id)
        if report_export is None:
            return

        try:
            analysis_task = self._repository.get_analysis_task(
                report_export.analysis_task_id
            )
            if analysis_task is None or analysis_task.status != "succeeded":
                raise ValueError("analysis task is not ready for export")

            payload = build_export_payload(analysis_task)
            file_path, file_name = self._build_export_output_path(
                task_id=task_id,
                analysis_task_id=analysis_task.id,
            )
            build_analysis_report_docx(payload, file_path)
            self._repository.mark_report_export_succeeded(
                task_id,
                file_name=file_name,
                file_path=str(file_path.resolve()),
            )
        except Exception as exc:
            self._repository.mark_report_export_failed(task_id, str(exc))

    # 查询导出任务的当前状态。
    def get_export_task_status(
        self, analysis_task_id: str, export_task_id: str
    ) -> ExportTaskStatusResponse | None:
        report_export = self._repository.get_report_export(export_task_id)
        if report_export is None or report_export.analysis_task_id != analysis_task_id:
            return None

        return ExportTaskStatusResponse(
            exportTaskId=report_export.id,
            analysisTaskId=report_export.analysis_task_id,
            status=report_export.status,
            message=report_export.status_message,
            progressPercent=report_export.progress_percent,
        )

    # 查询导出任务的结果详情。
    def get_export_task_result(
        self, analysis_task_id: str, export_task_id: str
    ) -> ExportTaskResultResponse | None:
        report_export = self._repository.get_report_export(export_task_id)
        if report_export is None or report_export.analysis_task_id != analysis_task_id:
            return None

        return ExportTaskResultResponse(
            exportTaskId=report_export.id,
            analysisTaskId=report_export.analysis_task_id,
            status=report_export.status,
            fileName=report_export.file_name,
            downloadUrl=(
                f"/polygon-obstacle/exports/{report_export.id}/download"
                if report_export.status == "succeeded" and report_export.file_path
                else None
            ),
            errorMessage=report_export.error_message,
        )

    # 返回可下载导出文件的路径和文件名。
    def get_export_download(self, export_task_id: str) -> tuple[str, str] | None:
        report_export = self._repository.get_report_export(export_task_id)
        if (
            report_export is None
            or report_export.status != "succeeded"
            or not report_export.file_path
            or not report_export.file_name
        ):
            return None

        file_path = Path(report_export.file_path)
        if not file_path.exists():
            return None
        return str(file_path), report_export.file_name

    # 生成新的分析任务编号。
    def _build_analysis_task_id(self) -> str:
        existing_task = self._repository.get_analysis_task("analysis-task-1")
        if existing_task is None:
            return "analysis-task-1"

        next_suffix = 1
        while (
            self._repository.get_analysis_task(f"analysis-task-{next_suffix}")
            is not None
        ):
            next_suffix += 1
        return f"analysis-task-{next_suffix}"

    # 投递导出异步任务到运行时调度器。
    def _dispatch_export_task(self, task_id: str) -> None:
        if runtime.dispatch_export_task is not None:
            runtime.dispatch_export_task(task_id)

    # 生成新的导出任务编号。
    def _build_export_task_id(self) -> str:
        existing_task = self._repository.get_report_export("export-task-1")
        if existing_task is None:
            return "export-task-1"

        next_suffix = 1
        while (
            self._repository.get_report_export(f"export-task-{next_suffix}") is not None
        ):
            next_suffix += 1
        return f"export-task-{next_suffix}"

    # 生成导出报告文件的输出路径。
    def _build_export_output_path(
        self, *, task_id: str, analysis_task_id: str
    ) -> tuple[Path, str]:
        if runtime.settings is None:
            runtime.settings = Settings.from_env()

        export_directory = runtime.settings.export_storage_dir / task_id
        file_name = f"polygon-obstacle-analysis-{analysis_task_id}.docx"
        return export_directory / file_name, file_name

    # 将障碍物记录转换为统一响应对象。
    def _build_imported_obstacle_response(
        self,
        obstacle: object,
    ) -> ImportedObstacleResponse:
        if isinstance(obstacle, dict):
            raw_payload = obstacle["raw_payload"]
            return ImportedObstacleResponse(
                id=obstacle["id"],
                name=obstacle["name"],
                obstacleType=obstacle["obstacle_type"] or "",
                topElevation=float(obstacle["top_elevation"] or 0),
                sourceRowNumbers=raw_payload["sourceRowNumbers"],
                boundingBox=None,
                geometry=ImportedObstacleGeometryResponse(
                    type=raw_payload["geometry"]["type"],
                    coordinates=raw_payload["geometry"]["coordinates"],
                ),
            )

        raw_payload = obstacle.raw_payload
        return ImportedObstacleResponse(
            id=obstacle.id,
            name=obstacle.name,
            obstacleType=obstacle.obstacle_type or "",
            topElevation=float(obstacle.top_elevation or 0),
            sourceRowNumbers=raw_payload["sourceRowNumbers"],
            boundingBox=None,
            geometry=ImportedObstacleGeometryResponse(
                type=raw_payload["geometry"]["type"],
                coordinates=raw_payload["geometry"]["coordinates"],
            ),
        )
