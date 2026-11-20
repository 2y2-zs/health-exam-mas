import simpy

from health_exam_mas.model0 import (
    EventLog,
    MODEL0_STATIONS,
    PackageConfig,
    PatientAgent,
    PatientState,
    StationAgent,
    patient_process,
)


def test_t03_three_patients_compete_for_capacity_two_c():
    # Direct C requests keep the upstream B queue out of this capacity test.
    c_only = PackageConfig(
        required_tests=frozenset({"C"}),
        fixed_route=("C",),
        hard_precedence=frozenset(),
    )

    env = simpy.Environment()
    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }
    event_log = EventLog(run_id="T03")
    patients = [
        PatientAgent(patient_id=f"u{i}", patient_rank=i, package=c_only)
        for i in (1, 2, 3)
    ]

    for patient in patients:
        env.process(patient_process(env, patient, stations, event_log))
    env.run()

    records = event_log.records

    def matching(patient_id: str, event_type: str):
        return [
            record
            for record in records
            if record.patient_id == patient_id and record.event_type == event_type
        ]

    def only(patient_id: str, event_type: str):
        found = matching(patient_id, event_type)
        assert len(found) == 1, (patient_id, event_type, found)
        return found[0]

    expected = {
        "u1": (0.0, 0.0, 5.0, 0.0, 5.0),
        "u2": (0.0, 0.0, 5.0, 0.0, 5.0),
        "u3": (0.0, 5.0, 10.0, 5.0, 10.0),
    }
    for patient_id, (queue_time, start_time, end_time, wait, departure_time) in expected.items():
        entry = only(patient_id, "QUEUE_ENTRY")
        start = only(patient_id, "SERVICE_START")
        end = only(patient_id, "SERVICE_END")
        departure = only(patient_id, "DEPARTURE")

        assert entry.station_id == start.station_id == end.station_id == "C"
        assert entry.sim_time == queue_time
        assert (start.sim_time, end.sim_time) == (start_time, end_time)
        assert start.sim_time - entry.sim_time == wait
        assert departure.sim_time == departure_time
        assert entry.visit_id == start.visit_id == end.visit_id
        assert entry.sequence_id < start.sequence_id < end.sequence_id < departure.sequence_id

        route = only(patient_id, "ROUTE_DECISION")
        assert (route.recommended_station, route.chosen_station) == ("C", "C")

    c_entries = [
        record for record in records
        if record.event_type == "QUEUE_ENTRY" and record.station_id == "C"
    ]
    assert [(record.patient_id, record.sim_time) for record in c_entries] == [
        ("u1", 0.0),
        ("u2", 0.0),
        ("u3", 0.0),
    ]

    station_events = {
        "QUEUE_ENTRY", "SERVICE_START", "SERVICE_END", "RESOURCE_RELEASE",
        "TRAVEL_START", "TRAVEL_END",
    }
    assert all(
        record.station_id == "C"
        for record in records
        if record.event_type in station_events
    )

    # For half-open service intervals, subtract completions before adding starts.
    occupancy_changes = sorted(
        (
            record.sim_time,
            0 if record.event_type == "SERVICE_END" else 1,
            -1 if record.event_type == "SERVICE_END" else 1,
        )
        for record in records
        if record.station_id == "C"
        and record.event_type in {"SERVICE_START", "SERVICE_END"}
    )
    assert len(occupancy_changes) == 6
    occupancy = 0
    max_occupancy = 0
    for _, _, delta in occupancy_changes:
        occupancy += delta
        assert 0 <= occupancy <= 2
        max_occupancy = max(max_occupancy, occupancy)
    assert max_occupancy == 2
    assert occupancy == 0

    assert env.now == 10.0
    assert len([record for record in records if record.event_type == "DEPARTURE"]) == 3
    for patient in patients:
        assert patient.state == PatientState.FINISHED
        assert patient.location == "C"
        assert patient.completed_tests == {"C"}
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    assert set(stations) == {"A", "B", "C"}
    for station in stations.values():
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
