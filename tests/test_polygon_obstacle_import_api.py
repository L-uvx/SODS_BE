from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.db.base import Base
from app.main import app
from app.models.airport import Airport
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
        tables=[Project.__table__, ImportBatch.__table__, Airport.__table__],
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
        tables=[Airport.__table__, ImportBatch.__table__, Project.__table__],
    )
    app.dependency_overrides = {}


def test_create_import_task_returns_minimal_task_payload() -> None:
    with _create_test_client() as client:
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
        "status": "succeeded",
        "message": "import task created",
        "progressPercent": 100,
        "projectId": 1,
        "obstacleBatchId": "import-batch-1",
    }


def test_get_import_task_status_returns_existing_task() -> None:
    with _create_test_client() as client:
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
        "status": "succeeded",
        "message": "import task created",
        "progressPercent": 100,
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
        "status": "succeeded",
        "projectId": 1,
        "obstacleBatchId": task_id,
        "importedCount": 2,
        "failedCount": 0,
        "boundingBox": None,
        "obstacles": [
            {
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
            },
            {
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
            },
        ],
    }


def test_create_import_task_persists_obstacles_to_database() -> None:
    with _create_test_client() as client:
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
    assert len(obstacles) == 2
    assert obstacles[0].name == "障碍物1"
    assert obstacles[0].project_id == 1
    assert obstacles[0].source_batch_id == "import-batch-1"
    assert obstacles[0].obstacle_type == "building"
    assert float(obstacles[0].top_elevation) == 549.9
    assert json.loads(obstacles[0].raw_payload) == {
        "sourceRowNumbers": [2, 3, 4, 5, 6],
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
        "points": [
            {
                "rowNumber": 2,
                "longitudeText": '103°58′33.11"',
                "latitudeText": '030°30′24.77"',
                "longitudeDecimal": 103.9758638888889,
                "latitudeDecimal": 30.506880555555554,
            },
            {
                "rowNumber": 3,
                "longitudeText": '103°58′41.20"',
                "latitudeText": '030°30′20.34"',
                "longitudeDecimal": 103.97811111111112,
                "latitudeDecimal": 30.50565,
            },
            {
                "rowNumber": 4,
                "longitudeText": '103°58′36.87"',
                "latitudeText": '030°30′13.91"',
                "longitudeDecimal": 103.97690833333334,
                "latitudeDecimal": 30.50386388888889,
            },
            {
                "rowNumber": 5,
                "longitudeText": '103°58′27.30"',
                "latitudeText": '030°30′18.37"',
                "longitudeDecimal": 103.97425,
                "latitudeDecimal": 30.50510277777778,
            },
            {
                "rowNumber": 6,
                "longitudeText": '103°58′27.19"',
                "latitudeText": '030°30′18.87"',
                "longitudeDecimal": 103.97421944444444,
                "latitudeDecimal": 30.505241666666667,
            },
        ],
    }


def test_get_import_task_result_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/import/missing-task/result")

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


def test_get_import_targets_returns_all_airports_with_placeholder_distance() -> None:
    with _create_test_client() as client:
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
            "distance": 15.69,
            "distanceUnit": "km",
        },
    ]


def test_get_import_targets_returns_404_for_unknown_task() -> None:
    with _create_test_client() as client:
        response = client.get("/polygon-obstacle/import/missing-task/targets")

    assert response.status_code == 404
    assert response.json() == {"detail": "import task not found"}


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


def test_create_import_task_returns_400_for_invalid_excel_template() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("invalid.xlsx", _build_invalid_excel_bytes())},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "invalid header row: expected ['障碍物名称', '经度', '纬度', '顶部高程'], got ['经度', '障碍物名称', '纬度', '顶部高程']"
    }


def test_create_import_task_returns_400_for_non_excel_file() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/polygon-obstacle/import",
            data={
                "projectName": "Wuhan Demo",
                "obstacleType": "building",
            },
            files={"excelFile": ("invalid.txt", b"not-an-excel-file")},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid excel file"}
