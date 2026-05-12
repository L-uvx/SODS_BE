import pytest

from app.application.data_management_import import (
    _parse_degree,
    _get_number_from_string,
    _extract_runway_info,
)


class TestParseDegree:
    def test_decimal_degrees_returns_float(self) -> None:
        assert _parse_degree("103.94371") == pytest.approx(103.94371)

    def test_dms_with_degree_symbol(self) -> None:
        # 103°56'37.8" = 103 + 56/60 + 37.8/3600
        expected = 103.0 + 56.0 / 60.0 + 37.8 / 3600.0
        assert _parse_degree("103°56'37.8\"") == pytest.approx(expected)

    def test_dms_with_chinese_chars(self) -> None:
        expected = 103.0 + 56.0 / 60.0 + 37.8 / 3600.0
        assert _parse_degree("103度56分37.8秒") == pytest.approx(expected)

    def test_plain_float_string(self) -> None:
        assert _parse_degree("30.53463") == pytest.approx(30.53463)

    def test_none_returns_none(self) -> None:
        assert _parse_degree(None) is None

    def test_int_returns_float(self) -> None:
        assert _parse_degree(103) == pytest.approx(103.0)

    def test_float_returns_float(self) -> None:
        assert _parse_degree(103.5) == pytest.approx(103.5)

    def test_minutes_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_degree("103°65'37.8\"")

    def test_seconds_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_degree("103°56'65.0\"")


class TestGetNumberFromString:
    def test_plain_number(self) -> None:
        assert _get_number_from_string("3600") == pytest.approx(3600.0)

    def test_number_with_space(self) -> None:
        assert _get_number_from_string(" 3600 ") == pytest.approx(3600.0)

    def test_km_conversion(self) -> None:
        assert _get_number_from_string("3km") == pytest.approx(3000.0)

    def test_km_chinese(self) -> None:
        assert _get_number_from_string("3千米") == pytest.approx(3000.0)

    def test_nm_conversion(self) -> None:
        assert _get_number_from_string("1nm") == pytest.approx(1852.0)

    def test_float_with_unit(self) -> None:
        assert _get_number_from_string("3.5km") == pytest.approx(3500.0)

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError):
            _get_number_from_string("abc")

    def test_none_returns_none(self) -> None:
        assert _get_number_from_string(None) is None

    def test_integer_passed(self) -> None:
        assert _get_number_from_string(3600) == pytest.approx(3600.0)

    def test_float_passed(self) -> None:
        assert _get_number_from_string(3600.5) == pytest.approx(3600.5)


class TestExtractRunwayInfo:
    def test_typical_loc_name(self) -> None:
        assert _extract_runway_info("LOC20R") == "20R"

    def test_typical_gp_name(self) -> None:
        assert _extract_runway_info("GP02L") == "02L"

    def test_fallback_last_word(self) -> None:
        assert _extract_runway_info("双流机场 02L") == "02L"

    def test_no_runway_number_returns_last_word(self) -> None:
        assert _extract_runway_info("西南近无方向信标台") == "西南近无方向信标台"

    def test_none_returns_none(self) -> None:
        assert _extract_runway_info(None) is None
