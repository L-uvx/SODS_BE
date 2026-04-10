import app.db.models  # noqa: F401

from app.db.base import Base


def test_project_and_obstacle_tables_are_registered() -> None:
    assert "projects" in Base.metadata.tables
    assert "import_batches" in Base.metadata.tables
    assert "obstacles" in Base.metadata.tables


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


def test_obstacle_source_batch_matches_import_batch_key_type() -> None:
    obstacle_table = Base.metadata.tables["obstacles"]
    import_batch_table = Base.metadata.tables["import_batches"]

    assert type(obstacle_table.c.source_batch_id.type) is type(
        import_batch_table.c.id.type
    )
