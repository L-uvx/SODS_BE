from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.application.data_management import (
    DataManagementConflictError,
    DataManagementNotFoundError,
    DataManagementService,
    DataManagementValidationError,
)
from app.schemas.data_management import (
    AirportImportBatchResponse,
    AirportListResponse,
    AirportResponse,
    AirportUpsertRequest,
    AirportWriteResponse,
    DomainErrorResponse,
    ObstacleListResponse,
    ObstacleResponse,
    OptionItemResponse,
    RunwayListResponse,
    RunwayResponse,
    RunwayUpsertRequest,
    RunwayWriteResponse,
    StationCreateResponse,
    StationListResponse,
    StationResponse,
    StationTypeOptionResponse,
    StationWriteResponse,
    StationUpsertRequest,
)


router = APIRouter(prefix="/data-management", tags=["data-management"])

NOT_FOUND_RESPONSE = {404: {"model": DomainErrorResponse}}
CONFLICT_RESPONSE = {409: {"model": DomainErrorResponse}}
NOT_FOUND_AND_CONFLICT_RESPONSES = {
    404: {"model": DomainErrorResponse},
    409: {"model": DomainErrorResponse},
}


def _raise_api_error(
    error: DataManagementConflictError
    | DataManagementNotFoundError
    | DataManagementValidationError,
) -> None:
    error_code = error.code
    if error_code == "runway_referenced_by_station":
        error_code = "runway_has_stations"

    detail = {
        "code": error_code,
        "message": error.message,
    }
    if isinstance(error, DataManagementConflictError):
        detail.update(error.extra)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    if isinstance(error, DataManagementValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# 查询机场列表。
@router.get("/airports", response_model=AirportListResponse)
def list_airports(
    keyword: str | None = None,
    has_coordinates: bool | None = Query(default=None, alias="hasCoordinates"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1),
    session: Session = Depends(get_db_session),
) -> AirportListResponse:
    service = DataManagementService(session)
    return service.list_airports(
        keyword=keyword,
        has_coordinates=has_coordinates,
        page=page,
        page_size=page_size,
    )


# 查询机场详情。
@router.get("/airports/{airport_id}", response_model=AirportResponse, responses=NOT_FOUND_RESPONSE)
def get_airport(
    airport_id: int,
    session: Session = Depends(get_db_session),
) -> AirportResponse:
    service = DataManagementService(session)
    try:
        return service.get_airport(airport_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)


# 创建机场。
@router.post(
    "/airports",
    response_model=AirportWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_airport(
    payload: AirportUpsertRequest,
    session: Session = Depends(get_db_session),
) -> AirportWriteResponse:
    service = DataManagementService(session)
    try:
        return service.create_airport(payload)
    except DataManagementValidationError as error:
        _raise_api_error(error)


# 更新机场。
@router.put("/airports/{airport_id}", response_model=AirportWriteResponse, responses=NOT_FOUND_RESPONSE)
def update_airport(
    airport_id: int,
    payload: AirportUpsertRequest,
    session: Session = Depends(get_db_session),
) -> AirportWriteResponse:
    service = DataManagementService(session)
    try:
        return service.update_airport(airport_id, payload)
    except (DataManagementNotFoundError, DataManagementValidationError) as error:
        _raise_api_error(error)


# 删除机场。
@router.delete(
    "/airports/{airport_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
)
def delete_airport(
    airport_id: int,
    session: Session = Depends(get_db_session),
) -> Response:
    service = DataManagementService(session)
    try:
        service.delete_airport(airport_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# 查询跑道列表。
@router.get("/runways", response_model=RunwayListResponse)
def list_runways(
    airport_id: int | None = Query(default=None, alias="airportId"),
    keyword: str | None = None,
    run_number: str | None = Query(default=None, alias="runNumber"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1),
    session: Session = Depends(get_db_session),
) -> RunwayListResponse:
    service = DataManagementService(session)
    return service.list_runways(
        airport_id=airport_id,
        keyword=keyword,
        run_number=run_number,
        page=page,
        page_size=page_size,
    )


# 查询跑道详情。
@router.get("/runways/{runway_id}", response_model=RunwayResponse, responses=NOT_FOUND_RESPONSE)
def get_runway(
    runway_id: int,
    session: Session = Depends(get_db_session),
) -> RunwayResponse:
    service = DataManagementService(session)
    try:
        return service.get_runway(runway_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)


# 创建跑道。
@router.post(
    "/runways",
    response_model=RunwayWriteResponse,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND_AND_CONFLICT_RESPONSES,
)
def create_runway(
    payload: RunwayUpsertRequest,
    session: Session = Depends(get_db_session),
) -> RunwayWriteResponse:
    service = DataManagementService(session)
    try:
        return service.create_runway(payload)
    except (DataManagementConflictError, DataManagementNotFoundError, DataManagementValidationError) as error:
        _raise_api_error(error)


# 更新跑道。
@router.put(
    "/runways/{runway_id}",
    response_model=RunwayWriteResponse,
    responses=NOT_FOUND_AND_CONFLICT_RESPONSES,
)
def update_runway(
    runway_id: int,
    payload: RunwayUpsertRequest,
    session: Session = Depends(get_db_session),
) -> RunwayWriteResponse:
    service = DataManagementService(session)
    try:
        return service.update_runway(runway_id, payload)
    except (DataManagementConflictError, DataManagementNotFoundError, DataManagementValidationError) as error:
        _raise_api_error(error)


# 删除跑道。
@router.delete(
    "/runways/{runway_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
)
def delete_runway(
    runway_id: int,
    session: Session = Depends(get_db_session),
) -> Response:
    service = DataManagementService(session)
    try:
        service.delete_runway(runway_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# 查询台站列表。
@router.get("/stations", response_model=StationListResponse)
def list_stations(
    airport_id: int | None = Query(default=None, alias="airportId"),
    station_type: str | None = Query(default=None, alias="stationType"),
    keyword: str | None = None,
    runway_no: str | None = Query(default=None, alias="runwayNo"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1),
    session: Session = Depends(get_db_session),
) -> StationListResponse:
    service = DataManagementService(session)
    return service.list_stations(
        airport_id=airport_id,
        station_type=station_type,
        keyword=keyword,
        runway_no=runway_no,
        page=page,
        page_size=page_size,
    )


# 查询台站详情。
@router.get("/stations/{station_id}", response_model=StationResponse, responses=NOT_FOUND_RESPONSE)
def get_station(
    station_id: int,
    session: Session = Depends(get_db_session),
) -> StationResponse:
    service = DataManagementService(session)
    try:
        return service.get_station(station_id)
    except (DataManagementNotFoundError, DataManagementValidationError) as error:
        _raise_api_error(error)


# 创建台站。
@router.post(
    "/stations",
    response_model=StationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND_RESPONSE,
)
def create_station(
    payload: StationUpsertRequest,
    session: Session = Depends(get_db_session),
) -> StationCreateResponse:
    service = DataManagementService(session)
    try:
        station, warnings = service.create_station(payload)
    except (DataManagementNotFoundError, DataManagementValidationError) as error:
        _raise_api_error(error)
    return StationCreateResponse(id=station.id, warnings=warnings)


# 更新台站。
@router.put("/stations/{station_id}", response_model=StationWriteResponse, responses=NOT_FOUND_RESPONSE)
def update_station(
    station_id: int,
    payload: StationUpsertRequest,
    session: Session = Depends(get_db_session),
) -> StationWriteResponse:
    service = DataManagementService(session)
    try:
        station, warnings = service.update_station(station_id, payload)
    except (DataManagementNotFoundError, DataManagementValidationError) as error:
        _raise_api_error(error)
    return StationWriteResponse(id=station.id, warnings=warnings)


# 删除台站。
@router.delete(
    "/stations/{station_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
)
def delete_station(
    station_id: int,
    session: Session = Depends(get_db_session),
) -> Response:
    service = DataManagementService(session)
    try:
        service.delete_station(station_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# 批量导入机场 Excel（含跑道和台站）。
@router.post(
    "/import/airports",
    response_model=AirportImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_airports(
    excel_files: List[UploadFile] = File(alias="excelFiles"),
    session: Session = Depends(get_db_session),
) -> AirportImportBatchResponse:
    service = DataManagementService(session)
    files = [
        (file.file.read(), file.filename or "unknown.xlsx")
        for file in excel_files
    ]
    return service.import_airports_from_batch(files)


# 查询机场选项。
@router.get("/options/airports", response_model=list[OptionItemResponse])
def list_airport_options(
    session: Session = Depends(get_db_session),
) -> list[OptionItemResponse]:
    service = DataManagementService(session)
    return service.list_airport_options()


# 查询台站类型选项。
@router.get("/options/station-types", response_model=list[StationTypeOptionResponse])
def list_station_type_options(
    session: Session = Depends(get_db_session),
) -> list[StationTypeOptionResponse]:
    service = DataManagementService(session)
    return service.list_station_type_options()


# 查询机场下跑道选项。
@router.get(
    "/airports/{airport_id}/runways/options",
    response_model=list[OptionItemResponse],
    responses=NOT_FOUND_RESPONSE,
)
def list_airport_runway_options(
    airport_id: int,
    session: Session = Depends(get_db_session),
) -> list[OptionItemResponse]:
    service = DataManagementService(session)
    try:
        return service.list_runway_options_by_airport_id(airport_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)


# 查询障碍物列表。
@router.get("/obstacles", response_model=ObstacleListResponse)
def list_obstacles(
    project_id: int | None = Query(default=None, alias="projectId"),
    keyword: str | None = None,
    obstacle_type: str | None = Query(default=None, alias="obstacleType"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1),
    session: Session = Depends(get_db_session),
) -> ObstacleListResponse:
    service = DataManagementService(session)
    return service.list_obstacles(
        project_id=project_id,
        keyword=keyword,
        obstacle_type=obstacle_type,
        page=page,
        page_size=page_size,
    )


# 查询障碍物详情。
@router.get("/obstacles/{obstacle_id}", response_model=ObstacleResponse, responses=NOT_FOUND_RESPONSE)
def get_obstacle(
    obstacle_id: int,
    session: Session = Depends(get_db_session),
) -> ObstacleResponse:
    service = DataManagementService(session)
    try:
        return service.get_obstacle(obstacle_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)


# 删除障碍物。
@router.delete(
    "/obstacles/{obstacle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
)
def delete_obstacle(
    obstacle_id: int,
    session: Session = Depends(get_db_session),
) -> Response:
    service = DataManagementService(session)
    try:
        service.delete_obstacle(obstacle_id)
    except DataManagementNotFoundError as error:
        _raise_api_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
