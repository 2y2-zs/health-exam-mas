"""T05: travel time and waiting time are distinct in a shared station."""

import simpy

from health_exam_mas.model0 import (
    EventLog,
    MODEL0_STATIONS,
    P1_CONFIG,
    PackageConfig,
    PatientAgent,
    PatientState,
    StationAgent,
    patient_process,
)


def test_t05_travel_time_is_not_queue_waiting_time():
    # Test-only P2 package; the production P1 configuration is unchanged.
    p2_config = PackageConfig(
        required_tests=frozenset({"B", "C"}),
        fixed_route=("B", "C"),
        hard_precedence=frozenset(),
    )

    env = simpy.Environment()
    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }
    event_log = EventLog(run_id="T05")
    u1 = PatientAgent(patient_id="u1", patient_rank=1, package=P1_CONFIG)
    u2 = PatientAgent(patient_id="u2", patient_rank=2, package=p2_config)

    def start_u2_at_four():
        yield env.timeout(4.0)
        yield env.process(patient_process(env, u2, stations, event_log))

    env.process(patient_process(env, u1, stations, event_log))
    env.process(start_u2_at_four())
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

    # Fixed expected timeline, independently calculated from the scenario.
    assert only("u1", "ARRIVAL").sim_time == 0.0
    assert only("u2", "ARRIVAL").sim_time == 4.0

    expected_services = {
        ("u1", "A"): (0.0, 4.0),
        ("u1", "B"): (7.0, 10.0),
        ("u2", "B"): (4.0, 7.0),
        ("u2", "C"): (8.0, 13.0),
    }
    for (patient_id, station_id), expected_interval in expected_services.items():
        start = only(patient_id, "SERVICE_START", station_id)
        end = only(patient_id, "SERVICE_END", station_id)
        assert (start.sim_time, end.sim_time) == expected_interval
        assert start.visit_id == end.visit_id

    # Movement is measured by TRAVEL_START -> TRAVEL_END, not by queue entry.
    expected_travel = {
        ("u1", "A"): (0.0, 0.0),  # ENTRY -> A
        ("u1", "B"): (4.0, 5.0),  # A -> B
        ("u2", "B"): (4.0, 4.0),  # ENTRY -> B
        ("u2", "C"): (7.0, 8.0),  # B -> C
    }
    for (patient_id, station_id), expected_interval in expected_travel.items():
        assert (
            only(patient_id, "TRAVEL_START", station_id).sim_time,
            only(patient_id, "TRAVEL_END", station_id).sim_time,
        ) == expected_interval

    # Queue entry occurs only after travel ends. In particular, u1 does NOT
    # enter the B queue at t=4; u1 enters at t=5 and waits until t=7.
    expected_queues = {
        ("u1", "A"): (0.0, 0.0),
        ("u1", "B"): (5.0, 2.0),
        ("u2", "B"): (4.0, 0.0),
        ("u2", "C"): (8.0, 0.0),
    }
    for (patient_id, station_id), (expected_entry, expected_wait) in expected_queues.items():
        entry = only(patient_id, "QUEUE_ENTRY", station_id)
        service_start = only(patient_id, "SERVICE_START", station_id)
        travel_end = only(patient_id, "TRAVEL_END", station_id)
        assert entry.sim_time == expected_entry
        assert entry.sim_time == travel_end.sim_time
        assert service_start.sim_time - entry.sim_time == expected_wait
        assert entry.visit_id == service_start.visit_id

    assert only("u1", "QUEUE_ENTRY", "B").sim_time == 5.0
    assert only("u1", "SERVICE_START", "B").sim_time == 7.0

    assert only("u1", "DEPARTURE").sim_time == 10.0
    assert only("u2", "DEPARTURE").sim_time == 13.0
    assert len([r for r in records if r.event_type == "DEPARTURE"]) == 2

    # Calculate u1's cycle-time components from the corresponding event pairs;
    # compare each to the hard-coded manual values, not to observed totals.
    u1_stations = ("A", "B")
    service_time = sum(
        only("u1", "SERVICE_END", station).sim_time
        - only("u1", "SERVICE_START", station).sim_time
        for station in u1_stations
    )
    travel_time = sum(
        only("u1", "TRAVEL_END", station).sim_time
        - only("u1", "TRAVEL_START", station).sim_time
        for station in u1_stations
    )
    waiting_time = sum(
        only("u1", "SERVICE_START", station).sim_time
        - only("u1", "QUEUE_ENTRY", station).sim_time
        for station in u1_stations
    )
    cycle_time = (
        only("u1", "DEPARTURE").sim_time
        - only("u1", "ARRIVAL").sim_time
    )

    assert service_time == 7.0
    assert travel_time == 1.0
    assert waiting_time == 2.0
    assert cycle_time == 10.0
    assert cycle_time == service_time + travel_time + waiting_time

    assert env.now == 13.0
    for patient, expected_location, expected_completed in (
        (u1, "B", {"A", "B"}),
        (u2, "C", {"B", "C"}),
    ):
        assert patient.state == PatientState.FINISHED
        assert patient.location == expected_location
        assert patient.completed_tests == expected_completed
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    assert set(stations) == {"A", "B", "C"}
    for station in stations.values():
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
