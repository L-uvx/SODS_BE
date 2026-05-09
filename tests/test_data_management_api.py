from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, UTC

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.application.data_management import DataManagementValidationError
from app.db.base import Base
from app.main import app
from app.models.airport import Airport
from app.models.runway import Runway
from app.models.station import Station


@contextmanager
def _create_test_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Airport.__table__,
            Runway.__table__,
            Station.__table__,
        ],
    )

    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(
            bind=engine,
            tables=[
                Station.__table__,
                Runway.__table__,
                Airport.__table__,
            ],
        )


def _seed_airport(name: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        session.add(Airport(name=name))
        session.commit()


def _seed_runway(airport_id: int, name: str, run_number: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        session.add(Runway(airport_id=airport_id, name=name, run_number=run_number))
        session.commit()


def _seed_station(airport_id: int, name: str, station_type: str) -> None:
    with next(iter(app.dependency_overrides[get_db_session]())) as session:
        session.add(Station(airport_id=airport_id, name=name, station_type=station_type))
        session.commit()


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
            Airport.__table__,
            Runway.__table__,
            Station.__table__,
        ],
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
        ],
    )
    app.dependency_overrides = {}


def test_airport_list_response_uses_pagination_envelope() -> None:
    with _create_test_client() as client:
        response = client.get("/data-management/airports")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
    }


def test_get_airport_detail_returns_airport_payload() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            airport = session.get(Airport, 1)
            assert airport is not None
            airport.longitude = 104.1
            airport.latitude = 30.6
            airport.altitude = 500.0
            session.commit()
        response = client.get("/data-management/airports/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Airport One",
        "longitude": 104.1,
        "latitude": 30.6,
        "altitude": 500.0,
    }


def test_create_airport_returns_created_airport_payload() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/data-management/airports",
            json={
                "name": "Airport One",
                "longitude": 104.1,
                "latitude": 30.6,
                "altitude": 500.0,
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "warnings": [],
    }


def test_create_airport_returns_structured_validation_error_detail() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/data-management/airports",
            json={
                "name": "Airport One",
                "longitude": 181.0,
            },
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"][0]["loc"] == ["body", "longitude"]
    assert payload["detail"][0]["type"] == "less_than_equal"


def test_create_airport_maps_service_validation_error_to_structured_422(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_validation(*args, **kwargs):
        raise DataManagementValidationError(
            "invalid_longitude",
            "longitude must be between -180 and 180",
        )

    monkeypatch.setattr(
        "app.api.data_management.DataManagementService.create_airport",
        _raise_validation,
    )

    with _create_test_client() as client:
        response = client.post(
            "/data-management/airports",
            json={
                "name": "Airport One",
                "longitude": 104.1,
                "latitude": 30.6,
                "altitude": 500.0,
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "invalid_longitude",
            "message": "longitude must be between -180 and 180",
        }
    }


def test_update_airport_returns_updated_airport_payload() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        response = client.put(
            "/data-management/airports/1",
            json={
                "name": "Airport One Updated",
                "longitude": 105.1,
                "latitude": 31.6,
                "altitude": 550.0,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "warnings": [],
    }


def test_list_airports_passes_supported_query_contract() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/airports",
            params={
                "keyword": "Airport",
                "hasCoordinates": "true",
                "page": 2,
                "pageSize": 50,
            },
        )

    assert response.status_code == 200


def test_list_airports_rejects_invalid_pagination_values() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/airports",
            params={
                "page": 0,
                "pageSize": 0,
            },
        )

    assert response.status_code == 422


