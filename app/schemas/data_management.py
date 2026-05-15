from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DataManagementBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
    )

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty")
        return value

    @staticmethod
    def validate_non_empty_identifier(value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class WarningResponse(DataManagementBaseModel):
    code: str
    message: str


class ConflictDetailResponse(DataManagementBaseModel):
    code: str
    message: str
    runway_count: int | None = Field(default=None, alias="runwayCount")
    station_count: int | None = Field(default=None, alias="stationCount")
    referenced_station_count: int | None = Field(
        default=None,
        alias="referencedStationCount",
    )


class ConflictResponseEnvelope(DataManagementBaseModel):
    detail: ConflictDetailResponse


class DomainErrorResponse(DataManagementBaseModel):
    detail: ConflictDetailResponse


class OptionItemResponse(DataManagementBaseModel):
    id: int
    name: str


class StationTypeOptionResponse(DataManagementBaseModel):
    value: str
    label: str


class AirportUpsertRequest(DataManagementBaseModel):
    name: str
    longitude: float | None = Field(default=None)
    latitude: float | None = Field(default=None)
    altitude: float | None = Field(default=None, ge=0)

    @field_validator('longitude', 'latitude', mode='before')
    @classmethod
    def parse_coordinate(cls, v):
        from app.application.data_management_import import _parse_degree
        return _parse_degree(v)

    @field_validator('longitude')
    @classmethod
    def validate_longitude_range(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError('longitude must be between -180 and 180')
        return v

    @field_validator('latitude')
    @classmethod
    def validate_latitude_range(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('latitude must be between -90 and 90')
        return v


class AirportResponse(DataManagementBaseModel):
    id: int
    name: str
    longitude: float | None = None
    latitude: float | None = None
    altitude: float | None = None


class AirportWriteResponse(DataManagementBaseModel):
    id: int
    warnings: list[WarningResponse] = Field(default_factory=list)


class AirportListItemResponse(AirportResponse):
    runway_count: int = Field(alias="runwayCount")
    station_count: int = Field(alias="stationCount")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class AirportListResponse(DataManagementBaseModel):
    items: list[AirportListItemResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class RunwayUpsertRequest(DataManagementBaseModel):
    airport_id: int = Field(alias="airportId")
    name: str
    run_number: str = Field(alias="runNumber")
    direction: float | None = Field(default=None, alias="headingDegrees", ge=0, lt=360)
    length: float | None = Field(default=None, alias="lengthMeters", ge=0)
    width: float | None = Field(default=None, ge=0)
    altitude: float | None = Field(default=None, ge=0)
    longitude: float | None = Field(default=None)
    latitude: float | None = Field(default=None)
    enter_height: float | None = Field(default=None, alias="enterHeight", ge=0)
    maximum_airworthiness: float | None = Field(
        default=None,
        alias="maximumAirworthiness",
        ge=0,
    )
    station_sub_type: str | None = Field(default=None, alias="stationSubType")
    runway_code_a: str | None = Field(default=None, alias="runwayCodeA")
    runway_type: str | None = Field(default=None, alias="runwayType")
    runway_code_b: str | None = Field(default=None, alias="runwayCodeB")

    @field_validator("run_number")
    @classmethod
    def validate_run_number_not_empty(cls, value: str) -> str:
        return cls.validate_non_empty_identifier(value)

    @field_validator('longitude', 'latitude', mode='before')
    @classmethod
    def parse_coordinate(cls, v):
        from app.application.data_management_import import _parse_degree
        return _parse_degree(v)

    @field_validator('longitude')
    @classmethod
    def validate_longitude_range(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError('longitude must be between -180 and 180')
        return v

    @field_validator('latitude')
    @classmethod
    def validate_latitude_range(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('latitude must be between -90 and 90')
        return v


class RunwayResponse(DataManagementBaseModel):
    id: int
    airport_id: int = Field(alias="airportId")
    name: str
    run_number: str = Field(alias="runNumber")
    direction: float | None = Field(default=None, alias="headingDegrees")
    length: float | None = Field(default=None, alias="lengthMeters")
    width: float | None = None
    altitude: float | None = None
    longitude: float | None = None
    latitude: float | None = None
    enter_height: float | None = Field(default=None, alias="enterHeight")
    maximum_airworthiness: float | None = Field(
        default=None,
        alias="maximumAirworthiness",
    )
    station_sub_type: str | None = Field(default=None, alias="stationSubType")
    runway_code_a: str | None = Field(default=None, alias="runwayCodeA")
    runway_type: str | None = Field(default=None, alias="runwayType")
    runway_code_b: str | None = Field(default=None, alias="runwayCodeB")


class RunwayWriteResponse(DataManagementBaseModel):
    id: int
    warnings: list[WarningResponse] = Field(default_factory=list)


class RunwayListItemResponse(RunwayResponse):
    airport_name: str = Field(alias="airportName")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class RunwayListResponse(DataManagementBaseModel):
    items: list[RunwayListItemResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class StationUpsertRequest(DataManagementBaseModel):
    airport_id: int = Field(alias="airportId")
    name: str
    station_type: str = Field(alias="stationType")
    station_group: str | None = Field(default=None, alias="stationGroup")
    frequency: float | None = Field(default=None, ge=0)
    longitude: float | None = Field(default=None)
    latitude: float | None = Field(default=None)
    altitude: float | None = Field(default=None, ge=0)
    coverage_radius: float | None = Field(default=None, alias="coverageRadius", ge=0)
    fly_height: float | None = Field(default=None, alias="flyHeight", ge=0)
    antenna_hag: float | None = Field(default=None, alias="antennaHag", ge=0)
    runway_no: str | None = Field(default=None, alias="runwayNo")
    reflection_net_hag: float | None = Field(default=None, alias="reflectionNetHag", ge=0)
    center_antenna_h: float | None = Field(default=None, alias="centerAntennaH", ge=0)
    b_antenna_h: float | None = Field(default=None, alias="bAntennaH", ge=0)
    b_to_center_distance: float | None = Field(default=None, alias="bToCenterDistance", ge=0)
    reflection_diameter: float | None = Field(default=None, alias="reflectionDiameter", ge=0)
    downward_angle: float | None = Field(default=None, alias="downwardAngle", ge=0)
    antenna_tag: float | None = Field(default=None, alias="antennaTag", ge=0)
    distance_to_runway: float | None = Field(default=None, alias="distanceToRunway", ge=0)
    distance_v_to_runway: float | None = Field(default=None, alias="distanceVToRunway", ge=0)
    distance_endo_runway: float | None = Field(default=None, alias="distanceEndoRunway", ge=0)
    unit_number: str | None = Field(default=None, alias="unitNumber")
    aircraft: str | None = None
    antenna_height: float | None = Field(default=None, alias="antennaHeight", ge=0)
    station_sub_type: str | None = Field(default=None, alias="stationSubType")
    combine_id: str | None = Field(default=None, alias="combineId")

    @field_validator("station_type")
    @classmethod
    def validate_station_type_not_empty(cls, value: str) -> str:
        return cls.validate_non_empty_identifier(value)

    @field_validator('longitude', 'latitude', mode='before')
    @classmethod
    def parse_coordinate(cls, v):
        from app.application.data_management_import import _parse_degree
        return _parse_degree(v)

    @field_validator('longitude')
    @classmethod
    def validate_longitude_range(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError('longitude must be between -180 and 180')
        return v

    @field_validator('latitude')
    @classmethod
    def validate_latitude_range(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError('latitude must be between -90 and 90')
        return v


class StationResponse(DataManagementBaseModel):
    id: int
    airport_id: int = Field(alias="airportId")
    name: str
    station_type: str = Field(alias="stationType")
    station_group: str | None = Field(default=None, alias="stationGroup")
    frequency: float | None = None
    longitude: float | None = None
    latitude: float | None = None
    altitude: float | None = None
    coverage_radius: float | None = Field(default=None, alias="coverageRadius")
    fly_height: float | None = Field(default=None, alias="flyHeight")
    antenna_hag: float | None = Field(default=None, alias="antennaHag")
    runway_no: str | None = Field(default=None, alias="runwayNo")
    reflection_net_hag: float | None = Field(default=None, alias="reflectionNetHag")
    center_antenna_h: float | None = Field(default=None, alias="centerAntennaH")
    b_antenna_h: float | None = Field(default=None, alias="bAntennaH")
    b_to_center_distance: float | None = Field(default=None, alias="bToCenterDistance")
    reflection_diameter: float | None = Field(default=None, alias="reflectionDiameter")
    downward_angle: float | None = Field(default=None, alias="downwardAngle")
    antenna_tag: float | None = Field(default=None, alias="antennaTag")
    distance_to_runway: float | None = Field(default=None, alias="distanceToRunway")
    distance_v_to_runway: float | None = Field(default=None, alias="distanceVToRunway")
    distance_endo_runway: float | None = Field(default=None, alias="distanceEndoRunway")
    unit_number: str | None = Field(default=None, alias="unitNumber")
    aircraft: str | None = None
    antenna_height: float | None = Field(default=None, alias="antennaHeight")
    station_sub_type: str | None = Field(default=None, alias="stationSubType")
    combine_id: str | None = Field(default=None, alias="combineId")


class StationListItemResponse(StationResponse):
    airport_name: str = Field(alias="airportName")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class StationListResponse(DataManagementBaseModel):
    items: list[StationListItemResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class StationWriteResponse(DataManagementBaseModel):
    id: int
    warnings: list[WarningResponse] = Field(default_factory=list)


class StationCreateResponse(StationWriteResponse):
    pass


class StationUpdateResponse(StationWriteResponse):
    pass


class DeleteResponse(DataManagementBaseModel):
    success: bool


class AirportImportWarning(DataManagementBaseModel):
    code: str
    message: str


class AirportImportResponse(DataManagementBaseModel):
    id: int
    airport_name: str = Field(alias="airportName")
    runway_count: int = Field(alias="runwayCount")
    station_count: int = Field(alias="stationCount")
    warnings: list[AirportImportWarning] = Field(default_factory=list)


class AirportImportItem(DataManagementBaseModel):
    filename: str = Field(alias="fileName")
    status: str
    airport_id: int | None = Field(default=None, alias="airportId")
    airport_name: str | None = Field(default=None, alias="airportName")
    runway_count: int = Field(default=0, alias="runwayCount")
    station_count: int = Field(default=0, alias="stationCount")
    error_message: str | None = Field(default=None, alias="errorMessage")


class AirportImportBatchResponse(DataManagementBaseModel):
    items: list[AirportImportItem] = Field(default_factory=list)
    total_files: int = Field(alias="totalFiles")
    imported_count: int = Field(alias="importedCount")
    skipped_count: int = Field(alias="skippedCount")


class ObstacleGeometryResponse(DataManagementBaseModel):
    type: str
    coordinates: Any


class ObstacleResponse(DataManagementBaseModel):
    id: int
    project_id: int = Field(alias="projectId")
    name: str
    obstacle_type: str | None = Field(default=None, alias="obstacleType")
    top_elevation: float | None = Field(default=None, alias="topElevation")
    source_batch_id: str | None = Field(default=None, alias="sourceBatchId")
    source_row_no: int | None = Field(default=None, alias="sourceRowNo")
    geometry: ObstacleGeometryResponse | None = None
    raw_payload: dict[str, Any] | None = Field(default=None, alias="rawPayload")


class ObstacleListItemResponse(ObstacleResponse):
    project_name: str = Field(alias="projectName")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ObstacleListResponse(DataManagementBaseModel):
    items: list[ObstacleListItemResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
