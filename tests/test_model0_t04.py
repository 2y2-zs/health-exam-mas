import pytest
import simpy

from health_exam_mas.model0 import (
    ENTRY_LOCATION,
    EventLog,
    MODEL0_STATIONS,
    PackageConfig,
    PatientAgent,
    PatientState,
    StationAgent,
    eligible_stations,
    patient_process,
)


def test_t04_rejects_fixed_route_that_violates_hard_precedence():
    package = PackageConfig(
        required_tests=frozenset({"A", "B", "C"}),
        fixed_route=("C", "A", "B"),
        hard_precedence=frozenset({("A", "C")}),
    )

    env = simpy.Environment()
    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }
    event_log = EventLog(run_id="T04-invalid")
    patient = PatientAgent(patient_id="u1", patient_rank=1, package=package)

    assert eligible_stations(package, patient.completed_tests) == frozenset({"A", "B"})

    env.process(patient_process(env, patient, stations, event_log))
    with pytest.raises(ValueError, match=r"Fixed route recommends station 'C'.*not eligible"):
        env.run()

    assert env.now == 0.0
    assert not any(
        record.event_type in {"TRAVEL_START", "QUEUE_ENTRY", "SERVICE_START"}
        for record in event_log.records
    )
    assert patient.completed_tests == set()
    assert patient.location == ENTRY_LOCATION
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    for station in stations.values():
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


def test_t04_allows_alternative_fixed_route_a_c_b():
    package = PackageConfig(
        required_tests=frozenset({"A", "B", "C"}),
        fixed_route=("A", "C", "B"),
        hard_precedence=frozenset({("A", "C")}),
    )

    assert eligible_stations(package, set()) == frozenset({"A", "B"})
    assert "B" in eligible_stations(package, set())
    assert eligible_stations(package, {"A"}) == frozenset({"B", "C"})

    env = simpy.Environment()
    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }
    event_log = EventLog(run_id="T04-valid")
    patient = PatientAgent(patient_id="u1", patient_rank=1, package=package)

    env.process(patient_process(env, patient, stations, event_log))
    env.run()
    records = event_log.records

    def events(event_type: str):
        return [record for record in records if record.event_type == event_type]

    assert [(r.station_id, r.sim_time) for r in events("QUEUE_ENTRY")] == [
        ("A", 0.0),
        ("C", 6.0),
        ("B", 12.0),
    ]
    assert [(r.station_id, r.sim_time) for r in events("SERVICE_START")] == [
        ("A", 0.0),
        ("C", 6.0),
        ("B", 12.0),
    ]
    assert [(r.station_id, r.sim_time) for r in events("SERVICE_END")] == [
        ("A", 4.0),
        ("C", 11.0),
        ("B", 15.0),
    ]

    assert [(r.station_id, r.sim_time) for r in events("TRAVEL_START")] == [
        ("A", 0.0),
        ("C", 4.0),
        ("B", 11.0),
    ]
    assert [(r.station_id, r.sim_time) for r in events("TRAVEL_END")] == [
        ("A", 0.0),
        ("C", 6.0),
        ("B", 12.0),
    ]

    assert [
        (r.recommended_station, r.chosen_station)
        for r in events("ROUTE_DECISION")
    ] == [("A", "A"), ("C", "C"), ("B", "B")]

    departures = events("DEPARTURE")
    assert len(departures) == 1
    assert departures[0].patient_id == "u1"
    assert departures[0].sim_time == 15.0
    assert env.now == 15.0

    assert patient.state == PatientState.FINISHED
    assert patient.location == "B"
    assert patient.completed_tests == {"A", "B", "C"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert set(stations) == {"A", "B", "C"}
    for station in stations.values():
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