def test_list_airports_with_has_coordinates_false_returns_all_airports() -> None:
    with _create_test_client() as client:
        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add_all(
                [
                    Airport(name="Airport With Coordinates", longitude=104.1, latitude=30.6),
                    Airport(name="Airport Without Coordinates"),
                    Airport(name="Another Airport", longitude=105.1, latitude=31.6),
                ]
            )
            session.commit()

        response = client.get(
            "/data-management/airports",
            params={"hasCoordinates": "false"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert [item["name"] for item in payload["items"]] == [
        "Airport With Coordinates",
        "Airport Without Coordinates",
        "Another Airport",
    ]


def test_airport_list_response_serializes_page_size_as_camel_case() -> None:
    from app.schemas.data_management import AirportListResponse

    response = AirportListResponse(items=[], total=0, page=1, pageSize=20)

    assert response.model_dump(by_alias=True) == {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
    }


def test_airport_list_item_response_includes_required_review_fields() -> None:
    from app.schemas.data_management import AirportListItemResponse

    timestamp = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    response = AirportListItemResponse(
        id=1,
        name="Airport One",
        longitude=114.123456,
        latitude=30.123456,
        altitude=42.5,
        runwayCount=2,
        stationCount=3,
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    assert response.model_dump(by_alias=True) == {
        "id": 1,
        "name": "Airport One",
        "longitude": 114.123456,
        "latitude": 30.123456,
        "altitude": 42.5,
        "runwayCount": 2,
        "stationCount": 3,
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }


def test_runway_list_item_response_includes_required_review_fields() -> None:
    from app.schemas.data_management import RunwayListItemResponse

    timestamp = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    response = RunwayListItemResponse(
        id=1,
        airportId=1,
        airportName="Airport One",
        name="Runway 18/36",
        runNumber="18",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    assert response.model_dump(by_alias=True) == {
        "id": 1,
        "airportId": 1,
        "airportName": "Airport One",
        "name": "Runway 18/36",
        "runNumber": "18",
        "headingDegrees": None,
        "lengthMeters": None,
        "width": None,
        "altitude": None,
        "longitude": None,
        "latitude": None,
        "enterHeight": None,
        "maximumAirworthiness": None,
        "stationSubType": None,
        "runwayCodeA": None,
        "runwayType": None,
        "runwayCodeB": None,
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }


def test_station_list_item_response_includes_required_review_fields() -> None:
    from app.schemas.data_management import StationListItemResponse

    timestamp = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    response = StationListItemResponse(
        id=1,
        airportId=1,
        airportName="Airport One",
        name="LOC Station",
        stationType="LOC",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    assert response.model_dump(by_alias=True) == {
        "id": 1,
        "airportId": 1,
        "airportName": "Airport One",
        "name": "LOC Station",
        "stationType": "LOC",
        "stationGroup": None,
        "frequency": None,
        "longitude": None,
        "latitude": None,
        "altitude": None,
        "coverageRadius": None,
        "flyHeight": None,
        "antennaHag": None,
        "runwayNo": None,
        "reflectionNetHag": None,
        "centerAntennaH": None,
        "bAntennaH": None,
        "bToCenterDistance": None,
        "reflectionDiameter": None,
        "downwardAngle": None,
        "antennaTag": None,
        "distanceToRunway": None,
        "distanceVToRunway": None,
        "distanceEndoRunway": None,
        "unitNumber": None,
        "aircraft": None,
        "antennaHeight": None,
        "stationSubType": None,
        "combineId": None,
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }


def test_runway_upsert_request_requires_run_number() -> None:
    from app.schemas.data_management import RunwayUpsertRequest

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(
            airportId=1,
            name="Runway 18/36",
        )


def test_airport_upsert_request_rejects_empty_name() -> None:
    from app.schemas.data_management import AirportUpsertRequest

    with pytest.raises(ValidationError):
        AirportUpsertRequest(name="   ")


def test_airport_upsert_request_rejects_out_of_range_coordinates() -> None:
    from app.schemas.data_management import AirportUpsertRequest

    with pytest.raises(ValidationError):
        AirportUpsertRequest(name="Airport One", longitude=181.0)

    with pytest.raises(ValidationError):
        AirportUpsertRequest(name="Airport One", latitude=91.0)


def test_airport_upsert_request_rejects_negative_altitude() -> None:
    from app.schemas.data_management import AirportUpsertRequest

    with pytest.raises(ValidationError):
        AirportUpsertRequest(name="Airport One", altitude=-1.0)


def test_runway_upsert_request_rejects_empty_name() -> None:
    from app.schemas.data_management import RunwayUpsertRequest

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="   ", runNumber="18")


def test_runway_upsert_request_rejects_blank_run_number() -> None:
    from app.schemas.data_management import RunwayUpsertRequest

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="Runway 18/36", runNumber="   ")


def test_runway_upsert_request_rejects_invalid_direction_and_negative_numbers() -> None:
    from app.schemas.data_management import RunwayUpsertRequest

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="Runway 18/36", runNumber="18", headingDegrees=360.0)

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="Runway 18/36", runNumber="18", headingDegrees=-1.0)

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="Runway 18/36", runNumber="18", lengthMeters=-1.0)


def test_runway_upsert_request_rejects_out_of_range_coordinates() -> None:
    from app.schemas.data_management import RunwayUpsertRequest

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="Runway 18/36", runNumber="18", longitude=-181.0)

    with pytest.raises(ValidationError):
        RunwayUpsertRequest(airportId=1, name="Runway 18/36", runNumber="18", latitude=-91.0)


def test_station_upsert_request_rejects_empty_name() -> None:
    from app.schemas.data_management import StationUpsertRequest

    with pytest.raises(ValidationError):
        StationUpsertRequest(airportId=1, name="   ", stationType="LOC")


def test_station_upsert_request_requires_station_type() -> None:
    from app.schemas.data_management import StationUpsertRequest

    with pytest.raises(ValidationError):
        StationUpsertRequest(
            airportId=1,
            name="LOC Station",
        )


def test_station_upsert_request_rejects_blank_station_type() -> None:
    from app.schemas.data_management import StationUpsertRequest

    with pytest.raises(ValidationError):
        StationUpsertRequest(airportId=1, name="LOC Station", stationType="   ")


