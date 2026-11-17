
"""Tests for A/B multi-station coordination components and boundaries."""

import pytest
import simpy

from health_exam_mas.model0 import (
    EventLog,
    PackageConfig,
    PatientAgent,
    PatientState,
)

from model0_a_only_prototype import (
    AOnlyCoordinatedStation,
    ScheduledArrival,
)

from model0_ab_coordinator import MultiStationCoordinator


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


@pytest.mark.parametrize(
    "insertion_order",
    [
        ("A", "B"),
        ("B", "A"),
    ],
)
def test_ab_coordinator_registration_has_stable_order(
    insertion_order,
):
    """Both insertion orders produce the same A -> B traversal."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    log = EventLog(run_id="AB_INIT_ORDER")

    source = {
        "A": station_a,
        "B": station_b,
    }

    supplied = {
        station_id: source[station_id]
        for station_id in insertion_order
    }

    coordinator = MultiStationCoordinator(
        env=env,
        stations=supplied,
        event_log=log,
    )

    assert coordinator.env is env
    assert coordinator.event_log is log

    assert coordinator.station_ids == ("A", "B")
    assert list(coordinator.stations) == ["A", "B"]

    assert tuple(coordinator.stations.values()) == (
        station_a,
        station_b,
    )

    assert coordinator.stations["A"] is station_a
    assert coordinator.stations["B"] is station_b

    supplied["A"] = station_b

    assert coordinator.stations["A"] is station_a
    assert list(coordinator.stations) == ["A", "B"]

    assert env.now == 0
    assert log.records == []

    assert not hasattr(coordinator, "run")

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}

        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

        assert station.release_count == 0
        assert station.peak_resource_count == 0


@pytest.mark.parametrize(
    "foreign_station",
    [
        "A",
        "B",
    ],
)
def test_ab_coordinator_rejects_different_environments(
    foreign_station,
):
    """A and B must share the exact Coordinator Environment."""

    env = simpy.Environment()
    other_env = simpy.Environment()

    stations = {
        "A": AOnlyCoordinatedStation(env, station_id="A"),
        "B": AOnlyCoordinatedStation(env, station_id="B"),
    }

    stations[foreign_station] = AOnlyCoordinatedStation(
        other_env,
        station_id=foreign_station,
    )

    log = EventLog(run_id="AB_INIT_DIFFERENT_ENV")

    with pytest.raises(
        ValueError,
        match="Environment",
    ):
        MultiStationCoordinator(
            env=env,
            stations=stations,
            event_log=log,
        )

    assert log.records == []
    assert env.now == 0
    assert other_env.now == 0


@pytest.mark.parametrize(
    "wrong_key",
    [
        "A",
        "B",
    ],
)
def test_ab_coordinator_rejects_station_id_mismatch(
    wrong_key,
):
    """A dictionary key must match its Station's station_id."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    stations = {
        "A": station_a,
        "B": station_b,
    }

    stations[wrong_key] = (
        station_b if wrong_key == "A" else station_a
    )

    log = EventLog(run_id="AB_INIT_KEY_MISMATCH")

    with pytest.raises(
        ValueError,
        match="station_id",
    ):
        MultiStationCoordinator(
            env=env,
            stations=stations,
            event_log=log,
        )

    assert log.records == []
    assert env.now == 0


@pytest.mark.parametrize(
    "keys",
    [
        ("A",),
        ("B",),
        ("A", "B", "C"),
    ],
)
def test_ab_coordinator_rejects_missing_or_extra_stations(
    keys,
):
    """The registry must contain exactly A and B."""

    env = simpy.Environment()

    stations = {
        station_id: AOnlyCoordinatedStation(
            env,
            station_id=station_id,
        )
        for station_id in keys
    }

    log = EventLog(run_id="AB_INIT_KEY_SET")

    with pytest.raises(
        ValueError,
        match="exactly stations A and B",
    ):
        MultiStationCoordinator(
            env=env,
            stations=stations,
            event_log=log,
        )

    assert log.records == []
    assert env.now == 0


def prepare_ab_services_ending_at_t4():
    """Prepare A [0,4) and B [1,4), without a Coordinator run()."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    log = EventLog(run_id="AB_DUE_SERVICES")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    patient_a = PatientAgent(
        patient_id="uA",
        patient_rank=2,
        package=A_ONLY,
    )
    patient_b = PatientAgent(
        patient_id="uB",
        patient_rank=1,
        package=B_ONLY,
    )

    # A service [0,4).
    patient_a.location = "A"
    patient_a.state = PatientState.TRAVELLING

    station_a.enqueue(patient_a, log)
    station_a.start_available(log)

    assert patient_a.state == PatientState.IN_SERVICE
    assert station_a.resource.count == 1

    # B service [1,4).
    env.run(until=1.0)

    assert env.now == 1.0

    patient_b.location = "B"
    patient_b.state = PatientState.TRAVELLING

    station_b.enqueue(patient_b, log)
    station_b.start_available(log)

    assert patient_b.state == PatientState.IN_SERVICE
    assert station_b.resource.count == 1

    assert station_a.config.service_duration == 4.0
    assert station_b.config.service_duration == 3.0

    assert coordinator.station_ids == ("A", "B")
    assert list(coordinator.stations) == ["A", "B"]

    return (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    )


def test_complete_due_services_all_ends_before_any_release():
    """At t=4, both SERVICE_END records precede all releases."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    assert env.now == 1.0

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert patient_a.completed_tests == set()
    assert patient_b.completed_tests == set()

    env.run(until=4.0)

    assert env.now == 4.0

    assert len(station_a.active) == 1
    assert len(station_b.active) == 1

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    released = coordinator.complete_due_services()

    assert len(released) == 2
    assert released[0] is patient_a
    assert released[1] is patient_b

    assert env.now == 4.0

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

    expected_t4 = [
        (0, "uA", "SERVICE_END", "A"),
        (0, "uB", "SERVICE_END", "B"),
        (1, "uA", "RESOURCE_RELEASE", "A"),
        (1, "uB", "RESOURCE_RELEASE", "B"),
    ]

    raw_t4_log = "\n".join(
        f"seq={record.sequence_id} "
        f"time={record.sim_time:g} "
        f"phase={record.phase} "
        f"patient={record.patient_id} "
        f"event={record.event_type} "
        f"station={record.station_id}"
        for record in log.records
        if record.sim_time == 4.0
    )

    assert actual_t4 == expected_t4, (
        f"Expected: {expected_t4!r}\n"
        f"Actual: {actual_t4!r}\n"
        f"Raw t=4 log:\n{raw_t4_log}"
    )

    ends = [
        record
        for record in log.records
        if record.event_type == "SERVICE_END"
    ]
    releases = [
        record
        for record in log.records
        if record.event_type == "RESOURCE_RELEASE"
    ]

    assert len(ends) == 2
    assert len(releases) == 2

    assert (
        max(record.sequence_id for record in ends)
        < min(record.sequence_id for record in releases)
    )

    assert patient_a.state == PatientState.FINISHED
    assert patient_a.location == "A"
    assert patient_a.completed_tests == {"A"}

    assert patient_b.state == PatientState.FINISHED
    assert patient_b.location == "B"
    assert patient_b.completed_tests == {"B"}

    for patient in (patient_a, patient_b):
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    for record in releases:
        assert record.prior_state == PatientState.IN_SERVICE
        assert record.new_state == PatientState.FINISHED
        assert record.phase == 1

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}

        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

        assert station.release_count == 1
        assert station.peak_resource_count == 1

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]

    expected_events = [
        (0.0, 4, "QUEUE_ENTRY", "A"),
        (0.0, 5, "SERVICE_START", "A"),
        (1.0, 4, "QUEUE_ENTRY", "B"),
        (1.0, 5, "SERVICE_START", "B"),
        (4.0, 0, "SERVICE_END", "A"),
        (4.0, 0, "SERVICE_END", "B"),
        (4.0, 1, "RESOURCE_RELEASE", "A"),
        (4.0, 1, "RESOURCE_RELEASE", "B"),
    ]

    actual_events = [
        (
            record.sim_time,
            record.phase,
            record.event_type,
            record.station_id,
        )
        for record in log.records
    ]

    assert actual_events == expected_events

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))

    for earlier, later in zip(log.records, log.records[1:]):
        assert earlier.sim_time <= later.sim_time
        if earlier.sim_time == later.sim_time:
            assert earlier.phase <= later.phase


def test_complete_due_services_without_due_has_no_side_effects():
    """At t=2, neither A [0,4) nor B [1,4) has finished."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    env.run(until=2.0)

    assert env.now == 2.0

    records_before = list(log.records)

    patient_a_before = (
        patient_a.state,
        patient_a.location,
        set(patient_a.completed_tests),
        patient_a.active_visit_id,
        patient_a.active_station_id,
    )
    patient_b_before = (
        patient_b.state,
        patient_b.location,
        set(patient_b.completed_tests),
        patient_b.active_visit_id,
        patient_b.active_station_id,
    )

    active_a_before = dict(station_a.active)
    active_b_before = dict(station_b.active)

    users_a_before = list(station_a.resource.users)
    users_b_before = list(station_b.resource.users)

    counts_before = (
        station_a.release_count,
        station_b.release_count,
        station_a.peak_resource_count,
        station_b.peak_resource_count,
    )

    released = coordinator.complete_due_services()

    assert released == []
    assert env.now == 2.0
    assert log.records == records_before

    assert (
        patient_a.state,
        patient_a.location,
        patient_a.completed_tests,
        patient_a.active_visit_id,
        patient_a.active_station_id,
    ) == patient_a_before

    assert (
        patient_b.state,
        patient_b.location,
        patient_b.completed_tests,
        patient_b.active_visit_id,
        patient_b.active_station_id,
    ) == patient_b_before

    assert station_a.active.keys() == active_a_before.keys()
    assert station_b.active.keys() == active_b_before.keys()

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert station_a.resource.users == users_a_before
    assert station_b.resource.users == users_b_before

    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    assert station_a.waiting == []
    assert station_b.waiting == []

    assert (
        station_a.release_count,
        station_b.release_count,
        station_a.peak_resource_count,
        station_b.peak_resource_count,
    ) == counts_before

    assert coordinator.complete_due_services() == []

    assert env.now == 2.0
    assert log.records == records_before

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1


def test_next_service_completion_time_both_end_at_t4_is_pure():
    """A [0,4) and B [1,4) both produce a next completion time of 4."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    assert env.now == 1.0

    records_before = list(log.records)

    active_a_before = dict(station_a.active)
    active_b_before = dict(station_b.active)

    patient_a_before = (
        patient_a.state,
        patient_a.location,
        set(patient_a.completed_tests),
        patient_a.active_visit_id,
        patient_a.active_station_id,
    )
    patient_b_before = (
        patient_b.state,
        patient_b.location,
        set(patient_b.completed_tests),
        patient_b.active_visit_id,
        patient_b.active_station_id,
    )

    users_a_before = list(station_a.resource.users)
    users_b_before = list(station_b.resource.users)

    assert coordinator.next_service_completion_time() == 4.0
    assert coordinator.next_service_completion_time() == 4.0

    assert env.now == 1.0
    assert log.records == records_before

    assert station_a.active == active_a_before
    assert station_b.active == active_b_before

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit

    assert station_a.resource.users == users_a_before
    assert station_b.resource.users == users_b_before

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert (
        patient_a.state,
        patient_a.location,
        patient_a.completed_tests,
        patient_a.active_visit_id,
        patient_a.active_station_id,
    ) == patient_a_before

    assert (
        patient_b.state,
        patient_b.location,
        patient_b.completed_tests,
        patient_b.active_visit_id,
        patient_b.active_station_id,
    ) == patient_b_before

    env.run(until=4.0)

    assert env.now == 4.0
    assert coordinator.next_service_completion_time() == 4.0

    assert log.records == records_before

    assert station_a.release_count == 0
    assert station_b.release_count == 0

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert patient_a.state == PatientState.IN_SERVICE
    assert patient_b.state == PatientState.IN_SERVICE

    assert patient_a.completed_tests == set()
    assert patient_b.completed_tests == set()


def test_next_service_completion_time_updates_after_a_release():
    """A [0,4), B [2,5): query 4, then 5 after A is released."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    log = EventLog(run_id="AB_STAGGERED_SERVICE_TIMES")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    patient_a = PatientAgent(
        patient_id="uA",
        patient_rank=2,
        package=A_ONLY,
    )
    patient_b = PatientAgent(
        patient_id="uB",
        patient_rank=1,
        package=B_ONLY,
    )

    patient_a.location = "A"
    patient_a.state = PatientState.TRAVELLING

    station_a.enqueue(patient_a, log)
    station_a.start_available(log)

    env.run(until=2.0)

    patient_b.location = "B"
    patient_b.state = PatientState.TRAVELLING

    station_b.enqueue(patient_b, log)
    station_b.start_available(log)

    assert env.now == 2.0
    assert coordinator.next_service_completion_time() == 4.0

    records_before_query = list(log.records)

    assert env.now == 2.0
    assert log.records == records_before_query

    env.run(until=4.0)

    assert coordinator.next_service_completion_time() == 4.0
    assert env.now == 4.0

    released_a = coordinator.complete_due_services()

    assert released_a == [patient_a]
    assert released_a[0] is patient_a

    assert patient_a.state == PatientState.FINISHED
    assert patient_a.completed_tests == {"A"}

    assert station_a.active == {}
    assert station_a.resource.count == 0
    assert station_a.release_count == 1

    assert patient_b.state == PatientState.IN_SERVICE
    assert patient_b.completed_tests == set()

    assert len(station_b.active) == 1
    assert station_b.resource.count == 1
    assert station_b.release_count == 0

    records_before_query = list(log.records)

    assert coordinator.next_service_completion_time() == 5.0
    assert coordinator.next_service_completion_time() == 5.0

    assert env.now == 4.0
    assert log.records == records_before_query
    assert station_b.resource.count == 1

    env.run(until=5.0)

    assert coordinator.next_service_completion_time() == 5.0
    assert env.now == 5.0

    released_b = coordinator.complete_due_services()

    assert released_b == [patient_b]
    assert released_b[0] is patient_b

    assert patient_b.state == PatientState.FINISHED
    assert patient_b.completed_tests == {"B"}

    assert coordinator.next_service_completion_time() is None
    assert env.now == 5.0

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 1

    actual_completions = [
        (
            record.sim_time,
            record.phase,
            record.event_type,
            record.station_id,
        )
        for record in log.records
        if record.event_type in (
            "SERVICE_END",
            "RESOURCE_RELEASE",
        )
    ]

    assert actual_completions == [
        (4.0, 0, "SERVICE_END", "A"),
        (4.0, 1, "RESOURCE_RELEASE", "A"),
        (5.0, 0, "SERVICE_END", "B"),
        (5.0, 1, "RESOURCE_RELEASE", "B"),
    ]

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]


def test_next_service_completion_time_none_when_no_active_visits():
    """None means no active service, even when a station has waiting work."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    log = EventLog(run_id="AB_NO_ACTIVE_SERVICE")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "A": station_a,
            "B": station_b,
        },
        event_log=log,
    )

    assert coordinator.next_service_completion_time() is None

    assert env.now == 0
    assert log.records == []

    patient = PatientAgent(
        patient_id="u1",
        patient_rank=1,
        package=A_ONLY,
    )

    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    station_a.enqueue(patient, log)

    assert patient.state == PatientState.WAITING
    assert len(station_a.waiting) == 1
    assert station_a.active == {}

    assert station_a.resource.count == 0
    assert station_b.active == {}

    records_before = list(log.records)

    assert coordinator.next_service_completion_time() is None
    assert coordinator.next_service_completion_time() is None

    assert env.now == 0
    assert log.records == records_before

    assert len(station_a.waiting) == 1
    assert station_a.waiting[0].patient is patient

    assert patient.state == PatientState.WAITING
    assert patient.location == "A"
    assert patient.completed_tests == set()

    assert station_a.active == {}
    assert station_b.active == {}

    for station in (station_a, station_b):
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0


def test_next_service_completion_time_rejects_overdue_active_visit():
    """An active visit ending before env.now must raise without mutation."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    env.run(until=4.5)

    assert env.now == 4.5

    records_before = list(log.records)

    active_a_before = dict(station_a.active)
    active_b_before = dict(station_b.active)

    users_a_before = list(station_a.resource.users)
    users_b_before = list(station_b.resource.users)

    patient_a_before = (
        patient_a.state,
        patient_a.location,
        set(patient_a.completed_tests),
        patient_a.active_visit_id,
        patient_a.active_station_id,
    )
    patient_b_before = (
        patient_b.state,
        patient_b.location,
        set(patient_b.completed_tests),
        patient_b.active_visit_id,
        patient_b.active_station_id,
    )

    counts_before = (
        station_a.release_count,
        station_b.release_count,
        station_a.peak_resource_count,
        station_b.peak_resource_count,
    )

    with pytest.raises(
        RuntimeError,
        match="Overdue active service completion",
    ):
        coordinator.next_service_completion_time()

    assert env.now == 4.5
    assert log.records == records_before

    assert station_a.active.keys() == active_a_before.keys()
    assert station_b.active.keys() == active_b_before.keys()

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit
        assert visit.ends_at == 4.0

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit
        assert visit.ends_at == 4.0

    assert (
        patient_a.state,
        patient_a.location,
        patient_a.completed_tests,
        patient_a.active_visit_id,
        patient_a.active_station_id,
    ) == patient_a_before

    assert (
        patient_b.state,
        patient_b.location,
        patient_b.completed_tests,
        patient_b.active_visit_id,
        patient_b.active_station_id,
    ) == patient_b_before

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert station_a.resource.users == users_a_before
    assert station_b.resource.users == users_b_before

    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    assert (
        station_a.release_count,
        station_b.release_count,
        station_a.peak_resource_count,
        station_b.peak_resource_count,
    ) == counts_before


def test_process_next_service_completion_same_time_batch():
    """Generator waits until t=4 and commits A/B together."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    assert env.now == 1.0
    assert coordinator.next_service_completion_time() == 4.0

    process = env.process(
        coordinator.process_next_service_completion()
    )

    assert patient_a.state == PatientState.IN_SERVICE
    assert patient_b.state == PatientState.IN_SERVICE

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    env.run()

    assert process.triggered
    assert len(process.value) == 2
    assert process.value[0] is patient_a
    assert process.value[1] is patient_b

    assert env.now == 4.0

    actual_t4 = [
        (
            record.phase,
            record.event_type,
            record.station_id,
        )
        for record in log.records
        if record.sim_time == 4.0
    ]

    assert actual_t4 == [
        (0, "SERVICE_END", "A"),
        (0, "SERVICE_END", "B"),
        (1, "RESOURCE_RELEASE", "A"),
        (1, "RESOURCE_RELEASE", "B"),
    ]

    assert patient_a.state == PatientState.FINISHED
    assert patient_a.completed_tests == {"A"}

    assert patient_b.state == PatientState.FINISHED
    assert patient_b.completed_tests == {"B"}

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 1

    assert coordinator.next_service_completion_time() is None

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))


def test_process_next_service_completion_staggered_batches():
    """A finishes at 4; the next generator call finishes B at 5."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_GENERATOR_STAGGERED")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    patient_a = PatientAgent("uA", 2, A_ONLY)
    patient_b = PatientAgent("uB", 1, B_ONLY)

    patient_a.location = "A"
    patient_a.state = PatientState.TRAVELLING

    station_a.enqueue(patient_a, log)
    station_a.start_available(log)

    env.run(until=2.0)

    patient_b.location = "B"
    patient_b.state = PatientState.TRAVELLING

    station_b.enqueue(patient_b, log)
    station_b.start_available(log)

    assert env.now == 2.0
    assert coordinator.next_service_completion_time() == 4.0

    first = env.process(
        coordinator.process_next_service_completion()
    )

    env.run(until=4.5)

    assert env.now == 4.5
    assert first.triggered
    assert len(first.value) == 1
    assert first.value[0] is patient_a

    assert patient_a.state == PatientState.FINISHED
    assert patient_a.completed_tests == {"A"}

    assert station_a.active == {}
    assert station_a.resource.count == 0
    assert station_a.release_count == 1

    assert patient_b.state == PatientState.IN_SERVICE
    assert patient_b.completed_tests == set()
    assert len(station_b.active) == 1
    assert station_b.resource.count == 1
    assert station_b.release_count == 0

    assert coordinator.next_service_completion_time() == 5.0

    second = env.process(
        coordinator.process_next_service_completion()
    )

    env.run()

    assert env.now == 5.0
    assert second.triggered
    assert len(second.value) == 1
    assert second.value[0] is patient_b

    assert patient_b.state == PatientState.FINISHED
    assert patient_b.completed_tests == {"B"}

    assert coordinator.next_service_completion_time() is None

    actual_completions = [
        (
            record.sim_time,
            record.phase,
            record.event_type,
            record.station_id,
        )
        for record in log.records
        if record.event_type in (
            "SERVICE_END",
            "RESOURCE_RELEASE",
        )
    ]

    assert actual_completions == [
        (4.0, 0, "SERVICE_END", "A"),
        (4.0, 1, "RESOURCE_RELEASE", "A"),
        (5.0, 0, "SERVICE_END", "B"),
        (5.0, 1, "RESOURCE_RELEASE", "B"),
    ]

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 1

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))


def test_process_next_service_completion_due_now():
    """When completion is due at env.now, no timeout is needed."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    env.run(until=4.0)

    assert env.now == 4.0
    assert coordinator.next_service_completion_time() == 4.0

    process = env.process(
        coordinator.process_next_service_completion()
    )

    env.run()

    assert env.now == 4.0
    assert process.triggered

    assert len(process.value) == 2
    assert process.value[0] is patient_a
    assert process.value[1] is patient_b

    assert [
        (
            record.phase,
            record.event_type,
            record.station_id,
        )
        for record in log.records
        if record.sim_time == 4.0
    ] == [
        (0, "SERVICE_END", "A"),
        (0, "SERVICE_END", "B"),
        (1, "RESOURCE_RELEASE", "A"),
        (1, "RESOURCE_RELEASE", "B"),
    ]

    assert station_a.release_count == 1
    assert station_b.release_count == 1

    assert station_a.resource.count == 0
    assert station_b.resource.count == 0

    assert coordinator.next_service_completion_time() is None


def test_process_next_service_completion_without_active_service():
    """No active service returns [] without time advance or queue mutation."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_GENERATOR_NO_ACTIVE")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "A": station_a,
            "B": station_b,
        },
        event_log=log,
    )

    assert coordinator.next_service_completion_time() is None

    first = env.process(
        coordinator.process_next_service_completion()
    )
    env.run()

    assert first.triggered
    assert first.value == []
    assert env.now == 0
    assert log.records == []

    patient = PatientAgent("u1", 1, A_ONLY)
    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    station_a.enqueue(patient, log)

    assert patient.state == PatientState.WAITING
    assert len(station_a.waiting) == 1
    assert station_a.active == {}

    records_before = list(log.records)

    assert coordinator.next_service_completion_time() is None

    second = env.process(
        coordinator.process_next_service_completion()
    )
    env.run()

    assert second.triggered
    assert second.value == []
    assert env.now == 0
    assert log.records == records_before

    assert len(station_a.waiting) == 1
    assert station_a.waiting[0].patient is patient

    assert patient.state == PatientState.WAITING
    assert patient.completed_tests == set()

    assert station_a.active == {}
    assert station_b.active == {}

    for station in (station_a, station_b):
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0


def test_dispatch_available_services_starts_both_idle_stations():
    """Both A and B start their waiting patient immediately at t=0."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    log = EventLog(run_id="AB_DISPATCH_IDLE_STATIONS")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    patient_a = PatientAgent("uA", 2, A_ONLY)
    patient_b = PatientAgent("uB", 1, B_ONLY)

    patient_a.location = "A"
    patient_a.state = PatientState.TRAVELLING

    patient_b.location = "B"
    patient_b.state = PatientState.TRAVELLING

    station_a.enqueue(patient_a, log)
    station_b.enqueue(patient_b, log)

    assert env.now == 0
    assert patient_a.state == PatientState.WAITING
    assert patient_b.state == PatientState.WAITING

    assert len(station_a.waiting) == 1
    assert len(station_b.waiting) == 1

    assert station_a.active == {}
    assert station_b.active == {}

    assert station_a.resource.count == 0
    assert station_b.resource.count == 0

    coordinator.dispatch_available_services()

    assert env.now == 0
    assert patient_a.state == PatientState.IN_SERVICE
    assert patient_b.state == PatientState.IN_SERVICE

    assert station_a.waiting == []
    assert station_b.waiting == []

    assert len(station_a.active) == 1
    assert len(station_b.active) == 1

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert len(station_a.resource.users) == 1
    assert len(station_b.resource.users) == 1

    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    active_a = next(iter(station_a.active.values()))
    active_b = next(iter(station_b.active.values()))

    assert active_a.patient is patient_a
    assert active_b.patient is patient_b

    assert active_a.ends_at == 4.0
    assert active_b.ends_at == 3.0

    assert station_a.peak_resource_count == 1
    assert station_b.peak_resource_count == 1

    assert station_a.release_count == 0
    assert station_b.release_count == 0

    assert [
        (
            record.sim_time,
            record.phase,
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in log.records
    ] == [
        (0.0, 4, "uA", "QUEUE_ENTRY", "A"),
        (0.0, 4, "uB", "QUEUE_ENTRY", "B"),
        (0.0, 5, "uA", "SERVICE_START", "A"),
        (0.0, 5, "uB", "SERVICE_START", "B"),
    ]

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))

    assert not [
        record
        for record in log.records
        if record.event_type in (
            "SERVICE_END",
            "RESOURCE_RELEASE",
            "DEPARTURE",
        )
    ]


def test_dispatch_available_services_when_full_is_idempotent():
    """Repeated Phase 5 dispatch cannot start another visit at capacity."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_DISPATCH_FULL")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "A": station_a,
            "B": station_b,
        },
        event_log=log,
    )

    a1 = PatientAgent("a1", 1, A_ONLY)
    a2 = PatientAgent("a2", 2, A_ONLY)
    b1 = PatientAgent("b1", 1, B_ONLY)
    b2 = PatientAgent("b2", 2, B_ONLY)

    for patient in (a1, a2):
        patient.location = "A"
        patient.state = PatientState.TRAVELLING
        station_a.enqueue(patient, log)

    for patient in (b1, b2):
        patient.location = "B"
        patient.state = PatientState.TRAVELLING
        station_b.enqueue(patient, log)

    assert len(station_a.waiting) == 2
    assert len(station_b.waiting) == 2

    coordinator.dispatch_available_services()

    assert a1.state == PatientState.IN_SERVICE
    assert b1.state == PatientState.IN_SERVICE

    assert a2.state == PatientState.WAITING
    assert b2.state == PatientState.WAITING

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert len(station_a.waiting) == 1
    assert len(station_b.waiting) == 1

    assert station_a.waiting[0].patient is a2
    assert station_b.waiting[0].patient is b2

    assert [
        (record.patient_id, record.station_id)
        for record in log.records
        if record.event_type == "SERVICE_START"
    ] == [
        ("a1", "A"),
        ("b1", "B"),
    ]

    records_before = list(log.records)

    waiting_a_before = list(station_a.waiting)
    waiting_b_before = list(station_b.waiting)

    active_a_before = dict(station_a.active)
    active_b_before = dict(station_b.active)

    users_a_before = list(station_a.resource.users)
    users_b_before = list(station_b.resource.users)

    counts_before = (
        station_a.peak_resource_count,
        station_b.peak_resource_count,
        station_a.release_count,
        station_b.release_count,
    )

    coordinator.dispatch_available_services()

    assert env.now == 0
    assert log.records == records_before

    assert station_a.waiting == waiting_a_before
    assert station_b.waiting == waiting_b_before

    assert station_a.active.keys() == active_a_before.keys()
    assert station_b.active.keys() == active_b_before.keys()

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert station_a.resource.users == users_a_before
    assert station_b.resource.users == users_b_before

    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    assert (
        station_a.peak_resource_count,
        station_b.peak_resource_count,
        station_a.release_count,
        station_b.release_count,
    ) == counts_before

    assert a2.state == PatientState.WAITING
    assert b2.state == PatientState.WAITING

    assert len([
        record
        for record in log.records
        if record.event_type == "SERVICE_START"
    ]) == 2

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))


def test_dispatch_available_services_starts_waiters_at_release_time():
    """Phase 5 can reuse capacity at t=4 after synchronous Phase 0/1."""

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    assert env.now == 1.0

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    env.run(until=2.0)

    waiting_a = PatientAgent("uA2", 3, A_ONLY)
    waiting_b = PatientAgent("uB2", 4, B_ONLY)

    waiting_a.location = "A"
    waiting_a.state = PatientState.TRAVELLING

    waiting_b.location = "B"
    waiting_b.state = PatientState.TRAVELLING

    station_a.enqueue(waiting_a, log)
    station_b.enqueue(waiting_b, log)

    assert env.now == 2.0

    assert waiting_a.state == PatientState.WAITING
    assert waiting_b.state == PatientState.WAITING

    assert len(station_a.waiting) == 1
    assert len(station_b.waiting) == 1

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert len(station_a.active) == 1
    assert len(station_b.active) == 1

    records_before = list(log.records)

    coordinator.dispatch_available_services()

    assert log.records == records_before
    assert waiting_a.state == PatientState.WAITING
    assert waiting_b.state == PatientState.WAITING

    env.run(until=4.0)

    assert env.now == 4.0

    released = coordinator.complete_due_services()

    assert len(released) == 2
    assert released[0] is patient_a
    assert released[1] is patient_b

    assert patient_a.state == PatientState.FINISHED
    assert patient_b.state == PatientState.FINISHED

    assert patient_a.completed_tests == {"A"}
    assert patient_b.completed_tests == {"B"}

    assert station_a.release_count == 1
    assert station_b.release_count == 1

    assert station_a.resource.count == 0
    assert station_b.resource.count == 0

    assert station_a.active == {}
    assert station_b.active == {}

    assert len(station_a.waiting) == 1
    assert len(station_b.waiting) == 1

    assert station_a.waiting[0].patient is waiting_a
    assert station_b.waiting[0].patient is waiting_b

    assert waiting_a.state == PatientState.WAITING
    assert waiting_b.state == PatientState.WAITING

    coordinator.dispatch_available_services()

    assert env.now == 4.0

    assert waiting_a.state == PatientState.IN_SERVICE
    assert waiting_b.state == PatientState.IN_SERVICE

    assert station_a.waiting == []
    assert station_b.waiting == []

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert len(station_a.active) == 1
    assert len(station_b.active) == 1

    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    assert station_a.release_count == 1
    assert station_b.release_count == 1

    active_a = next(iter(station_a.active.values()))
    active_b = next(iter(station_b.active.values()))

    assert active_a.patient is waiting_a
    assert active_b.patient is waiting_b

    assert active_a.ends_at == 8.0
    assert active_b.ends_at == 7.0

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

    expected_t4 = [
        (0, "uA", "SERVICE_END", "A"),
        (0, "uB", "SERVICE_END", "B"),
        (1, "uA", "RESOURCE_RELEASE", "A"),
        (1, "uB", "RESOURCE_RELEASE", "B"),
        (5, "uA2", "SERVICE_START", "A"),
        (5, "uB2", "SERVICE_START", "B"),
    ]

    raw_t4_log = "\n".join(
        f"seq={record.sequence_id} "
        f"t={record.sim_time:g} "
        f"phase={record.phase} "
        f"patient={record.patient_id} "
        f"event={record.event_type} "
        f"station={record.station_id}"
        for record in log.records
        if record.sim_time == 4.0
    )

    assert actual_t4 == expected_t4, (
        f"Expected: {expected_t4!r}\n"
        f"Actual: {actual_t4!r}\n"
        f"Raw t=4 log:\n{raw_t4_log}"
    )

    releases_t4 = [
        record
        for record in log.records
        if record.sim_time == 4.0
        and record.event_type == "RESOURCE_RELEASE"
    ]

    starts_t4 = [
        record
        for record in log.records
        if record.sim_time == 4.0
        and record.event_type == "SERVICE_START"
    ]

    assert len(releases_t4) == 2
    assert len(starts_t4) == 2

    assert (
        max(record.sequence_id for record in releases_t4)
        < min(record.sequence_id for record in starts_t4)
    )

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))

    for earlier, later in zip(log.records, log.records[1:]):
        assert earlier.sim_time <= later.sim_time
        if earlier.sim_time == later.sim_time:
            assert earlier.phase <= later.phase

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]


def test_register_arrival_accepts_now_and_future_without_admission():
    """Registration stores plans only; current-time arrivals are allowed."""

    env = simpy.Environment()
    env.run(until=4.0)

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_REGISTER_ARRIVALS")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={"B": station_b, "A": station_a},
        event_log=log,
    )

    patient_now = PatientAgent("u1", 1, A_ONLY)
    patient_future = PatientAgent("u2", 2, B_ONLY)

    arrival_now = ScheduledArrival(
        at=4.0,
        patient=patient_now,
    )
    arrival_future = ScheduledArrival(
        at=6.0,
        patient=patient_future,
    )

    assert coordinator.pending_arrivals == []

    assert coordinator.register_arrival(arrival_now) is None

    assert len(coordinator.pending_arrivals) == 1
    assert coordinator.pending_arrivals[0] is arrival_now

    assert coordinator.register_arrival(arrival_future) is None

    assert len(coordinator.pending_arrivals) == 2
    assert coordinator.pending_arrivals[0] is arrival_now
    assert coordinator.pending_arrivals[1] is arrival_future

    assert env.now == 4.0

    for patient in (patient_now, patient_future):
        assert patient.state == PatientState.ARRIVED
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    assert log.records == []

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0
        assert station.peak_resource_count == 0

    assert coordinator.next_service_completion_time() is None
    assert len(coordinator.pending_arrivals) == 2


def test_register_arrival_rejects_duplicate_patient_id_without_side_effects():
    """Reject repeated objects and distinct objects sharing an ID."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_DUPLICATE_ARRIVAL")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={"A": station_a, "B": station_b},
        event_log=log,
    )

    original_patient = PatientAgent("u1", 1, A_ONLY)
    other_object_same_id = PatientAgent("u1", 2, B_ONLY)

    first = ScheduledArrival(
        at=2.0,
        patient=original_patient,
    )
    same_object_again = ScheduledArrival(
        at=3.0,
        patient=original_patient,
    )
    different_object_same_id = ScheduledArrival(
        at=4.0,
        patient=other_object_same_id,
    )

    coordinator.register_arrival(first)

    assert coordinator.pending_arrivals == [first]
    assert coordinator.pending_arrivals[0] is first

    original_state = (
        original_patient.state,
        original_patient.location,
        set(original_patient.completed_tests),
        original_patient.active_visit_id,
        original_patient.active_station_id,
    )
    other_state = (
        other_object_same_id.state,
        other_object_same_id.location,
        set(other_object_same_id.completed_tests),
        other_object_same_id.active_visit_id,
        other_object_same_id.active_station_id,
    )

    records_before = list(log.records)
    pending_before = list(coordinator.pending_arrivals)

    with pytest.raises(ValueError, match="Duplicate arrival"):
        coordinator.register_arrival(same_object_again)

    assert coordinator.pending_arrivals == pending_before
    assert coordinator.pending_arrivals[0] is first
    assert log.records == records_before

    with pytest.raises(ValueError, match="Duplicate arrival"):
        coordinator.register_arrival(different_object_same_id)

    assert coordinator.pending_arrivals == pending_before
    assert coordinator.pending_arrivals[0] is first
    assert len(coordinator.pending_arrivals) == 1

    assert env.now == 0
    assert log.records == records_before

    assert (
        original_patient.state,
        original_patient.location,
        original_patient.completed_tests,
        original_patient.active_visit_id,
        original_patient.active_station_id,
    ) == original_state

    assert (
        other_object_same_id.state,
        other_object_same_id.location,
        other_object_same_id.completed_tests,
        other_object_same_id.active_visit_id,
        other_object_same_id.active_station_id,
    ) == other_state

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0


def test_register_arrival_rejects_past_time_without_side_effects():
    """An arrival before env.now is invalid and cannot alter plans."""

    env = simpy.Environment()
    env.run(until=4.0)

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_PAST_ARRIVAL")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={"A": station_a, "B": station_b},
        event_log=log,
    )

    valid_patient = PatientAgent("u1", 1, A_ONLY)
    invalid_patient = PatientAgent("u2", 2, B_ONLY)

    valid_plan = ScheduledArrival(
        at=6.0,
        patient=valid_patient,
    )
    invalid_plan = ScheduledArrival(
        at=3.0,
        patient=invalid_patient,
    )

    coordinator.register_arrival(valid_plan)

    assert coordinator.pending_arrivals == [valid_plan]
    assert coordinator.pending_arrivals[0] is valid_plan

    pending_before = list(coordinator.pending_arrivals)
    records_before = list(log.records)

    valid_state = (
        valid_patient.state,
        valid_patient.location,
        set(valid_patient.completed_tests),
        valid_patient.active_visit_id,
        valid_patient.active_station_id,
    )
    invalid_state = (
        invalid_patient.state,
        invalid_patient.location,
        set(invalid_patient.completed_tests),
        invalid_patient.active_visit_id,
        invalid_patient.active_station_id,
    )

    with pytest.raises(
        ValueError,
        match="Arrival time cannot be in the past",
    ):
        coordinator.register_arrival(invalid_plan)

    assert coordinator.pending_arrivals == pending_before
    assert len(coordinator.pending_arrivals) == 1
    assert coordinator.pending_arrivals[0] is valid_plan

    assert env.now == 4.0
    assert log.records == records_before

    assert (
        valid_patient.state,
        valid_patient.location,
        valid_patient.completed_tests,
        valid_patient.active_visit_id,
        valid_patient.active_station_id,
    ) == valid_state

    assert (
        invalid_patient.state,
        invalid_patient.location,
        invalid_patient.completed_tests,
        invalid_patient.active_visit_id,
        invalid_patient.active_station_id,
    ) == invalid_state

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0
        assert station.peak_resource_count == 0


# ==========================================================
# Phase 2 batch-arrival tests
# ==========================================================


def test_commit_due_arrivals_stable_order_and_future_preservation():
    """Reverse registration must yield rank/ID order at t=4.

    Future plans remain pending. Phase 2 has no routing, travel,
    queue or service side effects.
    """

    env = simpy.Environment()
    env.run(until=4.0)

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_PHASE2_STABLE_ORDER")

    coordinator = MultiStationCoordinator(
        env,
        {"B": station_b, "A": station_a},
        log,
    )

    u2 = PatientAgent("u2", 2, A_ONLY)
    u1 = PatientAgent("u1", 1, B_ONLY)
    u3 = PatientAgent("u3", 3, A_ONLY)

    arrival_u2 = ScheduledArrival(4.0, u2)
    arrival_u1 = ScheduledArrival(4.0, u1)
    arrival_u3 = ScheduledArrival(6.0, u3)

    # Deliberately register the current-time patients in reverse rank order.
    coordinator.register_arrival(arrival_u2)
    coordinator.register_arrival(arrival_u3)
    coordinator.register_arrival(arrival_u1)

    assert coordinator.pending_arrivals == [
        arrival_u2,
        arrival_u3,
        arrival_u1,
    ]
    assert log.records == []

    committed = coordinator.commit_due_arrivals()

    assert len(committed) == 2
    assert committed[0] is u1
    assert committed[1] is u2

    # Only the future plan remains, preserving object identity.
    assert len(coordinator.pending_arrivals) == 1
    assert coordinator.pending_arrivals[0] is arrival_u3

    # Original append order, never sorted for assertion.
    assert [
        (
            record.sim_time,
            record.phase,
            record.patient_id,
            record.event_type,
            record.prior_state,
            record.new_state,
        )
        for record in log.records
    ] == [
        (
            4.0, 2, "u1", "ARRIVAL",
            None, PatientState.ARRIVED,
        ),
        (
            4.0, 2, "u2", "ARRIVAL",
            None, PatientState.ARRIVED,
        ),
    ]

    assert [
        record.sequence_id
        for record in log.records
    ] == [1, 2]

    assert env.now == 4.0

    # Phase 2 does not mutate either patient or admit either to a station.
    for patient in (u1, u2, u3):
        assert patient.state == PatientState.ARRIVED
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0

    # No second admission at the same simulation time.
    records_before = list(log.records)

    assert coordinator.commit_due_arrivals() == []
    assert log.records == records_before
    assert coordinator.pending_arrivals == [arrival_u3]
    assert env.now == 4.0

    # Future work remains, but it has not been admitted.
    assert coordinator.next_service_completion_time() is None


def test_commit_due_arrivals_consumed_id_remains_reserved():
    """An ID remains registered after its arrival plan is consumed."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_PHASE2_PERSISTENT_ID")

    coordinator = MultiStationCoordinator(
        env,
        {"A": station_a, "B": station_b},
        log,
    )

    patient = PatientAgent("u1", 1, A_ONLY)
    arrival = ScheduledArrival(0.0, patient)

    coordinator.register_arrival(arrival)

    assert coordinator.pending_arrivals == [arrival]

    committed = coordinator.commit_due_arrivals()

    assert len(committed) == 1
    assert committed[0] is patient
    assert coordinator.pending_arrivals == []

    assert [
        (record.sim_time, record.phase, record.event_type)
        for record in log.records
    ] == [
        (0.0, 2, "ARRIVAL"),
    ]

    # Calling Phase 2 again cannot duplicate the event.
    before_log = list(log.records)
    assert coordinator.commit_due_arrivals() == []
    assert log.records == before_log

    # A second plan with the SAME patient object is forbidden.
    same_patient_again = ScheduledArrival(1.0, patient)

    with pytest.raises(ValueError, match="Duplicate arrival"):
        coordinator.register_arrival(same_patient_again)

    # A DIFFERENT patient object reusing the same ID is also forbidden.
    replacement = PatientAgent("u1", 99, B_ONLY)
    replacement_plan = ScheduledArrival(1.0, replacement)

    with pytest.raises(ValueError, match="Duplicate arrival"):
        coordinator.register_arrival(replacement_plan)

    assert coordinator.pending_arrivals == []
    assert log.records == before_log
    assert env.now == 0

    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"
    assert patient.completed_tests == set()

    assert replacement.state == PatientState.ARRIVED
    assert replacement.location == "ENTRY"
    assert replacement.completed_tests == set()

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


def test_commit_due_arrivals_rejects_overdue_plan_without_mutation():
    """Overdue work blocks the entire Phase 2 batch, including due-now work."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_PHASE2_OVERDUE")

    coordinator = MultiStationCoordinator(
        env,
        {"A": station_a, "B": station_b},
        log,
    )

    old_patient = PatientAgent("old", 1, A_ONLY)
    now_patient = PatientAgent("now", 2, B_ONLY)
    future_patient = PatientAgent("future", 3, A_ONLY)

    old_plan = ScheduledArrival(1.0, old_patient)
    now_plan = ScheduledArrival(3.0, now_patient)
    future_plan = ScheduledArrival(5.0, future_patient)

    coordinator.register_arrival(old_plan)
    coordinator.register_arrival(now_plan)
    coordinator.register_arrival(future_plan)

    # Advance externally without committing the t=1 plan.
    env.run(until=3.0)

    pending_before = list(coordinator.pending_arrivals)
    records_before = list(log.records)

    with pytest.raises(
        RuntimeError,
        match="Overdue pending arrival",
    ):
        coordinator.commit_due_arrivals()

    assert env.now == 3.0
    assert log.records == records_before

    assert len(coordinator.pending_arrivals) == 3
    assert all(
        actual is expected
        for actual, expected in zip(
            coordinator.pending_arrivals,
            pending_before,
        )
    )

    # Even the patient due at t=3 has not partially arrived.
    for patient in (old_patient, now_patient, future_patient):
        assert patient.state == PatientState.ARRIVED
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


def test_commit_due_arrivals_prevalidates_full_batch():
    """One invalid patient must prevent every ARRIVAL in the batch."""

    env = simpy.Environment()
    env.run(until=4.0)

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_PHASE2_BATCH_VALIDATION")

    coordinator = MultiStationCoordinator(
        env,
        {"A": station_a, "B": station_b},
        log,
    )

    valid_patient = PatientAgent("u1", 1, A_ONLY)
    invalid_patient = PatientAgent("u2", 2, B_ONLY)
    future_patient = PatientAgent("u3", 3, A_ONLY)

    valid_plan = ScheduledArrival(4.0, valid_patient)
    invalid_plan = ScheduledArrival(4.0, invalid_patient)
    future_plan = ScheduledArrival(6.0, future_patient)

    coordinator.register_arrival(valid_plan)
    coordinator.register_arrival(invalid_plan)
    coordinator.register_arrival(future_plan)

    # Deliberately invalidate the SECOND due patient.
    invalid_patient.state = PatientState.DECIDING

    pending_before = list(coordinator.pending_arrivals)
    records_before = list(log.records)

    with pytest.raises(
        ValueError,
        match="must be ARRIVED",
    ):
        coordinator.commit_due_arrivals()

    # No earlier valid patient was partially committed.
    assert env.now == 4.0
    assert log.records == records_before

    assert len(coordinator.pending_arrivals) == 3
    assert all(
        actual is expected
        for actual, expected in zip(
            coordinator.pending_arrivals,
            pending_before,
        )
    )

    assert valid_patient.state == PatientState.ARRIVED
    assert invalid_patient.state == PatientState.DECIDING

    for patient in (valid_patient, invalid_patient, future_patient):
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    # Repair the test fixture; the original batch can now be consumed.
    invalid_patient.state = PatientState.ARRIVED

    committed = coordinator.commit_due_arrivals()

    assert len(committed) == 2
    assert committed[0] is valid_patient
    assert committed[1] is invalid_patient

    assert len(coordinator.pending_arrivals) == 1
    assert coordinator.pending_arrivals[0] is future_plan

    assert [
        (
            record.sim_time,
            record.phase,
            record.patient_id,
            record.event_type,
        )
        for record in log.records
    ] == [
        (4.0, 2, "u1", "ARRIVAL"),
        (4.0, 2, "u2", "ARRIVAL"),
    ]
