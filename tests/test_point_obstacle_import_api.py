from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO

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
from app.models.runway import Runway
from app.models.station import Station


def _build_point_excel_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"

    for row in rows:
        worksheet.append(row)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _read_valid_point_excel_bytes() -> bytes:
    return _build_point_excel_bytes(
        [
            ["障碍物名称", "经度", "纬度", "顶部高程"],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["点障碍物2", "103°58'41.20\"", "030°30'20.34\"", 550.1],
        ]
    )


class _DispatchRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def delay(self, task_id: str) -> None:
        self.calls.append({"task_id": task_id})


def _run_point_import_task(task_id: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        from app.application.polygon_obstacle_import import PolygonObstacleImportService

        service = PolygonObstacleImportService(session)
        service.run_point_import_task(task_id)


def _run_analysis_task(task_id: str) -> None:
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
            Runway.__table__,
            Station.__table__,
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
            AnalysisTask.__table__,
            ImportBatch.__table__,
            Project.__table__,
        ],
    )
    app.dependency_overrides = {}


def test_create_point_import_task_returns_minimal_task_payload() -> None:
    with _create_test_client() as client:
        dispatch_recorder = _DispatchRecorder()
        app.state.dispatch_import_task = dispatch_recorder.delay
        runtime.dispatch_import_task = dispatch_recorder.delay
        response = client.post(
            "/point-obstacle/import",
            data={"projectName": "Point Demo", "obstacleType": "tree"},
            files={"excelFile": ("point_import.xlsx", _read_valid_point_excel_bytes())},
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


def test_point_import_result_returns_point_geometry_and_deduplicated_rows() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/point-obstacle/import",
            data={"projectName": "Point Demo", "obstacleType": "tree"},
            files={"excelFile": ("point_import.xlsx", _read_valid_point_excel_bytes())},
        )
        task_id = create_response.json()["taskId"]

        _run_point_import_task(task_id)

        response = client.get(f"/point-obstacle/import/{task_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "taskId": task_id,
        "status": "succeeded",
        "projectId": 1,
        "obstacleBatchId": task_id,
        "importedCount": 2,
        "failedCount": 0,
        "boundingBox": None,
        "obstacles": [
            {
                "id": 1,
                "name": "点障碍物1",
                "obstacleType": "tree",
                "topElevation": 549.9,
                "sourceRowNumbers": [2],
                "boundingBox": None,
                "geometry": {
                    "type": "Point",
                    "coordinates": [103.9758638888889, 30.506880555555554],
                },
            },
            {
                "id": 2,
                "name": "点障碍物2",
                "obstacleType": "tree",
                "topElevation": 550.1,
                "sourceRowNumbers": [4],
                "boundingBox": None,
                "geometry": {
                    "type": "Point",
                    "coordinates": [103.97811111111112, 30.50565],
                },
            },
        ],
    }


def test_point_import_status_and_result_reject_polygon_import_task() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/polygon-obstacle/import",
            data={"projectName": "Polygon Demo", "obstacleType": "building"},
            files={
                "excelFile": (
                    "import_demo.xlsx",
                    __import__(
                        "pathlib"
                    ).Path("docs/import_demo.xlsx").read_bytes(),
                )
            },
        )
        task_id = create_response.json()["taskId"]

        status_response = client.get(f"/point-obstacle/import/{task_id}/status")
        result_response = client.get(f"/point-obstacle/import/{task_id}/result")

    assert status_response.status_code == 404
    assert status_response.json() == {"detail": "import task not found"}
    assert result_response.status_code == 404
    assert result_response.json() == {"detail": "import task not found"}


def test_point_import_bootstrap_targets_and_analysis_reuse_existing_chain() -> None:
    with _create_test_client() as client:
        app.state.dispatch_import_task = _DispatchRecorder().delay
        runtime.dispatch_import_task = app.state.dispatch_import_task
        create_response = client.post(
            "/point-obstacle/import",
            data={"projectName": "Point Demo", "obstacleType": "building"},
            files={"excelFile": ("point_import.xlsx", _read_valid_point_excel_bytes())},
        )
        import_task_id = create_response.json()["taskId"]
        _run_point_import_task(import_task_id)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            airport = Airport(name="Airport Near", longitude=103.975864, latitude=30.506881)
            session.add(airport)
            session.flush()
            session.add(
                Station(
                    airport_id=airport.id,
                    name="NDB Station",
                    station_type="NDB",
                    longitude=103.9758638888889,
                    latitude=30.506880555555554,
                    altitude=500.0,
                )
            )
            session.commit()

        bootstrap_response = client.get("/polygon-obstacle/bootstrap")
        targets_response = client.get(
            f"/polygon-obstacle/import/{import_task_id}/targets"
        )

        app.state.dispatch_analysis_task = _DispatchRecorder().delay
        runtime.dispatch_analysis_task = app.state.dispatch_analysis_task
        analysis_create_response = client.post(
            "/polygon-obstacle/analysis",
            json={"importTaskId": import_task_id, "targetIds": [1]},
        )
        analysis_task_id = analysis_create_response.json()["analysisTaskId"]
        _run_analysis_task(analysis_task_id)
        analysis_result_response = client.get(
            f"/polygon-obstacle/analysis/{analysis_task_id}/result"
        )

    assert bootstrap_response.status_code == 200
    assert bootstrap_response.json()["historicalObstacles"] == [
        {
            "id": 1,
            "name": "点障碍物1",
            "obstacleType": "building",
            "topElevation": 549.9,
            "sourceRowNumbers": [2],
            "boundingBox": None,
            "geometry": {
                "type": "Point",
                "coordinates": [103.9758638888889, 30.506880555555554],
            },
        },
        {
            "id": 2,
            "name": "点障碍物2",
            "obstacleType": "building",
            "topElevation": 550.1,
            "sourceRowNumbers": [4],
            "boundingBox": None,
            "geometry": {
                "type": "Point",
                "coordinates": [103.97811111111112, 30.50565],
            },
        },
    ]
    assert targets_response.status_code == 200
    assert targets_response.json() == [
        {
            "id": 1,
            "name": "Airport Near",
            "category": "机场",
            "distance": 0.0,
            "distanceUnit": "km",
        }
    ]
    assert analysis_result_response.status_code == 200
    assert analysis_result_response.json()["status"] == "succeeded"
    assert analysis_result_response.json()["obstacleCount"] == 2
