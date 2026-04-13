from decimal import Decimal
import json
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.airport import Airport
from app.models.import_batch import ImportBatch
from app.models.obstacle import Obstacle
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

    def create_obstacles(
        self,
        *,
        project_id: int,
        obstacle_type: str,
        source_batch_id: str,
        obstacles: list[dict[str, Any]],
    ) -> list[Obstacle] | None:
        if (
            self._session.bind is not None
            and self._session.bind.dialect.name == "sqlite"
        ):
            self._create_obstacles_for_sqlite(
                project_id=project_id,
                obstacle_type=obstacle_type,
                source_batch_id=source_batch_id,
                obstacles=obstacles,
            )
            return None

        created_obstacles: list[Obstacle] = []

        for obstacle in obstacles:
            created_obstacle = Obstacle(
                project_id=project_id,
                name=obstacle["name"],
                obstacle_type=obstacle_type,
                source_batch_id=source_batch_id,
                source_row_no=obstacle["source_row_numbers"][0],
                top_elevation=Decimal(str(obstacle["top_elevation"])),
                raw_payload=obstacle["raw_payload"],
                geom=WKTElement(obstacle["geometry_wkt"], srid=4326),
            )
            self._session.add(created_obstacle)
            created_obstacles.append(created_obstacle)

        self._session.commit()

        for created_obstacle in created_obstacles:
            self._session.refresh(created_obstacle)

        return created_obstacles

    def _create_obstacles_for_sqlite(
        self,
        *,
        project_id: int,
        obstacle_type: str,
        source_batch_id: str,
        obstacles: list[dict[str, Any]],
    ) -> None:
        statement = text(
            """
            INSERT INTO obstacles (
                project_id,
                name,
                obstacle_type,
                source_batch_id,
                source_row_no,
                top_elevation,
                raw_payload,
                geom
            ) VALUES (
                :project_id,
                :name,
                :obstacle_type,
                :source_batch_id,
                :source_row_no,
                :top_elevation,
                :raw_payload,
                :geom
            )
            """
        )
        for obstacle in obstacles:
            self._session.execute(
                statement,
                {
                    "project_id": project_id,
                    "name": obstacle["name"],
                    "obstacle_type": obstacle_type,
                    "source_batch_id": source_batch_id,
                    "source_row_no": obstacle["source_row_numbers"][0],
                    "top_elevation": obstacle["top_elevation"],
                    "raw_payload": json.dumps(
                        obstacle["raw_payload"], ensure_ascii=False
                    ),
                    "geom": obstacle["geometry_wkt"],
                },
            )
        self._session.commit()

    def list_obstacles_by_batch_id(
        self, source_batch_id: str
    ) -> list[Obstacle] | list[dict[str, Any]]:
        if (
            self._session.bind is not None
            and self._session.bind.dialect.name == "sqlite"
        ):
            rows = (
                self._session.execute(
                    text(
                        """
                    SELECT id, name, obstacle_type, top_elevation, raw_payload
                    FROM obstacles
                    WHERE source_batch_id = :source_batch_id
                    ORDER BY id
                    """
                    ),
                    {"source_batch_id": source_batch_id},
                )
                .mappings()
                .all()
            )
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "obstacle_type": row["obstacle_type"],
                    "top_elevation": row["top_elevation"],
                    "raw_payload": json.loads(row["raw_payload"]),
                }
                for row in rows
            ]

        statement = (
            select(Obstacle)
            .where(Obstacle.source_batch_id == source_batch_id)
            .order_by(Obstacle.id)
        )
        return list(self._session.scalars(statement))

    def list_airports(self) -> list[Airport]:
        statement = select(Airport).order_by(Airport.id)
        return list(self._session.scalars(statement))
