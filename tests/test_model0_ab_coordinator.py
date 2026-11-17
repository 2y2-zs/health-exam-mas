
"""Initialization, service completion and time-query tests for A/B Coordinator."""

import pytest
import simpy

from health_exam_mas.model0 import (
    EventLog,
    PackageConfig,
    PatientAgent,
    PatientState,
)

from model0_a_only_prototype import AOnlyCoordinatedStation

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

    # The traversal order must not depend on input order.
    assert coordinator.station_ids == ("A", "B")

    assert list(coordinator.stations) == [
        "A",
        "B",
    ]

    assert tuple(
        coordinator.stations.values()
    ) == (
        station_a,
        station_b,
    )

    # Coordinator stores the original Station objects.
    assert coordinator.stations["A"] is station_a
    assert coordinator.stations["B"] is station_b

    # The registry is a copy of the caller's dictionary.
    supplied["A"] = station_b

    assert coordinator.stations["A"] is station_a
    assert list(coordinator.stations) == [
        "A",
        "B",
    ]

    # Initialization must not advance simulation time.
    assert env.now == 0

    # No domain events or resource operations.
    assert log.records == []

    # Scheduling is intentionally not implemented.
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
        "A": AOnlyCoordinatedStation(
            env,
            station_id="A",
        ),
        "B": AOnlyCoordinatedStation(
            env,
            station_id="B",
        ),
    }

    # Replace one station with one built in another Environment.
    stations[foreign_station] = AOnlyCoordinatedStation(
        other_env,
        station_id=foreign_station,
    )

    log = EventLog(
        run_id="AB_INIT_DIFFERENT_ENV"
    )

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

    station_a = AOnlyCoordinatedStation(
        env,
        station_id="A",
    )
    station_b = AOnlyCoordinatedStation(
        env,
        station_id="B",
    )

    stations = {
        "A": station_a,
        "B": station_b,
    }

    # Deliberately associate one key with the wrong station.
    stations[wrong_key] = (
        station_b
        if wrong_key == "A"
        else station_a
    )

    log = EventLog(
        run_id="AB_INIT_KEY_MISMATCH"
    )

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
    """Prepare A [0,4) and B [1,4), without a Coordinator run().

    Return the environment at t=1, with both services active.
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

    log = EventLog(run_id="AB_DUE_SERVICES")

    # Deliberately supply the station dictionary in reverse order.
    # MultiStationCoordinator must still process A before B.
    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "B": station_b,
            "A": station_a,
        },
        event_log=log,
    )

    # Use opposite patient ranks to verify that the required
    # ordering is by station A -> B, not a global rank sort.
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

    # t=0: Start A service [0,4).
    patient_a.location = "A"
    patient_a.state = PatientState.TRAVELLING

    station_a.enqueue(patient_a, log)
    station_a.start_available(log)

    assert patient_a.state == PatientState.IN_SERVICE
    assert station_a.resource.count == 1

    # t=1: Start B service [1,4).
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

    # Both stations are occupied before the shared completion time.
    assert env.now == 1.0
    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    assert patient_a.completed_tests == set()
    assert patient_b.completed_tests == set()

    # Advance to the shared due time t=4.
    env.run(until=4.0)

    assert env.now == 4.0

    # Both services are still active until Phase 1.
    assert len(station_a.active) == 1
    assert len(station_b.active) == 1

    assert station_a.resource.count == 1
    assert station_b.resource.count == 1

    # One synchronous Coordinator call.
    released = coordinator.complete_due_services()

    # All released patients are returned in station order.
    assert len(released) == 2
    assert released[0] is patient_a
    assert released[1] is patient_b

    # The method must not advance simulation time.
    assert env.now == 4.0

    # Strict t=4 raw EventLog append order.
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

    # All SERVICE_END records precede both releases.
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

    # Both patients completed their own packages.
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

    # Complete Resource cleanup at both stations.
    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}

        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

        assert station.release_count == 1
        assert station.peak_resource_count == 1

    # The method does not perform Phase 3 departures.
    assert not [
        record
        for record in log.records
        if record.event_type == "DEPARTURE"
    ]

    # Global raw log phase and sequence checks.
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

    # Both stations remain busy at t=2.
    env.run(until=2.0)

    assert env.now == 2.0

    # Capture the original log and domain state.
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

    # No service is due at the current time.
    released = coordinator.complete_due_services()

    assert released == []
    assert env.now == 2.0

    # No event records were appended.
    assert log.records == records_before

    # No patient state or progress changed.
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

    # Active visits retain the same objects and ownership.
    assert station_a.active.keys() == active_a_before.keys()
    assert station_b.active.keys() == active_b_before.keys()

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit

    # Both Resources remain occupied.
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

    # Repeated no-due calls also have no effect.
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

    # Query while both services are in progress.
    assert coordinator.next_service_completion_time() == 4.0
    assert coordinator.next_service_completion_time() == 4.0

    # Querying must not advance time or change anything.
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

    # At exactly t=4 the services are due, not overdue.
    env.run(until=4.0)

    assert env.now == 4.0
    assert coordinator.next_service_completion_time() == 4.0

    # Querying at the due boundary still commits nothing.
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

    log = EventLog(
        run_id="AB_STAGGERED_SERVICE_TIMES"
    )

    # Reverse input order must not affect the time query.
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

    assert station_a.resource.count == 1
    assert patient_a.state == PatientState.IN_SERVICE

    # B service [2,5).
    env.run(until=2.0)

    patient_b.location = "B"
    patient_b.state = PatientState.TRAVELLING

    station_b.enqueue(patient_b, log)
    station_b.start_available(log)

    assert env.now == 2.0
    assert station_b.resource.count == 1
    assert patient_b.state == PatientState.IN_SERVICE

    # The first completion is at A, t=4.
    records_before_query = list(log.records)

    assert coordinator.next_service_completion_time() == 4.0
    assert env.now == 2.0
    assert log.records == records_before_query

    # Advance externally to A's completion boundary.
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

    # B is not due at t=4 and must remain in service.
    assert patient_b.state == PatientState.IN_SERVICE
    assert patient_b.completed_tests == set()
    assert len(station_b.active) == 1
    assert station_b.resource.count == 1
    assert station_b.release_count == 0

    # After A's release, the earliest active completion is B at t=5.
    records_before_query = list(log.records)

    assert coordinator.next_service_completion_time() == 5.0
    assert coordinator.next_service_completion_time() == 5.0

    assert env.now == 4.0
    assert log.records == records_before_query
    assert station_b.resource.count == 1

    # Advance externally to B's completion boundary.
    env.run(until=5.0)

    assert coordinator.next_service_completion_time() == 5.0
    assert env.now == 5.0

    released_b = coordinator.complete_due_services()

    assert released_b == [patient_b]
    assert released_b[0] is patient_b

    assert patient_b.state == PatientState.FINISHED
    assert patient_b.completed_tests == {"B"}

    # No active service remains after both releases.
    assert coordinator.next_service_completion_time() is None

    assert env.now == 5.0

    for station in (station_a, station_b):
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert station.release_count == 1

    # Raw log order for the two separate completion buckets.
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

    # Query and service completion do not commit Phase 3 departure.
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

    log = EventLog(
        run_id="AB_NO_ACTIVE_SERVICE"
    )

    coordinator = MultiStationCoordinator(
        env=env,
        stations={
            "A": station_a,
            "B": station_b,
        },
        event_log=log,
    )

    # Initially there are no active services at either station.
    assert coordinator.next_service_completion_time() is None

    assert env.now == 0
    assert log.records == []

    # Prepare a patient waiting at A, but do NOT start service.
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

    # Work remains in the domain queue, but no service is active.
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

    # None is NOT evidence that the overall simulation is complete.


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

    # Both active services end at t=4, but no release is committed.
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

    # Failure must not change simulation time or write events.
    assert env.now == 4.5
    assert log.records == records_before

    # Neither visit may be removed by a failed query.
    assert station_a.active.keys() == active_a_before.keys()
    assert station_b.active.keys() == active_b_before.keys()

    for visit_id, visit in active_a_before.items():
        assert station_a.active[visit_id] is visit
        assert visit.ends_at == 4.0

    for visit_id, visit in active_b_before.items():
        assert station_b.active[visit_id] is visit
        assert visit.ends_at == 4.0

    # Both patients remain in service without progress changes.
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

    # Resource ownership and release counters are unchanged.
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
