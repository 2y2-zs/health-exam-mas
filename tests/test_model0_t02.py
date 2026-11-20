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


def test_t02_two_p1_patients_compete_for_a():
    env = simpy.Environment()
    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }
    event_log = EventLog(run_id="T02")
    u1 = PatientAgent(patient_id="u1", patient_rank=1, package=P1_CONFIG)
    u2 = PatientAgent(patient_id="u2", patient_rank=2, package=P1_CONFIG)

    env.process(patient_process(env, u1, stations, event_log))
    env.process(patient_process(env, u2, stations, event_log))
    env.run()

    records = event_log.records

    def matching(patient_id: str, event_type: str, station_id: str | None = None):
        return [
            record
            for record in records
            if record.patient_id == patient_id
            and record.event_type == event_type
            and (station_id is None or record.station_id == station_id)
        ]

    def only(patient_id: str, event_type: str, station_id: str | None = None):
        found = matching(patient_id, event_type, station_id)
        assert len(found) == 1, (patient_id, event_type, station_id, found)
        return found[0]

    expected_intervals = {
        ("u1", "A"): (0.0, 4.0),
        ("u1", "B"): (5.0, 8.0),
        ("u2", "A"): (4.0, 8.0),
        ("u2", "B"): (9.0, 12.0),
    }
    for (patient_id, station_id), (start_time, end_time) in expected_intervals.items():
        start = only(patient_id, "SERVICE_START", station_id)
        end = only(patient_id, "SERVICE_END", station_id)
        assert (start.sim_time, end.sim_time) == (start_time, end_time)
        assert start.visit_id == end.visit_id
        assert start.sequence_id < end.sequence_id

    a_entries = [r for r in records if r.event_type == "QUEUE_ENTRY" and r.station_id == "A"]
    assert [(r.patient_id, r.sim_time) for r in a_entries] == [
        ("u1", 0.0),
        ("u2", 0.0),
    ]
    assert only("u1", "SERVICE_START", "A").sequence_id < only(
        "u2", "SERVICE_START", "A"
    ).sequence_id

    expected_queue_times_and_waits = {
        ("u1", "A"): (0.0, 0.0),
        ("u2", "A"): (0.0, 4.0),
        ("u1", "B"): (5.0, 0.0),
        ("u2", "B"): (9.0, 0.0),
    }
    for (patient_id, station_id), (entry_time, wait_time) in expected_queue_times_and_waits.items():
        entry = only(patient_id, "QUEUE_ENTRY", station_id)
        service_start = only(patient_id, "SERVICE_START", station_id)
        assert entry.sim_time == entry_time
        assert service_start.sim_time - entry.sim_time == wait_time
        assert entry.visit_id == service_start.visit_id

    for station_id in ("A", "B"):
        actual_intervals = sorted(
            (
                only(patient_id, "SERVICE_START", station_id).sim_time,
                only(patient_id, "SERVICE_END", station_id).sim_time,
            )
            for patient_id in ("u1", "u2")
        )
        assert all(start < end for start, end in actual_intervals)
        assert actual_intervals[0][1] <= actual_intervals[1][0]

    departures = [r for r in records if r.event_type == "DEPARTURE"]
    assert len(departures) == 2
    assert (only("u1", "DEPARTURE").sim_time, only("u2", "DEPARTURE").sim_time) == (
        8.0,
        12.0,
    )

    assert env.now == 12.0
    for patient in (u1, u2):
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
