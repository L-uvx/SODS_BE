from pathlib import Path
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.application.polygon_obstacle_excel_parser import (
    PolygonObstacleExcelParseError,
    parse_polygon_obstacle_excel,
)


def test_parse_fixed_template_groups_rows_into_obstacles() -> None:
    excel_bytes = Path("docs/import_demo.xlsx").read_bytes()

    obstacles = parse_polygon_obstacle_excel(excel_bytes)

    assert len(obstacles) == 2

    first_obstacle = obstacles[0]
    assert first_obstacle.name == "障碍物1"
    assert len(first_obstacle.points) == 5
    assert first_obstacle.top_elevation == 549.9
    assert [point.row_number for point in first_obstacle.points] == [2, 3, 4, 5, 6]
    assert round(first_obstacle.points[0].longitude_decimal, 6) == 103.975864
    assert round(first_obstacle.points[0].latitude_decimal, 6) == 30.506881

    second_obstacle = obstacles[1]
    assert second_obstacle.name == "障碍物2"
    assert len(second_obstacle.points) == 5
    assert second_obstacle.top_elevation == 549.9
    assert [point.row_number for point in second_obstacle.points] == [7, 8, 9, 10, 11]


def _build_workbook_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"

    for row in rows:
        worksheet.append(row)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_raises_for_inconsistent_top_elevation_with_same_name() -> None:
    workbook_bytes = _build_workbook_bytes(
        [
            ["障碍物名称", "经度", "纬度", "顶部高程"],
            ["障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["障碍物1", "103°58'41.20\"", "030°30'20.34\"", 550.1],
        ]
    )

    with pytest.raises(PolygonObstacleExcelParseError) as exc_info:
        parse_polygon_obstacle_excel(workbook_bytes)

    assert "顶部高程" in str(exc_info.value)


def test_parse_raises_for_invalid_excel_file_bytes() -> None:
    with pytest.raises(PolygonObstacleExcelParseError) as exc_info:
        parse_polygon_obstacle_excel(b"not-an-excel-file")

    assert str(exc_info.value) == "invalid excel file"
