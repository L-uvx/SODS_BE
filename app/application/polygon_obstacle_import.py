from pathlib import Path
import re

from sqlalchemy.orm import Session

from app.analysis.context_builder import build_airport_analysis_context
from app.analysis.local_coordinate import AirportLocalProjector
from app.analysis.protection_zone_builder import (
    build_protection_zone_geometry,
    build_protection_zone_vertical,
)
from app.analysis.spatial_facts import build_airport_spatial_facts
from app.analysis.station_dispatcher import StationAnalysisDispatcher
from app.analysis.standards import build_rule_standards
from app.application.polygon_obstacle_excel_parser import (
    PolygonObstacleExcelParseError,
    parse_polygon_obstacle_excel,
)
from app.application.polygon_obstacle_geometry import build_multipolygon_geometry
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
        project = self._repository.create_project(payload.project_name)
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
                        "source_row_numbers": [
                            point.row_number for point in obstacle.points
                        ],
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
            self._repository.mark_import_batch_succeeded(task_id)
        except PolygonObstacleExcelParseError as exc:
            self._repository.mark_import_batch_failed(task_id, str(exc))

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
                protection_zone
                for context, airport_fact in zip(contexts, airport_facts, strict=False)
                for protection_zone in self._build_airport_protection_zones(
                    context=context,
                    airport_facts=airport_fact,
                )
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
                        self._build_rule_result_payload(rule_result)
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
                    self._build_internal_rule_result_payload(
                        result=result,
                        station_name=station.name,
                    )
                    for result in station_results
                ]
            )

        airport_facts["ruleResults"] = rule_results
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
                }
            )
        return runway_contexts

    # 将规则结果序列化为 analysis API 输出项。
    def _build_internal_rule_result_payload(
        self,
        *,
        result: object,
        station_name: str,
    ) -> dict[str, object]:
        standards = build_rule_standards(
            station_type=result.station_type,
            rule_name=(
                "loc_site_protection_cable"
                if result.station_type == "LOC"
                and result.global_obstacle_category == "power_or_communication_cable"
                else result.rule_name
            ),
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
            "ruleName": result.rule_name,
            "zoneCode": result.zone_code,
            "zoneName": result.zone_name,
            "regionCode": result.region_code,
            "regionName": result.region_name,
            "zoneDefinition": result.zone_definition,
            "isApplicable": result.is_applicable,
            "isCompliant": result.is_compliant,
            "message": result.message,
            "metrics": result.metrics,
            "standards": {
                "gb": (
                    {
                        "code": standards.gb.code,
                        "text": standards.gb.text,
                        "isCompliant": result.is_compliant,
                    }
                    if standards.gb is not None
                    else None
                ),
                "mh": (
                    {
                        "code": standards.mh.code,
                        "text": standards.mh.text,
                        "isCompliant": result.is_compliant,
                    }
                    if standards.mh is not None
                    else None
                ),
            },
        }

    # 将内部规则结果裁剪为对外 analysis API 输出项。
    def _build_rule_result_payload(self, rule_result: dict[str, object]) -> dict[str, object]:
        return {
            key: value
            for key, value in rule_result.items()
            if key != "zoneDefinition"
        }

    # 汇总机场下各台站的保护区要素。
    def _build_airport_protection_zones(
        self,
        *,
        context: object,
        airport_facts: dict[str, object],
    ) -> list[dict[str, object]]:
        airport = context.airport
        projector = AirportLocalProjector(
            float(airport.longitude),
            float(airport.latitude),
        )
        stations_by_id = {station.id: station for station in context.stations}
        protection_zones: list[dict[str, object]] = []
        seen_keys: set[tuple[object, ...]] = set()

        for rule_result in airport_facts.get("ruleResults", []):
            rule_code = str(rule_result["ruleName"])
            key = (
                airport.id,
                rule_result["stationId"],
                rule_code,
                rule_result["zoneCode"],
                rule_result["regionCode"],
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)

            station = stations_by_id.get(rule_result["stationId"])
            if station is None or station.longitude is None or station.latitude is None:
                continue

            zone_definition = rule_result["zoneDefinition"]
            zone_feature = self._build_protection_zone_feature(
                airport=airport,
                projector=projector,
                station=station,
                rule_code=rule_code,
                rule_result=rule_result,
                zone_definition=zone_definition,
            )
            if zone_feature is None:
                continue

            protection_zones.append(zone_feature)

        return protection_zones

    # 将规则结果转换为保护区响应结构。
    def _build_protection_zone_feature(
        self,
        *,
        airport: object,
        projector: AirportLocalProjector,
        station: object,
        rule_code: str,
        rule_result: dict[str, object],
        zone_definition: dict[str, object],
    ) -> dict[str, object] | None:
        base_feature = {
            "id": (
                f"airport-{airport.id}-station-{station.id}-"
                f"zone-{rule_result['zoneCode']}-region-{rule_result['regionCode']}"
            ),
            "airportId": airport.id,
            "airportName": airport.name,
            "stationId": station.id,
            "stationName": station.name,
            "stationType": station.station_type,
            "ruleCode": rule_code,
            "ruleName": rule_result["ruleName"],
            "zoneCode": rule_result["zoneCode"],
            "zoneName": rule_result["zoneName"],
            "regionCode": rule_result["regionCode"],
            "regionName": rule_result["regionName"],
            "properties": {
                "label": (
                    f"{station.name} {rule_result['zoneName']} "
                    f"{rule_result['regionName']}"
                )
            },
            "renderGeometry": None,
        }

        station_local_point = projector.project_point(
            float(station.longitude),
            float(station.latitude),
        )
        geometry = build_protection_zone_geometry(
            projector=projector,
            center_point=station_local_point,
            zone_definition=zone_definition,
        )
        if geometry is None:
            return None

        metrics = rule_result["metrics"]
        shape = zone_definition.get("shape")
        if rule_code == "ndb_conical_clearance_3deg" and shape == "radial_band":
            vertical = build_protection_zone_vertical(
                shape="radial_band",
                zone_definition=zone_definition,
                distance_source_point=(
                    float(station.longitude),
                    float(station.latitude),
                ),
                base_height_meters=float(metrics["baseHeightMeters"]),
                elevation_angle_degrees=float(metrics["elevationAngleDegrees"]),
            )
        elif shape == "sector":
            vertical = {
                "mode": "analytic_surface",
                "baseReference": "station",
                "baseHeightMeters": float(metrics["baseHeightMeters"]),
                "heightFunction": {
                    "type": "elevation_angle",
                    "elevationAngleDegrees": float(metrics["elevationAngleDegrees"]),
                    "distanceMetric": "radial",
                    "startDistanceMeters": float(zone_definition["min_radius_m"]),
                    "endDistanceMeters": float(zone_definition["max_radius_m"]),
                },
            }
        elif shape in {"circle", "multipolygon", "radial_band"}:
            vertical = build_protection_zone_vertical(
                shape=shape,
                zone_definition=zone_definition,
                base_height_meters=float(station.altitude or 0.0),
            )
        else:
            return None

        if vertical is None:
            return None

        return {
            **base_feature,
            "geometry": geometry,
            "vertical": vertical,
        }

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
                for item in result_payload.get("ruleResults", [])
            ],
            protectionZones=[
                AnalysisProtectionZoneResponse(**item)
                for item in result_payload.get("protectionZones", [])
            ],
        )

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
