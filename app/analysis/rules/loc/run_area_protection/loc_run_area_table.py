import math
from dataclasses import dataclass
from enum import Enum


class Aircraft(str, Enum):
    H6 = "H6"
    H14 = "H14"
    H20 = "H20"
    H25 = "H25"


@dataclass(slots=True, frozen=True)
class LocRunAreaTableItem:
    xc_meters: float
    yc_meters: float
    zc_meters: float
    zs1_meters: float | None = None
    zs2_meters: float | None = None
    y1_meters: float | None = None
    y2_meters: float | None = None
    xs_meters: float | None = None


class LocRunAreaTable:
    _AIRCRAFT_MAPPING = {
        0: Aircraft.H6,
        1: Aircraft.H14,
        2: Aircraft.H20,
        3: Aircraft.H25,
    }

    # 初始化 LOC 运行保护区参数表。
    def __init__(self, l_meters: float) -> None:
        self._l_meters = float(l_meters)
        self._k = math.sqrt(self._l_meters / 3300.0)
        self._items = self._build_items()

    # 按跑道适航等级映射航空器分档。
    @classmethod
    def resolve_aircraft(cls, maximum_airworthiness: int) -> Aircraft | None:
        return cls._AIRCRAFT_MAPPING.get(int(maximum_airworthiness))

    # 按天线数量解析分组。
    @staticmethod
    def resolve_unit_group(unit_number: int) -> int:
        if unit_number <= 11:
            return 1
        if unit_number <= 15:
            return 2
        return 3

    # 构建运行保护区参数查表 key。
    def build_key(
        self,
        *,
        station_sub_type: str,
        aircraft: Aircraft,
        unit_number: int,
    ) -> str:
        unit_group = self.resolve_unit_group(unit_number)
        return f"{station_sub_type}_{aircraft.value}_{unit_group}"

    # 获取单个 LOC 运行保护区参数项。
    def get_item(
        self,
        *,
        station_sub_type: str,
        aircraft: Aircraft,
        unit_number: int,
    ) -> LocRunAreaTableItem | None:
        key = self.build_key(
            station_sub_type=station_sub_type,
            aircraft=aircraft,
            unit_number=unit_number,
        )
        return self._items.get(key)

    def _build_items(self) -> dict[str, LocRunAreaTableItem]:
        k = self._k
        l_meters = self._l_meters
        return {
            "I_H6_1": self._item(180, 50, 10, 15, 15, 40, 40, 200),
            "I_H6_2": self._item(65, 15, 10),
            "I_H6_3": self._item(65, 15, 10),
            "I_H14_1": self._item(360, 110, 35, 35, 35, 90, 90, 500),
            "I_H14_2": self._item(200, 25, 35),
            "I_H14_3": self._item(150, 25, 35),
            "I_H20_2": self._item(500, 50, 50),
            "I_H20_3": self._item(410, 30, 50),
            "I_H25_2": self._item(660, 55, 60, 60, 60, 90, 90, 1300),
            "I_H25_3": self._item(580, 40, 60, 60, 60, 50, 50, 1100),
            "II_H6_2": self._item(75, 15, 10, 15, 15, 15, 15, 75),
            "II_H6_3": self._item(55, 20, 10, 15, 15),
            "II_H14_2": self._item(200, 25, 35, 35, 45, 50, 50, 500),
            "II_H14_3": self._item(200, 25, 35, 35, 45),
            "II_H20_2": self._item(500, 50, 50, 60, 160, 125 * k, 125 * k, 2100),
            "II_H20_3": self._item(475, 30, 50, 60, 160, 60 * k, 60 * k, 1400),
            "II_H25_2": self._item(750, 70, 60, 70, 250, 180 * k, 180 * k, l_meters),
            "II_H25_3": self._item(675, 50, 60, 70, 250, 100 * k, 125 * k, l_meters),
            "III_H6_2": self._item(75, 15, 10, 15, 15, 15, 15, 100),
            "III_H6_3": self._item(55, 20, 10, 15, 15),
            "III_H14_2": self._item(200, 25, 35, 35, 45, 50, 50, 900),
            "III_H14_3": self._item(200, 25, 35, 35, 45),
            "III_H20_2": self._item(500, 50, 50, 60, 160, 140 * k, 160 * k, 3100),
            "III_H20_3": self._item(475, 30, 50, 60, 160, 120 * k, 120 * k, 3100),
            "III_H25_2": self._item(750, 70, 60, 70, 250, 180 * k, 260 * k, l_meters),
            "III_H25_3": self._item(675, 50, 60, 70, 250, 150 * k, 180 * k, l_meters),
        }

    def _item(
        self,
        xc_meters: float,
        yc_meters: float,
        zc_meters: float,
        zs1_meters: float | None = None,
        zs2_meters: float | None = None,
        y1_meters: float | None = None,
        y2_meters: float | None = None,
        xs_meters: float | None = None,
    ) -> LocRunAreaTableItem:
        return LocRunAreaTableItem(
            xc_meters=float(xc_meters),
            yc_meters=float(yc_meters),
            zc_meters=float(zc_meters),
            zs1_meters=float(zs1_meters) if zs1_meters is not None else None,
            zs2_meters=float(zs2_meters) if zs2_meters is not None else None,
            y1_meters=float(y1_meters) if y1_meters is not None else None,
            y2_meters=float(y2_meters) if y2_meters is not None else None,
            xs_meters=float(xs_meters) if xs_meters is not None else None,
        )
