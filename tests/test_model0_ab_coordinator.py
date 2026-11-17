
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
    ScheduledTravel,
)

from model0_ab_coordinator import MultiStationCoordinator, ReadyQueueEntry


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
    """A dictionary key must match the Station's station_id."""

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

    assert len(coordinator.pending_arrivals) == 1
    assert coordinator.pending_arrivals[0] is arrival_u3

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

    records_before = list(log.records)

    assert coordinator.commit_due_arrivals() == []
    assert log.records == records_before
    assert coordinator.pending_arrivals == [arrival_u3]
    assert env.now == 4.0

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

    before_log = list(log.records)
    assert coordinator.commit_due_arrivals() == []
    assert log.records == before_log

    same_patient_again = ScheduledArrival(1.0, patient)

    with pytest.raises(ValueError, match="Duplicate arrival"):
        coordinator.register_arrival(same_patient_again)

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

    invalid_patient.state = PatientState.DECIDING

    pending_before = list(coordinator.pending_arrivals)
    records_before = list(log.records)

    with pytest.raises(
        ValueError,
        match="must be ARRIVED",
    ):
        coordinator.commit_due_arrivals()

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


# ==========================================================
# New next_event_time() tests
# ==========================================================


def test_next_event_time_arrival_precedes_service_completion():
    """Arrival@2 must win over active A service completion@4.

    The query must not commit either event or advance time.
    """

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")
    log = EventLog(run_id="AB_NEXT_EVENT_ARRIVAL_FIRST")

    coordinator = MultiStationCoordinator(
        env,
        {"B": station_b, "A": station_a},
        log,
    )

    service_patient = PatientAgent("service", 2, A_ONLY)
    service_patient.location = "A"
    service_patient.state = PatientState.TRAVELLING

    station_a.enqueue(service_patient, log)
    station_a.start_available(log)

    assert coordinator.next_service_completion_time() == 4.0

    arrival_patient = PatientAgent("arrival", 1, B_ONLY)
    arrival = ScheduledArrival(
        at=2.0,
        patient=arrival_patient,
    )

    coordinator.register_arrival(arrival)

    before_log = list(log.records)
    before_active = dict(station_a.active)
    before_users = list(station_a.resource.users)

    assert coordinator.next_event_time() == 2.0
    assert coordinator.next_event_time() == 2.0

    assert env.now == 0
    assert log.records == before_log

    assert coordinator.pending_arrivals == [arrival]
    assert coordinator.pending_arrivals[0] is arrival

    assert station_a.active.keys() == before_active.keys()

    for visit_id, visit in before_active.items():
        assert station_a.active[visit_id] is visit
        assert visit.ends_at == 4.0

    assert station_a.resource.count == 1
    assert station_a.resource.users == before_users
    assert station_a.release_count == 0

    assert service_patient.state == PatientState.IN_SERVICE
    assert service_patient.completed_tests == set()

    assert arrival_patient.state == PatientState.ARRIVED
    assert arrival_patient.location == "ENTRY"
    assert arrival_patient.completed_tests == set()

    assert station_b.waiting == []
    assert station_b.active == {}
    assert station_b.resource.count == 0

    # Even though the next event is at t=2, querying does not
    # advance the simulation or record ARRIVAL.
    assert not [
        record
        for record in log.records
        if record.event_type == "ARRIVAL"
    ]


def test_next_event_time_tied_arrival_and_service_is_pure():
    """Arrival@4 and both service completions@4 return 4 only."""

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

    arrival_patient = PatientAgent("arrival", 3, A_ONLY)
    arrival = ScheduledArrival(4.0, arrival_patient)

    coordinator.register_arrival(arrival)

    records_before = list(log.records)
    active_a_before = dict(station_a.active)
    active_b_before = dict(station_b.active)

    assert coordinator.next_event_time() == 4.0
    assert coordinator.next_event_time() == 4.0

    assert env.now == 1.0
    assert log.records == records_before
    assert coordinator.pending_arrivals == [arrival]

    # Reaching the due timestamp externally does not cause the
    # pure query to execute Phase 0/1 or Phase 2.
    env.run(until=4.0)

    assert env.now == 4.0
    assert coordinator.next_event_time() == 4.0

    assert log.records == records_before
    assert coordinator.pending_arrivals == [arrival]

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert station_a.release_count == 0
    assert station_b.release_count == 0

    assert patient_a.state == PatientState.IN_SERVICE
    assert patient_b.state == PatientState.IN_SERVICE

    assert arrival_patient.state == PatientState.ARRIVED
    assert arrival_patient.location == "ENTRY"

    # No new Phase 0, Phase 1, Phase 2 or later records.
    assert not [
        record
        for record in log.records
        if record.event_type in (
            "SERVICE_END",
            "RESOURCE_RELEASE",
            "ARRIVAL",
            "DEPARTURE",
        )
    ]


def test_next_event_time_only_future_arrival():
    """With no active service, Arrival@6 is still an event at t=6."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")
    log = EventLog(run_id="AB_NEXT_EVENT_ARRIVAL_ONLY")

    coordinator = MultiStationCoordinator(
        env,
        {"A": station_a, "B": station_b},
        log,
    )

    patient = PatientAgent("u1", 1, A_ONLY)
    arrival = ScheduledArrival(6.0, patient)

    coordinator.register_arrival(arrival)

    assert coordinator.next_service_completion_time() is None

    before_log = list(log.records)

    assert coordinator.next_event_time() == 6.0
    assert coordinator.next_event_time() == 6.0

    assert env.now == 0
    assert log.records == before_log

    assert coordinator.pending_arrivals == [arrival]
    assert coordinator.pending_arrivals[0] is arrival

    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"
    assert patient.completed_tests == set()

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0


def test_next_event_time_rejects_overdue_arrival_without_mutation():
    """An uncommitted Arrival@1 at t=2 must raise, even with due-now work."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")
    log = EventLog(run_id="AB_NEXT_EVENT_OVERDUE_ARRIVAL")

    coordinator = MultiStationCoordinator(
        env,
        {"A": station_a, "B": station_b},
        log,
    )

    old_patient = PatientAgent("old", 1, A_ONLY)
    future_patient = PatientAgent("future", 2, B_ONLY)

    old_plan = ScheduledArrival(1.0, old_patient)
    future_plan = ScheduledArrival(5.0, future_patient)

    coordinator.register_arrival(old_plan)
    coordinator.register_arrival(future_plan)

    env.run(until=2.0)

    assert env.now == 2.0

    pending_before = list(coordinator.pending_arrivals)
    records_before = list(log.records)

    with pytest.raises(
        RuntimeError,
        match="Overdue pending arrival",
    ):
        coordinator.next_event_time()

    assert env.now == 2.0
    assert log.records == records_before

    assert len(coordinator.pending_arrivals) == 2
    assert all(
        actual is expected
        for actual, expected in zip(
            coordinator.pending_arrivals,
            pending_before,
        )
    )

    for patient in (old_patient, future_patient):
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


def test_next_event_time_rejects_overdue_service_without_mutation():
    """An active service ending at t=4 is overdue at t=4.5.

    A valid future arrival must not hide the overdue service.
    """

    (
        env,
        coordinator,
        station_a,
        station_b,
        log,
        patient_a,
        patient_b,
    ) = prepare_ab_services_ending_at_t4()

    future_patient = PatientAgent("future", 3, A_ONLY)
    future_plan = ScheduledArrival(6.0, future_patient)

    coordinator.register_arrival(future_plan)

    # Deliberately skip committing t=4 completions.
    env.run(until=4.5)

    assert env.now == 4.5

    records_before = list(log.records)
    pending_before = list(coordinator.pending_arrivals)

    active_a_before = dict(station_a.active)
    active_b_before = dict(station_b.active)

    users_a_before = list(station_a.resource.users)
    users_b_before = list(station_b.resource.users)

    with pytest.raises(
        RuntimeError,
        match="Overdue active service completion",
    ):
        coordinator.next_event_time()

    assert env.now == 4.5
    assert log.records == records_before

    assert coordinator.pending_arrivals == pending_before
    assert coordinator.pending_arrivals[0] is future_plan

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit
        assert visit.ends_at == 4.0

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit
        assert visit.ends_at == 4.0

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert station_a.resource.users == users_a_before
    assert station_b.resource.users == users_b_before

    assert station_a.release_count == 0
    assert station_b.release_count == 0

    assert patient_a.state == PatientState.IN_SERVICE
    assert patient_b.state == PatientState.IN_SERVICE

    assert patient_a.completed_tests == set()
    assert patient_b.completed_tests == set()

    assert future_patient.state == PatientState.ARRIVED
    assert future_patient.location == "ENTRY"


