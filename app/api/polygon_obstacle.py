from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.application.polygon_obstacle_import import PolygonObstacleImportService
from app.schemas.polygon_obstacle import (
    AnalysisTaskCreateRequest,
    AnalysisTaskResultResponse,
    AnalysisTaskStatusResponse,
    BootstrapResponse,
    ExportTaskResultResponse,
    ExportTaskStatusResponse,
    ImportTaskCreateRequest,
    ImportTaskResultResponse,
    ImportTaskStatusResponse,
    ImportTargetResponse,
)


router = APIRouter(prefix="/polygon-obstacle", tags=["polygon-obstacle"])


@router.get(
    "/bootstrap",
    response_model=BootstrapResponse,
)
def get_bootstrap(
    session: Session = Depends(get_db_session),
) -> BootstrapResponse:
    service = PolygonObstacleImportService(session)
    return service.get_bootstrap()


@router.post(
    "/import",
    response_model=ImportTaskStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_import_task(
    payload: ImportTaskCreateRequest = Depends(ImportTaskCreateRequest.as_form),
    session: Session = Depends(get_db_session),
) -> ImportTaskStatusResponse:
    service = PolygonObstacleImportService(session)
    return service.create_import_task(payload)


@router.get(
    "/import/{task_id}/status",
    response_model=ImportTaskStatusResponse,
)
def get_import_task_status(
    task_id: str,
    session: Session = Depends(get_db_session),
) -> ImportTaskStatusResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_import_task_status(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="import task not found")

    return result


@router.get(
    "/import/{task_id}/result",
    response_model=ImportTaskResultResponse,
)
def get_import_task_result(
    task_id: str,
    session: Session = Depends(get_db_session),
) -> ImportTaskResultResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_import_task_result(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="import task not found")

    return result


@router.get(
    "/import/{task_id}/targets",
    response_model=list[ImportTargetResponse],
)
def get_import_targets(
    task_id: str,
    session: Session = Depends(get_db_session),
) -> list[ImportTargetResponse]:
    service = PolygonObstacleImportService(session)
    result = service.get_import_targets(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="import task not found")

    return result


@router.post(
    "/analysis",
    response_model=AnalysisTaskStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_task(
    payload: AnalysisTaskCreateRequest,
    session: Session = Depends(get_db_session),
) -> AnalysisTaskStatusResponse:
    service = PolygonObstacleImportService(session)
    result = service.create_analysis_task(payload)

    if result is None:
        raise HTTPException(status_code=404, detail="import task not found")

    return result


@router.get(
    "/analysis/{task_id}/status",
    response_model=AnalysisTaskStatusResponse,
)
def get_analysis_task_status(
    task_id: str,
    session: Session = Depends(get_db_session),
) -> AnalysisTaskStatusResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_analysis_task_status(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="analysis task not found")

    return result


@router.get(
    "/analysis/{task_id}/result",
    response_model=AnalysisTaskResultResponse,
)
def get_analysis_task_result(
    task_id: str,
    session: Session = Depends(get_db_session),
) -> AnalysisTaskResultResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_analysis_task_result(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="analysis task not found")

    return result


@router.post(
    "/analysis/{task_id}/export",
    response_model=ExportTaskStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_export_task(
    task_id: str,
    session: Session = Depends(get_db_session),
) -> ExportTaskStatusResponse:
    service = PolygonObstacleImportService(session)
    try:
        result = service.create_export_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="analysis task not found")

    return result


@router.get(
    "/analysis/{task_id}/export/{export_task_id}/status",
    response_model=ExportTaskStatusResponse,
)
def get_export_task_status(
    task_id: str,
    export_task_id: str,
    session: Session = Depends(get_db_session),
) -> ExportTaskStatusResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_export_task_status(task_id, export_task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="export task not found")

    return result


@router.get(
    "/analysis/{task_id}/export/{export_task_id}/result",
    response_model=ExportTaskResultResponse,
)
def get_export_task_result(
    task_id: str,
    export_task_id: str,
    session: Session = Depends(get_db_session),
) -> ExportTaskResultResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_export_task_result(task_id, export_task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="export task not found")

    return result


@router.get("/exports/{export_task_id}/download")
def download_export_file(
    export_task_id: str,
    session: Session = Depends(get_db_session),
) -> FileResponse:
    service = PolygonObstacleImportService(session)
    result = service.get_export_download(export_task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="export file not found")

    file_path, file_name = result
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
