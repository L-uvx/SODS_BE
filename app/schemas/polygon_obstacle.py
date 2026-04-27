from typing import Annotated

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field


class ImportTaskCreateRequest(BaseModel):
    project_name: str = Field(alias="projectName")
    obstacle_type: str = Field(alias="obstacleType")
    file_name: str = Field(alias="fileName")
    file_bytes: bytes = Field(alias="fileBytes")

    model_config = ConfigDict(populate_by_name=True)

    # 将 multipart 表单数据转换为导入请求对象。
    @classmethod
    async def as_form(
        cls,
        project_name: Annotated[str, Form(alias="projectName")],
        obstacle_type: Annotated[str, Form(alias="obstacleType")],
        excel_file: Annotated[UploadFile, File(alias="excelFile")],
    ) -> "ImportTaskCreateRequest":
        file_bytes = await excel_file.read()
        return cls(
            projectName=project_name,
            obstacleType=obstacle_type,
            fileName=excel_file.filename,
            fileBytes=file_bytes,
        )


class ImportTaskStatusResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str
    message: str
    progress_percent: int = Field(alias="progressPercent")
    project_id: int = Field(alias="projectId")
    obstacle_batch_id: str = Field(alias="obstacleBatchId")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ImportTaskResultResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str
    project_id: int = Field(alias="projectId")
    obstacle_batch_id: str = Field(alias="obstacleBatchId")
    imported_count: int = Field(alias="importedCount")
    failed_count: int = Field(alias="failedCount")
    bounding_box: dict[str, float] | None = Field(alias="boundingBox")
    obstacles: list["ImportedObstacleResponse"] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ImportedObstacleGeometryResponse(BaseModel):
    type: str
    coordinates: list[list[list[list[float]]]]


class ImportedObstacleResponse(BaseModel):
    id: int
    name: str
    obstacle_type: str = Field(alias="obstacleType")
    top_elevation: float = Field(alias="topElevation")
    source_row_numbers: list[int] = Field(alias="sourceRowNumbers")
    bounding_box: dict[str, float] | None = Field(alias="boundingBox")
    geometry: ImportedObstacleGeometryResponse

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ImportTargetResponse(BaseModel):
    id: int
    name: str
    category: str
    distance: float
    distance_unit: str = Field(alias="distanceUnit")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class BootstrapAirportResponse(BaseModel):
    id: int
    name: str
    longitude: float
    latitude: float
    stations: list["BootstrapStationResponse"] = Field(default_factory=list)


class BootstrapStationResponse(BaseModel):
    id: int
    name: str
    station_type: str | None = Field(alias="stationType")
    longitude: float
    latitude: float
    altitude: float | None

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


BootstrapAirportResponse.model_rebuild()


