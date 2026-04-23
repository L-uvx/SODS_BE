from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path as SysPath
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.analysis.local_coordinate import AirportLocalProjector
from app.core import runtime
from app.db.base import Base
from app.main import app
from app.schemas.polygon_obstacle import AnalysisProtectionZoneResponse
from app.models.airport import Airport
from app.models.analysis_task import AnalysisTask
from app.models.import_batch import ImportBatch
from app.models.project import Project
from app.models.runway import Runway
from app.models.station import Station


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


def _create_succeeded_import_task(client: TestClient) -> str:
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
    return task_id


def _create_analysis_task(
    client: TestClient, import_task_id: str, target_ids: list[int]
) -> str:
    app.state.dispatch_analysis_task = _DispatchRecorder().delay
    runtime.dispatch_analysis_task = app.state.dispatch_analysis_task
    create_response = client.post(
        "/polygon-obstacle/analysis",
        json={
            "importTaskId": import_task_id,
            "targetIds": target_ids,
        },
    )
    return create_response.json()["analysisTaskId"]


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


def test_get_import_targets_returns_all_airports_with_distance_from_nearest_station() -> (
    None
):
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
            session.add_all(
                [
                    Station(
                        id=101,
                        name="Near Station",
                        airport_id=1,
                        longitude=103.975864,
                        latitude=30.506881,
                    ),
                    Station(
                        id=201,
                        name="Far Station",
                        airport_id=2,
                        longitude=103.975864,
                        latitude=30.506881,
                    ),
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
            "distance": 0.0,
            "distanceUnit": "km",
        },
    ]


def test_get_import_targets_returns_zero_distance_when_airport_has_no_valid_station() -> (
    None
):
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
            session.add(
                Airport(
                    id=1,
                    name="Airport Without Station Coordinates",
                    longitude=103.975864,
                    latitude=30.506881,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="Station Without Coordinates",
                    airport_id=1,
                    longitude=None,
                    latitude=None,
                )
            )
            session.commit()

        response = client.get(f"/polygon-obstacle/import/{task_id}/targets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Airport Without Station Coordinates",
            "category": "机场",
            "distance": 0.0,
            "distanceUnit": "km",
        }
    ]


def test_get_import_targets_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/import/missing-task/targets")

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


