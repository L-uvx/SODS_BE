from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path as SysPath
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
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


def _read_valid_excel_bytes() -> bytes:
    return Path("docs/import_demo.xlsx").read_bytes()


def _build_invalid_excel_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"
    worksheet.append(["经度", "障碍物名称", "纬度", "顶部高程"])
    worksheet.append(["103°58'33.11\"", "障碍物1", "030°30'24.77\"", 549.9])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class _DispatchRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def delay(self, task_id: str) -> None:
        self.calls.append({"task_id": task_id})


def _run_import_task(client: TestClient, task_id: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        from app.application.polygon_obstacle_import import PolygonObstacleImportService

        service = PolygonObstacleImportService(session)
        service.run_import_task(task_id)


def _run_analysis_task(client: TestClient, task_id: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        from app.application.polygon_obstacle_import import PolygonObstacleImportService

        service = PolygonObstacleImportService(session)
        service.run_analysis_task(task_id)


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
            Airport.__table__,
            AnalysisTask.__table__,
            ImportBatch.__table__,
            Project.__table__,
        ],
    )
    app.dependency_overrides = {}


def test_create_import_task_returns_minimal_task_payload() -> None:
    with _create_test_client() as client:
        dispatch_recorder = _DispatchRecorder()
        app.state.dispatch_import_task = dispatch_recorder.delay
        runtime.dispatch_import_task = dispatch_recorder.delay
        response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )

    assert response.status_code == 201
    assert response.json() == {
        "taskId": "import-batch-1",
        "status": "pending",
        "message": "import task created",
        "progressPercent": 0,
        "projectId": 1,
        "obstacleBatchId": "import-batch-1",
    }
    assert dispatch_recorder.calls == [{"task_id": "import-batch-1"}]


def test_get_import_task_status_returns_existing_task() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        task_id = create_response.json()["taskId"]

        response = client.get(f"/polygon-obstacle/import/{task_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "taskId": task_id,
        "status": "pending",
        "message": "import task created",
        "progressPercent": 0,
        "projectId": 1,
        "obstacleBatchId": task_id,
    }


def test_get_import_task_status_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/import/missing-task/status")

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


def test_get_import_task_result_returns_minimal_result_payload() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        task_id = create_response.json()["taskId"]

        response = client.get(f"/polygon-obstacle/import/{task_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "taskId": task_id,
        "status": "pending",
        "projectId": 1,
        "obstacleBatchId": task_id,
        "importedCount": 0,
        "failedCount": 0,
        "boundingBox": None,
        "obstacles": [],
    }


def test_create_import_task_persists_obstacles_to_database() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )

        task_id = create_response.json()["taskId"]

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            obstacles = (
                session.execute(
                    text(
                        "SELECT id, project_id, name, obstacle_type, source_batch_id, top_elevation, raw_payload FROM obstacles ORDER BY id"
                    )
                )
                .mappings()
                .all()
            )

    assert task_id == "import-batch-1"
    assert obstacles == []


def test_create_import_task_persists_source_file_path_for_worker() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )

        task_id = create_response.json()["taskId"]

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            import_batch = session.get(ImportBatch, task_id)

    assert import_batch is not None
    assert import_batch.status == "pending"
    assert import_batch.source_file_name == "import_demo.xlsx"
    assert import_batch.source_file_path is not None
    assert SysPath(import_batch.source_file_path).name == "import_demo.xlsx"
    assert SysPath(import_batch.source_file_path).parent.name == task_id
    assert SysPath(import_batch.source_file_path).exists()


def test_get_import_task_result_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/import/missing-task/result")

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


def test_get_import_targets_returns_all_airports_with_placeholder_distance() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        task_id = create_response.json()["taskId"]
        _run_import_task(client, task_id)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(
                        name="Airport Near",
                        longitude=103.975864,
                        latitude=30.506881,
                    ),
                    Airport(
                        name="Airport Far",
                        longitude=104.100000,
                        latitude=30.600000,
                    ),
                    Airport(name="Airport Missing Coordinates"),
                ]
            )
            session.commit()

        response = client.get(f"/polygon-obstacle/import/{task_id}/targets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Airport Near",
            "category": "机场",
            "distance": 0.0,
            "distanceUnit": "km",
        },
        {
            "id": 2,
            "name": "Airport Far",
            "category": "机场",
            "distance": 18.24,
            "distanceUnit": "km",
        },
    ]


