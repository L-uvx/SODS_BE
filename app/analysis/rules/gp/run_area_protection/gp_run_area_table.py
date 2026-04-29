from dataclasses import dataclass
from enum import Enum


class Aircraft(str, Enum):
    H6 = "H6"
    H14 = "H14"
    H20 = "H20"
    H25 = "H25"


@dataclass(slots=True, frozen=True)
class GpRunAreaTableItem:
    pc_x_meters: float
    pc_y_meters: float
    ps_x_meters: float
    ps_y_meters: float


class GpRunAreaTable:
    _AIRCRAFT_MAPPING = {
        0: Aircraft.H6,
        1: Aircraft.H14,
        2: Aircraft.H20,
        3: Aircraft.H25,
    }

    # 初始化 GP 运行保护区参数表。
    def __init__(self) -> None:
        self._items = self._build_items()

    # 按跑道适航等级映射航空器分档。
    @classmethod
    def resolve_aircraft(cls, maximum_airworthiness: int) -> Aircraft | None:
        return cls._AIRCRAFT_MAPPING.get(int(maximum_airworthiness))

    # 构建运行保护区参数查表 key。
    @staticmethod
    def build_key(*, station_sub_type: str, aircraft: Aircraft, antenna_type: str) -> str:
        return f"{station_sub_type}_{aircraft.value}_{antenna_type}"

    # 获取单个 GP 运行保护区参数项。
    def get_item(
        self,
        *,
        station_sub_type: str,
        aircraft: Aircraft,
        antenna_type: str,
    ) -> GpRunAreaTableItem | None:
        key = self.build_key(
            station_sub_type=station_sub_type,
            aircraft=aircraft,
            antenna_type=antenna_type,
        )
        return self._items.get(key)

    def _build_items(self) -> dict[str, GpRunAreaTableItem]:
        return {
            "I_H6_M": self._item(299, 29, 299, 29),
            "I_H6_O": self._item(191, 29, 399, 24),
            "I_H14_M": self._item(329, 39, 297, 39),
            "I_H14_O": self._item(829, 39, 537, 39),
            "I_H20_M": self._item(467, 35, 444, 25),
            "I_H20_O": self._item(1167, 55, 717, 18),
            "I_H25_M": self._item(610, 34, 541, 24),
            "I_H25_O": self._item(1360, 55, 760, 24),
            "II_H6_M": self._item(299, 29, 299, 29),
            "II_H6_O": self._item(449, 29, 449, 24),
            "II_H14_M": self._item(347, 39, 429, 39),
            "II_H14_O": self._item(829, 39, 829, 39),
            "II_H20_M": self._item(567, 35, 528, 25),
            "II_H20_O": self._item(1267, 55, 817, 25),
            "II_H25_M": self._item(672, 34, 610, 24),
            "II_H25_O": self._item(1410, 55, 1010, 24),
            "III_H6_M": self._item(299, 29, 299, 29),
            "III_H6_O": self._item(449, 29, 449, 24),
            "III_H14_M": self._item(347, 39, 429, 39),
            "III_H14_O": self._item(829, 39, 829, 39),
            "III_H20_M": self._item(567, 35, 528, 25),
            "III_H20_O": self._item(1267, 55, 817, 25),
            "III_H25_M": self._item(672, 34, 610, 24),
            "III_H25_O": self._item(1410, 55, 1010, 24),
        }

    def _item(
        self,
        pc_x_meters: float,
        pc_y_meters: float,
        ps_x_meters: float,
        ps_y_meters: float,
    ) -> GpRunAreaTableItem:
        return GpRunAreaTableItem(
            pc_x_meters=float(pc_x_meters),
            pc_y_meters=float(pc_y_meters),
            ps_x_meters=float(ps_x_meters),
            ps_y_meters=float(ps_y_meters),
        )
