"""测试机场电磁环境保护区规则"""

import math
import pytest
from shapely.geometry import Point, Polygon, MultiPolygon

from app.analysis.rules.runway.config import _CODE_B_CONFIG, ZONE_CODE, ZONE_NAME, RULE_CODE, RULE_NAME, REGION_CODE, REGION_NAME
from app.analysis.rules.runway.electromagnetic_environment import (
    build_stadium_polygon,
    build_runway_em_protection_zone,
    build_runway_em_rule_result,
)


class TestCodeBConfig:
    """runway_code_b 配置映射测试"""

    def test_code_b_config_mapping(self) -> None:
        assert _CODE_B_CONFIG["A"] == (10000.0, 0.0, True)
        assert _CODE_B_CONFIG["B"] == (10000.0, 10.0, False)
        assert _CODE_B_CONFIG["C"] == (13000.0, 10.0, False)
        assert _CODE_B_CONFIG["D"] == (13000.0, 10.0, False)
        assert _CODE_B_CONFIG["E"] == (13000.0, 10.0, False)
        assert _CODE_B_CONFIG["F"] == (13000.0, 10.0, False)

    def test_code_b_unknown_returns_none(self) -> None:
        assert _CODE_B_CONFIG.get("X") is None
        assert _CODE_B_CONFIG.get("") is None


class TestStadiumPolygon:
    """体育场形多边形构建测试"""

    def test_stadium_basic_shape(self) -> None:
        polygon = build_stadium_polygon(
            center_x=0.0,
            center_y=0.0,
            runway_length_m=3000.0,
            radius_m=10000.0,
            direction_degrees=90.0,  # 导航90°=正东，旋转角0，不旋转
            step_degrees=2.5,
        )
        assert isinstance(polygon, Polygon)

        min_x, min_y, max_x, max_y = polygon.bounds
        assert min_x == pytest.approx(-11500.0, rel=0.01)
        assert max_x == pytest.approx(11500.0, rel=0.01)
        assert min_y == pytest.approx(-10000.0, rel=0.01)
        assert max_y == pytest.approx(10000.0, rel=0.01)

    def test_stadium_zero_runway_length(self) -> None:
        polygon = build_stadium_polygon(
            center_x=0.0,
            center_y=0.0,
            runway_length_m=0.0,
            radius_m=10000.0,
            direction_degrees=90.0,  # 导航90°=正东，runway_length=0时退化为圆，旋转角度不影响
            step_degrees=2.5,
        )
        assert isinstance(polygon, Polygon)

        min_x, min_y, max_x, max_y = polygon.bounds
        # 长度为0时两个半圆圆都在原点，退化为近似圆
        assert min_x == pytest.approx(-10000.0, rel=0.01)
        assert max_x == pytest.approx(10000.0, rel=0.01)
        assert min_y == pytest.approx(-10000.0, rel=0.01)
        assert max_y == pytest.approx(10000.0, rel=0.01)

    def test_stadium_rotation(self) -> None:
        polygon = build_stadium_polygon(
            center_x=100.0,
            center_y=200.0,
            runway_length_m=3000.0,
            radius_m=10000.0,
            direction_degrees=45.0,
            step_degrees=2.5,
        )
        assert isinstance(polygon, Polygon)

        # 旋转 45° 后的体育场形应覆盖 (100, 200) 附近的区域
        assert polygon.contains(polygon.centroid)
        assert polygon.bounds[0] < 100.0 < polygon.bounds[2]
        assert polygon.bounds[1] < 200.0 < polygon.bounds[3]

    def test_stadium_no_rotation(self) -> None:
        polygon = build_stadium_polygon(
            center_x=0.0,
            center_y=0.0,
            runway_length_m=3000.0,
            radius_m=10000.0,
            direction_degrees=90.0,  # 导航90°=正东，C#: 90-90=0，不旋转
            step_degrees=2.5,
        )
        assert isinstance(polygon, Polygon)

        # 验证关键点位在预期位置
        exterior_coords = list(polygon.exterior.coords)

        # 第一个点 (deg=-90°, 右帽底): (half_l, -r) = (1500, -10000)
        assert exterior_coords[0][0] == pytest.approx(1500.0, rel=0.01)
        assert exterior_coords[0][1] == pytest.approx(-10000.0, rel=0.01)

        # 顶部点 (deg≈90, 右帽): (half_l, r) = (1500, 10000)
        top_candidates = [
            c for c in exterior_coords
            if c[1] > 9000.0 and abs(c[0] - 1500.0) < 200.0
        ]
        assert len(top_candidates) > 0

        # 最左侧点 (deg=180, 左圆): (-half_l - r, 0) = (-11500, 0)
        min_x_coord = min(exterior_coords, key=lambda c: c[0])
        assert min_x_coord[0] == pytest.approx(-11500.0, rel=0.01)

        # 底部点 (deg≈270, 左圆): (-half_l, -r) = (-1500, -10000)
        bottom_candidates = [
            c for c in exterior_coords
            if c[1] < -9000.0 and abs(c[0] - (-1500.0)) < 200.0
        ]
        assert len(bottom_candidates) > 0


