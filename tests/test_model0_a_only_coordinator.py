
"""Verification of single-station coordination and rejection boundaries."""

import simpy
import pytest

from health_exam_mas.model0 import (
    EventLog,
    PackageConfig,
    PatientAgent,
    PatientState,
    P1_CONFIG,
    recommend_fixed_route,
    transition_patient_state,
)

from model0_a_only_prototype import (
    ActiveVisit,
    AOnlyCoordinatedStation,
    AOnlyCoordinator,
    ScheduledArrival,
    ScheduledTravel,
)


A_ONLY = PackageConfig(
    required_tests=frozenset({"A"}),
    fixed_route=("A",),
    hard_precedence=frozenset(),
)

B_ONLY = PackageConfig(
    required_tests=frozenset({"B"}),
    fixed_route=("B",),
    hard_precedence=frozenset(),
)

C_ONLY = PackageConfig(
    required_tests=frozenset({"C"}),
    fixed_route=("C",),
    hard_precedence=frozenset(),
)


EVENT_PHASES = {
    "SERVICE_END": 0,
    "RESOURCE_RELEASE": 1,
    "ARRIVAL": 2,
    "NEEDS_ROUTING": 3,
    "DECIDING": 3,
    "ROUTE_DECISION": 3,
    "TRAVEL_START": 3,
    "TRAVEL_END": 3,
    "DEPARTURE": 3,
    "QUEUE_ENTRY": 4,
    "SERVICE_START": 5,
}


def prepare_b_travel(
    *, patient_id="u1", patient_rank=1, arrivals=(), run_id="B_TRAVEL"
):
    """Prepare t=4 with B and a P1 patient who has completed A."""
    env = simpy.Environment()
    env.run(until=4.0)
    assert env.now == 4.0
    station = AOnlyCoordinatedStation(env, station_id="B")
    log = EventLog(run_id=run_id)
    coordinator = AOnlyCoordinator(env, station, log, arrivals)
    patient = PatientAgent(patient_id, patient_rank, P1_CONFIG)
    patient.location = "A"
    patient.state = PatientState.DECIDING
    patient.completed_tests.add("A")
    return env, station, log, coordinator, patient


def assert_empty_station(station):
    """Check queue/resource cleanup without requiring patient completion."""
    assert station.waiting == []
    assert station.active == {}
    assert station.resource.count == 0
    assert station.resource.users == []
    assert station.resource.queue == []


def patient_snapshot(patient):
    return (
        patient.state,
        patient.location,
        frozenset(patient.completed_tests),
        patient.active_visit_id,
        patient.active_station_id,
    )


def run_scenario(arrivals, station_id="A"):
    """Build one independent single-station simulation."""

    env = simpy.Environment()

    station = AOnlyCoordinatedStation(env, station_id=station_id)

    log = EventLog(run_id="A_ONLY_PROTOTYPE")

    packages = {'A': A_ONLY, 'B': B_ONLY, 'C': C_ONLY}

    patients = {
        patient_id: PatientAgent(
            patient_id=patient_id,
            patient_rank=rank,
            package=packages[station_id],
        )
        for patient_id, rank, _ in arrivals
    }

    scheduled = [
        ScheduledArrival(
            at=time,
            patient=patients[patient_id],
        )
        for patient_id, _, time in arrivals
    ]

    coordinator = AOnlyCoordinator(
        env=env,
        station=station,
        event_log=log,
        arrivals=scheduled,
    )

    env.process(coordinator.run())
    env.run()

    return env, station, log, patients


def only(records, patient_id, event_type):
    """Return exactly one matching event."""

    matching = [
        record
        for record in records
        if record.patient_id == patient_id
        and record.event_type == event_type
    ]

    assert len(matching) == 1, (patient_id, event_type, matching)

    return matching[0]


def assert_phase_contract(records):
    """Validate original append order without sorting."""

    for record in records:
        assert record.event_type in EVENT_PHASES, record
        assert record.phase == EVENT_PHASES[record.event_type], record

    for earlier, later in zip(records, records[1:]):
        assert earlier.sim_time <= later.sim_time

        if earlier.sim_time == later.sim_time:
            assert earlier.phase <= later.phase, (earlier, later)


def assert_travel_and_state_lifecycle(
    records,
    patients,
    station_id="A",
):
    expected_states = [
        PatientState.ARRIVED,
        PatientState.NEEDS_ROUTING,
        PatientState.DECIDING,
        PatientState.TRAVELLING,
        PatientState.WAITING,
        PatientState.IN_SERVICE,
        PatientState.FINISHED,
    ]

    for patient_id in patients:
        arrival = only(records, patient_id, 'ARRIVAL')
        start = only(records, patient_id, 'TRAVEL_START')
        end = only(records, patient_id, 'TRAVEL_END')
        entry = only(records, patient_id, 'QUEUE_ENTRY')
        service = only(records, patient_id, 'SERVICE_START')

        assert start.sim_time == end.sim_time == arrival.sim_time
        assert (start.phase, end.phase) == (3, 3)

        assert start.station_id == station_id
        assert end.station_id == station_id

        assert start.prior_state == PatientState.DECIDING
        assert start.new_state == PatientState.TRAVELLING

        assert end.prior_state == PatientState.TRAVELLING
        assert end.new_state == PatientState.TRAVELLING

        assert (
            start.sequence_id
            < end.sequence_id
            < entry.sequence_id
            < service.sequence_id
        )

        state_changes = [
            record.new_state
            for record in records
            if record.patient_id == patient_id
            and (
                record.prior_state is None
                or record.prior_state != record.new_state
            )
        ]

        assert state_changes == expected_states, (
            patient_id,
            state_changes,
        )


def assert_cleanup(
    env,
    station,
    log,
    patients,
    end_time,
    station_id="A",
):
    assert env.now == end_time

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))

    assert_phase_contract(log.records)

    assert_travel_and_state_lifecycle(
        log.records,
        patients,
        station_id=station_id,
    )

    expected_capacity = {"A": 1, "B": 1, "C": 2}[station_id]

    assert station.resource.capacity == expected_capacity
    assert station.peak_resource_count == expected_capacity
    assert station.release_count == len(patients)

    assert_empty_station(station)

    for patient in patients.values():
        assert patient.state == PatientState.FINISHED
        assert patient.completed_tests == {station_id}
        assert patient.location == station_id

        assert patient.active_visit_id is None
        assert patient.active_station_id is None