def test_next_event_time_none_does_not_mean_simulation_drained():
    """No arrival or active service returns None even with a waiting patient."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")
    log = EventLog(run_id="AB_NEXT_EVENT_NO_SCHEDULED_EVENT")

    coordinator = MultiStationCoordinator(
        env,
        {"A": station_a, "B": station_b},
        log,
    )

    # Truly empty scheduling sources.
    assert coordinator.pending_arrivals == []
    assert coordinator.next_service_completion_time() is None
    assert coordinator.next_event_time() is None

    # Populate a waiting queue without starting a service.
    patient = PatientAgent("waiting", 1, A_ONLY)
    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    station_a.enqueue(patient, log)

    assert patient.state == PatientState.WAITING
    assert len(station_a.waiting) == 1
    assert station_a.active == {}

    records_before = list(log.records)
    waiting_before = list(station_a.waiting)

    # This still returns None, because neither of the two
    # currently supported event sources has a scheduled event.
    assert coordinator.next_event_time() is None
    assert coordinator.next_event_time() is None

    assert env.now == 0
    assert log.records == records_before
    assert coordinator.pending_arrivals == []

    assert station_a.waiting == waiting_before
    assert station_a.waiting[0].patient is patient

    assert patient.state == PatientState.WAITING
    assert patient.location == "A"
    assert patient.completed_tests == set()

    for station in (station_a, station_b):
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0

    # A waiting patient still exists: None is NOT a completion signal.

# ==========================================================
# Unified event-bucket generator tests: Phase 0-2 only
# ==========================================================


def test_process_next_event_bucket_arrival_before_service():
    """Arrival@2 precedes A service completion@4.

    The first bucket processes only Phase 2 at t=2.
    The second bucket processes A Phase 0/1 at t=4.
    """

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_BUCKET_ARRIVAL_FIRST")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    service_patient = PatientAgent(
        "service",
        2,
        A_ONLY,
    )
    arrival_patient = PatientAgent(
        "arrival",
        1,
        B_ONLY,
    )

    # Start A's [0,4) service as an existing component fixture.
    service_patient.location = "A"
    service_patient.state = PatientState.TRAVELLING

    station_a.enqueue(service_patient, log)
    station_a.start_available(log)

    assert service_patient.state == PatientState.IN_SERVICE
    assert coordinator.next_service_completion_time() == 4.0

    plan = ScheduledArrival(
        at=2.0,
        patient=arrival_patient,
    )
    coordinator.register_arrival(plan)

    assert coordinator.next_event_time() == 2.0

    # First invocation: only the next event bucket.
    first = env.process(
        coordinator.process_next_event_bucket()
    )

    env.run(until=first)

    assert first.triggered
    assert env.now == 2.0

    released, arrived = first.value

    assert released == []
    assert len(arrived) == 1
    assert arrived[0] is arrival_patient

    # Arrival is committed, but the patient is not yet routed.
    assert coordinator.pending_arrivals == []
    assert arrival_patient.state == PatientState.ARRIVED
    assert arrival_patient.location == "ENTRY"
    assert arrival_patient.completed_tests == set()

    # A's service is still active and ends at t=4.
    assert service_patient.state == PatientState.IN_SERVICE
    assert service_patient.completed_tests == set()

    assert station_a.resource.count == 1
    assert len(station_a.active) == 1
    assert station_a.release_count == 0

    assert station_b.waiting == []
    assert station_b.active == {}
    assert station_b.resource.count == 0

    # The original log must contain no premature service completion.
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
        (0.0, 4, "service", "QUEUE_ENTRY", "A"),
        (0.0, 5, "service", "SERVICE_START", "A"),
        (2.0, 2, "arrival", "ARRIVAL", None),
    ]

    assert coordinator.next_event_time() == 4.0

    # Second invocation: now finish A's service at t=4.
    second = env.process(
        coordinator.process_next_event_bucket()
    )

    env.run(until=second)

    assert second.triggered
    assert env.now == 4.0

    released, arrived = second.value

    assert len(released) == 1
    assert released[0] is service_patient
    assert arrived == []

    assert service_patient.state == PatientState.FINISHED
    assert service_patient.completed_tests == {"A"}

    assert station_a.active == {}
    assert station_a.resource.count == 0
    assert station_a.release_count == 1

    # Exact original append order across both event buckets.
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
        (0.0, 4, "service", "QUEUE_ENTRY", "A"),
        (0.0, 5, "service", "SERVICE_START", "A"),
        (2.0, 2, "arrival", "ARRIVAL", None),
        (4.0, 0, "service", "SERVICE_END", "A"),
        (4.0, 1, "service", "RESOURCE_RELEASE", "A"),
    ]

    assert coordinator.next_event_time() is None

    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]


def test_process_next_event_bucket_same_time_global_phase_order():
    """A/B completions and three arrivals share t=4.

    Expected raw ordering:
        SERVICE_END A
        SERVICE_END B
        RESOURCE_RELEASE A
        RESOURCE_RELEASE B
        ARRIVAL z0
        ARRIVAL z1
        ARRIVAL z2

    Arrival ordering uses rank, then patient_id.
    """

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

    # Two arrivals share rank=1; IDs break the tie.
    z2 = PatientAgent("z2", 2, A_ONLY)
    z1 = PatientAgent("z1", 1, B_ONLY)
    z0 = PatientAgent("z0", 1, A_ONLY)

    future = PatientAgent("future", 3, B_ONLY)

    plan_z2 = ScheduledArrival(4.0, z2)
    plan_z1 = ScheduledArrival(4.0, z1)
    plan_z0 = ScheduledArrival(4.0, z0)
    future_plan = ScheduledArrival(6.0, future)

    # Deliberately use reverse order for the due arrivals.
    coordinator.register_arrival(plan_z2)
    coordinator.register_arrival(future_plan)
    coordinator.register_arrival(plan_z1)
    coordinator.register_arrival(plan_z0)

    assert coordinator.next_event_time() == 4.0

    process = env.process(
        coordinator.process_next_event_bucket()
    )

    env.run(until=process)

    assert process.triggered
    assert env.now == 4.0

    released, arrived = process.value

    # Phase 0/1 releases are returned in A -> B order.
    assert len(released) == 2
    assert released[0] is patient_a
    assert released[1] is patient_b

    # Phase 2 arrivals are returned by rank then ID.
    assert len(arrived) == 3
    assert arrived[0] is z0
    assert arrived[1] is z1
    assert arrived[2] is z2

    # Compare the ENTIRE original EventLog append order.
    # Do not sort the log for this assertion.
    actual_raw = [
        (
            record.sim_time,
            record.phase,
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in log.records
    ]

    expected_raw = [
        (0.0, 4, "uA", "QUEUE_ENTRY", "A"),
        (0.0, 5, "uA", "SERVICE_START", "A"),

        (1.0, 4, "uB", "QUEUE_ENTRY", "B"),
        (1.0, 5, "uB", "SERVICE_START", "B"),

        (4.0, 0, "uA", "SERVICE_END", "A"),
        (4.0, 0, "uB", "SERVICE_END", "B"),

        (4.0, 1, "uA", "RESOURCE_RELEASE", "A"),
        (4.0, 1, "uB", "RESOURCE_RELEASE", "B"),

        (4.0, 2, "z0", "ARRIVAL", None),
        (4.0, 2, "z1", "ARRIVAL", None),
        (4.0, 2, "z2", "ARRIVAL", None),
    ]

    assert actual_raw == expected_raw

    # All service ends precede every release;
    # every release precedes every ARRIVAL.
    t4 = [
        record
        for record in log.records
        if record.sim_time == 4.0
    ]

    assert [record.phase for record in t4] == [
        0, 0, 1, 1, 2, 2, 2,
    ]

    assert [record.event_type for record in t4] == [
        "SERVICE_END",
        "SERVICE_END",
        "RESOURCE_RELEASE",
        "RESOURCE_RELEASE",
        "ARRIVAL",
        "ARRIVAL",
        "ARRIVAL",
    ]

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))

    # Original A and B services are fully released.
    assert patient_a.state == PatientState.FINISHED
    assert patient_a.completed_tests == {"A"}

    assert patient_b.state == PatientState.FINISHED
    assert patient_b.completed_tests == {"B"}

    for station in (station_a, station_b):
        assert station.active == {}
        assert station.waiting == []
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 1

    # The newly arrived patients have not routed or queued.
    for patient in (z0, z1, z2, future):
        assert patient.state == PatientState.ARRIVED
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    # The future arrival is not consumed.
    assert len(coordinator.pending_arrivals) == 1
    assert coordinator.pending_arrivals[0] is future_plan

    assert coordinator.next_event_time() == 6.0

    # Repeating the same bucket would find the future event;
    # there is no duplicate ARRIVAL at t=4.
    assert len([
        record
        for record in log.records
        if record.event_type == "ARRIVAL"
    ]) == 3

    # No Phase 3, 4 or 5 events are generated by the bucket method.
    assert not [
        record
        for record in log.records
        if record.event_type in (
            "ROUTE_DECISION",
            "TRAVEL_START",
            "TRAVEL_END",
            "DEPARTURE",
        )
    ]


def test_process_next_event_bucket_event_due_now():
    """Due-now arrival is committed without moving the clock."""

    env = simpy.Environment()
    env.run(until=4.0)

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_BUCKET_DUE_NOW")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "A": station_a,
            "B": station_b,
        },
        event_log=log,
    )

    patient = PatientAgent("u1", 1, A_ONLY)
    arrival = ScheduledArrival(4.0, patient)

    coordinator.register_arrival(arrival)

    assert env.now == 4.0
    assert coordinator.next_event_time() == 4.0

    process = env.process(
        coordinator.process_next_event_bucket()
    )

    env.run(until=process)

    assert process.triggered
    assert env.now == 4.0

    released, arrived = process.value

    assert released == []
    assert len(arrived) == 1
    assert arrived[0] is patient

    assert coordinator.pending_arrivals == []

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
    ]

    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"
    assert patient.completed_tests == set()

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    # A second invocation has no scheduled event.
    second = env.process(
        coordinator.process_next_event_bucket()
    )

    env.run(until=second)

    assert second.value == ([], [])
    assert env.now == 4.0
    assert len(log.records) == 1


def test_process_next_event_bucket_no_scheduled_event():
    """No event returns two empty lists, even with waiting work."""

    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_BUCKET_NO_EVENT")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "A": station_a,
            "B": station_b,
        },
        event_log=log,
    )

    assert coordinator.next_event_time() is None

    # A patient can remain waiting even when there is no scheduled
    # arrival or active service completion.
    patient = PatientAgent("waiting", 1, A_ONLY)

    patient.location = "A"
    patient.state = PatientState.TRAVELLING

    station_a.enqueue(patient, log)

    assert patient.state == PatientState.WAITING
    assert len(station_a.waiting) == 1
    assert station_a.active == {}

    assert coordinator.next_event_time() is None

    records_before = list(log.records)
    waiting_before = list(station_a.waiting)

    process = env.process(
        coordinator.process_next_event_bucket()
    )

    env.run(until=process)

    assert process.triggered
    assert process.value == ([], [])
    assert env.now == 0

    # No event or patient state was changed.
    assert log.records == records_before
    assert coordinator.pending_arrivals == []

    assert station_a.waiting == waiting_before
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

    # The absence of scheduled events is not proof that the
    # domain has no remaining work.

# ==========================================================
# Phase 3: ENTRY -> first station, zero-time travel
# ==========================================================

from health_exam_mas.model0 import P1_CONFIG


def _make_ab_phase3_fixture():
    env = simpy.Environment()

    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")

    log = EventLog(run_id="AB_PHASE3_ENTRY")

    coordinator = MultiStationCoordinator(
        env=env,
        stations={"B": station_b, "A": station_a},
        event_log=log,
    )

    return env, coordinator, station_a, station_b, log


def test_route_entry_arrivals_p1_reaches_a_without_queue_or_resource():
    """P1 arrives at t=0, then moves ENTRY -> A in Phase 3."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )

    patient = PatientAgent("u1", 1, P1_CONFIG)

    coordinator.register_arrival(
        ScheduledArrival(at=0.0, patient=patient)
    )

    # Phase 2: the ARRIVAL must actually be committed first.
    arrived = coordinator.commit_due_arrivals()

    assert len(arrived) == 1
    assert arrived[0] is patient

    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"

    assert [
        (r.phase, r.event_type)
        for r in log.records
    ] == [
        (2, "ARRIVAL"),
    ]

    # Phase 3: a separate synchronous call.
    ready = coordinator.route_entry_arrivals(arrived)

    assert len(ready) == 1
    assert ready[0] is patient

    assert env.now == 0.0

    assert patient.state == PatientState.TRAVELLING
    assert patient.location == "A"
    assert patient.completed_tests == set()

    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    # Verify the exact state-transition contract.
    assert [
        (
            r.phase,
            r.event_type,
            r.prior_state,
            r.new_state,
            r.station_id,
        )
        for r in log.records
    ] == [
        (2, "ARRIVAL", None, PatientState.ARRIVED, None),
        (
            3, "NEEDS_ROUTING",
            PatientState.ARRIVED,
            PatientState.NEEDS_ROUTING,
            None,
        ),
        (
            3, "DECIDING",
            PatientState.NEEDS_ROUTING,
            PatientState.DECIDING,
            None,
        ),
        (
            3, "ROUTE_DECISION",
            PatientState.DECIDING,
            PatientState.DECIDING,
            None,
        ),
        (
            3, "TRAVEL_START",
            PatientState.DECIDING,
            PatientState.TRAVELLING,
            "A",
        ),
        (
            3, "TRAVEL_END",
            PatientState.TRAVELLING,
            PatientState.TRAVELLING,
            "A",
        ),
    ]

    decision = next(
        r for r in log.records
        if r.event_type == "ROUTE_DECISION"
    )
    assert decision.recommended_station == "A"
    assert decision.chosen_station == "A"

    assert all(r.sim_time == 0.0 for r in log.records)

    assert [
        r.sequence_id for r in log.records
    ] == list(range(1, len(log.records) + 1))

    # ENTRY travel does not perform Phase 4 or Phase 5.
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0
        assert station.peak_resource_count == 0

    assert not [
        r for r in log.records
        if r.event_type in ("QUEUE_ENTRY", "SERVICE_START")
    ]


