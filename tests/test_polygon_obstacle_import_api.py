from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.db.base import Base
from app.main import app
from app.models.airport import Airport
from app.models.import_batch import ImportBatch
from app.models.project import Project


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
            files={"excelFile": ("demo.xlsx", b"fake-excel-content")},
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
            files={"excelFile": ("demo.xlsx", b"fake-excel-content")},
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
            files={"excelFile": ("demo.xlsx", b"fake-excel-content")},
        )
        task_id = create_response.json()["taskId"]

        response = client.get(f"/polygon-obstacle/import/{task_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "taskId": task_id,
        "status": "succeeded",
        "projectId": 1,
        "obstacleBatchId": task_id,
        "importedCount": 0,
        "failedCount": 0,
        "boundingBox": None,
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
            files={"excelFile": ("demo.xlsx", b"fake-excel-content")},
        )
        task_id = create_response.json()["taskId"]

        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(name="Airport B"),
                    Airport(name="Airport A"),
                ]
            )
            session.commit()

        response = client.get(f"/polygon-obstacle/import/{task_id}/targets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Airport B",
            "category": "",
            "distance": 0,
            "distanceUnit": "m",
        },
        {
            "id": 2,
            "name": "Airport A",
            "category": "",
            "distance": 0,
            "distanceUnit": "m",
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