class BootstrapResponse(BaseModel):
    airports: list[BootstrapAirportResponse] = Field(default_factory=list)
    historical_obstacles: list[ImportedObstacleResponse] = Field(
        default_factory=list,
        alias="historicalObstacles",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisTaskCreateRequest(BaseModel):
    import_task_id: str = Field(alias="importTaskId")
    target_ids: list[int] = Field(alias="targetIds", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class AnalysisTaskStatusResponse(BaseModel):
    analysis_task_id: str = Field(alias="analysisTaskId")
    status: str
    message: str
    progress_percent: int = Field(alias="progressPercent")
    import_task_id: str = Field(alias="importTaskId")
    target_ids: list[int] = Field(alias="targetIds")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisResultTargetResponse(BaseModel):
    id: int
    name: str
    category: str


class AnalysisSpatialReferencePointResponse(BaseModel):
    longitude: float
    latitude: float


class AnalysisSpatialObstacleBoundingBoxResponse(BaseModel):
    min_x: float = Field(alias="minX")
    min_y: float = Field(alias="minY")
    max_x: float = Field(alias="maxX")
    max_y: float = Field(alias="maxY")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisSpatialObstacleResponse(BaseModel):
    obstacle_id: int = Field(alias="obstacleId")
    name: str
    raw_obstacle_type: str | None = Field(alias="rawObstacleType", default=None)
    global_obstacle_category: str = Field(alias="globalObstacleCategory")
    distance_to_airport_meters: float = Field(alias="distanceToAirportMeters")
    local_bounding_box: AnalysisSpatialObstacleBoundingBoxResponse = Field(
        alias="localBoundingBox"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisRuleResultResponse(BaseModel):
    station_id: int = Field(alias="stationId")
    station_name: str = Field(alias="stationName")
    station_type: str = Field(alias="stationType")
    obstacle_id: int = Field(alias="obstacleId")
    obstacle_name: str = Field(alias="obstacleName")
    raw_obstacle_type: str | None = Field(alias="rawObstacleType", default=None)
    global_obstacle_category: str = Field(alias="globalObstacleCategory")
    rule_code: str = Field(alias="ruleCode")
    rule_name: str = Field(alias="ruleName")
    zone_code: str = Field(alias="zoneCode")
    zone_name: str = Field(alias="zoneName")
    region_code: str = Field(alias="regionCode")
    region_name: str = Field(alias="regionName")
    is_applicable: bool = Field(alias="isApplicable")
    is_compliant: bool = Field(alias="isCompliant")
    message: str
    metrics: dict[str, float | str | bool | None]
    standards: "AnalysisStandardSetResponse"

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisStandardReferenceResponse(BaseModel):
    code: str
    text: str
    is_compliant: bool | None = Field(alias="isCompliant", default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisStandardSetResponse(BaseModel):
    gb: AnalysisStandardReferenceResponse | None = None
    mh: AnalysisStandardReferenceResponse | None = None


class AnalysisProtectionZoneMultipolygonGeometryResponse(BaseModel):
    shape_type: str = Field(alias="shapeType")
    coordinates: list[list[list[list[float]]]]

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneVerticalResponse(BaseModel):
    mode: str
    base_reference: str = Field(alias="baseReference")
    base_height_meters: float = Field(alias="baseHeightMeters")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneHeightFunctionResponse(BaseModel):
    type: str
    elevation_angle_degrees: float = Field(alias="elevationAngleDegrees")
    distance_metric: str = Field(alias="distanceMetric")
    start_distance_meters: float = Field(alias="startDistanceMeters")
    end_distance_meters: float = Field(alias="endDistanceMeters")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneDistanceSourceResponse(BaseModel):
    kind: str
    point: list[float]


class AnalysisProtectionZoneClampRangeResponse(BaseModel):
    start_meters: float = Field(alias="startMeters")
    end_meters: float = Field(alias="endMeters")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneHeightModelResponse(BaseModel):
    type: str
    angle_degrees: float = Field(alias="angleDegrees")
    distance_offset_meters: float | None = Field(
        alias="distanceOffsetMeters",
        default=None,
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneSurfaceResponse(BaseModel):
    type: str
    distance_source: AnalysisProtectionZoneDistanceSourceResponse = Field(
        alias="distanceSource"
    )
    distance_metric: str = Field(alias="distanceMetric")
    clamp_range: AnalysisProtectionZoneClampRangeResponse = Field(alias="clampRange")
    height_model: AnalysisProtectionZoneHeightModelResponse = Field(alias="heightModel")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneLocBuildingRestrictionZoneRegion3SurfaceResponse(BaseModel):
    type: str
    arc_height_meters: float = Field(alias="arcHeightMeters")
    alpha_degrees: float = Field(alias="alphaDegrees")
    station_point: list[float] = Field(alias="stationPoint", min_length=2, max_length=2)
    apex_point: list[float] = Field(alias="apexPoint", min_length=2, max_length=2)
    root_left_point: list[float] = Field(
        alias="rootLeftPoint",
        min_length=2,
        max_length=2,
    )
    root_right_point: list[float] = Field(
        alias="rootRightPoint",
        min_length=2,
        max_length=2,
    )
    arc_radius_meters: float = Field(alias="arcRadiusMeters")
    arc_points: list[list[float]] = Field(alias="arcPoints")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneAnalyticSurfaceVerticalResponse(BaseModel):
    mode: str
    base_reference: str = Field(alias="baseReference")
    base_height_meters: float = Field(alias="baseHeightMeters")
    height_function: AnalysisProtectionZoneHeightFunctionResponse = Field(
        alias="heightFunction",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneSurfaceAnalyticVerticalResponse(BaseModel):
    mode: str
    base_reference: str = Field(alias="baseReference")
    base_height_meters: float = Field(alias="baseHeightMeters")
    surface: (
        AnalysisProtectionZoneSurfaceResponse
        | AnalysisProtectionZoneLocBuildingRestrictionZoneRegion3SurfaceResponse
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZonePropertiesResponse(BaseModel):
    label: str


class AnalysisProtectionZoneStyleResponse(BaseModel):
    color_key: str = Field(alias="colorKey")
    fill: str
    stroke: str

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisProtectionZoneResponse(BaseModel):
    id: str
    airport_id: int = Field(alias="airportId")
    airport_name: str = Field(alias="airportName")
    station_id: int = Field(alias="stationId")
    station_name: str = Field(alias="stationName")
    station_type: str = Field(alias="stationType")
    rule_code: str = Field(alias="ruleCode")
    rule_name: str = Field(alias="ruleName")
    zone_code: str = Field(alias="zoneCode")
    zone_name: str = Field(alias="zoneName")
    region_code: str = Field(alias="regionCode")
    region_name: str = Field(alias="regionName")
    geometry: AnalysisProtectionZoneMultipolygonGeometryResponse
    vertical: (
        AnalysisProtectionZoneVerticalResponse
        | AnalysisProtectionZoneAnalyticSurfaceVerticalResponse
        | AnalysisProtectionZoneSurfaceAnalyticVerticalResponse
    )
    style: AnalysisProtectionZoneStyleResponse
    properties: AnalysisProtectionZonePropertiesResponse
    render_geometry: dict[str, object] | None = Field(
        alias="renderGeometry",
        default=None,
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisTaskResultResponse(BaseModel):
    analysis_task_id: str = Field(alias="analysisTaskId")
    status: str
    import_task_id: str = Field(alias="importTaskId")
    target_ids: list[int] = Field(alias="targetIds")
    selected_targets: list[AnalysisResultTargetResponse] = Field(
        alias="selectedTargets"
    )
    obstacle_count: int = Field(alias="obstacleCount")
    summary: str
    rule_results: list[AnalysisRuleResultResponse] = Field(
        alias="ruleResults",
        default_factory=list,
    )
    protection_zones: list[AnalysisProtectionZoneResponse] = Field(
        alias="protectionZones",
        default_factory=list,
    )

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ExportTaskStatusResponse(BaseModel):
    export_task_id: str = Field(alias="exportTaskId")
    analysis_task_id: str = Field(alias="analysisTaskId")
    status: str
    message: str
    progress_percent: int = Field(alias="progressPercent")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ExportTaskResultResponse(BaseModel):
    export_task_id: str = Field(alias="exportTaskId")
    analysis_task_id: str = Field(alias="analysisTaskId")
    status: str
    file_name: str | None = Field(alias="fileName")
    download_url: str | None = Field(alias="downloadUrl")
    error_message: str | None = Field(alias="errorMessage")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )
