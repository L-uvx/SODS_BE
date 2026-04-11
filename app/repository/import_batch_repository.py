from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.airport import Airport
from app.models.import_batch import ImportBatch
from app.models.project import Project


class ImportBatchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_project(self, project_name: str) -> Project:
        project = Project(name=project_name)
        self._session.add(project)
        self._session.flush()
        return project

    def create_import_batch(
        self,
        *,
        task_id: str,
        project_id: int,
        obstacle_type: str,
        file_name: str,
    ) -> ImportBatch:
        import_batch = ImportBatch(
            id=task_id,
            project_id=project_id,
            status="succeeded",
            import_type=obstacle_type,
            source_file_name=file_name,
        )
        self._session.add(import_batch)
        self._session.commit()
        self._session.refresh(import_batch)
        return import_batch

    def get_import_batch(self, task_id: str) -> ImportBatch | None:
        return self._session.get(ImportBatch, task_id)

    def list_airports(self) -> list[Airport]:
        statement = select(Airport).order_by(Airport.id)
        return list(self._session.scalars(statement))