def test_station_upsert_request_rejects_out_of_range_coordinates() -> None:
    from app.schemas.data_management import StationUpsertRequest

    with pytest.raises(ValidationError):
        StationUpsertRequest(airportId=1, name="LOC Station", stationType="LOC", longitude=181.0)

    with pytest.raises(ValidationError):
        StationUpsertRequest(airportId=1, name="LOC Station", stationType="LOC", latitude=-91.0)


def test_station_upsert_request_rejects_negative_numeric_fields() -> None:
    from app.schemas.data_management import StationUpsertRequest

    with pytest.raises(ValidationError):
        StationUpsertRequest(airportId=1, name="LOC Station", stationType="LOC", coverageRadius=-1.0)

    with pytest.raises(ValidationError):
        StationUpsertRequest(airportId=1, name="LOC Station", stationType="LOC", distanceToRunway=-1.0)


def test_runway_response_requires_non_null_run_number() -> None:
    from app.schemas.data_management import RunwayResponse

    with pytest.raises(ValidationError):
        RunwayResponse(
            id=1,
            airportId=1,
            name="Runway 18/36",
            runNumber=None,
        )


def test_station_response_requires_non_null_station_type() -> None:
    from app.schemas.data_management import StationResponse

    with pytest.raises(ValidationError):
        StationResponse(
            id=1,
            airportId=1,
            name="LOC Station",
            stationType=None,
        )


def test_list_runways_returns_pagination_envelope() -> None:
    with _create_test_client() as client:
        response = client.get("/data-management/runways")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
    }


def test_list_runways_passes_supported_query_contract() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/runways",
            params={
                "airportId": 1,
                "keyword": "Runway",
                "runNumber": "18",
                "page": 2,
                "pageSize": 50,
            },
        )

    assert response.status_code == 200


def test_list_runways_rejects_invalid_pagination_values() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/runways",
            params={
                "page": -1,
                "pageSize": 0,
            },
        )

    assert response.status_code == 422


def test_get_runway_detail_returns_runway_payload() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            session.add(
                Runway(
                    airport_id=1,
                    name="Runway 18/36",
                    run_number="18",
                    direction=180.0,
                    length=3200.0,
                    width=45.0,
                    altitude=500.0,
                    longitude=104.1,
                    latitude=30.6,
                    enter_height=12.0,
                    maximum_airworthiness=4.0,
                )
            )
            session.commit()
        response = client.get("/data-management/runways/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "airportId": 1,
        "name": "Runway 18/36",
        "runNumber": "18",
        "headingDegrees": 180.0,
        "lengthMeters": 3200.0,
        "width": 45.0,
        "altitude": 500.0,
        "longitude": 104.1,
        "latitude": 30.6,
        "enterHeight": 12.0,
        "maximumAirworthiness": 4.0,
        "stationSubType": None,
        "runwayCodeA": None,
        "runwayType": None,
        "runwayCodeB": None,
    }


def test_create_runway_rejects_when_airport_not_found() -> None:
    with _create_test_client() as client:
        response = client.post(
            "/data-management/runways",
            json={
                "airportId": 999,
                "name": "Runway 18/36",
                "runNumber": "18",
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "airport_not_found",
            "message": "airport not found",
        }
    }


def test_create_runway_rejects_duplicate_run_number_within_airport() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        response = client.post(
            "/data-management/runways",
            json={
                "airportId": 1,
                "name": "Runway Duplicate",
                "runNumber": "18",
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "duplicate_runway_number",
            "message": "runNumber already exists within airport",
        }
    }


def test_update_runway_returns_updated_runway_payload() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        response = client.put(
            "/data-management/runways/1",
            json={
                "airportId": 1,
                "name": "Runway 18/36 Updated",
                "runNumber": "18",
                "headingDegrees": 180.0,
                "lengthMeters": 3200.0,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "warnings": [],
    }


def test_create_runway_returns_write_response_with_alias_fields_accepted() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        response = client.post(
            "/data-management/runways",
            json={
                "airportId": 1,
                "name": "Runway 18/36",
                "runNumber": "18",
                "headingDegrees": 180.0,
                "lengthMeters": 3200.0,
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "warnings": [],
    }


def test_list_runways_accepts_string_airport_id_query_param() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/runways",
            params={"airportId": "1"},
        )

    assert response.status_code == 200


def test_list_runways_response_includes_created_at() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        response = client.get("/data-management/runways")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["createdAt"]


def test_list_stations_response_includes_created_at() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_station(airport_id=1, name="LOC Station", station_type="LOC")
        response = client.get("/data-management/stations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["createdAt"]


def test_runway_upsert_request_accepts_frontend_alias_fields() -> None:
    from app.schemas.data_management import RunwayUpsertRequest

    payload = RunwayUpsertRequest(
        airportId=1,
        name="Runway 18/36",
        runNumber="18",
        headingDegrees=180.0,
        lengthMeters=3200.0,
    )

    assert payload.direction == 180.0
    assert payload.length == 3200.0


def test_runway_response_serializes_frontend_alias_fields() -> None:
    from app.schemas.data_management import RunwayResponse

    response = RunwayResponse(
        id=1,
        airportId=1,
        name="Runway 18/36",
        runNumber="18",
        direction=180.0,
        length=3200.0,
    )

    dumped = response.model_dump(by_alias=True)
    assert dumped["headingDegrees"] == 180.0
    assert dumped["lengthMeters"] == 3200.0


def test_list_stations_returns_pagination_envelope() -> None:
    with _create_test_client() as client:
        response = client.get("/data-management/stations")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
    }


def test_list_stations_passes_supported_query_contract() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/stations",
            params={
                "airportId": 1,
                "stationType": "LOC",
                "keyword": "Station",
                "runwayNo": "18",
                "page": 2,
                "pageSize": 50,
            },
        )

    assert response.status_code == 200


