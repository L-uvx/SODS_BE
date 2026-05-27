from dataclasses import dataclass

from pyproj import Transformer


@dataclass
class AirportLocalProjector:
    reference_longitude: float
    reference_latitude: float

    # 初始化机场局部坐标投影器。
    def __post_init__(self) -> None:
        local_crs = self._build_aeqd_crs()
        self._to_local = Transformer.from_crs(
            "EPSG:4326",
            local_crs,
            always_xy=True,
        )
        self._to_wgs84 = Transformer.from_crs(
            local_crs,
            "EPSG:4326",
            always_xy=True,
        )

    # 构建局部米制投影坐标系（横轴墨卡托，对齐 C# IAG 1975 椭球）。
    def _build_aeqd_crs(self) -> str:
        return (
            f"+proj=tmerc +lat_0=0 +lon_0={self.reference_longitude} "
            f"+k=1 +x_0=500000 +y_0=0 +ellps=IAU76 +units=m +no_defs"
        )

    # 将经纬度点投影到机场局部米制坐标系。
    def project_point(self, longitude: float, latitude: float) -> tuple[float, float]:
        x, y = self._to_local.transform(longitude, latitude)
        return float(x), float(y)

    # 将机场局部米制坐标点反投影到经纬度。
    def unproject_point(self, x: float, y: float) -> tuple[float, float]:
        longitude, latitude = self._to_wgs84.transform(x, y)
        return float(longitude), float(latitude)
