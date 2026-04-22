from dataclasses import dataclass

from pyproj import Transformer


@dataclass
class AirportLocalProjector:
    reference_longitude: float
    reference_latitude: float

    # 初始化机场局部坐标投影器。
    def __post_init__(self) -> None:
        self._to_local = Transformer.from_crs(
            "EPSG:4326",
            self._build_aeqd_crs(),
            always_xy=True,
        )

    # 构建机场局部等距方位投影坐标系定义。
    def _build_aeqd_crs(self) -> str:
        return (
            f"+proj=aeqd +lat_0={self.reference_latitude} "
            f"+lon_0={self.reference_longitude} +datum=WGS84 +units=m +no_defs"
        )

    # 将经纬度点投影到机场局部米制坐标系。
    def project_point(self, longitude: float, latitude: float) -> tuple[float, float]:
        x, y = self._to_local.transform(longitude, latitude)
        return float(x), float(y)