def test_get_bootstrap_returns_airports_with_nested_stations_and_historical_obstacles() -> (
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
            session.flush()
            session.add_all(
                [
                    Station(
                        airport_id=2,
                        name="NDB Station",
                        station_type="NDB",
                        longitude=103.976000,
                        latitude=30.507000,
                        altitude=500.0,
                    ),
                    Station(
                        airport_id=2,
                        name="Station Missing Coordinates",
                        station_type="VOR",
                    ),
                    Station(
                        airport_id=3,
                        name="VOR Station",
                        station_type="VOR",
                        longitude=104.101000,
                        latitude=30.601000,
                        altitude=520.0,
                    ),
                ]
            )
            session.commit()

            response = client.get("/polygon-obstacle/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["airports"] == [
        {
            "id": 2,
            "name": "Airport Near",
            "longitude": 103.975864,
            "latitude": 30.506881,
            "stations": [
                {
                    "id": 1,
                    "name": "NDB Station",
                    "stationType": "NDB",
                    "longitude": 103.976,
                    "latitude": 30.507,
                    "altitude": 500.0,
                }
            ],
        },
        {
            "id": 3,
            "name": "Airport Far",
            "longitude": 104.1,
            "latitude": 30.6,
            "stations": [
                {
                    "id": 3,
                    "name": "VOR Station",
                    "stationType": "VOR",
                    "longitude": 104.101,
                    "latitude": 30.601,
                    "altitude": 520.0,
                }
            ],
        },
    ]
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


def test_get_bootstrap_returns_empty_airports_when_no_airport_has_coordinates() -> None:
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
    assert response.json()["airports"] == []
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
            session.flush()
            session.add(
                Station(
                    airport_id=1,
                    name="NDB Station",
                    station_type="NDB",
                    longitude=103.976000,
                    latitude=30.507000,
                    altitude=500.0,
                )
            )
            session.commit()

        response = client.get("/polygon-obstacle/bootstrap")

    assert response.status_code == 200
    assert response.json() == {
        "airports": [
            {
                "id": 1,
                "name": "Airport Near",
                "longitude": 103.975864,
                "latitude": 30.506881,
                "stations": [
                    {
                        "id": 1,
                        "name": "NDB Station",
                        "stationType": "NDB",
                        "longitude": 103.976,
                        "latitude": 30.507,
                        "altitude": 500.0,
                    }
                ],
            }
        ],
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
    payload = response.json()
    assert payload["analysisTaskId"] == analysis_task_id
    assert payload["status"] == "succeeded"
    assert payload["importTaskId"] == import_task_id
    assert payload["targetIds"] == [1, 2]
    assert payload["selectedTargets"] == [
        {"id": 1, "name": "Airport Near", "category": "机场"},
        {"id": 2, "name": "Airport Far", "category": "机场"},
    ]
    assert payload["obstacleCount"] == 2
    assert payload["summary"] == "已完成局部坐标系与最小空间事实计算。"
    assert [
        airport_facts["airportId"]
        for airport_facts in payload["spatialFacts"]["airports"]
    ] == [1, 2]


def test_get_analysis_task_result_returns_spatial_facts_after_worker_runs() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysisTaskId"] == analysis_task_id
    assert payload["status"] == "succeeded"
    assert "spatialFacts" not in payload
    assert payload["ruleResults"] == []


def test_get_analysis_task_result_returns_ndb_rule_results() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    payload = response.json()
    rule_results = payload["ruleResults"]
    assert rule_results[0]["stationType"] == "NDB"
    assert rule_results[0]["stationName"] == "NDB Station"
    assert rule_results[0]["ruleName"] == "ndb_minimum_distance_50m"
    assert rule_results[0]["globalObstacleCategory"] == "building_general"
    assert "zoneDefinition" not in rule_results[0]


def test_get_analysis_task_result_returns_protection_zones() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    protection_zone = response.json()["protectionZones"][0]
    assert protection_zone["airportId"] == 1
    assert protection_zone["airportName"] == "Airport A"
    assert protection_zone["stationId"] == 101
    assert protection_zone["stationName"] == "NDB Station"
    assert protection_zone["stationType"] == "NDB"
    assert protection_zone["ruleCode"] == "ndb_minimum_distance_50m"
    assert protection_zone["ruleName"] == "ndb_minimum_distance_50m"
    assert protection_zone["zoneCode"] == "ndb_minimum_distance_50m"
    assert protection_zone["zoneName"] == "NDB 50m minimum distance zone"
    assert protection_zone["regionCode"] == "default"
    assert protection_zone["regionName"] == "default"
    assert protection_zone["geometry"]["shapeType"] == "multipolygon"
    assert "center" not in protection_zone["geometry"]
    assert len(protection_zone["geometry"]["coordinates"]) == 1
    assert len(protection_zone["geometry"]["coordinates"][0][0]) > 8
    assert protection_zone["vertical"] == {
        "mode": "flat",
        "baseReference": "station",
        "baseHeightMeters": 500.0,
    }
    assert protection_zone["properties"] == {
        "label": "NDB Station NDB 50m minimum distance zone default"
    }
    assert protection_zone["renderGeometry"] is None


def test_analysis_protection_zone_response_rejects_legacy_circle_geometry() -> None:
    try:
        AnalysisProtectionZoneResponse(
            id="airport-1-station-101-zone-ndb_minimum_distance_50m-region-default",
            airportId=1,
            airportName="Airport A",
            stationId=101,
            stationName="NDB Station",
            stationType="NDB",
            ruleCode="ndb_minimum_distance_50m",
            ruleName="ndb_minimum_distance_50m",
            zoneCode="ndb_minimum_distance_50m",
            zoneName="NDB 50m minimum distance zone",
            regionCode="default",
            regionName="default",
            geometry={
                "shapeType": "circle",
                "center": {
                    "longitude": 104.123456,
                    "latitude": 30.123456,
                },
                "radiusMeters": 50.0,
            },
            vertical={
                "mode": "flat",
                "baseReference": "station",
                "baseHeightMeters": 500.0,
            },
            properties={
                "label": "NDB Station NDB 50m minimum distance zone default"
            },
            renderGeometry=None,
        )
    except ValidationError as exc:
        assert "coordinates" in str(exc)
    else:
        raise AssertionError("legacy circle geometry should be rejected")


def test_get_analysis_task_result_returns_radial_band_analytic_surface_protection_zone() -> (
    None
):
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type, top_elevation = :top_elevation WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "top_elevation": 520.0,
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    radial_band_zone = next(
        item
        for item in response.json()["protectionZones"]
        if item["ruleCode"] == "ndb_conical_clearance_3deg"
    )
    assert radial_band_zone["geometry"]["shapeType"] == "multipolygon"
    assert "center" not in radial_band_zone["geometry"]
    assert len(radial_band_zone["geometry"]["coordinates"]) == 1
    assert len(radial_band_zone["geometry"]["coordinates"][0]) == 2
    assert radial_band_zone["vertical"] == {
        "mode": "analytic_surface",
        "baseReference": "station",
        "baseHeightMeters": 500.0,
        "surface": {
            "type": "distance_parameterized",
            "distanceSource": {
                "kind": "point",
                "point": [104.123456, 30.123456],
            },
            "distanceMetric": "radial",
            "clampRange": {
                "startMeters": 50.0,
                "endMeters": 37040.0,
            },
            "heightModel": {
                "type": "angle_linear_rise",
                "angleDegrees": 3.0,
                "distanceOffsetMeters": 50.0,
            },
        },
    }
    assert radial_band_zone["renderGeometry"] is None


def test_get_analysis_task_result_returns_offset_ndb_distance_source_point() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        airport_longitude = 104.123456
        airport_latitude = 30.123456
        station_longitude = 104.124456
        station_latitude = 30.123456

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=airport_longitude,
                    latitude=airport_latitude,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=station_longitude,
                    latitude=station_latitude,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type, top_elevation = :top_elevation WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "top_elevation": 520.0,
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    radial_band_zone = next(
        item
        for item in response.json()["protectionZones"]
        if item["ruleCode"] == "ndb_conical_clearance_3deg"
    )
    distance_source_point = radial_band_zone["vertical"]["surface"]["distanceSource"][
        "point"
    ]

    assert distance_source_point == [station_longitude, station_latitude]


def test_get_analysis_task_result_centers_ndb_protection_zone_on_station_point() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.124456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    protection_zone = next(
        item
        for item in response.json()["protectionZones"]
        if item["ruleCode"] == "ndb_minimum_distance_50m"
    )
    first_point = protection_zone["geometry"]["coordinates"][0][0][0]
    assert first_point[0] > 104.1248
    assert abs(first_point[1] - 30.123456) < 0.001


def test_get_analysis_task_result_returns_ndb_300m_rule_result_for_hill() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "山丘",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    rule_results = response.json()["ruleResults"]
    assert rule_results[0]["ruleName"] == "ndb_minimum_distance_300m"
    assert rule_results[0]["metrics"]["requiredDistanceMeters"] == 300.0


def test_get_analysis_task_result_returns_gb_and_mh_standards_for_ndb_rule() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    rule_result = response.json()["ruleResults"][0]
    assert rule_result["isCompliant"] is True
    assert rule_result["standards"] == {
        "gb": {
            "code": "GB_NDB_50m最小间距区域_50",
            "text": (
                "无方向信标天线与地形地物之间的最小间距：高于3m的树木、建筑物"
                "（机房除外）以及公路与台站最小允许间距50m。"
            ),
            "isCompliant": True,
        },
        "mh": {
            "code": "MH_NDB_50m最小间距区域_50",
            "text": (
                "无方向信标天线与地形地物之间的最小间距：建筑物（机房除外）、"
                "公路以及高于3m的树木与台站最小允许间距50m。"
            ),
            "isCompliant": True,
        },
    }


def test_get_analysis_task_result_returns_gb_and_mh_standards_for_ndb_conical_rule() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=104.123456,
                    latitude=30.123456,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type, top_elevation = :top_elevation WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "top_elevation": 520.0,
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    radial_band_rule = next(
        item
        for item in response.json()["ruleResults"]
        if item["ruleName"] == "ndb_conical_clearance_3deg"
    )
    assert radial_band_rule["isCompliant"] is True
    assert radial_band_rule["standards"] == {
        "gb": {
            "code": "GB_NDB_50米以外仰角区域",
            "text": "在无方向信标天线50m以外，不应有超出无方向信标天线中心底部为基准垂直张角3°的障碍物。",
            "isCompliant": True,
        },
        "mh": {
            "code": "MH_NDB_50米以外仰角区域",
            "text": "在无方向信标天线50m以外，不应有超出无方向信标天线中心底部基准垂直张角为3°的障碍物。",
            "isCompliant": True,
        },
    }


def test_get_analysis_task_result_returns_loc_site_protection_zone_as_multipolygon() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.add(
                Runway(
                    id=201,
                    airport_id=1,
                    run_number="18",
                    name="Runway 18/36",
                    longitude=103.975864,
                    latitude=30.507381,
                    direction=180.0,
                    length=600.0,
                    width=45.0,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="LOC Station",
                    airport_id=1,
                    station_type="LOC",
                    runway_no="18",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    loc_rule = response.json()["ruleResults"][0]
    assert loc_rule["stationType"] == "LOC"
    assert loc_rule["ruleName"] == "loc_site_protection"
    assert loc_rule["zoneCode"] == "loc_site_protection"
    assert loc_rule["regionCode"] == "default"
    assert "zoneDefinition" not in loc_rule
    assert loc_rule["standards"] == {
        "gb": {
            "code": "GB_ILSLOC_场地保护区",
            "text": "在航向信标台场地保护区内不应有障碍物存在。",
            "isCompliant": False,
        },
        "mh": {
            "code": "MH_ILSLOC_场地保护区",
            "text": "在航向信标台场地保护区内除必需的助航设施和滑行道外，不应有树木、建筑物（航向信标台机房除外）、道路、金属栅栏和架空线缆等障碍物。",
            "isCompliant": False,
        },
    }

    protection_zone = response.json()["protectionZones"][0]
    assert protection_zone["stationType"] == "LOC"
    assert protection_zone["ruleCode"] == "loc_site_protection"
    assert protection_zone["geometry"]["shapeType"] == "multipolygon"
    assert len(protection_zone["geometry"]["coordinates"]) == 1
    assert protection_zone["vertical"] == {
        "mode": "flat",
        "baseReference": "station",
        "baseHeightMeters": 500.0,
    }
    assert protection_zone["renderGeometry"] is None


def test_get_analysis_task_result_keeps_ndb_and_loc_outputs_stable_with_mixed_station_types() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.add(
                Runway(
                    id=201,
                    airport_id=1,
                    run_number="18",
                    name="Runway 18/36",
                    longitude=103.975864,
                    latitude=30.507381,
                    direction=180.0,
                    length=600.0,
                    width=45.0,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="NDB Station",
                    airport_id=1,
                    station_type="NDB",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=102,
                    name="LOC Station",
                    airport_id=1,
                    station_type="LOC",
                    runway_no="18",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)

        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    assert response.status_code == 200
    payload = response.json()
    rule_names_by_station_type = {
        (item["stationType"], item["ruleName"])
        for item in payload["ruleResults"]
    }
    assert ("NDB", "ndb_minimum_distance_50m") in rule_names_by_station_type
    assert ("NDB", "ndb_conical_clearance_3deg") in rule_names_by_station_type
    assert ("LOC", "loc_site_protection") in rule_names_by_station_type

    loc_rule = next(
        item
        for item in payload["ruleResults"]
        if item["stationType"] == "LOC"
    )
    assert loc_rule["zoneCode"] == "loc_site_protection"
    assert loc_rule["standards"]["gb"]["code"] == "GB_ILSLOC_场地保护区"

    ndb_rule = next(
        item
        for item in payload["ruleResults"]
        if item["stationType"] == "NDB"
        and item["ruleName"] == "ndb_minimum_distance_50m"
    )
    assert ndb_rule["standards"]["gb"]["code"] == "GB_NDB_50m最小间距区域_50"

    protection_zone_shapes = {
        (item["stationType"], item["geometry"]["shapeType"])
        for item in payload["protectionZones"]
    }
    assert ("LOC", "multipolygon") in protection_zone_shapes
    assert ("NDB", "multipolygon") in protection_zone_shapes


def test_build_airport_analysis_result_returns_only_internal_fields_still_in_use() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.add(
                Runway(
                    id=201,
                    airport_id=1,
                    run_number="18",
                    name="Runway 18/36",
                    longitude=103.975864,
                    latitude=30.507381,
                    direction=180.0,
                    length=600.0,
                    width=45.0,
                    altitude=500.0,
                )
            )
            session.add(
                Station(
                    id=101,
                    name="LOC Station",
                    airport_id=1,
                    station_type="LOC",
                    runway_no="18",
                    longitude=103.975864,
                    latitude=30.506881,
                    altitude=500.0,
                )
            )
            session.commit()

            obstacle = session.execute(
                text(
                    "SELECT id FROM obstacles WHERE source_batch_id = :source_batch_id ORDER BY id LIMIT 1"
                ),
                {"source_batch_id": import_task_id},
            ).scalar_one()
            session.execute(
                text(
                    "UPDATE obstacles SET obstacle_type = :obstacle_type WHERE id = :obstacle_id"
                ),
                {
                    "obstacle_type": "建筑物/构建物",
                    "obstacle_id": obstacle,
                },
            )
            session.commit()

            from app.application.polygon_obstacle_import import PolygonObstacleImportService
            from app.analysis.context_builder import build_airport_analysis_context

            service = PolygonObstacleImportService(session)
            context = build_airport_analysis_context(
                repository=service._repository,
                airport_ids=[1],
                import_batch_id=import_task_id,
            )[0]

            airport_result = service._build_airport_analysis_result(context)

    assert set(airport_result.keys()) == {"airportId", "obstacles", "ruleResults"}
    assert airport_result["airportId"] == 1
    assert airport_result["ruleResults"][0]["stationType"] == "LOC"
    assert "localGeometry" in airport_result["obstacles"][0]
    assert "geometry" in airport_result["obstacles"][0]
    assert "distanceToAirportMeters" not in airport_result["obstacles"][0]
    assert "localBoundingBox" not in airport_result["obstacles"][0]
def test_run_analysis_task_skips_station_without_coordinates() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=104.11,
                    latitude=30.11,
                )
            )
            session.execute(
                text(
                    """
                    INSERT INTO stations (
                        id, station_type, station_group, name, longitude, latitude,
                        altitude, station_sub_type, airport_id, created_at, updated_at
                    ) VALUES
                    (101, 'nav', NULL, 'Station A', 104.12, 30.12, 498.2, 'ils', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    (102, 'nav', NULL, 'Station B', NULL, NULL, 500.0, 'ils', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                )
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)
        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    airport_facts = response.json()["spatialFacts"]["airports"][0]
    assert "stations" not in airport_facts
    rule_results = airport_facts["ruleResults"]
    assert all(result["stationName"] == "NDB Station" for result in rule_results)


def test_run_analysis_task_fails_when_airport_has_no_coordinates() -> None:
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Airport(
                    id=1,
                    name="Airport A",
                    longitude=None,
                    latitude=None,
                )
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1])
        _run_analysis_task(client, analysis_task_id)
        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/status")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "analysis task failed"


def test_get_analysis_task_result_returns_parallel_airport_facts_for_multiple_targets() -> (
    None
):
    with _create_test_client() as client:
        import_task_id = _create_succeeded_import_task(client)

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(
                        id=1,
                        name="Airport A",
                        longitude=104.1,
                        latitude=30.1,
                    ),
                    Airport(
                        id=2,
                        name="Airport B",
                        longitude=104.2,
                        latitude=30.2,
                    ),
                ]
            )
            session.commit()

        analysis_task_id = _create_analysis_task(client, import_task_id, [1, 2])
        _run_analysis_task(client, analysis_task_id)
        response = client.get(f"/polygon-obstacle/analysis/{analysis_task_id}/result")

    airport_ids = [
        item["airportId"] for item in response.json()["spatialFacts"]["airports"]
    ]
    assert airport_ids == [1, 2]


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
        "spatialFacts": None,
        "protectionZones": [],
    }


def test_get_analysis_task_result_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/analysis/missing-task/result")

    assert response.status_code == 404
    assert response.json() == {"detail": "analysis task not found"}