def test_route_entry_arrivals_stable_order_with_reverse_input():
    """Phase 3 sorts by rank and ID, regardless of input order.

    All TRAVEL_START records precede all zero-time TRAVEL_END records.
    """

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )

    u3 = PatientAgent("u3", 2, P1_CONFIG)
    u2 = PatientAgent("u2", 1, B_ONLY)
    u1 = PatientAgent("u1", 1, P1_CONFIG)

    # Reverse registration order.
    for patient in (u3, u2, u1):
        coordinator.register_arrival(
            ScheduledArrival(0.0, patient)
        )

    arrived = coordinator.commit_due_arrivals()

    assert arrived == [u1, u2, u3]

    # Deliberately reverse the list again before Phase 3.
    ready = coordinator.route_entry_arrivals(
        list(reversed(arrived))
    )

    assert ready == [u1, u2, u3]
    assert env.now == 0.0

    assert [
        (r.phase, r.patient_id, r.event_type)
        for r in log.records
    ] == [
        (2, "u1", "ARRIVAL"),
        (2, "u2", "ARRIVAL"),
        (2, "u3", "ARRIVAL"),

        (3, "u1", "NEEDS_ROUTING"),
        (3, "u1", "DECIDING"),
        (3, "u1", "ROUTE_DECISION"),
        (3, "u1", "TRAVEL_START"),

        (3, "u2", "NEEDS_ROUTING"),
        (3, "u2", "DECIDING"),
        (3, "u2", "ROUTE_DECISION"),
        (3, "u2", "TRAVEL_START"),

        (3, "u3", "NEEDS_ROUTING"),
        (3, "u3", "DECIDING"),
        (3, "u3", "ROUTE_DECISION"),
        (3, "u3", "TRAVEL_START"),

        (3, "u1", "TRAVEL_END"),
        (3, "u2", "TRAVEL_END"),
        (3, "u3", "TRAVEL_END"),
    ]

    expected_destinations = {
        "u1": "A",
        "u2": "B",
        "u3": "A",
    }

    for r in log.records:
        if r.event_type == "ROUTE_DECISION":
            expected = expected_destinations[r.patient_id]
            assert r.recommended_station == expected
            assert r.chosen_station == expected

        if r.event_type in ("TRAVEL_START", "TRAVEL_END"):
            assert r.station_id == expected_destinations[r.patient_id]

    assert u1.location == "A"
    assert u2.location == "B"
    assert u3.location == "A"

    for patient in (u1, u2, u3):
        assert patient.state == PatientState.TRAVELLING
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    assert [
        r.sequence_id for r in log.records
    ] == list(range(1, len(log.records) + 1))