def test_get_import_targets_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/import/missing-task/targets")

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


def test_get_bootstrap_returns_first_airport_with_coordinates_and_historical_obstacles() -> (
    None
):
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        _run_import_task(client, "import-batch-1")

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(name="Airport Missing Coordinates"),
                    Airport(
                        name="Airport Near",
                        longitude=103.975864,
                        latitude=30.506881,
                    ),
                    Airport(
                        name="Airport Far",
                        longitude=104.100000,
                        latitude=30.600000,
                    ),
                ]
            )
            session.commit()

            response = client.get("/polygon-obstacle/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["airport"] == {
        "id": 2,
        "name": "Airport Near",
        "longitude": 103.975864,
        "latitude": 30.506881,
    }
    assert len(payload["historicalObstacles"]) == 2
    assert payload["historicalObstacles"][0] == {
        "id": 1,
        "name": "障碍物1",
        "obstacleType": "building",
        "topElevation": 549.9,
        "sourceRowNumbers": [2, 3, 4, 5, 6],
        "boundingBox": None,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [103.9758638888889, 30.506880555555554],
                        [103.97811111111112, 30.50565],
                        [103.97690833333334, 30.50386388888889],
                        [103.97425, 30.50510277777778],
                        [103.97421944444444, 30.505241666666667],
                        [103.9758638888889, 30.506880555555554],
                    ]
                ]
            ],
        },
    }
    assert payload["historicalObstacles"][1] == {
        "id": 2,
        "name": "障碍物2",
        "obstacleType": "building",
        "topElevation": 549.9,
        "sourceRowNumbers": [7, 8, 9, 10, 11],
        "boundingBox": None,
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [103.9758638888889, 30.506880555555554],
                        [103.97811111111112, 30.50565],
                        [103.97690833333334, 30.50386388888889],
                        [103.97425, 30.50510277777778],
                        [103.97421944444444, 30.505241666666667],
                        [103.9758638888889, 30.506880555555554],
                    ]
                ]
            ],
        },
    }


def test_get_bootstrap_returns_null_airport_when_no_airport_has_coordinates() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        _run_import_task(client, "import-batch-1")

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(name="Airport Missing Coordinates 1"),
                    Airport(name="Airport Missing Coordinates 2"),
                ]
            )
            session.commit()

        response = client.get("/polygon-obstacle/bootstrap")

    assert response.status_code == 200
    assert response.json()["airport"] is None
    assert len(response.json()["historicalObstacles"]) == 2


def test_get_bootstrap_returns_empty_historical_obstacles_when_no_obstacles_exist() -> (
    None
):
    with _create_test_client() as client:
        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    name="Airport Near",
                    longitude=103.975864,
                    latitude=30.506881,
                )
            )
            session.commit()

        response = client.get("/polygon-obstacle/bootstrap")

    assert response.status_code == 200
    assert response.json() == {
        "airport": {
            "id": 1,
            "name": "Airport Near",
            "longitude": 103.975864,
            "latitude": 30.506881,
        },
        "historicalObstacles": [],
    }


def test_create_import_task_requires_minimal_fields() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
        )

    assert response.status_code == 422


def test_run_import_task_marks_failed_for_invalid_excel_template() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("invalid.xlsx", _build_invalid_excel_bytes())},
        )
        task_id = create_response.json()["taskId"]
        _run_import_task(client, task_id)

        response = client.get(f"/polygon-obstacle/import/{task_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "taskId": task_id,
        "status": "failed",
        "message": "import task failed",
        "progressPercent": 100,
        "projectId": 1,
        "obstacleBatchId": task_id,
    }


def test_run_import_task_marks_failed_for_non_excel_file() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("invalid.txt", b"not-an-excel-file")},
        )
        task_id = create_response.json()["taskId"]
        _run_import_task(client, task_id)

        response = client.get(f"/polygon-obstacle/import/{task_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "taskId": task_id,
        "status": "failed",
        "message": "import task failed",
        "progressPercent": 100,
        "projectId": 1,
        "obstacleBatchId": task_id,
    }


def test_create_analysis_task_returns_minimal_task_payload() -> None:
    with _create_test_client() as client:
        dispatch_recorder = _DispatchRecorder()
        app.state.dispatch_analysis_task = dispatch_recorder.delay
        runtime.dispatch_analysis_task = dispatch_recorder.delay
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
            session.add_all(
                [
                    Airport(
                        name="Airport Near",
                        longitude=103.975864,
                        latitude=30.506881,
                    ),
                    Airport(
                        name="Airport Far",
                        longitude=104.100000,
                        latitude=30.600000,
                    ),
                ]
            )
            session.commit()

        response = client.post(
            "/polygon-obstacle/analysis",
            json={
                "importTaskId": import_task_id,
                "targetIds": [1, 2],
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "analysisTaskId": "analysis-task-1",
        "status": "pending",
        "message": "analysis task created",
        "progressPercent": 0,
        "importTaskId": import_task_id,
        "targetIds": [1, 2],
    }
    assert dispatch_recorder.calls == [{"task_id": "analysis-task-1"}]


def test_create_analysis_task_returns_404_for_unknown_import_task() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/polygon-obstacle/analysis",
            json={
                "importTaskId": "missing-import-task",
                "targetIds": [1],
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


def test_create_analysis_task_rejects_empty_target_ids() -> None:
    with _create_test_client() as client:
        create_import_response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("import_demo.xlsx", _read_valid_excel_bytes())},
        )
        import_task_id = create_import_response.json()["taskId"]

        response = client.post(
            "/polygon-obstacle/analysis",
            json={
                "importTaskId": import_task_id,
                "targetIds": [],
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "too_short"


def test_get_analysis_task_status_returns_existing_task() -> None:
    with _create_test_client() as client:
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

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "analysisTaskId": analysis_task_id,
        "status": "pending",
        "message": "analysis task created",
        "progressPercent": 0,
        "importTaskId": import_task_id,
        "targetIds": [1],
    }


def test_run_analysis_task_marks_status_succeeded() -> None:
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
        _run_import_task(client, import_task_id)

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

        _run_analysis_task(client, analysis_task_id)
        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "analysisTaskId": analysis_task_id,
        "status": "succeeded",
        "message": "analysis task succeeded",
        "progressPercent": 100,
        "importTaskId": import_task_id,
        "targetIds": [1],
    }


def test_get_analysis_task_status_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/analysis/missing-task/status")

    assert response.status_code == 404
    assert response.json() == {"detail": "analysis task not found"}


def test_get_analysis_task_result_returns_minimal_result_payload() -> None:
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
        _run_import_task(client, import_task_id)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(
                        name="Airport Near",
                        longitude=103.975864,
                        latitude=30.506881,
                    ),
                    Airport(
                        name="Airport Far",
                        longitude=104.100000,
                        latitude=30.600000,
                    ),
                ]
            )
            session.commit()

        create_analysis_response = client.post(
            "/polygon-obstacle/analysis",
            json={
                "importTaskId": import_task_id,
                "targetIds": [1, 2],
            },
        )
        analysis_task_id = create_analysis_response.json()["analysisTaskId"]
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "analysisTaskId": analysis_task_id,
        "status": "succeeded",
        "importTaskId": import_task_id,
        "targetIds": [1, 2],
        "selectedTargets": [
            {"id": 1, "name": "Airport Near", "category": "机场"},
            {"id": 2, "name": "Airport Far", "category": "机场"},
        ],
        "obstacleCount": 2,
        "summary": "已基于当前导入障碍物和所选机场生成最小分析结果。",
    }


def test_get_analysis_task_result_returns_empty_payload_before_completion() -> None:
    with _create_test_client() as client:
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

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "analysisTaskId": analysis_task_id,
        "status": "pending",
        "importTaskId": import_task_id,
        "targetIds": [1],
        "selectedTargets": [],
        "obstacleCount": 0,
        "summary": "",
    }


def test_get_analysis_task_result_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/analysis/missing-task/result")

    assert response.status_code == 404
    assert response.json() == {"detail": "analysis task not found"}
