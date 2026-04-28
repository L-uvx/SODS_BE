from decimal import Decimal
from datetime import datetime, timezone
import json
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.airport import Airport
from app.models.analysis_task import AnalysisTask
from app.models.import_batch import ImportBatch
from app.models.obstacle import Obstacle
from app.models.project import Project
from app.models.report_export import ReportExport
from app.models.runway import Runway
from app.models.station import Station


class ImportBatchRepository:
    # 初始化导入批次仓储。
    def __init__(self, session: Session) -> None:
        self._session = session

    # 创建项目记录。
    def create_project(self, project_name: str, project_type: str | None = None) -> Project:
        project = Project(name=project_name, project_type=project_type)
        self._session.add(project)
        self._session.flush()
        return project

    # 根据编号获取项目记录。
    def get_project(self, project_id: int) -> Project | None:
        return self._session.get(Project, project_id)

    # 创建导入批次记录。
    def create_import_batch(
        self,
        *,
        task_id: str,
        project_id: int,
        obstacle_type: str,
        file_name: str,
        source_file_path: str,
    ) -> ImportBatch:
        import_batch = ImportBatch(
            id=task_id,
            project_id=project_id,
            status="pending",
            import_type=obstacle_type,
            source_file_name=file_name,
            source_file_path=source_file_path,
            progress_percent=0,
            status_message="import task created",
        )
        self._session.add(import_batch)
        self._session.commit()
        self._session.refresh(import_batch)
        return import_batch

    # 将导入批次标记为运行中。
    def mark_import_batch_running(self, task_id: str) -> ImportBatch | None:
        import_batch = self.get_import_batch(task_id)
        if import_batch is None:
            return None

        import_batch.status = "running"
        import_batch.progress_percent = 50
        import_batch.status_message = "import task running"
        import_batch.started_at = datetime.now(timezone.utc)
        import_batch.error_message = None
        self._session.commit()
        self._session.refresh(import_batch)
        return import_batch

    # 将导入批次标记为成功完成。
    def mark_import_batch_succeeded(self, task_id: str) -> ImportBatch | None:
        import_batch = self.get_import_batch(task_id)
        if import_batch is None:
            return None

        import_batch.status = "succeeded"
        import_batch.progress_percent = 100
        import_batch.status_message = "import task succeeded"
        import_batch.finished_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(import_batch)
        return import_batch

    # 将导入批次标记为失败。
    def mark_import_batch_failed(
        self, task_id: str, error_message: str
    ) -> ImportBatch | None:
        import_batch = self.get_import_batch(task_id)
        if import_batch is None:
            return None

        import_batch.status = "failed"
        import_batch.progress_percent = 100
        import_batch.status_message = "import task failed"
        import_batch.error_message = error_message
        import_batch.finished_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(import_batch)
        return import_batch

    # 根据任务编号获取导入批次。
    def get_import_batch(self, task_id: str) -> ImportBatch | None:
        return self._session.get(ImportBatch, task_id)

    # 创建分析任务记录。
    def create_analysis_task(
        self,
        *,
        task_id: str,
        import_batch_id: str,
        selected_target_ids: list[int],
    ) -> AnalysisTask:
        analysis_task = AnalysisTask(
            id=task_id,
            import_batch_id=import_batch_id,
            status="pending",
            progress_percent=0,
            status_message="analysis task created",
            selected_target_ids=selected_target_ids,
            result_payload=None,
        )
        self._session.add(analysis_task)
        self._session.commit()
        self._session.refresh(analysis_task)
        return analysis_task

    # 根据任务编号获取分析任务。
    def get_analysis_task(self, task_id: str) -> AnalysisTask | None:
        return self._session.get(AnalysisTask, task_id)

    # 将分析任务标记为运行中。
    def mark_analysis_task_running(self, task_id: str) -> AnalysisTask | None:
        analysis_task = self.get_analysis_task(task_id)
        if analysis_task is None:
            return None

        analysis_task.status = "running"
        analysis_task.progress_percent = 50
        analysis_task.status_message = "analysis task running"
        analysis_task.error_message = None
        self._session.commit()
        self._session.refresh(analysis_task)
        return analysis_task

    # 将分析任务标记为成功完成。
    def mark_analysis_task_succeeded(
        self, task_id: str, result_payload: dict[str, Any]
    ) -> AnalysisTask | None:
        analysis_task = self.get_analysis_task(task_id)
        if analysis_task is None:
            return None

        analysis_task.status = "succeeded"
        analysis_task.progress_percent = 100
        analysis_task.status_message = "analysis task succeeded"
        analysis_task.error_message = None
        analysis_task.result_payload = result_payload
        self._session.commit()
        self._session.refresh(analysis_task)
        return analysis_task

    # 将分析任务标记为失败。
    def mark_analysis_task_failed(
        self, task_id: str, error_message: str
    ) -> AnalysisTask | None:
        analysis_task = self.get_analysis_task(task_id)
        if analysis_task is None:
            return None

        analysis_task.status = "failed"
        analysis_task.progress_percent = 100
        analysis_task.status_message = "analysis task failed"
        analysis_task.error_message = error_message
        self._session.commit()
        self._session.refresh(analysis_task)
        return analysis_task

    # 创建报告导出任务记录。
    def create_report_export(
        self, *, task_id: str, analysis_task_id: str
    ) -> ReportExport:
        report_export = ReportExport(
            id=task_id,
            analysis_task_id=analysis_task_id,
            status="pending",
            progress_percent=0,
            status_message="export task created",
            file_name=None,
            file_path=None,
        )
        self._session.add(report_export)
        self._session.commit()
        self._session.refresh(report_export)
        return report_export

    # 根据任务编号获取报告导出记录。
    def get_report_export(self, task_id: str) -> ReportExport | None:
        return self._session.get(ReportExport, task_id)

    # 将报告导出任务标记为运行中。
    def mark_report_export_running(self, task_id: str) -> ReportExport | None:
        report_export = self.get_report_export(task_id)
        if report_export is None:
            return None

        report_export.status = "running"
        report_export.progress_percent = 50
        report_export.status_message = "export task running"
        report_export.error_message = None
        self._session.commit()
        self._session.refresh(report_export)
        return report_export

    # 将报告导出任务标记为成功完成。
    def mark_report_export_succeeded(
        self,
        task_id: str,
        *,
        file_name: str,
        file_path: str,
    ) -> ReportExport | None:
        report_export = self.get_report_export(task_id)
        if report_export is None:
            return None

        report_export.status = "succeeded"
        report_export.progress_percent = 100
        report_export.status_message = "export task succeeded"
        report_export.error_message = None
        report_export.file_name = file_name
        report_export.file_path = file_path
        report_export.finished_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(report_export)
        return report_export

    # 将报告导出任务标记为失败。
    def mark_report_export_failed(
        self, task_id: str, error_message: str
    ) -> ReportExport | None:
        report_export = self.get_report_export(task_id)
        if report_export is None:
            return None

        report_export.status = "failed"
        report_export.progress_percent = 100
        report_export.status_message = "export task failed"
        report_export.error_message = error_message
        report_export.finished_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(report_export)
        return report_export

    # 批量创建导入后的障碍物记录。
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

    # 在 SQLite 测试环境下写入障碍物记录。
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

    # 查询指定导入批次下的障碍物列表。
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

    # 查询全部机场记录。
    def list_airports(self) -> list[Airport]:
        statement = select(Airport).order_by(Airport.id)
        return list(self._session.scalars(statement))

    # 查询带坐标的机场记录。
    def list_airports_with_coordinates(self) -> list[Airport]:
        statement = (
            select(Airport)
            .where(Airport.longitude.is_not(None), Airport.latitude.is_not(None))
            .order_by(Airport.id)
        )
        return list(self._session.scalars(statement))

    # 按编号列表查询机场记录。
    def list_airports_by_ids(self, airport_ids: list[int]) -> list[Airport]:
        if not airport_ids:
            return []

        statement = (
            select(Airport).where(Airport.id.in_(airport_ids)).order_by(Airport.id)
        )
        return list(self._session.scalars(statement))

    # 查询机场下的跑道列表。
    def list_runways_by_airport_id(self, airport_id: int) -> list[Runway]:
        statement = (
            select(Runway).where(Runway.airport_id == airport_id).order_by(Runway.id)
        )
        return list(self._session.scalars(statement))

    # 查询机场下的台站列表。
    def list_stations_by_airport_id(self, airport_id: int) -> list[Station]:
        statement = (
            select(Station).where(Station.airport_id == airport_id).order_by(Station.id)
        )
        return list(self._session.scalars(statement))

    # 查询全部历史障碍物记录。
    def list_all_obstacles(self) -> list[Obstacle] | list[dict[str, Any]]:
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
                    ORDER BY id
                    """
                    )
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

        statement = select(Obstacle).order_by(Obstacle.id)
        return list(self._session.scalars(statement))
