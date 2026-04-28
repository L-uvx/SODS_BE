from io import BytesIO

from openpyxl import Workbook
import pytest

from app.application.point_obstacle_excel_parser import (
    PointObstacleExcelParseError,
    parse_point_obstacle_excel,
)


def _build_workbook_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"

    for row in rows:
        worksheet.append(row)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_point_obstacle_excel_deduplicates_identical_rows() -> None:
    workbook_bytes = _build_workbook_bytes(
        [
            ["障碍物名称", "经度", "纬度", "顶部高程"],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["点障碍物2", "103°58'41.20\"", "030°30'20.34\"", 550.1],
        ]
    )

    obstacles = parse_point_obstacle_excel(workbook_bytes)

    assert len(obstacles) == 2
    assert obstacles[0].name == "点障碍物1"
    assert obstacles[0].top_elevation == 549.9
    assert obstacles[0].row_number == 2
    assert round(obstacles[0].longitude_decimal, 6) == 103.975864
    assert round(obstacles[0].latitude_decimal, 6) == 30.506881
    assert obstacles[1].name == "点障碍物2"
    assert obstacles[1].row_number == 4


def test_parse_point_obstacle_excel_raises_for_same_name_with_different_coordinates() -> None:
    workbook_bytes = _build_workbook_bytes(
        [
            ["障碍物名称", "经度", "纬度", "顶部高程"],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["点障碍物1", "103°58'41.20\"", "030°30'24.77\"", 549.9],
        ]
    )

    with pytest.raises(PointObstacleExcelParseError) as exc_info:
        parse_point_obstacle_excel(workbook_bytes)

    assert "坐标或顶部高程" in str(exc_info.value)


def test_parse_point_obstacle_excel_raises_for_same_name_with_different_top_elevation() -> None:
    workbook_bytes = _build_workbook_bytes(
        [
            ["障碍物名称", "经度", "纬度", "顶部高程"],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 549.9],
            ["点障碍物1", "103°58'33.11\"", "030°30'24.77\"", 550.1],
        ]
    )

    with pytest.raises(PointObstacleExcelParseError) as exc_info:
        parse_point_obstacle_excel(workbook_bytes)

    assert "坐标或顶部高程" in str(exc_info.value)


def test_parse_point_obstacle_excel_raises_for_invalid_excel_file_bytes() -> None:
    with pytest.raises(PointObstacleExcelParseError) as exc_info:
        parse_point_obstacle_excel(b"not-an-excel-file")

    assert str(exc_info.value) == "invalid excel file"