@pytest.mark.parametrize(
    "failure",
    [
        "unmanaged_destination",
        "duplicate_same_object",
        "duplicate_id_different_object",
    ],
)
def test_route_entry_arrivals_rejects_invalid_batch_atomically(
    failure,
):
    """An invalid later item cannot partially route an earlier patient."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )

    valid = PatientAgent("u1", 1, P1_CONFIG)

    if failure == "unmanaged_destination":
        # C is eligible for this package, but not managed by A/B.
        c_only = PackageConfig(
            required_tests=frozenset({"C"}),
            fixed_route=("C",),
            hard_precedence=frozenset(),
        )
        second = PatientAgent("u2", 2, c_only)
    else:
        second = PatientAgent("u2", 2, B_ONLY)

    for patient in (valid, second):
        coordinator.register_arrival(
            ScheduledArrival(0.0, patient)
        )

    arrived = coordinator.commit_due_arrivals()

    if failure == "unmanaged_destination":
        batch = [valid, second]
        error_message = "not managed"
    elif failure == "duplicate_same_object":
        batch = [valid, second, valid]
        error_message = "Duplicate patient ID"
    else:
        duplicate = PatientAgent("u1", 3, P1_CONFIG)
        batch = [valid, second, duplicate]
        error_message = "Duplicate patient ID"

    log_before = list(log.records)
    pending_before = list(coordinator.pending_arrivals)

    patient_before = [
        (
            p,
            p.state,
            p.location,
            set(p.completed_tests),
            p.active_visit_id,
            p.active_station_id,
        )
        for p in (valid, second)
    ]

    routed_ids_before = set(coordinator._entry_routed_ids)

    with pytest.raises(ValueError, match=error_message):
        coordinator.route_entry_arrivals(batch)

    # No Phase 3 event was appended for ANY patient.
    assert log.records == log_before
    assert all(r.phase == 2 for r in log.records)

    assert coordinator.pending_arrivals == pending_before
    assert coordinator._entry_routed_ids == routed_ids_before

    assert env.now == 0.0

    for (
        patient,
        state,
        location,
        completed,
        visit_id,
        station_id,
    ) in patient_before:
        assert patient.state == state
        assert patient.location == location
        assert patient.completed_tests == completed
        assert patient.active_visit_id == visit_id
        assert patient.active_station_id == station_id

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    # The original Phase 2 result is still usable after an error.
    assert arrived == [valid, second]


def test_route_entry_arrivals_cannot_move_patient_twice():
    """A completed ENTRY move cannot be committed again."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )

    patient = PatientAgent("u1", 1, P1_CONFIG)

    coordinator.register_arrival(
        ScheduledArrival(0.0, patient)
    )

    arrived = coordinator.commit_due_arrivals()
    assert coordinator.route_entry_arrivals(arrived) == [patient]

    assert patient.location == "A"
    assert patient.state == PatientState.TRAVELLING

    log_before = list(log.records)
    state_before = patient.state
    location_before = patient.location

    with pytest.raises(
        ValueError,
        match="Entry travel already committed",
    ):
        coordinator.route_entry_arrivals([patient])

    assert log.records == log_before
    assert patient.state == state_before
    assert patient.location == location_before

    assert coordinator._entry_routed_ids == {"u1"}
    assert env.now == 0.0

    assert sum(
        r.event_type == "TRAVEL_START"
        for r in log.records
    ) == 1

    assert sum(
        r.event_type == "TRAVEL_END"
        for r in log.records
    ) == 1

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.queue == []


def test_route_entry_arrivals_requires_actual_phase2_admission():
    """Registration alone is insufficient; a cloned ID is insufficient."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )

    patient = PatientAgent("u1", 1, P1_CONFIG)

    coordinator.register_arrival(
        ScheduledArrival(0.0, patient)
    )

    # A registered but not yet admitted patient cannot move.
    with pytest.raises(
        ValueError,
        match="has not been admitted",
    ):
        coordinator.route_entry_arrivals([patient])

    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"
    assert log.records == []

    arrived = coordinator.commit_due_arrivals()

    # Even after admission, a different object with the same ID
    # cannot impersonate the actual Phase 2 patient.
    impostor = PatientAgent("u1", 1, P1_CONFIG)

    log_before = list(log.records)

    with pytest.raises(
        ValueError,
        match="has not been admitted",
    ):
        coordinator.route_entry_arrivals([impostor])

    assert log.records == log_before
    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"

    # The true admitted patient can still route successfully.
    assert coordinator.route_entry_arrivals(arrived) == [patient]

    assert patient.state == PatientState.TRAVELLING
    assert patient.location == "A"
    assert impostor.state == PatientState.ARRIVED
    assert impostor.location == "ENTRY"

    assert env.now == 0.0

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


# ==========================================================
# Phase 4: unified deterministic QUEUE_ENTRY
# ==========================================================


def test_commit_queue_entries_mixed_stations_stable_order():
    """Station order A->B and rank/ID; no resource acquisition."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )
    env.run(until=4.0)

    a2 = PatientAgent("a2", 2, P1_CONFIG)
    b1 = PatientAgent("b1", 1, B_ONLY)
    a1 = PatientAgent("a1", 1, P1_CONFIG)
    a0 = PatientAgent("a0", 1, P1_CONFIG)

    # Reverse mixed-station registration order.
    for patient in (b1, a2, a1, a0):
        coordinator.register_arrival(
            ScheduledArrival(4.0, patient)
        )

    arrived = coordinator.commit_due_arrivals()
    assert arrived == [a0, a1, b1, a2]

    ready = coordinator.route_entry_arrivals(
        list(reversed(arrived))
    )
    assert ready == [a0, a1, b1, a2]

    assert {
        patient_id: entry.station_id
        for patient_id, entry in coordinator._ready_for_queue.items()
    } == {
        "a0": "A", "a1": "A", "a2": "A", "b1": "B",
    }
    assert all(
        entry.travel_ended_at == 4.0
        for entry in coordinator._ready_for_queue.values()
    )

    phase23_prefix = list(log.records)
    committed = coordinator.commit_queue_entries(
        list(reversed(ready))
    )

    assert committed == [a0, a1, a2, b1]
    assert coordinator._ready_for_queue == {}
    assert env.now == 4.0
    assert log.records[:len(phase23_prefix)] == phase23_prefix

    # Phase 4 records are kept in their actual append order.
    queue_records = [
        r for r in log.records if r.event_type == "QUEUE_ENTRY"
    ]
    assert [
        (r.sim_time, r.phase, r.patient_id, r.station_id,
         r.prior_state, r.new_state)
        for r in queue_records
    ] == [
        (4.0, 4, "a0", "A", PatientState.TRAVELLING, PatientState.WAITING),
        (4.0, 4, "a1", "A", PatientState.TRAVELLING, PatientState.WAITING),
        (4.0, 4, "a2", "A", PatientState.TRAVELLING, PatientState.WAITING),
        (4.0, 4, "b1", "B", PatientState.TRAVELLING, PatientState.WAITING),
    ]

    travel_ends = {
        r.patient_id: r
        for r in log.records if r.event_type == "TRAVEL_END"
    }
    assert len(travel_ends) == 4
    for record in queue_records:
        ending = travel_ends[record.patient_id]
        assert record.sim_time == ending.sim_time
        assert record.station_id == ending.station_id
        assert ending.sequence_id < record.sequence_id

    phase3 = [r for r in log.records if r.phase == 3]
    assert phase3
    assert max(r.sequence_id for r in phase3) < min(
        r.sequence_id for r in queue_records
    )

    assert [v.patient for v in station_a.waiting] == [a0, a1, a2]
    assert [v.patient for v in station_b.waiting] == [b1]
    assert all(
        v.entered_at == 4.0
        for v in station_a.waiting + station_b.waiting
    )
    for patient in (a0, a1, a2, b1):
        assert patient.state == PatientState.WAITING
        assert patient.active_visit_id is not None
        assert patient.active_station_id == patient.location

    for station in (station_a, station_b):
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0
        assert station.peak_resource_count == 0

    assert not [
        r for r in log.records if r.event_type == "SERVICE_START"
    ]
    assert [r.sequence_id for r in log.records] == list(
        range(1, len(log.records) + 1)
    )
    for before, after in zip(log.records, log.records[1:]):
        assert before.sim_time <= after.sim_time
        if before.sim_time == after.sim_time:
            assert before.phase <= after.phase


