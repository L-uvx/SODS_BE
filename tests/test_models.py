import app.db.models  # noqa: F401

from app.db.base import Base


def test_project_and_obstacle_tables_are_registered() -> None:
    assert "projects" in Base.metadata.tables
    assert "import_batches" in Base.metadata.tables
    assert "analysis_tasks" in Base.metadata.tables
    assert "obstacles" in Base.metadata.tables
    assert "airports" in Base.metadata.tables
    assert "runways" in Base.metadata.tables
    assert "stations" in Base.metadata.tables


def test_obstacle_has_project_foreign_key() -> None:
    obstacle_table = Base.metadata.tables["obstacles"]
    foreign_keys = list(obstacle_table.c.project_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "projects.id"


def test_obstacle_uses_json_and_geometry_columns() -> None:
    obstacle_table = Base.metadata.tables["obstacles"]

    assert obstacle_table.c.raw_payload.type.python_type is dict
    assert obstacle_table.c.top_elevation.nullable is True
    assert obstacle_table.c.geom.type.geometry_type == "MULTIPOLYGON"
    assert obstacle_table.c.geom.type.srid == 4326


def test_import_batch_has_project_foreign_key_and_status() -> None:
    import_batch_table = Base.metadata.tables["import_batches"]
    foreign_keys = list(import_batch_table.c.project_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "projects.id"
    assert import_batch_table.c.status.nullable is False
    assert import_batch_table.c.status.type.length == 50


def test_analysis_task_has_import_batch_foreign_key_and_json_columns() -> None:
    analysis_task_table = Base.metadata.tables["analysis_tasks"]
    foreign_keys = list(analysis_task_table.c.import_batch_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "import_batches.id"
    assert analysis_task_table.c.status.nullable is False
    assert analysis_task_table.c.selected_target_ids.nullable is False
    assert analysis_task_table.c.result_payload.type.python_type is dict


def test_obstacle_source_batch_matches_import_batch_key_type() -> None:
    obstacle_table = Base.metadata.tables["obstacles"]
    import_batch_table = Base.metadata.tables["import_batches"]

    assert type(obstacle_table.c.source_batch_id.type) is type(
        import_batch_table.c.id.type
    )


def test_airport_has_expected_core_columns() -> None:
    airport_table = Base.metadata.tables["airports"]

    assert airport_table.c.name.nullable is False
    assert airport_table.c.longitude.type.scale == 6
    assert airport_table.c.latitude.type.scale == 6
    assert airport_table.c.altitude.type.scale == 3


def test_runway_has_required_airport_foreign_key() -> None:
    runway_table = Base.metadata.tables["runways"]
    foreign_keys = list(runway_table.c.airport_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "airports.id"
    assert runway_table.c.airport_id.nullable is False
    assert runway_table.c.name.nullable is False
    assert runway_table.c.altitude.type.scale == 3


def test_station_has_required_airport_foreign_key() -> None:
    station_table = Base.metadata.tables["stations"]
    foreign_keys = list(station_table.c.airport_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "airports.id"
    assert station_table.c.airport_id.nullable is False
    assert station_table.c.name.nullable is False
    assert station_table.c.altitude.type.scale == 3
