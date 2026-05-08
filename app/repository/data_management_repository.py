from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.airport import Airport
from app.models.runway import Runway
from app.models.station import Station


class DataManagementRepository:
    # 初始化基础数据管理仓储。
    def __init__(self, session: Session) -> None:
        self._session = session

    # 根据编号获取机场。
    def get_airport(self, airport_id: int) -> Airport | None:
        return self._session.get(Airport, airport_id)

    # 根据编号获取跑道。
    def get_runway(self, runway_id: int) -> Runway | None:
        return self._session.get(Runway, runway_id)

    # 根据编号获取台站。
    def get_station(self, station_id: int) -> Station | None:
        return self._session.get(Station, station_id)

    # 分页查询机场列表。
    def list_airports(
        self,
        *,
        offset: int,
        limit: int,
        keyword: str | None = None,
        has_coordinates: bool | None = None,
    ) -> tuple[list[Airport], int]:
        statement = select(Airport)
        if keyword:
            statement = statement.where(Airport.name.contains(keyword))
        if has_coordinates is True:
            statement = statement.where(Airport.longitude.is_not(None), Airport.latitude.is_not(None))
        statement = statement.order_by(Airport.id).offset(offset).limit(limit)
        count_statement = select(func.count()).select_from(Airport)
        if keyword:
            count_statement = count_statement.where(Airport.name.contains(keyword))
        if has_coordinates is True:
            count_statement = count_statement.where(
                Airport.longitude.is_not(None), Airport.latitude.is_not(None)
            )
        total = int(self._session.scalar(count_statement) or 0)
        return list(self._session.scalars(statement).all()), total

    # 分页查询跑道列表。
    def list_runways(
        self,
        *,
        offset: int,
        limit: int,
        airport_id: int | None = None,
        keyword: str | None = None,
        run_number: str | None = None,
    ) -> tuple[list[Runway], int]:
        statement = select(Runway)
        if airport_id is not None:
            statement = statement.where(Runway.airport_id == airport_id)
        if keyword:
            statement = statement.where(Runway.name.contains(keyword))
        if run_number:
            statement = statement.where(Runway.run_number == run_number)
        statement = statement.order_by(Runway.id).offset(offset).limit(limit)
        count_statement = select(func.count()).select_from(Runway)
        if airport_id is not None:
            count_statement = count_statement.where(Runway.airport_id == airport_id)
        if keyword:
            count_statement = count_statement.where(Runway.name.contains(keyword))
        if run_number:
            count_statement = count_statement.where(Runway.run_number == run_number)
        total = int(self._session.scalar(count_statement) or 0)
        return list(self._session.scalars(statement).all()), total

    # 分页查询台站列表。
    def list_stations(
        self,
        *,
        offset: int,
        limit: int,
        airport_id: int | None = None,
        station_type: str | None = None,
        keyword: str | None = None,
        runway_no: str | None = None,
    ) -> tuple[list[Station], int]:
        statement = select(Station)
        if airport_id is not None:
            statement = statement.where(Station.airport_id == airport_id)
        if station_type:
            statement = statement.where(Station.station_type == station_type)
        if keyword:
            statement = statement.where(Station.name.contains(keyword))
        if runway_no:
            statement = statement.where(Station.runway_no == runway_no)
        statement = statement.order_by(Station.id).offset(offset).limit(limit)
        count_statement = select(func.count()).select_from(Station)
        if airport_id is not None:
            count_statement = count_statement.where(Station.airport_id == airport_id)
        if station_type:
            count_statement = count_statement.where(Station.station_type == station_type)
        if keyword:
            count_statement = count_statement.where(Station.name.contains(keyword))
        if runway_no:
            count_statement = count_statement.where(Station.runway_no == runway_no)
        total = int(self._session.scalar(count_statement) or 0)
        return list(self._session.scalars(statement).all()), total

    # 查询机场下跑道选项。
    def list_runway_options_by_airport_id(self, airport_id: int) -> list[Runway]:
        statement = (
            select(Runway)
            .where(Runway.airport_id == airport_id)
            .order_by(Runway.id)
        )
        return list(self._session.scalars(statement).all())

    # 创建机场记录。
    def create_airport(self, **values: Any) -> Airport:
        airport = Airport(**values)
        self._session.add(airport)
        self._session.flush()
        return airport

    # 创建跑道记录。
    def create_runway(self, **values: Any) -> Runway:
        runway = Runway(**values)
        self._session.add(runway)
        self._session.flush()
        return runway

    # 创建台站记录。
    def create_station(self, **values: Any) -> Station:
        station = Station(**values)
        self._session.add(station)
        self._session.flush()
        return station

    # 更新机场记录。
    def update_airport(self, airport: Airport, **values: Any) -> Airport:
        self._apply_updates(airport, values)
        self._session.flush()
        return airport

    # 更新跑道记录。
    def update_runway(self, runway: Runway, **values: Any) -> Runway:
        self._apply_updates(runway, values)
        self._session.flush()
        return runway

    # 更新台站记录。
    def update_station(self, station: Station, **values: Any) -> Station:
        self._apply_updates(station, values)
        self._session.flush()
        return station

    # 删除机场记录。
    def delete_airport(self, airport: Airport) -> None:
        self._session.delete(airport)

    # 删除跑道记录。
    def delete_runway(self, runway: Runway) -> None:
        self._session.delete(runway)

    # 删除台站记录。
    def delete_station(self, station: Station) -> None:
        self._session.delete(station)

    # 统计机场下跑道数量。
    def count_runways_by_airport_id(self, airport_id: int) -> int:
        statement = select(func.count()).select_from(Runway).where(Runway.airport_id == airport_id)
        return int(self._session.scalar(statement) or 0)

    # 统计机场下台站数量。
    def count_stations_by_airport_id(self, airport_id: int) -> int:
        statement = select(func.count()).select_from(Station).where(Station.airport_id == airport_id)
        return int(self._session.scalar(statement) or 0)

    # 统计引用跑道编号的台站数量。
    def count_stations_referencing_runway(self, runway_id: int) -> int:
        runway = self.get_runway(runway_id)
        if runway is None or runway.run_number is None:
            return 0

        statement = (
            select(func.count())
            .select_from(Station)
            .where(
                Station.airport_id == runway.airport_id,
                Station.runway_no == runway.run_number,
            )
        )
        return int(self._session.scalar(statement) or 0)

    # 判断机场下是否存在重复跑道号。
    def runway_number_exists(
        self,
        airport_id: int,
        run_number: str,
        exclude_runway_id: int | None = None,
    ) -> bool:
        statement = select(Runway.id).where(
            Runway.airport_id == airport_id,
            Runway.run_number == run_number,
        )
        if exclude_runway_id is not None:
            statement = statement.where(Runway.id != exclude_runway_id)
        return self._session.scalar(statement) is not None

    # 查询机场选项。
    def list_airport_options(self) -> list[Airport]:
        statement = select(Airport).order_by(Airport.id)
        return list(self._session.scalars(statement).all())

    # 查询台站类型选项。
    def list_station_type_options(self) -> list[str]:
        statement = (
            select(Station.station_type)
            .where(Station.station_type.is_not(None))
            .distinct()
            .order_by(Station.station_type)
        )
        return list(self._session.scalars(statement).all())

    # 统一统计模型数量。
    def _count(self, model: type[Airport] | type[Runway] | type[Station]) -> int:
        statement = select(func.count()).select_from(model)
        return int(self._session.scalar(statement) or 0)

    # 批量应用更新字段。
    def _apply_updates(
        self,
        target: Airport | Runway | Station,
        values: dict[str, Any],
    ) -> None:
        allowed_field_names = {
            attribute.key for attribute in target.__mapper__.column_attrs
        }
        for field_name, field_value in values.items():
            if field_name not in allowed_field_names:
                raise ValueError(f"unknown field: {field_name}")
            setattr(target, field_name, field_value)