def test_commit_queue_entries_rejects_repeated_queue_commit():
    """A consumed ready record cannot trigger a second QUEUE_ENTRY."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )
    patient = PatientAgent("u1", 1, P1_CONFIG)
    coordinator.register_arrival(ScheduledArrival(0.0, patient))
    arrived = coordinator.commit_due_arrivals()
    ready = coordinator.route_entry_arrivals(arrived)
    assert coordinator.commit_queue_entries(ready) == [patient]

    assert patient.state == PatientState.WAITING
    assert coordinator._ready_for_queue == {}
    before = list(log.records)
    waiting_before = list(station_a.waiting)

    with pytest.raises(ValueError, match="No unconsumed TRAVEL_END"):
        coordinator.commit_queue_entries([patient])

    assert log.records == before
    assert station_a.waiting == waiting_before
    assert len([
        r for r in log.records if r.event_type == "QUEUE_ENTRY"
    ]) == 1
    assert coordinator.commit_queue_entries([]) == []
    assert log.records == before
    assert env.now == 0.0
    assert station_a.resource.count == 0
    assert station_b.resource.count == 0


@pytest.mark.parametrize(
    "failure",
    [
        "duplicate_object",
        "duplicate_id_other_object",
        "impostor",
        "not_routed",
        "wrong_state",
        "wrong_location",
        "active_visit",
        "ineligible",
        "bad_destination",
        "stale_travel_end",
    ],
)
def test_commit_queue_entries_invalid_batch_is_atomic(failure):
    """Prevalidate all members: bad later item cannot enqueue first."""

    env, coordinator, station_a, station_b, log = (
        _make_ab_phase3_fixture()
    )
    a = PatientAgent("a", 1, P1_CONFIG)
    b = PatientAgent("b", 2, B_ONLY)
    c = PatientAgent("c", 3, P1_CONFIG)
    for patient in (a, b, c):
        coordinator.register_arrival(ScheduledArrival(0.0, patient))
    arrived = coordinator.commit_due_arrivals()
    assert arrived == [a, b, c]

    ready = coordinator.route_entry_arrivals([a, b])
    assert ready == [a, b]
    batch = [a, b]

    if failure == "duplicate_object":
        batch = [a, b, a]
        error = "Duplicate patient ID"
    elif failure == "duplicate_id_other_object":
        duplicate = PatientAgent("a", 99, P1_CONFIG)
        batch = [a, b, duplicate]
        error = "Duplicate patient ID"
    elif failure == "impostor":
        impostor = PatientAgent("b", 99, B_ONLY)
        batch = [a, impostor]
        error = "original Phase 2 admitted object"
    elif failure == "not_routed":
        batch = [a, c]
        error = "no completed Phase 3 entry travel"
    elif failure == "wrong_state":
        b.state = PatientState.DECIDING
        error = "must be TRAVELLING"
    elif failure == "wrong_location":
        b.location = "A"
        error = "does not match queue destination"
    elif failure == "active_visit":
        b.active_visit_id = "unexpected-visit"
        error = "already has an active visit"
    elif failure == "ineligible":
        b.completed_tests.add("B")
        error = "not eligible"
    elif failure == "bad_destination":
        coordinator._ready_for_queue["b"] = ReadyQueueEntry(
            patient=b, station_id="C", travel_ended_at=env.now
        )
        error = "not managed"
    elif failure == "stale_travel_end":
        env.run(until=1.0)
        error = "TRAVEL_END time mismatch"
    else:
        raise AssertionError(f"Unknown failure case {failure!r}")

    records_before = list(log.records)
    pending_before = list(coordinator.pending_arrivals)
    ready_before = dict(coordinator._ready_for_queue)
    routed_ids_before = set(coordinator._entry_routed_ids)
    patient_before = {
        patient.patient_id: (
            patient.state, patient.location,
            set(patient.completed_tests),
            patient.active_visit_id, patient.active_station_id,
        )
        for patient in (a, b, c)
    }

    with pytest.raises((ValueError, RuntimeError), match=error):
        coordinator.commit_queue_entries(batch)

    assert log.records == records_before
    assert not [
        r for r in log.records if r.event_type == "QUEUE_ENTRY"
    ]
    assert coordinator._ready_for_queue.keys() == ready_before.keys()
    for patient_id, entry in ready_before.items():
        assert coordinator._ready_for_queue[patient_id] is entry
    assert coordinator._entry_routed_ids == routed_ids_before
    assert coordinator.pending_arrivals == pending_before

    for patient in (a, b, c):
        assert (
            patient.state, patient.location, patient.completed_tests,
            patient.active_visit_id, patient.active_station_id,
        ) == patient_before[patient.patient_id]

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 0
        assert station.peak_resource_count == 0

    assert env.now == (
        1.0 if failure == "stale_travel_end" else 0.0
    )

# ==========================================================
# Integration: ENTRY -> Phase 2 -> 3 -> 4 -> 5 at t=0
# ==========================================================


def test_entry_flow_three_patients_through_phase5_at_t0():
    """Integrate the existing Phase 0-2 bucket and Phase 3-5 methods.

    Three patients arrive simultaneously at t=0, registered in
    reverse rank order:

        u1, rank 1, P1     -> A, IN_SERVICE
        u2, rank 2, P1     -> A, WAITING
        u3, rank 3, B_ONLY -> B, IN_SERVICE

    The test stops immediately after Phase 5 at t=0.
    No service completion, routing continuation or run() is invoked.
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

    log = EventLog(run_id="AB_ENTRY_FLOW_INTEGRATION")

    # Deliberately reverse the station dictionary order.
    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    u1 = PatientAgent(
        patient_id="u1",
        patient_rank=1,
        package=P1_CONFIG,
    )
    u2 = PatientAgent(
        patient_id="u2",
        patient_rank=2,
        package=P1_CONFIG,
    )
    u3 = PatientAgent(
        patient_id="u3",
        patient_rank=3,
        package=B_ONLY,
    )

    # ------------------------------------------------------
    # Registration only: reverse order u3 -> u2 -> u1.
    # ------------------------------------------------------

    for patient in (u3, u2, u1):
        coordinator.register_arrival(
            ScheduledArrival(
                at=0.0,
                patient=patient,
            )
        )

    assert env.now == 0.0
    assert log.records == []

    assert [
        arrival.patient
        for arrival in coordinator.pending_arrivals
    ] == [u3, u2, u1]

    for patient in (u1, u2, u3):
        assert patient.state == PatientState.ARRIVED
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()

    # No station work or resource ownership before admission.
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.queue == []

    # ------------------------------------------------------
    # Phase 0-2: process only the t=0 event bucket.
    # ------------------------------------------------------

    assert coordinator.next_event_time() == 0.0

    bucket = env.process(
        coordinator.process_next_event_bucket()
    )

    # IMPORTANT: run only until this Process completes.
    # Do not call env.run(until=3) or env.run(until=4).
    env.run(until=bucket)

    assert bucket.triggered
    assert env.now == 0.0

    released, arrived = bucket.value

    # There were no active services before t=0.
    assert released == []

    # Phase 2 must use rank/ID, not registration order.
    assert len(arrived) == 3
    assert arrived[0] is u1
    assert arrived[1] is u2
    assert arrived[2] is u3

    assert coordinator.pending_arrivals == []

    assert [
        (record.phase, record.patient_id, record.event_type)
        for record in log.records
    ] == [
        (2, "u1", "ARRIVAL"),
        (2, "u2", "ARRIVAL"),
        (2, "u3", "ARRIVAL"),
    ]

    for patient in (u1, u2, u3):
        assert patient.state == PatientState.ARRIVED
        assert patient.location == "ENTRY"

    # ------------------------------------------------------
    # Phase 3: synchronous zero-time ENTRY travel.
    # ------------------------------------------------------

    ready = coordinator.route_entry_arrivals(arrived)

    assert len(ready) == 3
    assert ready[0] is u1
    assert ready[1] is u2
    assert ready[2] is u3

    assert env.now == 0.0

    assert u1.location == "A"
    assert u2.location == "A"
    assert u3.location == "B"

    for patient in (u1, u2, u3):
        assert patient.state == PatientState.TRAVELLING
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    # Every TRAVEL_END must have a matching ready record.
    assert set(coordinator._ready_for_queue) == {
        "u1",
        "u2",
        "u3",
    }

    for patient in (u1, u2, u3):
        entry = coordinator._ready_for_queue[
            patient.patient_id
        ]

        assert entry.patient is patient
        assert entry.station_id == patient.location
        assert entry.travel_ended_at == 0.0

    # Movement alone does not enter queues or occupy Resources.
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    # ------------------------------------------------------
    # Phase 4: unified queue entry, A then B.
    # ------------------------------------------------------

    # Deliberately reverse Phase 4 input as well.
    queued = coordinator.commit_queue_entries(
        list(reversed(ready))
    )

    # Station A first, then B; rank/ID within each station.
    assert len(queued) == 3
    assert queued[0] is u1
    assert queued[1] is u2
    assert queued[2] is u3

    assert env.now == 0.0

    assert coordinator._ready_for_queue == {}

    for patient in (u1, u2, u3):
        assert patient.state == PatientState.WAITING
        assert patient.active_visit_id is not None
        assert patient.active_station_id == patient.location

    assert [
        visit.patient
        for visit in station_a.waiting
    ] == [u1, u2]

    assert [
        visit.patient
        for visit in station_b.waiting
    ] == [u3]

    # All waiting visits entered the domain queue at t=0.
    for visit in station_a.waiting + station_b.waiting:
        assert visit.entered_at == 0.0

    # Phase 4 does not request SimPy Resource capacity.
    assert station_a.resource.count == 0
    assert station_b.resource.count == 0

    assert station_a.resource.users == []
    assert station_b.resource.users == []

    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    # ------------------------------------------------------
    # Phase 5: explicit, independent service dispatch.
    # ------------------------------------------------------

    coordinator.dispatch_available_services()

    # The simulation is still at t=0.
    assert env.now == 0.0

    # A: u1 starts first (FCFS), u2 stays in domain queue.
    assert u1.state == PatientState.IN_SERVICE
    assert u1.location == "A"

    assert u2.state == PatientState.WAITING
    assert u2.location == "A"

    # B: u3 starts service immediately.
    assert u3.state == PatientState.IN_SERVICE
    assert u3.location == "B"

    assert u1.completed_tests == set()
    assert u2.completed_tests == set()
    assert u3.completed_tests == set()

    # Verify exact domain waiting-queue contents.
    assert len(station_a.waiting) == 1
    assert station_a.waiting[0].patient is u2
    assert station_a.waiting[0].entered_at == 0.0

    assert station_b.waiting == []

    # Verify exact active service ownership.
    assert len(station_a.active) == 1
    assert len(station_b.active) == 1

    active_a = next(iter(station_a.active.values()))
    active_b = next(iter(station_b.active.values()))

    assert active_a.patient is u1
    assert active_b.patient is u3

    # A lasts 4 time units; B lasts 3 time units.
    # They have STARTED, not completed.
    assert active_a.ends_at == 4.0
    assert active_b.ends_at == 3.0

    assert u1.active_station_id == "A"
    assert u2.active_station_id == "A"
    assert u3.active_station_id == "B"

    assert u1.active_visit_id is not None
    assert u2.active_visit_id is not None
    assert u3.active_visit_id is not None

    # Each station has capacity 1 and exactly one active service.
    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert len(station_a.resource.users) == 1
    assert len(station_b.resource.users) == 1

    assert station_a.resource.users[0] is active_a.request
    assert station_b.resource.users[0] is active_b.request

    # Native SimPy queues must remain empty.
    # u2 waits in station_a.waiting, NOT Resource.queue.
    assert station_a.resource.queue == []
    assert station_b.resource.queue == []

    assert station_a.peak_resource_count == 1
    assert station_b.peak_resource_count == 1

    assert station_a.release_count == 0
    assert station_b.release_count == 0

    # ------------------------------------------------------
    # Exact RAW EventLog append order.
    # No sorting or phase regrouping is allowed.
    # ------------------------------------------------------

    actual_raw = [
        (
            record.phase,
            record.patient_id,
            record.event_type,
            record.station_id,
        )
        for record in log.records
    ]

    expected_raw = [
        # Phase 2: all three arrivals.
        (2, "u1", "ARRIVAL", None),
        (2, "u2", "ARRIVAL", None),
        (2, "u3", "ARRIVAL", None),

        # Phase 3: routing and travel starts, rank/ID order.
        (3, "u1", "NEEDS_ROUTING", None),
        (3, "u1", "DECIDING", None),
        (3, "u1", "ROUTE_DECISION", None),
        (3, "u1", "TRAVEL_START", "A"),

        (3, "u2", "NEEDS_ROUTING", None),
        (3, "u2", "DECIDING", None),
        (3, "u2", "ROUTE_DECISION", None),
        (3, "u2", "TRAVEL_START", "A"),

        (3, "u3", "NEEDS_ROUTING", None),
        (3, "u3", "DECIDING", None),
        (3, "u3", "ROUTE_DECISION", None),
        (3, "u3", "TRAVEL_START", "B"),

        # Phase 3: all zero-time travel completions.
        (3, "u1", "TRAVEL_END", "A"),
        (3, "u2", "TRAVEL_END", "A"),
        (3, "u3", "TRAVEL_END", "B"),

        # Phase 4: all domain queue entries, A then B.
        (4, "u1", "QUEUE_ENTRY", "A"),
        (4, "u2", "QUEUE_ENTRY", "A"),
        (4, "u3", "QUEUE_ENTRY", "B"),

        # Phase 5: only available services start.
        (5, "u1", "SERVICE_START", "A"),
        (5, "u3", "SERVICE_START", "B"),
    ]

    raw_log = "\n".join(
        f"seq={r.sequence_id} "
        f"time={r.sim_time:g} "
        f"phase={r.phase} "
        f"patient={r.patient_id} "
        f"event={r.event_type} "
        f"station={r.station_id}"
        for r in log.records
    )

    assert actual_raw == expected_raw, (
        f"Expected raw events:\n{expected_raw!r}\n"
        f"Actual raw events:\n{actual_raw!r}\n"
        f"Full EventLog:\n{raw_log}"
    )

    # All records belong to this same t=0 bucket.
    assert len(log.records) == 23
    assert all(
        record.sim_time == 0.0
        for record in log.records
    )

    assert [
        record.sequence_id
        for record in log.records
    ] == list(range(1, len(log.records) + 1))

    # The four used phases are strictly nondecreasing.
    assert [
        record.phase
        for record in log.records
    ] == (
        [2] * 3
        + [3] * 15
        + [4] * 3
        + [5] * 2
    )

    # Verify event counts independently of expected_raw.
    assert sum(
        r.event_type == "ARRIVAL"
        for r in log.records
    ) == 3

    assert sum(
        r.event_type == "TRAVEL_END"
        for r in log.records
    ) == 3

    assert sum(
        r.event_type == "QUEUE_ENTRY"
        for r in log.records
    ) == 3

    assert sum(
        r.event_type == "SERVICE_START"
        for r in log.records
    ) == 2

    # Verify individual TRAVEL_END -> QUEUE_ENTRY linkage.
    travel_ends = {
        r.patient_id: r
        for r in log.records
        if r.event_type == "TRAVEL_END"
    }

    queue_entries = {
        r.patient_id: r
        for r in log.records
        if r.event_type == "QUEUE_ENTRY"
    }

    assert set(travel_ends) == {"u1", "u2", "u3"}
    assert set(queue_entries) == {"u1", "u2", "u3"}

    for patient_id in ("u1", "u2", "u3"):
        travel_end = travel_ends[patient_id]
        queue_entry = queue_entries[patient_id]

        assert travel_end.sim_time == queue_entry.sim_time
        assert travel_end.station_id == queue_entry.station_id
        assert travel_end.sequence_id < queue_entry.sequence_id

    # No service completion or release is allowed in this test.
    assert not [
        r for r in log.records
        if r.event_type in (
            "SERVICE_END",
            "RESOURCE_RELEASE",
            "DEPARTURE",
        )
    ]

    # The next scheduled event is B's completion at t=3,
    # but the integration test stops at t=0.
    assert coordinator.next_event_time() == 3.0
    assert env.now == 0.0


# ==========================================================
# Positive-duration travel: registration only
# ==========================================================


def _prepare_released_p1_at_t4():
    """P1 is admitted, served at A [0,4), and released for A -> B."""
    env = simpy.Environment()
    station_a = AOnlyCoordinatedStation(env, station_id="A")
    station_b = AOnlyCoordinatedStation(env, station_id="B")
    log = EventLog(run_id="AB_POSITIVE_TRAVEL_REGISTRATION")
    coordinator = MultiStationCoordinator(
        env, {"B": station_b, "A": station_a}, log
    )
    patient = PatientAgent("u1", 1, P1_CONFIG)
    coordinator.register_arrival(ScheduledArrival(0.0, patient))

    bucket = env.process(coordinator.process_next_event_bucket())
    env.run(until=bucket)
    released, arrived = bucket.value
    assert released == []
    assert arrived == [patient]

    ready = coordinator.route_entry_arrivals(arrived)
    assert ready == [patient]
    assert patient.location == "A"
    assert coordinator.commit_queue_entries(ready) == [patient]
    coordinator.dispatch_available_services()
    assert patient.state == PatientState.IN_SERVICE
    assert station_a.resource.count == 1
    assert station_b.resource.count == 0
    assert next(iter(station_a.active.values())).ends_at == 4.0

    env.run(until=4.0)
    released = coordinator.complete_due_services()
    assert released == [patient]
    assert env.now == 4.0
    assert patient.state == PatientState.NEEDS_ROUTING
    assert patient.location == "A"
    assert patient.completed_tests == {"A"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None
    assert coordinator.pending_travels == []
    assert station_a.active == {} and station_b.active == {}
    assert station_a.resource.count == 0
    assert station_b.resource.count == 0
    return env, coordinator, station_a, station_b, log, patient


def test_register_travel_p1_a_to_b_at_t4():
    """Register A -> B [4,5); no TRAVEL_START or time advancement."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    travel = ScheduledTravel(
        patient=patient,
        origin="A",
        destination="B",
        started_at=4.0,
        ends_at=5.0,
    )
    records_before = list(log.records)
    patient_before = (
        patient.state, patient.location, set(patient.completed_tests),
        patient.active_visit_id, patient.active_station_id,
    )
    assert coordinator.register_travel(travel) is None
    assert len(coordinator.pending_travels) == 1
    assert coordinator.pending_travels[0] is travel
    assert (travel.origin, travel.destination, travel.started_at, travel.ends_at) == (
        "A", "B", 4.0, 5.0
    )
    assert env.now == 4.0
    assert log.records == records_before
    assert (
        patient.state, patient.location, patient.completed_tests,
        patient.active_visit_id, patient.active_station_id,
    ) == patient_before
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
    assert not [
        r for r in log.records
        if r.sim_time == 4.0 and r.event_type in ("TRAVEL_START", "TRAVEL_END")
    ]


def test_register_travel_rejects_duplicate_without_side_effects():
    """A pending travel cannot be registered a second time."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    first = ScheduledTravel(patient, "A", "B", 4.0, 5.0)
    second = ScheduledTravel(patient, "A", "B", 4.0, 5.0)
    coordinator.register_travel(first)

    records_before = list(log.records)
    plans_before = list(coordinator.pending_travels)
    with pytest.raises(ValueError, match="already has a pending travel"):
        coordinator.register_travel(second)

    assert coordinator.pending_travels == plans_before
    assert len(coordinator.pending_travels) == 1
    assert coordinator.pending_travels[0] is first
    assert log.records == records_before
    assert env.now == 4.0
    assert patient.state == PatientState.NEEDS_ROUTING
    assert patient.location == "A"
    assert patient.completed_tests == {"A"}
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


@pytest.mark.parametrize(
    "failure",
    [
        "wrong_end_time",
        "impostor",
        "wrong_start_time",
        "wrong_origin",
        "unmanaged_destination",
        "ineligible_destination",
        "active_visit",
    ],
)
def test_register_travel_invalid_plan_is_atomic(failure):
    """All bad plans fail before state, EventLog or plan mutation."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    travel_patient = patient
    origin, destination = "A", "B"
    started_at, ends_at = 4.0, 5.0
    if failure == "wrong_end_time":
        ends_at = 5.5
        error = "does not match travel matrix"
    elif failure == "impostor":
        travel_patient = PatientAgent("u1", 1, P1_CONFIG)
        travel_patient.state = PatientState.NEEDS_ROUTING
        travel_patient.location = "A"
        travel_patient.completed_tests.add("A")
        error = "original Phase 2 admitted object"
    elif failure == "wrong_start_time":
        started_at = 3.0
        error = "must start at current simulation time"
    elif failure == "wrong_origin":
        origin = "B"
        error = "origin must match patient location"
    elif failure == "unmanaged_destination":
        destination = "C"
        error = "not managed"
    elif failure == "ineligible_destination":
        destination = "A"
        error = "not eligible"
    elif failure == "active_visit":
        patient.active_visit_id = "unexpected-visit"
        error = "active visit"
    else:
        raise AssertionError(f"Unexpected failure {failure!r}")

    bad_plan = ScheduledTravel(
        patient=travel_patient, origin=origin, destination=destination,
        started_at=started_at, ends_at=ends_at,
    )
    records_before = list(log.records)
    plans_before = list(coordinator.pending_travels)
    admitted_before = dict(coordinator._admitted_patients_by_id)
    state_before = (
        patient.state, patient.location, set(patient.completed_tests),
        patient.active_visit_id, patient.active_station_id,
    )
    other_before = (
        travel_patient.state, travel_patient.location,
        set(travel_patient.completed_tests), travel_patient.active_visit_id,
        travel_patient.active_station_id,
    )

    with pytest.raises(ValueError, match=error):
        coordinator.register_travel(bad_plan)
    assert coordinator.pending_travels == plans_before == []
    assert log.records == records_before
    assert env.now == 4.0
    assert coordinator._admitted_patients_by_id == admitted_before
    assert (
        patient.state, patient.location, patient.completed_tests,
        patient.active_visit_id, patient.active_station_id,
    ) == state_before
    assert (
        travel_patient.state, travel_patient.location,
        travel_patient.completed_tests, travel_patient.active_visit_id,
        travel_patient.active_station_id,
    ) == other_before
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


# ==========================================================
# Phase 3: start positive-duration continuation after release
# ==========================================================


def test_start_next_travel_p1_a_to_b_at_t4():
    """P1 released at t=4 starts A -> B [4,5) without arriving at B."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    before = list(log.records)

    travel = coordinator.start_next_travel(patient)

    assert len(coordinator.pending_travels) == 1
    assert coordinator.pending_travels[0] is travel
    assert travel.patient is patient
    assert (
        travel.origin,
        travel.destination,
        travel.started_at,
        travel.ends_at,
    ) == ("A", "B", 4.0, 5.0)

    assert env.now == 4.0
    assert patient.state == PatientState.TRAVELLING
    assert patient.location == "A"
    assert patient.completed_tests == {"A"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert log.records[:len(before)] == before
    t4 = [record for record in log.records if record.sim_time == 4.0]
    assert [record.phase for record in t4] == [0, 1, 3, 3, 3]
    assert [record.event_type for record in t4] == [
        "SERVICE_END",
        "RESOURCE_RELEASE",
        "DECIDING",
        "ROUTE_DECISION",
        "TRAVEL_START",
    ]
    assert [record.patient_id for record in t4] == ["u1"] * 5
    assert t4[2].prior_state == PatientState.NEEDS_ROUTING
    assert t4[2].new_state == PatientState.DECIDING
    assert t4[3].prior_state == PatientState.DECIDING
    assert t4[3].new_state == PatientState.DECIDING
    assert t4[3].recommended_station == "B"
    assert t4[3].chosen_station == "B"
    assert t4[4].prior_state == PatientState.DECIDING
    assert t4[4].new_state == PatientState.TRAVELLING
    assert t4[4].station_id == "B"
    assert [record.sequence_id for record in log.records] == list(
        range(1, len(log.records) + 1)
    )

    # A pending travel is not yet a scheduled event-bucket completion.
    assert coordinator.next_event_time() is None
    assert coordinator._ready_for_queue == {}
    assert not [
        record for record in log.records
        if record.sim_time == 4.0 and record.event_type in (
            "TRAVEL_END", "QUEUE_ENTRY", "SERVICE_START",
        )
    ]

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


def test_start_next_travel_rejects_existing_pending_without_side_effects():
    """Registering the plan first must prevent a partial Phase 3 start."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    pending = ScheduledTravel(patient, "A", "B", 4.0, 5.0)
    coordinator.register_travel(pending)

    records_before = list(log.records)
    plans_before = list(coordinator.pending_travels)
    patient_before = (
        patient.state, patient.location, set(patient.completed_tests),
        patient.active_visit_id, patient.active_station_id,
    )

    with pytest.raises(ValueError, match="already has a pending travel"):
        coordinator.start_next_travel(patient)

    assert coordinator.pending_travels == plans_before
    assert len(coordinator.pending_travels) == 1
    assert coordinator.pending_travels[0] is pending
    assert log.records == records_before
    assert env.now == 4.0
    assert (
        patient.state, patient.location, patient.completed_tests,
        patient.active_visit_id, patient.active_station_id,
    ) == patient_before
    assert patient.state == PatientState.NEEDS_ROUTING
    assert coordinator._ready_for_queue == {}
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


def test_start_next_travel_rejects_second_start_without_side_effects():
    """After TRAVEL_START the state is TRAVELLING; cannot start twice."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    travel = coordinator.start_next_travel(patient)

    records_before = list(log.records)
    plans_before = list(coordinator.pending_travels)
    patient_before = (
        patient.state, patient.location, set(patient.completed_tests),
        patient.active_visit_id, patient.active_station_id,
    )

    with pytest.raises(ValueError, match="must be NEEDS_ROUTING"):
        coordinator.start_next_travel(patient)

    assert coordinator.pending_travels == plans_before == [travel]
    assert coordinator.pending_travels[0] is travel
    assert log.records == records_before
    assert env.now == 4.0
    assert (
        patient.state, patient.location, patient.completed_tests,
        patient.active_visit_id, patient.active_station_id,
    ) == patient_before
    assert patient.state == PatientState.TRAVELLING
    assert patient.location == "A"
    assert coordinator._ready_for_queue == {}
    assert sum(r.event_type == "TRAVEL_START" for r in log.records) == 2
    # One zero-time ENTRY -> A and one positive-duration A -> B.
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []


@pytest.mark.parametrize(
    "invalid",
    ["impostor", "wrong_state", "active_visit", "no_remaining_test"],
)
def test_start_next_travel_invalid_patient_has_no_side_effects(invalid):
    """Invalid identity/state/visit/fixed-route leaves the batch intact."""
    env, coordinator, station_a, station_b, log, patient = (
        _prepare_released_p1_at_t4()
    )
    candidate = patient
    if invalid == "impostor":
        candidate = PatientAgent("u1", 1, P1_CONFIG)
        candidate.state = PatientState.NEEDS_ROUTING
        candidate.location = "A"
        candidate.completed_tests.add("A")
        error = "original Phase 2 admitted object"
    elif invalid == "wrong_state":
        patient.state = PatientState.WAITING
        error = "must be NEEDS_ROUTING"
    elif invalid == "active_visit":
        patient.active_visit_id = "unexpected-visit"
        error = "active visit"
    elif invalid == "no_remaining_test":
        patient.completed_tests.add("B")
        error = "no remaining fixed-route test"
    else:
        raise AssertionError(invalid)

    records_before = list(log.records)
    plans_before = list(coordinator.pending_travels)
    patient_before = (
        patient.state, patient.location, set(patient.completed_tests),
        patient.active_visit_id, patient.active_station_id,
    )
    candidate_before = (
        candidate.state, candidate.location, set(candidate.completed_tests),
        candidate.active_visit_id, candidate.active_station_id,
    )

    with pytest.raises(ValueError, match=error):
        coordinator.start_next_travel(candidate)

    assert coordinator.pending_travels == plans_before == []
    assert log.records == records_before
    assert env.now == 4.0
    assert (
        patient.state, patient.location, patient.completed_tests,
        patient.active_visit_id, patient.active_station_id,
    ) == patient_before
    assert (
        candidate.state, candidate.location, candidate.completed_tests,
        candidate.active_visit_id, candidate.active_station_id,
    ) == candidate_before
    assert coordinator._ready_for_queue == {}
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
