from sqlalchemy.orm import Session

from app.application.polygon_obstacle_excel_parser import parse_polygon_obstacle_excel
from app.repository.import_batch_repository import ImportBatchRepository
from app.schemas.polygon_obstacle import (
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
        # Current slice only validates the uploaded template before persistence.
        parse_polygon_obstacle_excel(payload.file_bytes)
        project = self._repository.create_project(payload.project_name)
        task_id = f"import-batch-{project.id}"
        import_batch = self._repository.create_import_batch(
            task_id=task_id,
            project_id=project.id,
            obstacle_type=payload.obstacle_type,
            file_name=payload.file_name,
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

        return ImportTaskResultResponse(
            taskId=import_batch.id,
            status=import_batch.status,
            projectId=import_batch.project_id,
            obstacleBatchId=import_batch.id,
            importedCount=0,
            failedCount=0,
            boundingBox=None,
        )

    def get_import_targets(self, task_id: str) -> list[ImportTargetResponse] | None:
        import_batch = self._repository.get_import_batch(task_id)
        if import_batch is None:
            return None

        return [
            ImportTargetResponse(
                id=airport.id,
                name=airport.name,
                category="",
                distance=0,
                distanceUnit="m",
            )
            for airport in self._repository.list_airports()
        ]
