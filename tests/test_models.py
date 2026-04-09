from app.db.base import Base


def test_project_and_obstacle_tables_are_registered() -> None:
    assert "projects" in Base.metadata.tables
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