def test_list_stations_accepts_string_airport_id_query_param() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/stations",
            params={
                "airportId": "1",
                "page": 1,
                "pageSize": 20,
            },
        )

    assert response.status_code == 200


def test_list_stations_rejects_invalid_pagination_values() -> None:
    with _create_test_client() as client:
        response = client.get(
            "/data-management/stations",
            params={
                "page": 0,
                "pageSize": -1,
            },
        )

    assert response.status_code == 422


def test_get_station_detail_returns_station_payload() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_station(airport_id=1, name="LOC Station", station_type="LOC")
        response = client.get("/data-management/stations/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "airportId": 1,
        "name": "LOC Station",
        "stationType": "LOC",
        "stationGroup": None,
        "frequency": None,
        "longitude": None,
        "latitude": None,
        "altitude": None,
        "coverageRadius": None,
        "flyHeight": None,
        "antennaHag": None,
        "runwayNo": None,
        "reflectionNetHag": None,
        "centerAntennaH": None,
        "bAntennaH": None,
        "bToCenterDistance": None,
        "reflectionDiameter": None,
        "downwardAngle": None,
        "antennaTag": None,
        "distanceToRunway": None,
        "distanceVToRunway": None,
        "distanceEndoRunway": None,
        "unitNumber": None,
        "aircraft": None,
        "antennaHeight": None,
        "stationSubType": None,
        "combineId": None,
    }


def test_update_station_returns_updated_station_payload() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_station(airport_id=1, name="LOC Station", station_type="LOC")
        response = client.put(
            "/data-management/stations/1",
            json={
                "airportId": 1,
                "name": "LOC Station Updated",
                "stationType": "LOC",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "warnings": [],
    }


def test_update_station_with_runway_no_returns_empty_warnings() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_station(airport_id=1, name="LOC Station", station_type="LOC")
        response = client.put(
            "/data-management/stations/1",
            json={
                "airportId": 1,
                "name": "LOC Station Updated",
                "stationType": "LOC",
                "runwayNo": "18",
            },
        )

    assert response.status_code == 200
    assert response.json()["warnings"] == []


def test_conflict_detail_response_serializes_optional_counts() -> None:
    from app.schemas.data_management import ConflictDetailResponse

    response = ConflictDetailResponse(
        code="airport_has_children",
        message="airport has child records",
        runwayCount=2,
        stationCount=3,
        referencedStationCount=1,
    )

    assert response.model_dump(by_alias=True) == {
        "code": "airport_has_children",
        "message": "airport has child records",
        "runwayCount": 2,
        "stationCount": 3,
        "referencedStationCount": 1,
    }


def test_conflict_response_envelope_serializes_detail_under_detail_key() -> None:
    from app.schemas.data_management import ConflictResponseEnvelope

    response = ConflictResponseEnvelope(
        detail={
            "code": "runway_has_stations",
            "message": "runway is referenced by stations",
            "referencedStationCount": 2,
        }
    )

    assert response.model_dump(by_alias=True) == {
        "detail": {
            "code": "runway_has_stations",
            "message": "runway is referenced by stations",
            "runwayCount": None,
            "stationCount": None,
            "referencedStationCount": 2,
        }
    }


def test_option_item_response_serializes_minimal_select_shape() -> None:
    from app.schemas.data_management import OptionItemResponse

    response = OptionItemResponse(id=1, name="Airport One")

    assert response.model_dump(by_alias=True) == {
        "id": 1,
        "name": "Airport One",
    }


def test_station_type_option_response_serializes_value_label_shape() -> None:
    from app.schemas.data_management import StationTypeOptionResponse

    response = StationTypeOptionResponse(value="NDB", label="NDB")

    assert response.model_dump(by_alias=True) == {
        "value": "NDB",
        "label": "NDB",
    }


def test_station_create_with_runway_no_returns_empty_warnings() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        response = client.post(
            "/data-management/stations",
            json={
                "airportId": 1,
                "name": "NDB Station",
                "stationType": "NDB",
                "runwayNo": "18",
            },
        )

    assert response.status_code == 201
    assert response.json()["warnings"] == []


def test_station_create_returns_created_id_without_warning() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        response = client.post(
            "/data-management/stations",
            json={
                "airportId": 1,
                "name": "LOC Station",
                "stationType": "LOC",
                "runwayNo": "18",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "warnings": [],
    }


def test_delete_airport_conflict_returns_structured_detail_under_detail() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        _seed_station(airport_id=1, name="NDB Station", station_type="NDB")
        response = client.delete("/data-management/airports/1")

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "airport_has_children",
            "message": "airport has child records",
            "runwayCount": 1,
            "stationCount": 1,
        }
    }