def test_a_only_reverse_creation_order_still_uses_rank():
    """Rank wins the same-time tie, independent of input order."""

    env, station, log, patients = run_scenario([
        ('u2', 2, 0.0),
        ('u1', 1, 0.0),
    ])

    records = log.records

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "QUEUE_ENTRY"
    ] == [
        ("u1", 0.0),
        ("u2", 0.0),
    ]

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "SERVICE_START"
    ] == [
        ("u1", 0.0),
        ("u2", 4.0),
    ]

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "SERVICE_END"
    ] == [
        ("u1", 4.0),
        ("u2", 8.0),
    ]

    assert [
        only(
            records,
            patient_id,
            "DEPARTURE",
        ).sim_time
        for patient_id in ("u1", "u2")
    ] == [
        4.0,
        8.0,
    ]

    assert_cleanup(
        env,
        station,
        log,
        patients,
        end_time=8.0,
    )


def test_a_only_completion_release_before_same_time_arrivals():
    """Phase 0/1 must precede arrivals at t=4."""

    env, station, log, patients = run_scenario([
        ("u1", 1, 0.0),
        ("u2", 2, 1.0),
        ("u4", 4, 4.0),
        ("u3", 3, 4.0),
    ])

    records = log.records

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "QUEUE_ENTRY"
    ] == [
        ("u1", 0.0),
        ("u2", 1.0),
        ("u3", 4.0),
        ("u4", 4.0),
    ]

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "SERVICE_START"
    ] == [
        ("u1", 0.0),
        ("u2", 4.0),
        ("u3", 8.0),
        ("u4", 12.0),
    ]

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "SERVICE_END"
    ] == [
        ("u1", 4.0),
        ("u2", 8.0),
        ("u3", 12.0),
        ("u4", 16.0),
    ]

    assert [
        only(
            records,
            patient_id,
            "DEPARTURE",
        ).sim_time
        for patient_id in ("u1", "u2", "u3", "u4")
    ] == [
        4.0,
        8.0,
        12.0,
        16.0,
    ]

    u2_entry = only(records, 'u2', 'QUEUE_ENTRY')
    u2_start = only(records, 'u2', 'SERVICE_START')

    assert u2_start.sim_time - u2_entry.sim_time == 3.0

    # Strict original t=4 ordering.
    expected_t4 = [
        ("u1", "SERVICE_END", "A"),
        ("u1", "RESOURCE_RELEASE", "A"),
        ("u3", "ARRIVAL", None),
        ("u4", "ARRIVAL", None),
        ("u3", "QUEUE_ENTRY", "A"),
        ("u4", "QUEUE_ENTRY", "A"),
        ("u2", "SERVICE_START", "A"),
    ]

    wanted = set(expected_t4)

    actual_t4 = [
        (
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in records
        if record.sim_time == 4.0
        and (
            record.patient_id,
            record.event_type,
            record.station_id,
        ) in wanted
    ]

    raw_t4_log = "\n".join(
        f"seq={record.sequence_id} "
        f"phase={record.phase} "
        f"patient={record.patient_id} "
        f"type={record.event_type} "
        f"station={record.station_id} "
        f"time={record.sim_time:g}"
        for record in records
        if record.sim_time == 4.0
    )

    assert actual_t4 == expected_t4, (
        f"Expected: {expected_t4!r}\n"
        f"Actual: {actual_t4!r}\n"
        f"Raw t=4 log:\n{raw_t4_log}"
    )

    assert_cleanup(
        env,
        station,
        log,
        patients,
        end_time=16.0,
    )


def test_a_only_service_end_release_and_departure_commit_boundaries():
    """Inspect Phase 0, Phase 1 and Phase 3 independently."""

    env = simpy.Environment()
    station = AOnlyCoordinatedStation(env)
    log = EventLog(run_id='A_ONLY_COMMIT_BOUNDARY')

    patient = PatientAgent(
        patient_id='u1',
        patient_rank=1,
        package=A_ONLY,
    )

    # Phase 3 travel was already completed.
    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    station.enqueue(patient, log)
    station.start_available(log)

    visit_id = patient.active_visit_id

    assert visit_id is not None
    assert patient.active_station_id == "A"

    assert station.resource.count == 1
    assert patient.state == PatientState.IN_SERVICE
    assert patient.completed_tests == set()

    env.run(until=4.0)
    assert env.now == 4.0

    # Phase 0: SERVICE_END
    due = station.close_services(log)

    assert len(due) == 1
    assert due[0].patient is patient
    assert due[0].visit_id == visit_id

    service_end = only(log.records, 'u1', 'SERVICE_END')

    assert service_end.phase == 0

    assert patient.completed_tests == set()
    assert patient.state == PatientState.IN_SERVICE
    assert patient.active_visit_id == visit_id
    assert patient.active_station_id == "A"

    assert station.active[visit_id] is due[0]
    assert station.resource.count == 1
    assert len(station.resource.users) == 1
    assert station.release_count == 0

    assert not [
        record
        for record in log.records
        if record.event_type == 'DEPARTURE'
    ]

    # Phase 1: RESOURCE_RELEASE
    released = station.release_services(due, log)

    assert released == [patient]
    assert released[0] is patient

    assert patient.completed_tests == {"A"}
    assert patient.state == PatientState.FINISHED
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert station.active == {}
    assert station.release_count == 1
    assert_empty_station(station)

    release = only(log.records, 'u1', 'RESOURCE_RELEASE')

    assert release.phase == 1
    assert release.prior_state == PatientState.IN_SERVICE
    assert release.new_state == PatientState.FINISHED

    assert not [
        record
        for record in log.records
        if record.event_type == 'DEPARTURE'
    ]

    # Phase 3: DEPARTURE
    coordinator = AOnlyCoordinator(
        env=env,
        station=station,
        event_log=log,
        arrivals=[],
    )
    coordinator.commit_departures(released)

    departures = [
        record
        for record in log.records
        if record.event_type == 'DEPARTURE'
    ]

    assert len(departures) == 1

    departure = departures[0]
    assert departure.patient_id == "u1"
    assert departure.sim_time == 4.0
    assert departure.phase == 3
    assert release.sequence_id < departure.sequence_id

    # Departure must not release Resource again.
    assert station.release_count == 1
    assert station.resource.count == 0

    assert_phase_contract(log.records)


def test_phase3_zero_travel_commits_before_phase4_queue_entry(
    monkeypatch,
):
    """Observe state immediately before Phase 4."""

    observed = []
    original_enqueue = AOnlyCoordinatedStation.enqueue

    def inspect_phase4_entry(
        station,
        patient,
        event_log,
    ):
        assert patient.location == "A"
        assert patient.state == PatientState.TRAVELLING

        assert patient.active_visit_id is None
        assert patient.active_station_id is None

        assert station.resource.count == 0
        assert station.resource.queue == []
        assert station.active == {}

        start = only(
            event_log.records,
            patient.patient_id,
            'TRAVEL_START',
        )
        end = only(
            event_log.records,
            patient.patient_id,
            'TRAVEL_END',
        )

        assert start.sim_time == end.sim_time == station.env.now
        assert start.phase == 3
        assert end.phase == 3
        assert start.sequence_id < end.sequence_id

        assert not [
            record
            for record in event_log.records
            if record.patient_id == patient.patient_id
            and record.event_type == "QUEUE_ENTRY"
        ]

        observed.append((patient.patient_id, station.env.now))

        return original_enqueue(
            station,
            patient,
            event_log,
        )

    monkeypatch.setattr(
        AOnlyCoordinatedStation,
        'enqueue',
        inspect_phase4_entry,
    )

    env, station, log, patients = run_scenario([
        ('u2', 2, 0.0),
        ('u1', 1, 0.0),
    ])

    assert observed == [
        ('u1', 0.0),
        ('u2', 0.0),
    ]

    last_travel_end = max(
        record.sequence_id
        for record in log.records
        if record.event_type == "TRAVEL_END"
        and record.sim_time == 0.0
    )

    first_queue_entry = min(
        record.sequence_id
        for record in log.records
        if record.event_type == "QUEUE_ENTRY"
        and record.sim_time == 0.0
    )

    assert last_travel_end < first_queue_entry

    assert_cleanup(
        env,
        station,
        log,
        patients,
        end_time=8.0,
    )


def test_c_two_services_complete_together_before_any_release_or_next_start():
    """Both C service END events precede all releases at t=5."""

    env, station, log, patients = run_scenario(
        [
            ("u1", 1, 0.0),
            ("u2", 2, 0.0),
            ("u3", 3, 0.0),
        ],
        station_id="C",
    )

    records = log.records

    assert station.station_id == "C"
    assert station.resource.capacity == 2
    assert station.config.service_duration == 5.0

    expected_intervals = {
        'u1': (0.0, 5.0),
        'u2': (0.0, 5.0),
        'u3': (5.0, 10.0),
    }
    expected_waits = {
        'u1': 0.0,
        'u2': 0.0,
        'u3': 5.0,
    }
    expected_departures = {
        'u1': 5.0,
        'u2': 5.0,
        'u3': 10.0,
    }

    for patient_id in ("u1", "u2", "u3"):
        entry = only(records, patient_id, 'QUEUE_ENTRY')
        start = only(records, patient_id, 'SERVICE_START')
        end = only(records, patient_id, 'SERVICE_END')
        departure = only(records, patient_id, 'DEPARTURE')

        assert entry.station_id == "C"
        assert entry.sim_time == 0.0

        assert (
            start.sim_time,
            end.sim_time,
        ) == expected_intervals[patient_id]

        assert (
            start.sim_time - entry.sim_time
        ) == expected_waits[patient_id]

        assert departure.sim_time == expected_departures[patient_id]
        assert entry.visit_id == start.visit_id == end.visit_id

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "QUEUE_ENTRY"
        and record.station_id == "C"
    ] == [
        ("u1", 0.0),
        ("u2", 0.0),
        ("u3", 0.0),
    ]

    assert len([
        record
        for record in records
        if record.event_type == "QUEUE_ENTRY"
        and record.patient_id == "u3"
    ]) == 1

    # Strict raw t=5 log order, without sorting.
    expected_t5 = [
        (0, "u1", "SERVICE_END", "C"),
        (0, "u2", "SERVICE_END", "C"),
        (1, "u1", "RESOURCE_RELEASE", "C"),
        (1, "u2", "RESOURCE_RELEASE", "C"),
        (3, "u1", "DEPARTURE", None),
        (3, "u2", "DEPARTURE", None),
        (5, "u3", "SERVICE_START", "C"),
    ]

    wanted = {
        (patient, event_type, station_id)
        for _, patient, event_type, station_id
        in expected_t5
    }

    actual_t5 = [
        (
            record.phase,
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in records
        if record.sim_time == 5.0
        and (
            record.patient_id,
            record.event_type,
            record.station_id,
        ) in wanted
    ]

    raw_t5_log = "\n".join(
        f"seq={record.sequence_id} "
        f"phase={record.phase} "
        f"patient={record.patient_id} "
        f"event={record.event_type} "
        f"station={record.station_id} "
        f"time={record.sim_time:g}"
        for record in records
        if record.sim_time == 5.0
    )

    assert actual_t5 == expected_t5, (
        f"Expected t=5: {expected_t5!r}\n"
        f"Actual t=5: {actual_t5!r}\n"
        f"Raw t=5 log:\n{raw_t5_log}"
    )

    simultaneous = 0
    maximum = 0

    for record in records:
        if record.station_id != "C":
            continue

        if record.event_type == "SERVICE_START":
            simultaneous += 1
            maximum = max(maximum, simultaneous)
        elif record.event_type == "SERVICE_END":
            simultaneous -= 1

        assert 0 <= simultaneous <= 2

    assert maximum == 2
    assert simultaneous == 0

    assert station.peak_resource_count == 2
    assert station.release_count == 3

    assert_cleanup(
        env,
        station,
        log,
        patients,
        end_time=10.0,
        station_id='C',
    )


def test_register_positive_travel_is_a_plan_only():
    """Register A -> B at t=4 without changing patient state."""

    env, station, log, coordinator, patient = prepare_b_travel(
        run_id='P1_REGISTER_TRAVEL'
    )

    travel = ScheduledTravel(
        patient=patient,
        origin="A",
        destination="B",
        started_at=4.0,
        ends_at=5.0,
    )

    assert coordinator.pending_travels == []

    coordinator.register_travel(travel)

    assert coordinator.pending_travels == [travel]
    assert coordinator.pending_travels[0] is travel

    assert env.now == 4.0
    assert patient.location == "A"
    assert patient.state == PatientState.DECIDING
    assert patient.completed_tests == {"A"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert log.records == []
    assert_empty_station(station)

    assert station.release_count == 0
    assert station.peak_resource_count == 0

    with pytest.raises(
        ValueError,
        match="already has a pending travel",
    ):
        coordinator.register_travel(travel)

    assert coordinator.pending_travels == [travel]
    assert env.now == 4.0

    assert patient.location == "A"
    assert patient.state == PatientState.DECIDING
    assert patient.completed_tests == {"A"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert log.records == []
    assert_empty_station(station)


def test_commit_due_travels_at_boundary_without_queueing():
    """Direct Phase 3 completion test for P1 A -> B travel.

    No Coordinator.run() is started.
    The patient remains TRAVELLING after TRAVEL_END
    until a future Phase 4 QUEUE_ENTRY.
    """

    env, station, log, coordinator, patient = prepare_b_travel(
        run_id='P1_TRAVEL_COMPLETION_BOUNDARY'
    )

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    # t=4: Register A -> B travel [4, 5).
    travel = ScheduledTravel(
        patient=patient,
        origin="A",
        destination="B",
        started_at=4.0,
        ends_at=5.0,
    )

    coordinator.register_travel(travel)

    assert coordinator.pending_travels == [travel]
    assert log.records == []

    transition_patient_state(
        patient=patient,
        event_log=log,
        sim_time=env.now,
        event_type="TRAVEL_START",
        new_state=PatientState.TRAVELLING,
        station_id="B",
        phase=3,
    )

    travel_start = only(log.records, 'u1', 'TRAVEL_START')

    assert travel_start.sim_time == 4.0
    assert travel_start.phase == 3
    assert travel_start.prior_state == PatientState.DECIDING
    assert travel_start.new_state == PatientState.TRAVELLING

    assert patient.location == "A"
    assert patient.completed_tests == {"A"}

    assert not [
        record
        for record in log.records
        if record.event_type == 'TRAVEL_END'
    ]

    # t=4.5: not due.
    env.run(until=4.5)

    assert env.now == 4.5

    before_due = coordinator.commit_due_travels()

    assert before_due == []
    assert coordinator.pending_travels == [travel]

    assert patient.location == "A"
    assert patient.state == PatientState.TRAVELLING
    assert patient.completed_tests == {"A"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert [
        record.event_type
        for record in log.records
    ] == ['TRAVEL_START']

    assert_empty_station(station)

    # t=5: exactly due.
    env.run(until=5.0)

    assert env.now == 5.0

    completed = coordinator.commit_due_travels()

    assert completed == [patient]
    assert coordinator.pending_travels == []

    assert patient.location == "B"
    assert patient.state == PatientState.TRAVELLING
    assert patient.completed_tests == {"A"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    travel_ends = [
        record
        for record in log.records
        if record.event_type == 'TRAVEL_END'
    ]

    assert len(travel_ends) == 1

    travel_end = travel_ends[0]

    assert travel_end.patient_id == "u1"
    assert travel_end.sim_time == 5.0
    assert travel_end.phase == 3
    assert travel_end.station_id == "B"

    assert travel_end.prior_state == PatientState.TRAVELLING
    assert travel_end.new_state == PatientState.TRAVELLING

    assert travel_start.sequence_id < travel_end.sequence_id

    assert [
        record.event_type
        for record in log.records
    ] == [
        'TRAVEL_START',
        'TRAVEL_END',
    ]

    assert_empty_station(station)

    assert station.release_count == 0
    assert station.peak_resource_count == 0

    # t=5: repeated call must not duplicate completion.
    completed_again = coordinator.commit_due_travels()

    assert completed_again == []
    assert coordinator.pending_travels == []

    assert len([
        record
        for record in log.records
        if record.event_type == 'TRAVEL_END'
    ]) == 1

    assert patient.location == "B"
    assert patient.state == PatientState.TRAVELLING
    assert patient.completed_tests == {"A"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert not [
        record
        for record in log.records
        if record.event_type in (
            "QUEUE_ENTRY",
            "SERVICE_START",
            "RESOURCE_RELEASE",
            "DEPARTURE",
        )
    ]

    assert_empty_station(station)
    assert env.now == 5.0
    assert_phase_contract(log.records)


def test_run_consumes_pending_travel_and_finishes_remaining_p1_at_t8():
    """Complete the remaining P1 pathway using only Station B.

    This is not the full coordinated T01.
    """

    env, station, log, coordinator, patient = prepare_b_travel(
        run_id='P1_B_REMAINING_INTEGRATION'
    )

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    # t=4: Register A -> B travel [4, 5).
    travel = ScheduledTravel(
        patient=patient,
        origin="A",
        destination="B",
        started_at=4.0,
        ends_at=5.0,
    )

    coordinator.register_travel(travel)

    transition_patient_state(
        patient=patient,
        event_log=log,
        sim_time=env.now,
        event_type="TRAVEL_START",
        new_state=PatientState.TRAVELLING,
        station_id="B",
        phase=3,
    )

    assert coordinator.pending == []
    assert coordinator.pending_travels == [travel]

    assert patient.location == "A"
    assert patient.state == PatientState.TRAVELLING
    assert patient.completed_tests == {"A"}

    assert [
        record.event_type
        for record in log.records
    ] == ['TRAVEL_START']

    env.process(coordinator.run())

    # t=4.5: Travel in progress.
    env.run(until=4.5)

    assert env.now == 4.5
    assert coordinator.pending_travels == [travel]

    assert patient.location == "A"
    assert patient.state == PatientState.TRAVELLING
    assert patient.completed_tests == {"A"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert_empty_station(station)
    assert station.peak_resource_count == 0
    assert station.release_count == 0

    assert [
        record.event_type
        for record in log.records
    ] == ['TRAVEL_START']

    # Drain t=5 and t=8.
    env.run()

    assert env.now == 8.0

    # Complete raw append order, without sorting.
    actual_events = [
        (
            record.sim_time,
            record.phase,
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in log.records
    ]

    expected_events = [
        (4.0, 3, "u1", "TRAVEL_START", "B"),
        (5.0, 3, "u1", "TRAVEL_END", "B"),
        (5.0, 4, "u1", "QUEUE_ENTRY", "B"),
        (5.0, 5, "u1", "SERVICE_START", "B"),
        (8.0, 0, "u1", "SERVICE_END", "B"),
        (8.0, 1, "u1", "RESOURCE_RELEASE", "B"),
        (8.0, 3, "u1", "DEPARTURE", None),
    ]

    raw_log = "\n".join(
        f"seq={record.sequence_id} "
        f"t={record.sim_time:g} "
        f"phase={record.phase} "
        f"patient={record.patient_id} "
        f"event={record.event_type} "
        f"station={record.station_id}"
        for record in log.records
    )

    assert actual_events == expected_events, (
        f"Expected: {expected_events!r}\n"
        f"Actual: {actual_events!r}\n"
        f"Raw append log:\n{raw_log}"
    )

    for event_type in (
        "TRAVEL_START",
        "TRAVEL_END",
        "QUEUE_ENTRY",
        "SERVICE_START",
        "SERVICE_END",
        "RESOURCE_RELEASE",
        "DEPARTURE",
    ):
        only(log.records, "u1", event_type)

    # No second arrival or routing after travel completion.
    assert not [
        record
        for record in log.records
        if record.event_type in (
            "ARRIVAL",
            "NEEDS_ROUTING",
            "DECIDING",
            "ROUTE_DECISION",
        )
    ]

    travel_end = only(log.records, 'u1', 'TRAVEL_END')
    queue_entry = only(log.records, 'u1', 'QUEUE_ENTRY')
    service_start = only(log.records, 'u1', 'SERVICE_START')
    service_end = only(log.records, 'u1', 'SERVICE_END')
    resource_release = only(log.records, 'u1', 'RESOURCE_RELEASE')
    departure = only(log.records, 'u1', 'DEPARTURE')

    assert (
        travel_end.sequence_id
        < queue_entry.sequence_id
        < service_start.sequence_id
        < service_end.sequence_id
        < resource_release.sequence_id
        < departure.sequence_id
    )

    assert queue_entry.sim_time == 5.0
    assert service_start.sim_time == 5.0
    assert service_end.sim_time == 8.0

    assert (
        service_start.sim_time - queue_entry.sim_time
    ) == 0.0

    assert (
        service_end.sim_time - service_start.sim_time
    ) == 3.0

    assert (
        queue_entry.visit_id
        == service_start.visit_id
        == service_end.visit_id
        == resource_release.visit_id
    )

    state_changes = [
        record.new_state
        for record in log.records
        if (
            record.prior_state is None
            or record.prior_state != record.new_state
        )
    ]

    assert state_changes == [
        PatientState.TRAVELLING,
        PatientState.WAITING,
        PatientState.IN_SERVICE,
        PatientState.FINISHED,
    ]

    assert patient.state == PatientState.FINISHED
    assert patient.location == "B"
    assert patient.completed_tests == {"A", "B"}

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert coordinator.pending == []
    assert coordinator.pending_travels == []

    assert_empty_station(station)

    assert station.station_id == "B"
    assert station.resource.capacity == 1
    assert station.config.service_duration == 3.0

    assert station.peak_resource_count == 1
    assert station.release_count == 1

    assert_phase_contract(log.records)

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))


def test_same_time_mixed_travel_sources_queue_by_rank_at_b():
    """Positive travel and entry travel finish at B at the same t=5.

    u2: P1, already completed A; A -> B travel [4, 5), rank 2.
    u1: B-only, entry arrival at t=5, rank 1.

    Expected:
        u1: B service [5, 8), departure at 8
        u2: B service [8, 11), departure at 11
    """

    u1 = PatientAgent(
        patient_id="u1",
        patient_rank=1,
        package=B_ONLY,
    )

    env, station, log, coordinator, u2 = prepare_b_travel(
        patient_id="u2",
        patient_rank=2,
        arrivals=[ScheduledArrival(at=5.0, patient=u1)],
        run_id="B_MIXED_TRAVEL_SOURCES",
    )

    assert coordinator.pending_travels == []
    assert len(coordinator.pending) == 1

    assert u1.location == "ENTRY"
    assert u1.state == PatientState.ARRIVED
    assert u1.completed_tests == set()

    assert u2.location == "A"
    assert u2.state == PatientState.DECIDING
    assert u2.completed_tests == {"A"}

    # t=4: Register u2 A -> B travel [4, 5).
    travel = ScheduledTravel(
        patient=u2,
        origin="A",
        destination="B",
        started_at=4.0,
        ends_at=5.0,
    )

    coordinator.register_travel(travel)

    assert u2.location == "A"
    assert u2.state == PatientState.DECIDING

    transition_patient_state(
        patient=u2,
        event_log=log,
        sim_time=env.now,
        event_type="TRAVEL_START",
        new_state=PatientState.TRAVELLING,
        station_id="B",
        phase=3,
    )

    assert coordinator.pending_travels == [travel]

    assert u2.location == "A"
    assert u2.state == PatientState.TRAVELLING
    assert u2.completed_tests == {"A"}

    assert u2.active_visit_id is None
    assert u2.active_station_id is None

    assert_empty_station(station)

    assert [
        (
            record.sim_time,
            record.phase,
            record.patient_id,
            record.event_type,
        )
        for record in log.records
    ] == [
        (4.0, 3, "u2", "TRAVEL_START"),
    ]

    env.process(coordinator.run())

    # t=4.5: No B queue entry yet.
    env.run(until=4.5)

    assert env.now == 4.5
    assert coordinator.pending_travels == [travel]
    assert len(coordinator.pending) == 1

    assert u1.location == "ENTRY"
    assert u1.state == PatientState.ARRIVED
    assert u1.completed_tests == set()

    assert u2.location == "A"
    assert u2.state == PatientState.TRAVELLING
    assert u2.completed_tests == {"A"}

    assert_empty_station(station)

    # Drain t=5, t=8 and t=11.
    env.run()

    assert env.now == 11.0

    records = log.records

    # 1. Both TRAVEL_END events before queue entry.
    travel_ends_t5 = [
        record
        for record in records
        if record.sim_time == 5.0
        and record.event_type == "TRAVEL_END"
    ]

    queue_entries_t5 = [
        record
        for record in records
        if record.sim_time == 5.0
        and record.event_type == "QUEUE_ENTRY"
    ]

    assert len(travel_ends_t5) == 2
    assert len(queue_entries_t5) == 2

    assert {
        record.patient_id
        for record in travel_ends_t5
    } == {'u1', 'u2'}

    assert all(
        record.phase == 3
        for record in travel_ends_t5
    )
    assert all(
        record.phase == 4
        for record in queue_entries_t5
    )

    assert (
        max(record.sequence_id for record in travel_ends_t5)
        <
        min(record.sequence_id for record in queue_entries_t5)
    )

    # 2. Strict raw QUEUE_ENTRY order: u1, u2.
    actual_queue_order = [
        (
            record.patient_id,
            record.sim_time,
            record.phase,
            record.station_id,
        )
        for record in records
        if record.event_type == "QUEUE_ENTRY"
    ]

    expected_queue_order = [
        ('u1', 5.0, 4, 'B'),
        ('u2', 5.0, 4, 'B'),
    ]

    assert actual_queue_order == expected_queue_order

    for patient_id in ("u1", "u2"):
        assert len([
            record
            for record in records
            if record.patient_id == patient_id
            and record.event_type == "QUEUE_ENTRY"
        ]) == 1

    # 3. Strict t=5 relevant event order.
    relevant_types = {
        'ARRIVAL',
        'TRAVEL_END',
        'QUEUE_ENTRY',
        'SERVICE_START',
    }

    actual_t5_relevant = [
        (
            record.phase,
            record.patient_id,
            record.event_type,
        )
        for record in records
        if record.sim_time == 5.0
        and record.event_type in relevant_types
    ]

    expected_t5_relevant = [
        (2, "u1", "ARRIVAL"),
        (3, "u2", "TRAVEL_END"),
        (3, "u1", "TRAVEL_END"),
        (4, "u1", "QUEUE_ENTRY"),
        (4, "u2", "QUEUE_ENTRY"),
        (5, "u1", "SERVICE_START"),
    ]

    raw_t5_log = "\n".join(
        f"seq={record.sequence_id} "
        f"t={record.sim_time:g} "
        f"phase={record.phase} "
        f"patient={record.patient_id} "
        f"event={record.event_type} "
        f"station={record.station_id}"
        for record in records
        if record.sim_time == 5.0
    )

    assert actual_t5_relevant == expected_t5_relevant, (
        f"Expected: {expected_t5_relevant!r}\n"
        f"Actual: {actual_t5_relevant!r}\n"
        f"Raw t=5 log:\n{raw_t5_log}"
    )

    # 4. Service intervals, waits and departures.
    expected_intervals = {
        'u1': (5.0, 8.0),
        'u2': (8.0, 11.0),
    }
    expected_waits = {
        'u1': 0.0,
        'u2': 3.0,
    }
    expected_departures = {
        'u1': 8.0,
        'u2': 11.0,
    }

    for patient_id in ("u1", "u2"):
        entry = only(records, patient_id, 'QUEUE_ENTRY')
        service_start = only(records, patient_id, 'SERVICE_START')
        service_end = only(records, patient_id, 'SERVICE_END')
        departure = only(records, patient_id, 'DEPARTURE')

        assert entry.sim_time == 5.0
        assert entry.station_id == "B"

        assert (
            service_start.sim_time,
            service_end.sim_time,
        ) == expected_intervals[patient_id]

        assert (
            service_start.sim_time - entry.sim_time
        ) == expected_waits[patient_id]

        assert (
            departure.sim_time
            == expected_departures[patient_id]
        )

        assert (
            service_end.sim_time - service_start.sim_time
        ) == 3.0

        assert (
            entry.sequence_id
            < service_start.sequence_id
            < service_end.sequence_id
            < departure.sequence_id
        )

        assert (
            entry.visit_id
            == service_start.visit_id
            == service_end.visit_id
        )

    assert [
        (record.patient_id, record.sim_time)
        for record in records
        if record.event_type == "SERVICE_START"
    ] == [
        ("u1", 5.0),
        ("u2", 8.0),
    ]

    # 5. u2 must not repeat ARRIVAL or Routing.
    u2_events = [
        record
        for record in records
        if record.patient_id == 'u2'
    ]

    assert not [
        record
        for record in u2_events
        if record.event_type in (
            "ARRIVAL",
            "NEEDS_ROUTING",
            "DECIDING",
            "ROUTE_DECISION",
        )
    ]

    assert len([
        record
        for record in u2_events
        if record.event_type == 'TRAVEL_START'
    ]) == 1

    u2_travel_start = only(records, 'u2', 'TRAVEL_START')
    u2_travel_end = only(records, 'u2', 'TRAVEL_END')

    assert u2_travel_start.sim_time == 4.0
    assert u2_travel_end.sim_time == 5.0
    assert u2_travel_start.phase == 3
    assert u2_travel_end.phase == 3
    assert u2_travel_start.sequence_id < u2_travel_end.sequence_id

    u1_arrival = only(records, 'u1', 'ARRIVAL')
    u1_travel_start = only(records, 'u1', 'TRAVEL_START')
    u1_travel_end = only(records, 'u1', 'TRAVEL_END')

    assert (
        u1_arrival.sim_time
        == u1_travel_start.sim_time
        == u1_travel_end.sim_time
        == 5.0
    )

    assert (
        u1_arrival.sequence_id
        < u1_travel_start.sequence_id
        < u1_travel_end.sequence_id
    )

    # 6. Final states.
    assert u1.state == PatientState.FINISHED
    assert u1.location == "B"
    assert u1.completed_tests == {"B"}

    assert u2.state == PatientState.FINISHED
    assert u2.location == "B"
    assert u2.completed_tests == {"A", "B"}

    for patient in (u1, u2):
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    expected_u1_states = [
        PatientState.ARRIVED,
        PatientState.NEEDS_ROUTING,
        PatientState.DECIDING,
        PatientState.TRAVELLING,
        PatientState.WAITING,
        PatientState.IN_SERVICE,
        PatientState.FINISHED,
    ]

    expected_u2_states = [
        PatientState.TRAVELLING,
        PatientState.WAITING,
        PatientState.IN_SERVICE,
        PatientState.FINISHED,
    ]

    for patient_id, expected_states in (
        ("u1", expected_u1_states),
        ("u2", expected_u2_states),
    ):
        actual_states = [
            record.new_state
            for record in records
            if record.patient_id == patient_id
            and (
                record.prior_state is None
                or record.prior_state != record.new_state
            )
        ]
        assert actual_states == expected_states, (
            patient_id,
            actual_states,
        )

    # 7. Cleanup.
    assert coordinator.pending == []
    assert coordinator.pending_travels == []

    assert_empty_station(station)

    assert station.station_id == "B"
    assert station.resource.capacity == 1
    assert station.config.service_duration == 3.0
    assert station.peak_resource_count == 1
    assert station.release_count == 2

    # 8. Phase and sequence contracts.
    assert_phase_contract(records)
    assert [
        record.sequence_id
        for record in records
    ] == list(range(1, len(records) + 1))


def test_station_releases_unfinished_p1_after_a_without_departure():
    """A Station must release a P1 patient who still needs B.

    This test directly exercises Station Phase 0 and Phase 1.
    No B Station is constructed and Coordinator.run() is not started.
    """

    env = simpy.Environment()

    # Construct only Station A.
    station = AOnlyCoordinatedStation(env, station_id='A')
    log = EventLog(run_id='P1_A_UNFINISHED_RELEASE')

    patient = PatientAgent(
        patient_id='u1',
        patient_rank=1,
        package=P1_CONFIG,
    )

    # Phase 3 ENTRY -> A travel has already completed.
    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    assert patient.completed_tests == set()
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    # t=0: Phase 4 and Phase 5.
    station.enqueue(patient, log)
    station.start_available(log)

    visit_id = patient.active_visit_id

    assert visit_id is not None
    assert patient.active_station_id == "A"
    assert patient.state == PatientState.IN_SERVICE
    assert patient.location == "A"

    assert station.resource.capacity == 1
    assert station.config.service_duration == 4.0
    assert station.resource.count == 1
    assert len(station.resource.users) == 1
    assert station.release_count == 0

    # Advance to t=4.
    env.run(until=4.0)
    assert env.now == 4.0

    # Phase 0: Record SERVICE_END only.
    due = station.close_services(log)

    assert len(due) == 1
    assert due[0].patient is patient
    assert due[0].visit_id == visit_id

    service_end = only(log.records, 'u1', 'SERVICE_END')

    assert service_end.sim_time == 4.0
    assert service_end.phase == 0
    assert service_end.station_id == "A"

    assert patient.state == PatientState.IN_SERVICE
    assert patient.completed_tests == set()
    assert patient.active_visit_id == visit_id
    assert patient.active_station_id == "A"

    assert station.active[visit_id] is due[0]
    assert station.resource.count == 1
    assert station.release_count == 0

    # Phase 1: Release unfinished P1.
    released = station.release_services(due, log)

    assert len(released) == 1
    assert released[0] is patient

    assert patient.state == PatientState.NEEDS_ROUTING
    assert patient.completed_tests == {"A"}
    assert patient.location == "A"

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert_empty_station(station)
    assert station.release_count == 1
    assert station.peak_resource_count == 1

    release = only(log.records, 'u1', 'RESOURCE_RELEASE')

    assert release.sim_time == 4.0
    assert release.phase == 1
    assert release.station_id == "A"
    assert release.prior_state == PatientState.IN_SERVICE
    assert release.new_state == PatientState.NEEDS_ROUTING
    assert release.visit_id == visit_id
    assert service_end.sequence_id < release.sequence_id

    # No Departure is allowed for an unfinished package.
    assert not [
        record
        for record in log.records
        if record.event_type == 'DEPARTURE'
    ]

    # No B admission or service has taken place.
    assert not [
        record
        for record in log.records
        if record.station_id == "B"
        and record.event_type in (
            "QUEUE_ENTRY",
            "SERVICE_START",
            "SERVICE_END",
            "RESOURCE_RELEASE",
        )
    ]

    recommended = recommend_fixed_route(
        patient.package,
        patient.completed_tests,
    )
    assert recommended == "B"

    assert patient.state == PatientState.NEEDS_ROUTING
    assert patient.location == "A"
    assert patient.completed_tests == {"A"}

    # Coordinator boundary: explicit rejection.
    coordinator = AOnlyCoordinator(
        env=env,
        station=station,
        event_log=log,
        arrivals=[],
    )

    with pytest.raises(
        NotImplementedError,
        match="多站续程尚未接入",
    ):
        coordinator.commit_departures(released)

    assert not [
        record
        for record in log.records
        if record.event_type == 'DEPARTURE'
    ]

    assert patient.state == PatientState.NEEDS_ROUTING
    assert patient.location == "A"
    assert patient.completed_tests == {"A"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert station.release_count == 1
    assert_empty_station(station)

    assert_phase_contract(log.records)
    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))


@pytest.mark.parametrize("arrival_time", [5.0, 6.0])
def test_travel_rejects_a_different_patient_with_an_arrival_id(arrival_time):
    """A pending arrival owns its ID even when its time differs from travel end."""

    entry_patient = PatientAgent("u1", 1, B_ONLY)
    arrival = ScheduledArrival(
        at=arrival_time,
        patient=entry_patient,
    )

    env, station, log, coordinator, traveller = prepare_b_travel(
        arrivals=[arrival],
        run_id="CROSS_SOURCE_PATIENT_ID",
    )

    assert traveller is not entry_patient

    travel = ScheduledTravel(
        traveller,
        "A",
        "B",
        4.0,
        5.0,
    )

    before_entry = patient_snapshot(entry_patient)
    before_traveller = patient_snapshot(traveller)

    with pytest.raises(ValueError, match="Patient ID"):
        coordinator.register_travel(travel)

    assert env.now == 4.0
    assert patient_snapshot(entry_patient) == before_entry
    assert patient_snapshot(traveller) == before_traveller

    assert coordinator.pending == [arrival]
    assert coordinator.pending[0] is arrival
    assert coordinator.pending_travels == []
    assert log.records == []

    assert_empty_station(station)
    assert station.release_count == 0
    assert station.peak_resource_count == 0


@pytest.mark.parametrize("stage", ["after_travel", "after_service"])
def test_patient_id_remains_owned_after_travel_or_service(stage):
    """Consuming a travel plan or completing service must not free its patient ID."""

    env, station, log, coordinator, patient = prepare_b_travel(
        run_id='PERSISTENT_PATIENT_ID'
    )

    travel = ScheduledTravel(
        patient,
        "A",
        "B",
        4.0,
        5.0,
    )
    coordinator.register_travel(travel)

    transition_patient_state(
        patient,
        log,
        env.now,
        "TRAVEL_START",
        PatientState.TRAVELLING,
        station_id="B",
        phase=3,
    )

    env.run(until=5.0)

    completed = coordinator.commit_due_travels()
    assert completed == [patient]
    assert completed[0] is patient
    assert coordinator.pending_travels == []

    if stage == "after_service":
        # B service is [5, 8).
        station.enqueue(patient, log)
        station.start_available(log)

        env.run(until=8.0)

        due = station.close_services(log)
        released = station.release_services(due, log)

        assert released == [patient]
        assert released[0] is patient

        coordinator.commit_departures(released)

        assert patient.state == PatientState.FINISHED
        assert patient.completed_tests == {"A", "B"}
    else:
        assert patient.state == PatientState.TRAVELLING
        assert patient.completed_tests == {"A"}

    assert patient.location == "B"
    assert_empty_station(station)

    replacement = PatientAgent("u1", 2, P1_CONFIG)
    replacement.location = "A"
    replacement.state = PatientState.DECIDING
    replacement.completed_tests.add("A")

    next_travel = ScheduledTravel(
        replacement,
        'A',
        'B',
        env.now,
        env.now + 1.0,
    )

    before_patient = patient_snapshot(patient)
    before_replacement = patient_snapshot(replacement)
    before_log = list(log.records)
    before_counts = (
        station.release_count,
        station.peak_resource_count,
    )
    before_time = env.now

    with pytest.raises(ValueError, match="Patient ID"):
        coordinator.register_travel(next_travel)

    assert env.now == before_time
    assert patient_snapshot(patient) == before_patient
    assert patient_snapshot(replacement) == before_replacement

    assert coordinator.pending == []
    assert coordinator.pending_travels == []
    assert log.records == before_log

    assert (
        station.release_count,
        station.peak_resource_count,
    ) == before_counts

    assert_empty_station(station)
    assert_phase_contract(log.records)


@pytest.mark.parametrize("invalid_batch", ["foreign_visit", "duplicate_visit"])
def test_invalid_release_batch_preserves_all_active_visits(invalid_batch):
    """Reject a bad batch before releasing its valid first visit."""

    env = simpy.Environment()
    station = AOnlyCoordinatedStation(
        env,
        station_id="C",
    )

    log = EventLog(run_id="RELEASE_BATCH_OWNERSHIP")
    patients = [
        PatientAgent(f"u{rank}", rank, C_ONLY)
        for rank in (1, 2)
    ]

    for patient in patients:
        patient.location = "C"
        patient.state = PatientState.TRAVELLING
        station.enqueue(patient, log)

    station.start_available(log)
    env.run(until=5.0)

    due = station.close_services(log)
    assert len(due) == 2

    if invalid_batch == "foreign_visit":
        original = due[1]
        forged = ActiveVisit(
            patient=original.patient,
            visit_id=original.visit_id,
            request=original.request,
            ends_at=original.ends_at,
        )
        assert forged is not original
        invalid = [due[0], forged]
    else:
        invalid = [due[0], due[0]]

    before_active = dict(station.active)
    before_users = list(station.resource.users)
    before_patients = [
        patient_snapshot(patient)
        for patient in patients
    ]
    before_log = list(log.records)
    before_counts = (
        station.release_count,
        station.peak_resource_count,
    )

    with pytest.raises(RuntimeError):
        station.release_services(invalid, log)

    assert env.now == 5.0
    assert station.active.keys() == before_active.keys()

    for visit_id, visit in before_active.items():
        assert station.active[visit_id] is visit
        assert visit.request in station.resource.users
        assert visit.request.triggered

    assert station.resource.users == before_users
    assert station.resource.count == 2
    assert station.resource.queue == []
    assert station.waiting == []

    assert [
        patient_snapshot(patient)
        for patient in patients
    ] == before_patients

    assert (
        station.release_count,
        station.peak_resource_count,
    ) == before_counts

    assert log.records == before_log

    # The original batch remains usable: both C services were [0, 5).
    released = station.release_services(due, log)

    assert len(released) == 2
    assert all(
        actual is expected
        for actual, expected in zip(released, patients)
    )

    assert station.release_count == 2
    assert station.peak_resource_count == 2
    assert_empty_station(station)

    for patient in patients:
        assert patient.state == PatientState.FINISHED
        assert patient.completed_tests == {"C"}
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]
    assert_phase_contract(log.records)


def test_start_next_travel_after_a_release_stops_at_t4():
    """Release P1 at A, then register and start A -> B at t=4 only.

    No Coordinator.run() process is started. The test stops before
    travel completion or B admission.
    """

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    log = EventLog(
        run_id="P1_START_NEXT_TRAVEL_BOUNDARY"
    )

    patient = PatientAgent(
        "u1",
        1,
        P1_CONFIG,
    )

    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    # A service [0, 4).
    station_a.enqueue(patient, log)
    station_a.start_available(log)

    env.run(until=4.0)
    assert env.now == 4.0

    # Phase 0 and Phase 1 at A.
    due = station_a.close_services(log)
    released = station_a.release_services(due, log)

    assert released == [patient]
    assert released[0] is patient
    assert patient.state == PatientState.NEEDS_ROUTING
    assert patient.completed_tests == {"A"}
    assert patient.location == "A"

    assert_empty_station(station_a)
    assert station_a.release_count == 1

    # Coordinator manages B only.
    coordinator_b = AOnlyCoordinator(
        env,
        station_b,
        log,
        arrivals=[],
    )
    assert coordinator_b.pending_travels == []

    # Failed precondition: no plan, state or log mutation.
    patient.active_visit_id = "invalid-active-visit"

    snapshot = patient_snapshot(patient)
    before_log = list(log.records)

    with pytest.raises(ValueError, match="active visit"):
        coordinator_b.start_next_travel(patient)

    assert patient_snapshot(patient) == snapshot
    assert log.records == before_log
    assert coordinator_b.pending_travels == []

    # Restore the deliberately injected invalid value.
    patient.active_visit_id = None

    # Successful Phase 3 movement start at t=4.
    travel = coordinator_b.start_next_travel(patient)

    assert isinstance(travel, ScheduledTravel)
    assert coordinator_b.pending_travels == [travel]
    assert coordinator_b.pending_travels[0] is travel

    assert travel.patient is patient
    assert (travel.origin, travel.destination) == ("A", "B")
    assert (travel.started_at, travel.ends_at) == (4.0, 5.0)

    # Starting travel does not advance time or change location.
    assert env.now == 4.0
    assert patient.state == PatientState.TRAVELLING
    assert patient.location == "A"
    assert patient.completed_tests == {"A"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    # B has no queue entry or resource reservation.
    assert_empty_station(station_b)
    assert station_b.release_count == 0
    assert station_b.peak_resource_count == 0

    # Check exact original append order at t=4 without sorting.
    actual_t4 = [
        (
            record.phase,
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in log.records
        if record.sim_time == 4.0
    ]

    assert actual_t4 == [
        (0, "u1", "SERVICE_END", "A"),
        (1, "u1", "RESOURCE_RELEASE", "A"),
        (3, "u1", "DECIDING", None),
        (3, "u1", "ROUTE_DECISION", None),
        (3, "u1", "TRAVEL_START", "B"),
    ]

    release = only(
        log.records,
        "u1",
        "RESOURCE_RELEASE",
    )
    deciding = only(
        log.records,
        "u1",
        "DECIDING",
    )
    decision = only(
        log.records,
        "u1",
        "ROUTE_DECISION",
    )
    start = only(
        log.records,
        "u1",
        "TRAVEL_START",
    )

    assert release.new_state == PatientState.NEEDS_ROUTING
    assert deciding.prior_state == PatientState.NEEDS_ROUTING
    assert deciding.new_state == PatientState.DECIDING

    assert decision.recommended_station == "B"
    assert decision.chosen_station == "B"

    assert start.prior_state == PatientState.DECIDING
    assert start.new_state == PatientState.TRAVELLING

    assert (
        release.sequence_id
        < deciding.sequence_id
        < decision.sequence_id
        < start.sequence_id
    )

    # Neither Departure nor TRAVEL_END has happened.
    assert not [
        record
        for record in log.records
        if record.event_type in ("DEPARTURE", "TRAVEL_END")
    ]

    # B admission and service must not begin at t=4.
    assert not [
        record
        for record in log.records
        if record.station_id == "B"
        and record.event_type in (
            "QUEUE_ENTRY",
            "SERVICE_START",
            "SERVICE_END",
            "RESOURCE_RELEASE",
        )
    ]

    # Duplicate start: explicitly rejected without side effects.
    snapshot = patient_snapshot(patient)
    before_log = list(log.records)
    before_pending = list(coordinator_b.pending_travels)

    with pytest.raises(ValueError, match="NEEDS_ROUTING"):
        coordinator_b.start_next_travel(patient)

    assert patient_snapshot(patient) == snapshot
    assert log.records == before_log
    assert coordinator_b.pending_travels == before_pending
    assert coordinator_b.pending_travels[0] is travel

    assert len([
        record
        for record in log.records
        if record.event_type == "DECIDING"
    ]) == 1

    assert len([
        record
        for record in log.records
        if record.event_type == "ROUTE_DECISION"
    ]) == 1

    assert len([
        record
        for record in log.records
        if record.event_type == "TRAVEL_START"
    ]) == 1

    assert_empty_station(station_a)
    assert_empty_station(station_b)

    # The test intentionally stops at the t=4 boundary.
    assert env.now == 4.0
    assert_phase_contract(log.records)

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))
