from typing import Annotated

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field


class ImportTaskCreateRequest(BaseModel):
    project_name: str = Field(alias="projectName")
    obstacle_type: str = Field(alias="obstacleType")
    file_name: str = Field(alias="fileName")
    file_bytes: bytes = Field(alias="fileBytes")

    model_config = ConfigDict(populate_by_name=True)

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


class BootstrapResponse(BaseModel):
    airport: BootstrapAirportResponse | None
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
    rule_name: str = Field(alias="ruleName")
    zone_name: str = Field(alias="zoneName")
    zone_definition: dict[str, object] = Field(alias="zoneDefinition")
    is_applicable: bool = Field(alias="isApplicable")
    is_compliant: bool = Field(alias="isCompliant")
    message: str
    metrics: dict[str, float | str | bool | None]

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisSpatialAirportFactsResponse(BaseModel):
    airport_id: int = Field(alias="airportId")
    reference_point: AnalysisSpatialReferencePointResponse = Field(
        alias="referencePoint"
    )
    runway_count: int = Field(alias="runwayCount")
    station_count: int = Field(alias="stationCount")
    obstacles: list[AnalysisSpatialObstacleResponse]
    rule_results: list[AnalysisRuleResultResponse] = Field(alias="ruleResults")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AnalysisSpatialFactsResponse(BaseModel):
    airports: list[AnalysisSpatialAirportFactsResponse]


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
    spatial_facts: AnalysisSpatialFactsResponse | None = Field(
        alias="spatialFacts",
        default=None,
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