def test_delete_runway_conflict_returns_referenced_station_count_detail() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        _seed_station(airport_id=1, name="LOC Station", station_type="LOC")
        with next(iter(app.dependency_overrides[get_db_session]())) as session:
            station = session.get(Station, 1)
            assert station is not None
            station.runway_no = "18"
            session.commit()
        response = client.delete("/data-management/runways/1")

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "runway_has_stations",
            "message": "runway is referenced by stations",
            "referencedStationCount": 1,
        }
    }


def test_openapi_documents_data_management_domain_error_responses() -> None:
    with _create_test_client() as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    airport_post = payload["paths"]["/data-management/airports"]["post"]
    runway_delete = payload["paths"]["/data-management/runways/{runway_id}"]["delete"]
    stations_get = payload["paths"]["/data-management/stations"]["get"]

    assert "422" in airport_post["responses"]
    assert "409" in runway_delete["responses"]
    assert airport_post["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/HTTPValidationError")
    assert runway_delete["responses"]["409"]["content"]["application/json"]["schema"]["$ref"].endswith("/DomainErrorResponse")
    assert "404" not in stations_get["responses"]
    assert "409" not in stations_get["responses"]


def test_options_airports_returns_minimal_select_items() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        response = client.get("/data-management/options/airports")

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "Airport One"}]


def test_options_station_types_returns_value_label_items() -> None:
    with _create_test_client() as client:
        response = client.get("/data-management/options/station-types")

    assert response.status_code == 200
    assert response.json() == [{"value": "NDB", "label": "NDB"}]


def test_airport_runway_options_returns_minimal_select_items() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_runway(airport_id=1, name="Runway 18/36", run_number="18")
        response = client.get("/data-management/airports/1/runways/options")

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "Runway 18/36"}]


def test_delete_station_returns_no_content() -> None:
    with _create_test_client() as client:
        _seed_airport(name="Airport One")
        _seed_station(airport_id=1, name="VOR Station", station_type="VOR")
        response = client.delete("/data-management/stations/1")

    assert response.status_code == 204


def test_station_create_response_serializes_empty_warnings() -> None:
    from app.schemas.data_management import StationCreateResponse

    response = StationCreateResponse(id=1, warnings=[])

    assert response.model_dump(by_alias=True) == {"id": 1, "warnings": []}


def test_station_write_response_serializes_empty_warnings() -> None:
    from app.schemas.data_management import StationWriteResponse

    response = StationWriteResponse(id=1, warnings=[])

    assert response.model_dump(by_alias=True) == {"id": 1, "warnings": []}


def test_airport_write_response_serializes_id_and_warnings() -> None:
    from app.schemas.data_management import AirportWriteResponse

    response = AirportWriteResponse(id=1, warnings=[])

    assert response.model_dump(by_alias=True) == {
        "id": 1,
        "warnings": [],
    }


def test_runway_write_response_serializes_id_and_warnings() -> None:
    from app.schemas.data_management import RunwayWriteResponse

    response = RunwayWriteResponse(id=1, warnings=[])

    assert response.model_dump(by_alias=True) == {
        "id": 1,
        "warnings": [],
    }


def test_station_write_response_serializes_id_and_warnings() -> None:
    from app.schemas.data_management import StationWriteResponse

    response = StationWriteResponse(id=1, warnings=[])

    assert response.model_dump(by_alias=True) == {"id": 1, "warnings": []}


def test_repository_runway_number_exists_rejects_duplicate_within_same_airport() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        another_airport = Airport(name="Airport Two")
        session.add_all([airport, another_airport])
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"),
                Runway(airport_id=another_airport.id, name="Runway 18/36", run_number="18"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)

        assert repository.runway_number_exists(airport.id, "18") is True
        assert repository.runway_number_exists(airport.id, "18", exclude_runway_id=1) is False
        assert repository.runway_number_exists(airport.id, "36") is False


def test_repository_counts_airport_children_for_delete_guard() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"),
                Runway(airport_id=airport.id, name="Runway 09/27", run_number="09"),
                Station(airport_id=airport.id, name="NDB Station", station_type="NDB"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)

        assert repository.count_runways_by_airport_id(airport.id) == 2
        assert repository.count_stations_by_airport_id(airport.id) == 1


