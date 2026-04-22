from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.core import runtime
from app.db.base import Base
from app.main import app
from app.models.airport import Airport
from app.models.analysis_task import AnalysisTask
from app.models.import_batch import ImportBatch
from app.models.project import Project
from app.models.report_export import ReportExport
from app.models.runway import Runway
from app.models.station import Station
from app.report.export_payload_builder import build_export_payload


def _read_valid_excel_bytes() -> bytes:
    return Path("docs/import_demo.xlsx").read_bytes()


class _DispatchRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def delay(self, task_id: str) -> None:
        self.calls.append({"task_id": task_id})


def _run_import_task() -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        from app.application.polygon_obstacle_import import PolygonObstacleImportService

        service = PolygonObstacleImportService(session)
        service.run_import_task("import-batch-1")


def _run_analysis_task(task_id: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        from app.application.polygon_obstacle_import import PolygonObstacleImportService

        service = PolygonObstacleImportService(session)
        service.run_analysis_task(task_id)


def _run_export_task(task_id: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        from app.application.polygon_obstacle_import import PolygonObstacleImportService

        service = PolygonObstacleImportService(session)
        service.run_export_task(task_id)


@contextmanager
def _create_test_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Project.__table__,
            ImportBatch.__table__,
            AnalysisTask.__table__,
            Airport.__table__,
            Runway.__table__,
            Station.__table__,
            ReportExport.__table__,
        ],
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE obstacles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    obstacle_type VARCHAR(100),
                    source_batch_id VARCHAR(100),
                    source_row_no INTEGER,
                    top_elevation NUMERIC(10, 2),
                    raw_payload JSON,
                    geom TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )

    def _override_session() -> Generator[Session, None, None]:
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides = {get_db_session: _override_session}

    with TestClient(app) as client:
        yield client

    Base.metadata.drop_all(
        bind=engine,
        tables=[
            Station.__table__,
            Runway.__table__,
            Airport.__table__,
            ReportExport.__table__,
            AnalysisTask.__table__,
            ImportBatch.__table__,
            Project.__table__,
        ],
    )
    app.dependency_overrides = {}


def _create_succeeded_analysis_task(client: TestClient) -> str:
    app.state.dispatch_import_task = _DispatchRecorder().delay
    runtime.dispatch_import_task = app.state.dispatch_import_task
    app.state.dispatch_analysis_task = _DispatchRecorder().delay
    runtime.dispatch_analysis_task = app.state.dispatch_analysis_task

    create_import_response = client.post(
        "/polygon-obstacle/import",
        data={
            "projectName": "Wuhan Demo",
            "obstacleType": "building",
        },
        files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
    )
    import_task_id = create_import_response.json()["taskId"]
    _run_import_task()

    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        session.add(
            Airport(
                name="Airport Near",
                longitude=103.975864,
                latitude=30.506881,
            )
        )
        session.commit()

    create_analysis_response = client.post(
        "/polygon-obstacle/analysis",
        json={
            "importTaskId": import_task_id,
            "targetIds": [1],
        },
    )
    analysis_task_id = create_analysis_response.json()["analysisTaskId"]
    _run_analysis_task(analysis_task_id)
    return analysis_task_id


def test_create_export_task_returns_minimal_task_payload() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        dispatch_recorder = _DispatchRecorder()
        app.state.dispatch_export_task = dispatch_recorder.delay
        runtime.dispatch_export_task = dispatch_recorder.delay

        response = client.post(f"/polygon-obstacle/analysis/{analysis_task_id}/export")

    assert response.status_code == 201
    assert response.json() == {
        "exportTaskId": "export-task-1",
        "analysisTaskId": analysis_task_id,
        "status": "pending",
        "message": "export task created",
        "progressPercent": 0,
    }
    assert dispatch_recorder.calls == [{"task_id": "export-task-1"}]


def test_create_export_task_returns_404_for_unknown_analysis_task() -> None:
    with _create_test_client() as client:
        response = client.post("/polygon-obstacle/analysis/missing-task/export")

    assert response.status_code == 404
    assert response.json() == {"detail": "analysis task not found"}


def test_create_export_task_returns_409_for_pending_analysis_task() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        app.state.dispatch_analysis_task = _DispatchRecorder().delay
        runtime.dispatch_analysis_task = app.state.dispatch_analysis_task
        create_import_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        import_task_id = create_import_response.json()["taskId"]

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    name="Airport Near",
                    longitude=103.975864,
                    latitude=30.506881,
                )
            )
            session.commit()

        create_analysis_response = client.post(
            "/polygon-obstacle/analysis",
            json={
                "importTaskId": import_task_id,
                "targetIds": [1],
            },
        )
        analysis_task_id = create_analysis_response.json()["analysisTaskId"]

        response = client.post(f"/polygon-obstacle/analysis/{analysis_task_id}/export")

    assert response.status_code == 409
    assert response.json() == {"detail": "analysis task is not ready for export"}


def test_get_export_task_status_returns_existing_task() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]

        response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/{export_task_id}/status"
        )

    assert response.status_code == 200
    assert response.json() == {
        "exportTaskId": export_task_id,
        "analysisTaskId": analysis_task_id,
        "status": "pending",
        "message": "export task created",
        "progressPercent": 0,
    }


def test_get_export_task_result_returns_empty_payload_before_completion() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]

        response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/{export_task_id}/result"
        )

    assert response.status_code == 200
    assert response.json() == {
        "exportTaskId": export_task_id,
        "analysisTaskId": analysis_task_id,
        "status": "pending",
        "fileName": None,
        "downloadUrl": None,
        "errorMessage": None,
    }


def test_get_export_task_status_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/missing-task/status"
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "export task not found"}


def test_get_export_task_result_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/missing-task/result"
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "export task not found"}


def test_download_export_file_returns_404_before_generation() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]

        response = client.get(f"/polygon-obstacle/exports/{export_task_id}/download")

    assert response.status_code == 404
    assert response.json() == {"detail": "export file not found"}


def test_run_export_task_marks_status_succeeded_and_returns_download_url() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]

        _run_export_task(export_task_id)
        status_response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/{export_task_id}/status"
        )
        result_response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/{export_task_id}/result"
        )

    assert status_response.status_code == 200
    assert status_response.json() == {
        "exportTaskId": export_task_id,
        "analysisTaskId": analysis_task_id,
        "status": "succeeded",
        "message": "export task succeeded",
        "progressPercent": 100,
    }
    assert result_response.status_code == 200
    assert result_response.json() == {
        "exportTaskId": export_task_id,
        "analysisTaskId": analysis_task_id,
        "status": "succeeded",
        "fileName": f"polygon-obstacle-analysis-{analysis_task_id}.docx",
        "downloadUrl": f"/polygon-obstacle/exports/{export_task_id}/download",
        "errorMessage": None,
    }


def test_build_export_payload_includes_rule_results_with_standards() -> None:
    analysis_task = AnalysisTask(
        id="analysis-task-1",
        import_batch_id="import-batch-1",
        selected_target_ids=[1],
        status="succeeded",
        result_payload={
            "summary": "done",
            "obstacleCount": 1,
            "selectedTargets": [{"id": 1, "name": "Airport A", "category": "机场"}],
            "ruleResults": [
                {
                    "airportId": 1,
                    "stationId": 101,
                    "stationName": "NDB Station",
                    "stationType": "NDB",
                    "obstacleId": 2,
                    "obstacleName": "Obstacle A",
                    "rawObstacleType": "建筑物/构建物",
                    "globalObstacleCategory": "building_general",
                    "ruleName": "ndb_minimum_distance_50m",
                    "zoneCode": "ndb_minimum_distance_50m",
                    "zoneName": "NDB 50m minimum distance zone",
                    "regionCode": "default",
                    "regionName": "default",
                    "zoneDefinition": {"shape": "circle", "radius_m": 50.0},
                    "isApplicable": True,
                    "isCompliant": False,
                    "message": "distance below minimum separation",
                    "metrics": {"requiredDistanceMeters": 50.0},
                    "standards": {
                        "gb": {
                            "code": "GB_NDB_50m最小间距区域_50",
                            "text": "GB text",
                            "isCompliant": False,
                        },
                        "mh": {
                            "code": "MH_NDB_50m最小间距区域_50",
                            "text": "MH text",
                            "isCompliant": False,
                        },
                    },
                }
            ],
        },
    )

    payload = build_export_payload(analysis_task)

    assert payload["ruleResults"][0]["standards"]["gb"]["code"] == "GB_NDB_50m最小间距区域_50"
    assert payload["ruleResults"][0]["standards"]["gb"]["isCompliant"] is False
    assert payload["ruleResults"][0]["standards"]["mh"]["code"] == "MH_NDB_50m最小间距区域_50"
    assert payload["ruleResults"][0]["standards"]["mh"]["isCompliant"] is False


def test_download_export_file_returns_docx_after_generation() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]

        _run_export_task(export_task_id)
        response = client.get(f"/polygon-obstacle/exports/{export_task_id}/download")

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert (
        f'filename="polygon-obstacle-analysis-{analysis_task_id}.docx"'
        in response.headers["content-disposition"]
    )
    assert len(response.content) > 0


def test_run_export_task_writes_gb_and_mh_standards_into_report() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            task = session.get(AnalysisTask, analysis_task_id)
            assert task is not None
            task.status = "succeeded"
            task.status_message = "analysis task succeeded"
            task.error_message = None
            task.result_payload = {
                "summary": "已完成测试分析",
                "obstacleCount": 1,
                "selectedTargets": [
                    {"id": 1, "name": "Airport Near", "category": "机场"}
                ],
                "ruleResults": [
                    {
                        "airportId": 1,
                        "stationId": 101,
                        "stationName": "NDB Station",
                        "stationType": "NDB",
                        "obstacleId": 2,
                        "obstacleName": "Obstacle A",
                        "rawObstacleType": "建筑物/构建物",
                        "globalObstacleCategory": "building_general",
                        "ruleName": "ndb_minimum_distance_50m",
                        "zoneCode": "ndb_minimum_distance_50m",
                        "zoneName": "NDB 50m minimum distance zone",
                        "regionCode": "default",
                        "regionName": "default",
                        "zoneDefinition": {"shape": "circle", "radius_m": 50.0},
                        "isApplicable": True,
                        "isCompliant": False,
                        "message": "distance below minimum separation",
                        "metrics": {"requiredDistanceMeters": 50.0},
                        "standards": {
                            "gb": {
                                "code": "GB_NDB_50m最小间距区域_50",
                                "text": "GB text",
                                "isCompliant": False,
                            },
                            "mh": {
                                "code": "MH_NDB_50m最小间距区域_50",
                                "text": "MH text",
                                "isCompliant": False,
                            },
                        },
                    }
                ],
            }
            session.commit()

        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]
        _run_export_task(export_task_id)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            report_export = session.get(ReportExport, export_task_id)
            assert report_export is not None
            document = Document(report_export.file_path)

    full_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "GB_NDB_50m最小间距区域_50" in full_text
    assert "GB text" in full_text
    assert "国标条文是否满足: 不满足" in full_text
    assert "MH_NDB_50m最小间距区域_50" in full_text
    assert "MH text" in full_text
    assert "行标条文是否满足: 不满足" in full_text


def test_run_export_task_succeeds_when_runtime_settings_are_uninitialized() -> None:
    with _create_test_client() as client:
        analysis_task_id = _create_succeeded_analysis_task(client)
        app.state.dispatch_export_task = _DispatchRecorder().delay
        runtime.dispatch_export_task = app.state.dispatch_export_task
        create_response = client.post(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export"
        )
        export_task_id = create_response.json()["exportTaskId"]

        original_settings = runtime.settings
        runtime.settings = None
        try:
            _run_export_task(export_task_id)
        finally:
            runtime.settings = original_settings

        response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/export/{export_task_id}/result"
        )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["downloadUrl"] == (
        f"/polygon-obstacle/exports/{export_task_id}/download"
    )
    assert response.json()["errorMessage"] is None