class TestEmProtectionZone:
    """电磁环境保护区构建测试"""

    def _make_runway_context(self, code_b, runway_id=1, direction=90.0, length=3000.0, altitude=0.0):
        return {
            "runwayId": runway_id,
            "runNumber": "18",
            "localCenterPoint": (0.0, 0.0),
            "directionDegrees": direction,
            "lengthMeters": length,
            "widthMeters": 45.0,
            "maximumAirworthiness": None,
            "runwayCodeB": code_b,
            "altitude": altitude,
        }

    def test_em_zone_code_a_produces_circle(self) -> None:
        ctx = self._make_runway_context("A")
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        assert isinstance(result.local_geometry, MultiPolygon)

        min_x, min_y, max_x, max_y = result.local_geometry.bounds
        assert min_x == pytest.approx(-10000.0, rel=0.01)
        assert max_x == pytest.approx(10000.0, rel=0.01)
        assert min_y == pytest.approx(-10000.0, rel=0.01)
        assert max_y == pytest.approx(10000.0, rel=0.01)

    def test_em_zone_code_b_produces_stadium(self) -> None:
        ctx = self._make_runway_context("B")
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        assert isinstance(result.local_geometry, MultiPolygon)

        # B 类: 体育场形, radius=10000, runway_altitude(0) + height_m(10) = 10
        assert result.vertical_definition["baseHeightMeters"] == 10.0

    def test_em_zone_code_c_produces_stadium_13km(self) -> None:
        ctx = self._make_runway_context("C")
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        assert isinstance(result.local_geometry, MultiPolygon)

        min_x, min_y, max_x, max_y = result.local_geometry.bounds
        assert min_x == pytest.approx(-14500.0, rel=0.01)
        assert max_x == pytest.approx(14500.0, rel=0.01)
        assert min_y == pytest.approx(-13000.0, rel=0.01)
        assert max_y == pytest.approx(13000.0, rel=0.01)

    def test_em_zone_null_code_b_returns_none(self) -> None:
        ctx = self._make_runway_context(None)
        result = build_runway_em_protection_zone(None, ctx)
        assert result is None

    def test_em_zone_unknown_code_b_returns_none(self) -> None:
        ctx = self._make_runway_context("X")
        result = build_runway_em_protection_zone(None, ctx)
        assert result is None

    def test_em_zone_has_runway_id(self) -> None:
        ctx = self._make_runway_context("A", runway_id=42)
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        assert result.runway_id == 42

    def test_em_zone_station_id_is_zero(self) -> None:
        ctx = self._make_runway_context("A")
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        assert result.station_id == -1
        assert result.station_type == "RUNWAY"

    def test_em_zone_vertical_flat(self) -> None:
        ctx = self._make_runway_context("B")
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        assert result.vertical_definition["mode"] == "flat"
        assert result.vertical_definition["baseReference"] == "runway"
        assert result.vertical_definition["baseHeightMeters"] == 10.0

    def test_em_zone_with_runway_altitude(self) -> None:
        ctx = self._make_runway_context("A", altitude=500.0)
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        # A类: runway_altitude(500) + height_m(0) = 500
        assert result.vertical_definition["baseHeightMeters"] == 500.0

    def test_em_zone_b_with_runway_altitude(self) -> None:
        ctx = self._make_runway_context("B", altitude=300.0)
        result = build_runway_em_protection_zone(None, ctx)
        assert result is not None
        # B类: runway_altitude(300) + height_m(10) = 310
        assert result.vertical_definition["baseHeightMeters"] == 310.0