def test_repository_counts_stations_referencing_runway_number_for_delete_guard() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        another_airport = Airport(name="Airport Two")
        session.add_all([airport, another_airport])
        session.flush()
        runway = Runway(airport_id=airport.id, name="Runway 18/36", run_number="18")
        session.add(runway)
        session.flush()
        session.add_all(
            [
                Station(
                    airport_id=airport.id,
                    name="LOC Station 1",
                    station_type="LOC",
                    runway_no="18",
                ),
                Station(
                    airport_id=airport.id,
                    name="LOC Station 2",
                    station_type="LOC",
                    runway_no="18",
                ),
                Station(
                    airport_id=airport.id,
                    name="LOC Station 3",
                    station_type="LOC",
                    runway_no="36",
                ),
                Station(
                    airport_id=another_airport.id,
                    name="LOC Station 4",
                    station_type="LOC",
                    runway_no="18",
                ),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)

        assert repository.count_stations_referencing_runway(runway.id) == 2


def test_service_create_runway_rejects_duplicate_run_number_within_airport() -> None:
    from app.application.data_management import (
        DataManagementConflictError,
        DataManagementService,
    )
    from app.schemas.data_management import RunwayUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add(Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"))
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementConflictError) as exc_info:
            service.create_runway(
                RunwayUpsertRequest(
                    airportId=airport.id,
                    name="Runway Duplicate",
                    runNumber="18",
                )
            )

    assert exc_info.value.code == "duplicate_runway_number"
    assert exc_info.value.message == "runNumber already exists within airport"


def test_service_update_runway_rejects_duplicate_run_number_within_same_airport() -> None:
    from app.application.data_management import (
        DataManagementConflictError,
        DataManagementService,
    )
    from app.schemas.data_management import RunwayUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"),
                Runway(airport_id=airport.id, name="Runway 09/27", run_number="09"),
            ]
        )
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementConflictError) as exc_info:
            service.update_runway(
                2,
                RunwayUpsertRequest(
                    airportId=airport.id,
                    name="Runway 09/27 Updated",
                    runNumber="18",
                ),
            )

    assert exc_info.value.code == "duplicate_runway_number"
    assert exc_info.value.message == "runNumber already exists within airport"


def test_service_update_runway_allows_keeping_its_own_run_number() -> None:
    from app.application.data_management import DataManagementService
    from app.schemas.data_management import RunwayUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"),
                Runway(airport_id=airport.id, name="Runway 09/27", run_number="09"),
            ]
        )
        session.commit()

        service = DataManagementService(session)

        updated_runway = service.update_runway(
            1,
            RunwayUpsertRequest(
                airportId=airport.id,
                name="Runway 18/36 Updated",
                runNumber="18",
            ),
        )

    assert updated_runway.id == 1
    assert updated_runway.warnings == []


def test_service_update_runway_rejects_identity_change_when_referenced_by_station() -> None:
    from app.application.data_management import (
        DataManagementConflictError,
        DataManagementService,
    )
    from app.schemas.data_management import RunwayUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        another_airport = Airport(name="Airport Two")
        session.add_all([airport, another_airport])
        session.flush()
        runway = Runway(airport_id=airport.id, name="Runway 18/36", run_number="18")
        session.add(runway)
        session.flush()
        session.add(
            Station(
                airport_id=airport.id,
                name="LOC Station",
                station_type="LOC",
                runway_no="18",
            )
        )
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementConflictError) as exc_info:
            service.update_runway(
                runway.id,
                RunwayUpsertRequest(
                    airportId=another_airport.id,
                    name="Runway 18/36 Updated",
                    runNumber="19",
                ),
            )

    assert exc_info.value.code == "runway_referenced_by_station"
    assert exc_info.value.message == "runway is referenced by stations"
    assert exc_info.value.extra == {"referencedStationCount": 1}


def test_service_delete_airport_rejects_when_child_records_exist() -> None:
    from app.application.data_management import (
        DataManagementConflictError,
        DataManagementService,
    )

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"),
                Station(airport_id=airport.id, name="LOC Station", station_type="LOC"),
            ]
        )
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementConflictError) as exc_info:
            service.delete_airport(airport.id)

    assert exc_info.value.code == "airport_has_children"
    assert exc_info.value.message == "airport has child records"
    assert exc_info.value.extra == {"runwayCount": 1, "stationCount": 1}


def test_service_delete_runway_rejects_when_station_references_runway_number() -> None:
    from app.application.data_management import (
        DataManagementConflictError,
        DataManagementService,
    )

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        runway = Runway(airport_id=airport.id, name="Runway 18/36", run_number="18")
        session.add(runway)
        session.flush()
        session.add(
            Station(
                airport_id=airport.id,
                name="LOC Station",
                station_type="LOC",
                runway_no="18",
            )
        )
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementConflictError) as exc_info:
            service.delete_runway(runway.id)

    assert exc_info.value.code == "runway_referenced_by_station"
    assert exc_info.value.message == "runway is referenced by stations"
    assert exc_info.value.extra == {"referencedStationCount": 1}


