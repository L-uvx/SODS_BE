from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from app.repository.data_management_repository import DataManagementRepository
from app.schemas.data_management import (
    AirportListItemResponse,
    AirportListResponse,
    AirportResponse,
    AirportUpsertRequest,
    AirportWriteResponse,
    OptionItemResponse,
    RunwayListItemResponse,
    RunwayListResponse,
    RunwayResponse,
    RunwayUpsertRequest,
    RunwayWriteResponse,
    StationListItemResponse,
    StationListResponse,
    StationResponse,
    StationTypeOptionResponse,
    StationUpsertRequest,
    StationWriteResponse,
)


class DataManagementValidationError(ValueError):
    # 表示基础数据校验失败。
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DataManagementConflictError(ValueError):
    # 表示基础数据存在冲突。
    def __init__(self, code: str, message: str, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra or {}


class DataManagementNotFoundError(ValueError):
    # 表示基础数据不存在。
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DataManagementService:
    # 初始化基础数据管理服务。
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = DataManagementRepository(session)

    # 创建机场。
    def create_airport(self, payload: AirportUpsertRequest) -> AirportWriteResponse:
        self._validate_airport_payload(payload)
        airport = self._repository.create_airport(**payload.model_dump(by_alias=False))
        self._session.commit()
        self._session.refresh(airport)
        self._session.expunge(airport)
        return AirportWriteResponse(id=airport.id, warnings=[])

    # 查询机场列表。
    def list_airports(
        self,
        *,
        keyword: str | None,
        has_coordinates: bool | None,
        page: int,
        page_size: int,
    ) -> AirportListResponse:
        offset = (page - 1) * page_size
        airports, total = self._repository.list_airports(
            offset=offset,
            limit=page_size,
            keyword=keyword,
            has_coordinates=has_coordinates,
        )
        items = [self._build_airport_list_item(airport) for airport in airports]
        return AirportListResponse(items=items, total=total, page=page, pageSize=page_size)

    # 查询机场详情。
    def get_airport(self, airport_id: int) -> AirportResponse:
        airport = self._repository.get_airport(airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")
        return AirportResponse.model_validate(airport)

    # 更新机场。
    def update_airport(self, airport_id: int, payload: AirportUpsertRequest) -> AirportWriteResponse:
        self._validate_airport_payload(payload)
        airport = self._repository.get_airport(airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")

        updated_airport = self._repository.update_airport(
            airport,
            **payload.model_dump(by_alias=False),
        )
        self._session.commit()
        self._session.refresh(updated_airport)
        self._session.expunge(updated_airport)
        return AirportWriteResponse(id=updated_airport.id, warnings=[])

    # 创建跑道。
    def create_runway(self, payload: RunwayUpsertRequest) -> RunwayWriteResponse:
        self._validate_runway_payload(payload)
        airport = self._repository.get_airport(payload.airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")
        if self._repository.runway_number_exists(payload.airport_id, payload.run_number):
            raise DataManagementConflictError(
                "duplicate_runway_number",
                "runNumber already exists within airport",
            )

        runway = self._repository.create_runway(**payload.model_dump(by_alias=False))
        self._session.commit()
        self._session.refresh(runway)
        self._session.expunge(runway)
        return RunwayWriteResponse(id=runway.id, warnings=[])

    # 查询跑道列表。
    def list_runways(
        self,
        *,
        airport_id: int | None,
        keyword: str | None,
        run_number: str | None,
        page: int,
        page_size: int,
    ) -> RunwayListResponse:
        offset = (page - 1) * page_size
        runways, total = self._repository.list_runways(
            offset=offset,
            limit=page_size,
            airport_id=airport_id,
            keyword=keyword,
            run_number=run_number,
        )
        items = [self._build_runway_list_item(runway) for runway in runways]
        return RunwayListResponse(items=items, total=total, page=page, pageSize=page_size)

    # 查询跑道详情。
    def get_runway(self, runway_id: int) -> RunwayResponse:
        runway = self._repository.get_runway(runway_id)
        if runway is None:
            raise DataManagementNotFoundError("runway_not_found", "runway not found")
        return RunwayResponse.model_validate(runway)

    # 更新跑道。
    def update_runway(self, runway_id: int, payload: RunwayUpsertRequest) -> RunwayWriteResponse:
        self._validate_runway_payload(payload)
        runway = self._repository.get_runway(runway_id)
        if runway is None:
            raise DataManagementNotFoundError("runway_not_found", "runway not found")

        airport = self._repository.get_airport(payload.airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")
        if self._repository.runway_number_exists(
            payload.airport_id,
            payload.run_number,
            exclude_runway_id=runway_id,
        ):
            raise DataManagementConflictError(
                "duplicate_runway_number",
                "runNumber already exists within airport",
            )

        referenced_station_count = self._repository.count_stations_referencing_runway(runway_id)
        identity_changed = (
            runway.airport_id != payload.airport_id
            or runway.run_number != payload.run_number
        )
        if referenced_station_count > 0 and identity_changed:
            raise DataManagementConflictError(
                "runway_referenced_by_station",
                "runway is referenced by stations",
                extra={"referencedStationCount": referenced_station_count},
            )

        updated_runway = self._repository.update_runway(
            runway,
            **payload.model_dump(by_alias=False),
        )
        self._session.commit()
        self._session.refresh(updated_runway)
        self._session.expunge(updated_runway)
        return RunwayWriteResponse(id=updated_runway.id, warnings=[])

    # 创建台站。
    def create_station(self, payload: StationUpsertRequest):
        self._validate_station_payload(payload)
        airport = self._repository.get_airport(payload.airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")

        station = self._repository.create_station(**payload.model_dump(by_alias=False))
        self._session.commit()
        self._session.refresh(station)
        self._session.expunge(station)
        return station, []

    # 查询台站列表。
    def list_stations(
        self,
        *,
        airport_id: int | None,
        station_type: str | None,
        keyword: str | None,
        runway_no: str | None,
        page: int,
        page_size: int,
    ) -> StationListResponse:
        offset = (page - 1) * page_size
        stations, total = self._repository.list_stations(
            offset=offset,
            limit=page_size,
            airport_id=airport_id,
            station_type=station_type,
            keyword=keyword,
            runway_no=runway_no,
        )
        items = [self._build_station_list_item(station) for station in stations]
        return StationListResponse(items=items, total=total, page=page, pageSize=page_size)

    # 查询台站详情。
    def get_station(self, station_id: int) -> StationResponse:
        station = self._repository.get_station(station_id)
        if station is None:
            raise DataManagementNotFoundError("station_not_found", "station not found")
        return StationResponse.model_validate(station)

    # 更新台站。
    def update_station(self, station_id: int, payload: StationUpsertRequest):
        self._validate_station_payload(payload)
        station = self._repository.get_station(station_id)
        if station is None:
            raise DataManagementNotFoundError("station_not_found", "station not found")

        airport = self._repository.get_airport(payload.airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")

        updated_station = self._repository.update_station(
            station,
            **payload.model_dump(by_alias=False),
        )
        self._session.commit()
        self._session.refresh(updated_station)
        self._session.expunge(updated_station)
        return updated_station, []

    # 删除机场，级联删除子跑道与子台站。
    def delete_airport(self, airport_id: int) -> None:
        airport = self._repository.get_airport(airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")

        for station in self._repository.list_stations_by_airport_id(airport_id):
            self._repository.delete_station(station)
        for runway in self._repository.list_runways_by_airport_id(airport_id):
            self._repository.delete_runway(runway)

        self._repository.delete_airport(airport)
        self._session.commit()

    # 删除跑道，级联删除引用该跑道的台站。
    def delete_runway(self, runway_id: int) -> None:
        runway = self._repository.get_runway(runway_id)
        if runway is None:
            raise DataManagementNotFoundError("runway_not_found", "runway not found")

        for station in self._repository.list_stations_referencing_runway(runway_id):
            self._repository.delete_station(station)

        self._repository.delete_runway(runway)
        self._session.commit()

    # 删除台站。
    def delete_station(self, station_id: int) -> None:
        station = self._repository.get_station(station_id)
        if station is None:
            raise DataManagementNotFoundError("station_not_found", "station not found")

        self._repository.delete_station(station)
        self._session.commit()

    # 从 Excel 文件导入机场（含跑道和台站）。
    def import_airport_from_excel(
        self,
        *,
        excel_bytes: bytes,
        original_filename: str,
    ) -> "AirportImportResponse":
        from app.application.data_management_import import (
            AirportImportParseError,
            _import_airport_from_excel,
        )
        from app.schemas.data_management import AirportImportResponse
        try:
            result = _import_airport_from_excel(
                session=self._session,
                excel_bytes=excel_bytes,
                original_filename=original_filename,
            )
            self._session.commit()
        except AirportImportParseError as exc:
            self._session.rollback()
            raise DataManagementValidationError("import_parse_error", str(exc)) from exc
        except Exception as exc:
            self._session.rollback()
            raise DataManagementValidationError("import_failed", str(exc)) from exc
        return AirportImportResponse(**result)

    # 批量从多个 Excel 文件导入机场。
    def import_airports_from_batch(
        self,
        files: list[tuple[bytes, str]],
    ) -> "AirportImportBatchResponse":
        from app.schemas.data_management import AirportImportBatchResponse, AirportImportItem

        items: list[AirportImportItem] = []
        imported_count = 0
        skipped_count = 0

        for file_bytes, filename in files:
            if not (filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls")):
                items.append(AirportImportItem(fileName=filename, status="skipped"))
                skipped_count += 1
                continue

            if filename.startswith("~$"):
                items.append(AirportImportItem(fileName=filename, status="skipped"))
                skipped_count += 1
                continue

            try:
                result = self.import_airport_from_excel(
                    excel_bytes=file_bytes,
                    original_filename=filename,
                )
                items.append(AirportImportItem(
                    fileName=filename,
                    status="imported",
                    airportId=result.id,
                    airportName=result.airport_name,
                    runwayCount=result.runway_count,
                    stationCount=result.station_count,
                ))
                imported_count += 1
            except DataManagementValidationError as exc:
                items.append(AirportImportItem(
                    fileName=filename,
                    status="error",
                    errorMessage=str(exc),
                ))

        return AirportImportBatchResponse(
            items=items,
            totalFiles=len(files),
            importedCount=imported_count,
            skippedCount=skipped_count,
        )

    # 查询机场选项。
    def list_airport_options(self) -> list[OptionItemResponse]:
        return [OptionItemResponse.model_validate(airport) for airport in self._repository.list_airport_options()]

    # 查询台站类型选项。
    def list_station_type_options(self) -> list[StationTypeOptionResponse]:
        station_types = self._repository.list_station_type_options()
        if not station_types:
            station_types = ["NDB"]
        return [
            StationTypeOptionResponse(value=station_type, label=station_type)
            for station_type in station_types
        ]

    # 查询机场下跑道选项。
    def list_runway_options_by_airport_id(self, airport_id: int) -> list[OptionItemResponse]:
        airport = self._repository.get_airport(airport_id)
        if airport is None:
            raise DataManagementNotFoundError("airport_not_found", "airport not found")
        runways = self._repository.list_runway_options_by_airport_id(airport_id)
        return [OptionItemResponse.model_validate(runway) for runway in runways]

    # 构造机场列表项。
    def _build_airport_list_item(self, airport) -> AirportListItemResponse:
        return AirportListItemResponse(
            id=airport.id,
            name=airport.name,
            longitude=airport.longitude,
            latitude=airport.latitude,
            altitude=airport.altitude,
            runwayCount=self._repository.count_runways_by_airport_id(airport.id),
            stationCount=self._repository.count_stations_by_airport_id(airport.id),
            createdAt=airport.created_at,
            updatedAt=airport.updated_at,
        )

    # 构造跑道列表项。
    def _build_runway_list_item(self, runway) -> RunwayListItemResponse:
        airport = self._repository.get_airport(runway.airport_id)
        return RunwayListItemResponse(
            id=runway.id,
            airportId=runway.airport_id,
            airportName=airport.name if airport is not None else "",
            name=runway.name,
            runNumber=runway.run_number,
            headingDegrees=runway.direction,
            lengthMeters=runway.length,
            width=runway.width,
            altitude=runway.altitude,
            longitude=runway.longitude,
            latitude=runway.latitude,
            enterHeight=runway.enter_height,
            maximumAirworthiness=runway.maximum_airworthiness,
            stationSubType=runway.station_sub_type,
            runwayCodeA=runway.runway_code_a,
            runwayType=runway.runway_type,
            runwayCodeB=runway.runway_code_b,
            createdAt=runway.created_at,
            updatedAt=runway.updated_at,
        )

    # 构造台站列表项。
    def _build_station_list_item(self, station) -> StationListItemResponse:
        airport = self._repository.get_airport(station.airport_id)
        return StationListItemResponse(
            id=station.id,
            airportId=station.airport_id,
            airportName=airport.name if airport is not None else "",
            name=station.name,
            stationType=station.station_type,
            stationGroup=station.station_group,
            frequency=station.frequency,
            longitude=station.longitude,
            latitude=station.latitude,
            altitude=station.altitude,
            coverageRadius=station.coverage_radius,
            flyHeight=station.fly_height,
            antennaHag=station.antenna_hag,
            runwayNo=station.runway_no,
            reflectionNetHag=station.reflection_net_hag,
            centerAntennaH=station.center_antenna_h,
            bAntennaH=station.b_antenna_h,
            bToCenterDistance=station.b_to_center_distance,
            reflectionDiameter=station.reflection_diameter,
            downwardAngle=station.downward_angle,
            antennaTag=station.antenna_tag,
            distanceToRunway=station.distance_to_runway,
            distanceVToRunway=station.distance_v_to_runway,
            distanceEndoRunway=station.distance_endo_runway,
            unitNumber=station.unit_number,
            aircraft=station.aircraft,
            antennaHeight=station.antenna_height,
            stationSubType=station.station_sub_type,
            combineId=station.combine_id,
            createdAt=station.created_at,
            updatedAt=station.updated_at,
        )

    # 校验机场入参。
    def _validate_airport_payload(self, payload: AirportUpsertRequest) -> None:
        self._validate_name(payload.name, field_name="name")
        self._validate_coordinates(payload.longitude, payload.latitude)
        self._validate_non_negative_fields((("altitude", payload.altitude),))

    # 校验跑道入参。
    def _validate_runway_payload(self, payload: RunwayUpsertRequest) -> None:
        self._validate_name(payload.name, field_name="name")
        self._validate_identifier(payload.run_number, field_name="runNumber")
        self._validate_coordinates(payload.longitude, payload.latitude)
        self._validate_non_negative_fields(
            (
                ("direction", payload.direction),
                ("length", payload.length),
                ("width", payload.width),
                ("altitude", payload.altitude),
                ("enterHeight", payload.enter_height),
                ("maximumAirworthiness", payload.maximum_airworthiness),
            )
        )
        if payload.direction is not None and float(payload.direction) >= 360:
            raise DataManagementValidationError(
                "invalid_direction",
                "direction must be less than 360",
            )

    # 校验台站入参。
    def _validate_station_payload(self, payload: StationUpsertRequest) -> None:
        self._validate_name(payload.name, field_name="name")
        self._validate_identifier(payload.station_type, field_name="stationType")
        self._validate_coordinates(payload.longitude, payload.latitude)
        self._validate_non_negative_fields(
            (
                ("frequency", payload.frequency),
                ("altitude", payload.altitude),
                ("coverageRadius", payload.coverage_radius),
                ("flyHeight", payload.fly_height),
                ("antennaHag", payload.antenna_hag),
                ("reflectionNetHag", payload.reflection_net_hag),
                ("centerAntennaH", payload.center_antenna_h),
                ("bAntennaH", payload.b_antenna_h),
                ("bToCenterDistance", payload.b_to_center_distance),
                ("reflectionDiameter", payload.reflection_diameter),
                ("downwardAngle", payload.downward_angle),
                ("antennaTag", payload.antenna_tag),
                ("distanceToRunway", payload.distance_to_runway),
                ("distanceVToRunway", payload.distance_v_to_runway),
                ("distanceEndoRunway", payload.distance_endo_runway),
                ("antennaHeight", payload.antenna_height),
            )
        )

    # 校验经纬度范围。
    def _validate_coordinates(
        self,
        longitude: float | None,
        latitude: float | None,
    ) -> None:
        if longitude is not None and not (-180 <= float(longitude) <= 180):
            raise DataManagementValidationError(
                "invalid_longitude",
                "longitude must be between -180 and 180",
            )
        if latitude is not None and not (-90 <= float(latitude) <= 90):
            raise DataManagementValidationError(
                "invalid_latitude",
                "latitude must be between -90 and 90",
            )

    # 校验数字字段不能为负数。
    def _validate_non_negative_fields(
        self,
        fields: Iterable[tuple[str, Any]],
    ) -> None:
        for field_name, value in fields:
            if value is None:
                continue
            if float(value) < 0:
                raise DataManagementValidationError(
                    f"invalid_{self._to_snake_case(field_name)}",
                    f"{field_name} must be greater than or equal to 0",
                )

    # 校验名称字段非空。
    def _validate_name(self, value: str, *, field_name: str) -> None:
        if not value.strip():
            raise DataManagementValidationError(
                f"invalid_{self._to_snake_case(field_name)}",
                f"{field_name} must not be empty",
            )

    # 校验标识字段非空。
    def _validate_identifier(self, value: str, *, field_name: str) -> None:
        if not value.strip():
            raise DataManagementValidationError(
                f"invalid_{self._to_snake_case(field_name)}",
                f"{field_name} must not be empty",
            )

    # 转换字段名为 snake_case 错误码片段。
    def _to_snake_case(self, value: str) -> str:
        characters: list[str] = []
        for index, character in enumerate(value):
            if character.isupper() and index > 0:
                characters.append("_")
            characters.append(character.lower())
        return "".join(characters)
