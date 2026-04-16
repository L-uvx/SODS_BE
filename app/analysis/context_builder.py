from dataclasses import dataclass
from typing import Any


@dataclass
class AirportAnalysisContext:
    airport: Any
    runways: list[Any]
    stations: list[Any]
    obstacles: list[Any]


def build_airport_analysis_context(
    *,
    repository: Any,
    airport_ids: list[int],
    import_batch_id: str,
) -> list[AirportAnalysisContext]:
    airports = repository.list_airports_by_ids(airport_ids)
    obstacles = repository.list_obstacles_by_batch_id(import_batch_id)
    return [
        AirportAnalysisContext(
            airport=airport,
            runways=repository.list_runways_by_airport_id(airport.id),
            stations=repository.list_stations_by_airport_id(airport.id),
            obstacles=obstacles,
        )
        for airport in airports
    ]