def test_service_create_station_with_runway_no_returns_empty_warnings() -> None:
    from app.application.data_management import DataManagementService
    from app.schemas.data_management import StationUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.commit()

        service = DataManagementService(session)

        station, warnings = service.create_station(
            StationUpsertRequest(
                airportId=airport.id,
                name="LOC Station",
                stationType="LOC",
                runwayNo="18",
            )
        )

    assert station.id == 1
    assert station.runway_no == "18"
    assert warnings == []


def test_service_update_station_with_runway_no_returns_empty_warnings() -> None:
    from app.application.data_management import DataManagementService
    from app.schemas.data_management import StationUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        station = Station(airport_id=airport.id, name="LOC Station", station_type="LOC")
        session.add(station)
        session.commit()

        service = DataManagementService(session)

        updated_station, warnings = service.update_station(
            station.id,
            StationUpsertRequest(
                airportId=airport.id,
                name="LOC Station Updated",
                stationType="LOC",
                runwayNo="18",
            ),
        )

    assert updated_station.name == "LOC Station Updated"
    assert updated_station.runway_no == "18"
    assert warnings == []


def test_service_create_station_requires_station_type() -> None:
    from app.application.data_management import DataManagementValidationError, DataManagementService
    from app.schemas.data_management import StationUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementValidationError) as exc_info:
            service.create_station(
                StationUpsertRequest(
                    airportId=airport.id,
                    name="LOC Station",
                    stationType="LOC",
                ).model_copy(update={"station_type": "   "})
            )

    assert exc_info.value.code == "invalid_station_type"
    assert exc_info.value.message == "stationType must not be empty"


def test_service_create_airport_rejects_out_of_range_coordinates() -> None:
    from app.application.data_management import DataManagementValidationError, DataManagementService
    from app.schemas.data_management import AirportUpsertRequest

    with _create_test_session() as session:
        service = DataManagementService(session)

        with pytest.raises(DataManagementValidationError) as exc_info:
            service.create_airport(
                AirportUpsertRequest(
                    name="Airport One",
                    longitude=104.1,
                    latitude=30.6,
                ).model_copy(update={"longitude": 181.0})
            )

    assert exc_info.value.code == "invalid_longitude"
    assert exc_info.value.message == "longitude must be between -180 and 180"


def test_service_create_station_rejects_negative_numeric_field() -> None:
    from app.application.data_management import DataManagementValidationError, DataManagementService
    from app.schemas.data_management import StationUpsertRequest

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.commit()

        service = DataManagementService(session)

        with pytest.raises(DataManagementValidationError) as exc_info:
            service.create_station(
                StationUpsertRequest(
                    airportId=airport.id,
                    name="LOC Station",
                    stationType="LOC",
                ).model_copy(update={"distance_to_runway": -1.0})
            )

    assert exc_info.value.code == "invalid_distance_to_runway"
    assert exc_info.value.message == "distanceToRunway must be greater than or equal to 0"