class TestEmRuleResult:
    """电磁环境保护区规则结果测试"""

    def _make_obstacle(self, obs_id=1, name="测试障碍物", x=0.0, y=0.0):
        return {
            "obstacleId": obs_id,
            "obstacleName": name,
            "rawObstacleType": "建筑物",
            "globalObstacleCategory": "building_general",
            "localGeometry": {"type": "Point", "coordinates": [x, y]},
        }

    def _make_dummy_zone(self, radius=10000.0):
        """创建一个简单的圆形保护区用于测试"""
        from app.analysis.rules.geometry_helpers import ensure_multipolygon, build_circle_polygon
        from app.analysis.protection_zone_spec import ProtectionZoneSpec
        poly = build_circle_polygon(center_point=(0.0, 0.0), radius_meters=radius)
        return ProtectionZoneSpec(
            station_id=-1,
            station_type="RUNWAY",
            rule_code=RULE_CODE,
            rule_name=RULE_NAME,
            zone_code=ZONE_CODE,
            zone_name=ZONE_NAME,
            region_code=REGION_CODE,
            region_name=REGION_NAME,
            local_geometry=ensure_multipolygon(poly),
            geometry_definition={},
            vertical_definition={},
            runway_id=1,
        )

    def test_em_rule_result_inside_zone(self) -> None:
        """障碍物在保护区内"""
        obstacle = self._make_obstacle(x=5000.0, y=0.0)
        zone = self._make_dummy_zone(radius=10000.0)
        result = build_runway_em_rule_result(obstacle, zone)
        assert result.is_compliant is True
        assert result.is_in_zone is True
        assert result.is_applicable is True
        assert result.message == "在机场电磁环境保护区内"

    def test_em_rule_result_outside_zone(self) -> None:
        """障碍物在保护区外"""
        obstacle = self._make_obstacle(x=20000.0, y=0.0)
        zone = self._make_dummy_zone(radius=10000.0)
        result = build_runway_em_rule_result(obstacle, zone)
        assert result.is_compliant is True
        assert result.is_in_zone is False
        assert result.message == "不在机场电磁环境保护区内"

    def test_em_rule_result_has_correct_fields(self) -> None:
        obstacle = self._make_obstacle(obs_id=7, name="高压线塔")
        zone = self._make_dummy_zone(radius=10000.0)
        result = build_runway_em_rule_result(obstacle, zone)

        assert result.zone_code == ZONE_CODE
        assert result.zone_name == ZONE_NAME
        assert result.rule_code == RULE_CODE
        assert result.rule_name == RULE_NAME
        assert result.region_code == REGION_CODE
        assert result.region_name == REGION_NAME
        assert result.station_id == -1
        assert result.station_type == "RUNWAY"
        assert result.obstacle_id == 7
        assert result.obstacle_name == "高压线塔"
        assert result.raw_obstacle_type == "建筑物"
        assert result.global_obstacle_category == "building_general"
        assert result.over_distance_meters == 0.0
        assert result.standards_rule_code == RULE_CODE

    def test_em_rule_result_inside_zone_metrics(self) -> None:
        """障碍物在保护区内，metrics 应反映此状态"""
        obstacle = self._make_obstacle(x=0.0, y=0.0)
        zone = self._make_dummy_zone(radius=10000.0)
        result = build_runway_em_rule_result(obstacle, zone)
        assert result.metrics["enteredProtectionZone"] is True

    def test_em_rule_result_outside_zone_metrics(self) -> None:
        """障碍物在保护区外，metrics 应反映此状态"""
        obstacle = self._make_obstacle(x=20000.0, y=0.0)
        zone = self._make_dummy_zone(radius=10000.0)
        result = build_runway_em_rule_result(obstacle, zone)
        assert result.metrics["enteredProtectionZone"] is False
