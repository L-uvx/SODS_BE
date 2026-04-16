from app.analysis.context_builder import build_airport_analysis_context


class DummyRepository:
    def list_airports_by_ids(self, airport_ids):
        return [
            type(
                "Airport",
                (),
                {
                    "id": 1,
                    "name": "Airport A",
                    "longitude": 104.1,
                    "latitude": 30.1,
                },
            )()
        ]

    def list_runways_by_airport_id(self, airport_id):
        return [type("Runway", (), {"id": 11, "name": "RWY 01"})()]

    def list_stations_by_airport_id(self, airport_id):
        return [
            type(
                "Station",
                (),
                {
                    "id": 21,
                    "name": "Station A",
                    "longitude": 104.11,
                    "latitude": 30.11,
                    "altitude": 498.2,
                },
            )()
        ]

    def list_obstacles_by_batch_id(self, import_batch_id):
        return [
            type(
                "Obstacle",
                (),
                {
                    "id": 31,
                    "name": "Obstacle A",
                    "raw_payload": {
                        "geometry": {
                            "type": "MultiPolygon",
                            "coordinates": [
                                [
                                    [
                                        [104.1, 30.1],
                                        [104.1005, 30.1],
                                        [104.1005, 30.1005],
                                        [104.1, 30.1005],
                                        [104.1, 30.1],
                                    ]
                                ]
                            ],
                        }
                    },
                },
            )()
        ]


def test_build_airport_analysis_context_collects_related_entities() -> None:
    contexts = build_airport_analysis_context(
        repository=DummyRepository(),
        airport_ids=[1],
        import_batch_id="import-batch-1",
    )

    assert len(contexts) == 1
    assert contexts[0].airport.id == 1
    assert len(contexts[0].runways) == 1
    assert len(contexts[0].stations) == 1
    assert len(contexts[0].obstacles) == 1