def test_repository_lists_airports_with_offset_and_limit() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        session.add_all(
            [
                Airport(name="Airport 1"),
                Airport(name="Airport 2"),
                Airport(name="Airport 3"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        airports, total = repository.list_airports(offset=1, limit=1)

        assert total == 3
        assert [airport.name for airport in airports] == ["Airport 2"]


def test_repository_lists_airports_with_filters() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        session.add_all(
            [
                Airport(name="Airport With Coordinates", longitude=104.1, latitude=30.6),
                Airport(name="Airport Without Coordinates"),
                Airport(name="Another Airport", longitude=105.1, latitude=31.6),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        airports, total = repository.list_airports(
            offset=0,
            limit=20,
            keyword="Airport",
            has_coordinates=True,
        )

        assert total == 2
        assert [airport.name for airport in airports] == [
            "Airport With Coordinates",
            "Another Airport",
        ]


def test_repository_list_airports_with_has_coordinates_false_matches_unfiltered_results() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        session.add_all(
            [
                Airport(name="Airport With Coordinates", longitude=104.1, latitude=30.6),
                Airport(name="Airport Without Coordinates"),
                Airport(name="Another Airport", longitude=105.1, latitude=31.6),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        unfiltered_airports, unfiltered_total = repository.list_airports(offset=0, limit=20)
        filtered_airports, filtered_total = repository.list_airports(
            offset=0,
            limit=20,
            has_coordinates=False,
        )

        assert filtered_total == unfiltered_total == 3
        assert [airport.name for airport in filtered_airports] == [
            airport.name for airport in unfiltered_airports
        ]


def test_repository_lists_runways_with_offset_and_limit() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 01", run_number="01"),
                Runway(airport_id=airport.id, name="Runway 02", run_number="02"),
                Runway(airport_id=airport.id, name="Runway 03", run_number="03"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        runways, total = repository.list_runways(offset=1, limit=1)

        assert total == 3
        assert [(runway.id, runway.name, runway.run_number) for runway in runways] == [
            (2, "Runway 02", "02")
        ]


def test_repository_lists_runways_with_filters() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        another_airport = Airport(name="Airport Two")
        session.add_all([airport, another_airport])
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 01", run_number="01"),
                Runway(airport_id=airport.id, name="Runway 02", run_number="02"),
                Runway(airport_id=another_airport.id, name="Runway 03", run_number="03"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        runways, total = repository.list_runways(
            offset=0,
            limit=20,
            airport_id=airport.id,
            keyword="Runway",
            run_number="02",
        )

        assert total == 1
        assert [(runway.id, runway.name, runway.run_number) for runway in runways] == [
            (2, "Runway 02", "02")
        ]


def test_repository_lists_stations_with_offset_and_limit() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Station(airport_id=airport.id, name="Station 01", station_type="NDB"),
                Station(airport_id=airport.id, name="Station 02", station_type="LOC"),
                Station(airport_id=airport.id, name="Station 03", station_type="VOR"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        stations, total = repository.list_stations(offset=1, limit=1)

        assert total == 3
        assert [(station.id, station.name, station.station_type) for station in stations] == [
            (2, "Station 02", "LOC")
        ]


def test_repository_lists_stations_with_filters() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        another_airport = Airport(name="Airport Two")
        session.add_all([airport, another_airport])
        session.flush()
        session.add_all(
            [
                Station(airport_id=airport.id, name="Station 01", station_type="NDB", runway_no="01"),
                Station(airport_id=airport.id, name="Station 02", station_type="LOC", runway_no="02"),
                Station(airport_id=another_airport.id, name="Station 03", station_type="VOR", runway_no="03"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        stations, total = repository.list_stations(
            offset=0,
            limit=20,
            airport_id=airport.id,
            station_type="LOC",
            keyword="Station",
            runway_no="02",
        )

        assert total == 1
        assert [(station.id, station.name, station.station_type) for station in stations] == [
            (2, "Station 02", "LOC")
        ]


def test_repository_lists_runway_options_by_airport() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        another_airport = Airport(name="Airport Two")
        session.add_all([airport, another_airport])
        session.flush()
        session.add_all(
            [
                Runway(airport_id=airport.id, name="Runway 09/27", run_number="09"),
                Runway(airport_id=airport.id, name="Runway 18/36", run_number="18"),
                Runway(airport_id=another_airport.id, name="Runway Other", run_number="01"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        runways = repository.list_runway_options_by_airport_id(airport.id)

        assert [(runway.id, runway.name) for runway in runways] == [
            (1, "Runway 09/27"),
            (2, "Runway 18/36"),
        ]


def test_repository_lists_airport_options() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        session.add_all([Airport(name="Airport One"), Airport(name="Airport Two")])
        session.commit()

        repository = DataManagementRepository(session)
        airports = repository.list_airport_options()

        assert [(airport.id, airport.name) for airport in airports] == [
            (1, "Airport One"),
            (2, "Airport Two"),
        ]


def test_repository_lists_station_type_options() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.flush()
        session.add_all(
            [
                Station(airport_id=airport.id, name="Station 01", station_type="LOC"),
                Station(airport_id=airport.id, name="Station 02", station_type="NDB"),
                Station(airport_id=airport.id, name="Station 03", station_type="LOC"),
            ]
        )
        session.commit()

        repository = DataManagementRepository(session)
        station_types = repository.list_station_type_options()

        assert station_types == ["LOC", "NDB"]


def test_repository_crud_for_airport_runway_and_station() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        repository = DataManagementRepository(session)

        airport = repository.create_airport(name="Airport One", longitude=104.1)
        runway = repository.create_runway(
            airport_id=airport.id,
            name="Runway 18/36",
            run_number="18",
        )
        station = repository.create_station(
            airport_id=airport.id,
            name="LOC Station",
            station_type="LOC",
            runway_no="18",
        )

        assert repository.get_airport(airport.id) is not None
        assert repository.get_runway(runway.id) is not None
        assert repository.get_station(station.id) is not None

        repository.update_airport(airport, name="Airport One Updated")
        repository.update_runway(runway, name="Runway Updated", run_number="36")
        repository.update_station(station, name="LOC Station Updated", runway_no="36")
        session.commit()

        assert repository.get_airport(airport.id).name == "Airport One Updated"
        assert repository.get_runway(runway.id).run_number == "36"
        assert repository.get_station(station.id).runway_no == "36"

        repository.delete_station(station)
        repository.delete_runway(runway)
        repository.delete_airport(airport)
        session.commit()

        assert repository.get_station(station.id) is None
        assert repository.get_runway(runway.id) is None
        assert repository.get_airport(airport.id) is None


def test_repository_update_rejects_unknown_field_name() -> None:
    from app.repository.data_management_repository import DataManagementRepository

    with _create_test_session() as session:
        airport = Airport(name="Airport One")
        session.add(airport)
        session.commit()

        repository = DataManagementRepository(session)

        with pytest.raises(ValueError, match="unknown field: not_a_real_field"):
            repository.update_airport(airport, not_a_real_field="boom")
