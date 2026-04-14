from sqlalchemy.orm import Session

from app.application.polygon_obstacle_excel_parser import parse_polygon_obstacle_excel
from app.application.polygon_obstacle_geometry import build_multipolygon_geometry
from app.application.polygon_obstacle_targets import (
    calculate_minimum_target_distance_km,
)
from app.repository.import_batch_repository import ImportBatchRepository
from app.schemas.polygon_obstacle import (
    AnalysisResultTargetResponse,
    AnalysisTaskCreateRequest,
    AnalysisTaskResultResponse,
    AnalysisTaskStatusResponse,
    BootstrapAirportResponse,
    BootstrapResponse,
    ImportedObstacleGeometryResponse,
    ImportedObstacleResponse,
    ImportTaskCreateRequest,
    ImportTaskResultResponse,
    ImportTaskStatusResponse,
    ImportTargetResponse,
)


class PolygonObstacleImportService:
    def __init__(self, session: Session) -> None:
        self._repository = ImportBatchRepository(session)

    def create_import_task(
        self, payload: ImportTaskCreateRequest
    ) -> ImportTaskStatusResponse:
        parsed_obstacles = parse_polygon_obstacle_excel(payload.file_bytes)
        project = self._repository.create_project(payload.project_name)
        task_id = f"import-batch-{project.id}"
        import_batch = self._repository.create_import_batch(
            task_id=task_id,
            project_id=project.id,
            obstacle_type=payload.obstacle_type,
            file_name=payload.file_name,
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
            project_id=project.id,
            obstacle_type=payload.obstacle_type,
            source_batch_id=import_batch.id,
            obstacles=obstacle_payloads,
        )

        return ImportTaskStatusResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            message="import task created",
            progressPercent=100,
            projectId=project.id,
            obstacleBatchId=import_batch.id,
        )

    def get_import_task_status(self, task_id: str) -> ImportTaskStatusResponse | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        return ImportTaskStatusResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            message="import task created",
            progressPercent=100,
            projectId=import_batch.project_id,
            obstacleBatchId=import_batch.id,
        )

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

    def get_bootstrap(self) -> BootstrapResponse:
        airport = self._repository.get_first_airport_with_coordinates()
        obstacles = self._repository.list_all_obstacles()

        return BootstrapResponse(
            airport=(
                BootstrapAirportResponse(
                    id=airport.id,
                    name=airport.name,
                    longitude=float(airport.longitude),
                    latitude=float(airport.latitude),
                )
                if airport is not None
                else None
            ),
            historicalObstacles=[
                self._build_imported_obstacle_response(obstacle)
                for obstacle in obstacles
            ],
        )

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

            distance_km = calculate_minimum_target_distance_km(
                airport_longitude=float(airport.longitude),
                airport_latitude=float(airport.latitude),
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

    def create_analysis_task(
        self, payload: AnalysisTaskCreateRequest
    ) -> AnalysisTaskStatusResponse | None:
        import_batch = self._repository.get_import_batch(payload.import_task_id)
        if import_batch is None:
            return None

        selected_airports = self._repository.list_airports_by_ids(payload.target_ids)
        selected_targets = [
            {"id": airport.id, "name": airport.name, "category": "机场"}
            for airport in selected_airports
        ]
        obstacle_count = len(
            self._repository.list_obstacles_by_batch_id(import_batch.id)
        )
        analysis_task_id = self._build_analysis_task_id()
        self._repository.create_analysis_task(
            task_id=analysis_task_id,
            import_batch_id=import_batch.id,
            selected_target_ids=payload.target_ids,
            result_payload={
                "selectedTargets": selected_targets,
                "obstacleCount": obstacle_count,
                "summary": "已基于当前导入障碍物和所选机场生成最小分析结果。",
            },
        )

        return AnalysisTaskStatusResponse(
            analysisTaskId=analysis_task_id,
            status="succeeded",
            message="analysis task created",
            progressPercent=100,
            importTaskId=import_batch.id,
            targetIds=payload.target_ids,
        )

    def get_analysis_task_status(
        self, task_id: str
    ) -> AnalysisTaskStatusResponse | None:
        analysis_task = self._repository.get_analysis_task(task_id)
        if analysis_task is None:
            return None

        return AnalysisTaskStatusResponse(
            analysisTaskId=analysis_task.id,
            status=analysis_task.status,
            message="analysis task created",
            progressPercent=100,
            importTaskId=analysis_task.import_batch_id,
            targetIds=analysis_task.selected_target_ids,
        )

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
        )

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
