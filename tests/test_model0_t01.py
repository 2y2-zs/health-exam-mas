"""T01: one P1 patient completes the fixed A -> B route at t=8."""

import simpy

from health_exam_mas.model0 import (
    EventLog,
    MODEL0_STATIONS,
    P1_CONFIG,
    PatientAgent,
    PatientState,
    StationAgent,
    patient_process,
)


def test_t01_single_p1_patient_finishes_at_8():
    # Build an entirely fresh scenario for this test.
    env = simpy.Environment()
    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }
    patient = PatientAgent(patient_id="P1-001", patient_rank=1, package=P1_CONFIG)
    event_log = EventLog(run_id="T01")

    env.process(patient_process(env, patient, stations, event_log))
    env.run()  # Run until the event queue is empty.

    records = event_log.records

    def events(event_type: str):
        return [record for record in records if record.event_type == event_type]

    # Expected service intervals: A [0, 4), B [5, 8).
    service_starts = events("SERVICE_START")
    service_ends = events("SERVICE_END")
    assert [(e.station_id, e.sim_time) for e in service_starts] == [
        ("A", 0.0),
        ("B", 5.0),
    ]
    assert [(e.station_id, e.sim_time) for e in service_ends] == [
        ("A", 4.0),
        ("B", 8.0),
    ]
    assert [e.visit_id for e in service_starts] == [e.visit_id for e in service_ends]

    # Each queue entry precedes its matching service start with zero waiting.
    queue_entries = events("QUEUE_ENTRY")
    assert [(e.station_id, e.sim_time) for e in queue_entries] == [
        ("A", 0.0),
        ("B", 5.0),
    ]
    assert [e.visit_id for e in queue_entries] == [e.visit_id for e in service_starts]
    assert len({e.visit_id for e in queue_entries}) == 2
    for entry, start in zip(queue_entries, service_starts):
        assert start.sim_time - entry.sim_time == 0.0

    # B0 follows the Fixed Route recommendations exactly: A->A, B->B.
    route_decisions = events("ROUTE_DECISION")
    assert [
        (e.recommended_station, e.chosen_station) for e in route_decisions
    ] == [("A", "A"), ("B", "B")]

    # The patient departs exactly once, after finishing both services.
    arrivals = events("ARRIVAL")
    assert len(arrivals) == 1
    assert (arrivals[0].sim_time, arrivals[0].prior_state, arrivals[0].new_state) == (
        0.0,
        None,
        PatientState.ARRIVED,
    )
    departures = events("DEPARTURE")
    assert len(departures) == 1
    assert departures[0].sim_time == 8.0
    assert departures[0].prior_state == PatientState.FINISHED
    assert departures[0].new_state == PatientState.FINISHED

    # Final patient state and complete resource cleanup.
    assert env.now == 8.0
    assert patient.state == PatientState.FINISHED
    assert patient.location == "B"
    assert patient.completed_tests == {"A", "B"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None
    assert set(stations) == {"A", "B", "C"}
    for station in stations.values():
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    # Audit log: no backwards time and contiguous IDs in actual append order.
    times = [e.sim_time for e in records]
    assert times == sorted(times)
    assert [e.sequence_id for e in records] == list(range(1, len(records) + 1))
