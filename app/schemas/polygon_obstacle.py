from typing import Annotated

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field


class ImportTaskCreateRequest(BaseModel):
    project_name: str = Field(alias="projectName")
    obstacle_type: str = Field(alias="obstacleType")
    file_name: str = Field(alias="fileName")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def as_form(
        cls,
        project_name: Annotated[str, Form(alias="projectName")],
        obstacle_type: Annotated[str, Form(alias="obstacleType")],
        excel_file: Annotated[UploadFile, File(alias="excelFile")],
    ) -> "ImportTaskCreateRequest":
        return cls(
            projectName=project_name,
            obstacleType=obstacle_type,
            fileName=excel_file.filename,
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

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )
