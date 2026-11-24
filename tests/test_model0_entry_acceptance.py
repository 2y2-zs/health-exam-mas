"""Model 0 acceptance through the packaged A/B/C entry point."""

from dataclasses import replace

import pytest
import simpy

from health_exam_mas.model0 import (
    MODEL0_TRAVEL_TIMES,
    EventLog,
    P1_CONFIG,
    PackageConfig,
    PatientAgent,
    PatientState,
)
from health_exam_mas.model0_coordinator import MultiStationCoordinator, ScheduledArrival
from health_exam_mas.model0_station import AOnlyCoordinatedStation


def test_t01_single_p1_abc_formal_entry_finishes_at_t8():
    env = simpy.Environment()
    event_log = EventLog(run_id="ENTRY_T01")
    stations = {
        station_id: AOnlyCoordinatedStation(env, station_id)
        for station_id in ("A", "B", "C")
    }

    assert all(station.env is env for station in stations.values())
    assert {
        name: (station.config.capacity, station.config.service_duration)
        for name, station in stations.items()
    } == {"A": (1, 4.0), "B": (1, 3.0), "C": (2, 5.0)}
    assert MODEL0_TRAVEL_TIMES[("ENTRY", "A")] == 0.0
    assert MODEL0_TRAVEL_TIMES[("A", "B")] == 1.0

    patient = PatientAgent("u1", patient_rank=1, package=P1_CONFIG)
    assert patient.state == PatientState.ARRIVED
    assert patient.location == "ENTRY"
    assert patient.completed_tests == set()

    coordinator = MultiStationCoordinator(env, stations, event_log)
    assert coordinator.station_ids == ("A", "B", "C")
    coordinator.register_arrival(ScheduledArrival(at=0.0, patient=patient))
    assert env.now == 0.0
    assert event_log.records == []

    process = env.process(coordinator.run())
    env.run()
    assert process.triggered and process.ok
    assert env.now == 8.0

    records = event_log.records
    print("\n=== T01 RAW EVENT LOG (APPEND ORDER) ===")
    for record in records:
        print(repr(record))
    print("=== END T01 RAW EVENT LOG ===")

    assert len(records) == 19
    assert [record.sequence_id for record in records] == list(range(1, 20))
    assert all(record.run_id == "ENTRY_T01" for record in records)
    assert all(record.patient_id == "u1" for record in records)

    # Compare the emitted order; never sort the records.
    actual_raw = [
        (
            record.sim_time,
            record.phase,
            record.event_type,
            record.prior_state,
            record.new_state,
            record.station_id,
        )
        for record in records
    ]
    S = PatientState
    expected_raw = [
        (0.0, 2, "ARRIVAL", None, S.ARRIVED, None),
        (0.0, 3, "NEEDS_ROUTING", S.ARRIVED, S.NEEDS_ROUTING, None),
        (0.0, 3, "DECIDING", S.NEEDS_ROUTING, S.DECIDING, None),
        (0.0, 3, "ROUTE_DECISION", S.DECIDING, S.DECIDING, None),
        (0.0, 3, "TRAVEL_START", S.DECIDING, S.TRAVELLING, "A"),
        (0.0, 3, "TRAVEL_END", S.TRAVELLING, S.TRAVELLING, "A"),
        (0.0, 4, "QUEUE_ENTRY", S.TRAVELLING, S.WAITING, "A"),
        (0.0, 5, "SERVICE_START", S.WAITING, S.IN_SERVICE, "A"),
        (4.0, 0, "SERVICE_END", S.IN_SERVICE, S.IN_SERVICE, "A"),
        (4.0, 1, "RESOURCE_RELEASE", S.IN_SERVICE, S.NEEDS_ROUTING, "A"),
        (4.0, 3, "DECIDING", S.NEEDS_ROUTING, S.DECIDING, None),
        (4.0, 3, "ROUTE_DECISION", S.DECIDING, S.DECIDING, None),
        (4.0, 3, "TRAVEL_START", S.DECIDING, S.TRAVELLING, "B"),
        (5.0, 3, "TRAVEL_END", S.TRAVELLING, S.TRAVELLING, "B"),
        (5.0, 4, "QUEUE_ENTRY", S.TRAVELLING, S.WAITING, "B"),
        (5.0, 5, "SERVICE_START", S.WAITING, S.IN_SERVICE, "B"),
        (8.0, 0, "SERVICE_END", S.IN_SERVICE, S.IN_SERVICE, "B"),
        (8.0, 1, "RESOURCE_RELEASE", S.IN_SERVICE, S.FINISHED, "B"),
        (8.0, 3, "DEPARTURE", S.FINISHED, S.FINISHED, None),
    ]
    assert actual_raw == expected_raw, "T01 raw event trace differs"

    def events(event_type):
        return [record for record in records if record.event_type == event_type]

    assert [
        (record.recommended_station, record.chosen_station)
        for record in events("ROUTE_DECISION")
    ] == [("A", "A"), ("B", "B")]

    queue_entries = events("QUEUE_ENTRY")
    service_starts = events("SERVICE_START")
    service_ends = events("SERVICE_END")
    releases = events("RESOURCE_RELEASE")
    assert len(queue_entries) == 2
    assert len(service_starts) == 2
    assert len(service_ends) == 2
    assert len(releases) == 2
    # Visit identity includes its patient and station.
    assert len({
        (record.patient_id, record.station_id, record.visit_id)
        for record in queue_entries
    }) == 2

    for visit_events in zip(
        queue_entries, service_starts, service_ends, releases, strict=True
    ):
        entry = visit_events[0]
        assert entry.visit_id
        assert entry.resource_token_or_server_id
        visit_key = (entry.patient_id, entry.station_id, entry.visit_id)
        assert all(
            (record.patient_id, record.station_id, record.visit_id) == visit_key
            for record in visit_events
        )
        assert all(
            record.resource_token_or_server_id == entry.resource_token_or_server_id
            for record in visit_events
        )

    assert [(r.station_id, r.sim_time) for r in queue_entries] == [
        ("A", 0.0), ("B", 5.0)
    ]
    assert [(r.station_id, r.sim_time) for r in service_starts] == [
        ("A", 0.0), ("B", 5.0)
    ]
    assert [(r.station_id, r.sim_time) for r in service_ends] == [
        ("A", 4.0), ("B", 8.0)
    ]

    travel_starts = events("TRAVEL_START")
    travel_ends = events("TRAVEL_END")
    assert [(r.station_id, r.sim_time) for r in travel_starts] == [
        ("A", 0.0), ("B", 4.0)
    ]
    assert [(r.station_id, r.sim_time) for r in travel_ends] == [
        ("A", 0.0), ("B", 5.0)
    ]

    waiting_duration = sum(
        start.sim_time - entry.sim_time
        for entry, start in zip(queue_entries, service_starts, strict=True)
    )
    service_duration = sum(
        end.sim_time - start.sim_time
        for start, end in zip(service_starts, service_ends, strict=True)
    )
    travel_duration = sum(
        end.sim_time - start.sim_time
        for start, end in zip(travel_starts, travel_ends, strict=True)
    )
    assert (waiting_duration, service_duration, travel_duration) == (0.0, 7.0, 1.0)

    departures = events("DEPARTURE")
    assert len(departures) == 1
    assert (
        departures[0].sim_time,
        departures[0].prior_state,
        departures[0].new_state,
    ) == (8.0, S.FINISHED, S.FINISHED)
    assert patient.state == S.FINISHED
    assert patient.location == "B"
    assert patient.completed_tests == {"A", "B"}
    assert patient.active_visit_id is None
    assert patient.active_station_id is None

    assert coordinator.pending_arrivals == []
    assert coordinator.pending_travels == []
    assert coordinator.next_event_time() is None
    expected_usage = {"A": (1, 1), "B": (1, 1), "C": (0, 0)}
    for station_id, station in stations.items():
        assert station.waiting == []
        assert station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []
        assert (station.release_count, station.peak_resource_count) == expected_usage[
            station_id
        ]
    assert not any(record.station_id == "C" for record in records)


@pytest.mark.parametrize(
    "registration_order",
    [("u1", "u2"), ("u2", "u1")],
    ids=["forward_registration", "reverse_registration"],
)
def test_t02_two_p1_same_time_arrivals_fcfs(registration_order):
    """T02: simultaneous P1 arrivals follow rank under both registration orders."""

    env = simpy.Environment()
    event_log = EventLog(run_id="ENTRY_T02")

    stations = {
        station_id: AOnlyCoordinatedStation(env, station_id)
        for station_id in ("A", "B", "C")
    }

    assert all(station.env is env for station in stations.values())

    assert {
        name: (station.config.capacity, station.config.service_duration)
        for name, station in stations.items()
    } == {"A": (1, 4.0), "B": (1, 3.0), "C": (2, 5.0)}

    assert MODEL0_TRAVEL_TIMES[("ENTRY", "A")] == 0.0
    assert MODEL0_TRAVEL_TIMES[("A", "B")] == 1.0

    u1 = PatientAgent("u1", patient_rank=1, package=P1_CONFIG)

    u2 = PatientAgent("u2", patient_rank=2, package=P1_CONFIG)

    patients = {"u1": u1, "u2": u2}

    S = PatientState

    for patient in patients.values():
        assert patient.state == S.ARRIVED
        assert patient.location == "ENTRY"
        assert patient.completed_tests == set()
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    coordinator = MultiStationCoordinator(env, stations, event_log)

    assert coordinator.station_ids == ("A", "B", "C")

    for patient_id in registration_order:
        coordinator.register_arrival(ScheduledArrival(at=0.0, patient=patients[patient_id]))

    assert env.now == 0.0
    assert event_log.records == []

    process = env.process(coordinator.run())
    env.run()

    records = event_log.records

    print("\n=== T02 RAW EVENT LOG " f"(registration={registration_order!r}) ===")

    for record in records:
        print(repr(record))

    print("=== END T02 RAW EVENT LOG ===")

    assert process.triggered and process.ok
    assert env.now == 12.0

    assert len(records) == 38

    assert [record.sequence_id for record in records] == list(range(1, 39))

    assert all(record.run_id == "ENTRY_T02" for record in records)

    assert {record.patient_id for record in records} == {"u1", "u2"}

    # Check the emitted order without sorting.
    for earlier, later in zip(records, records[1:]):
        assert earlier.sim_time <= later.sim_time

        if earlier.sim_time == later.sim_time:
            assert earlier.phase <= later.phase

    def events(event_type, patient_id=None, station_id=None):
        """Filter raw events without changing their order."""

        return [
            record
            for record in records
            if record.event_type == event_type
            and (
                patient_id is None or record.patient_id == patient_id
            )
            and (
                station_id is None or record.station_id == station_id
            )
        ]

    def expected_patient_trace(
        a_start,
        a_end,
        b_arrival,
        departure,
    ):
        """Independent expected trace, not derived from output."""

        return [
            (0.0, 2, "ARRIVAL", None, S.ARRIVED, None),

            (0.0, 3, "NEEDS_ROUTING", S.ARRIVED, S.NEEDS_ROUTING, None),
            (0.0, 3, "DECIDING", S.NEEDS_ROUTING, S.DECIDING, None),
            (0.0, 3, "ROUTE_DECISION", S.DECIDING, S.DECIDING, None),
            (0.0, 3, "TRAVEL_START", S.DECIDING, S.TRAVELLING, "A"),
            (0.0, 3, "TRAVEL_END", S.TRAVELLING, S.TRAVELLING, "A"),

            (0.0, 4, "QUEUE_ENTRY", S.TRAVELLING, S.WAITING, "A"),
            (a_start, 5, "SERVICE_START", S.WAITING, S.IN_SERVICE, "A"),

            (a_end, 0, "SERVICE_END", S.IN_SERVICE, S.IN_SERVICE, "A"),
            (a_end, 1, "RESOURCE_RELEASE", S.IN_SERVICE, S.NEEDS_ROUTING, "A"),

            (a_end, 3, "DECIDING", S.NEEDS_ROUTING, S.DECIDING, None),
            (a_end, 3, "ROUTE_DECISION", S.DECIDING, S.DECIDING, None),
            (a_end, 3, "TRAVEL_START", S.DECIDING, S.TRAVELLING, "B"),
            (b_arrival, 3, "TRAVEL_END", S.TRAVELLING, S.TRAVELLING, "B"),

            (b_arrival, 4, "QUEUE_ENTRY", S.TRAVELLING, S.WAITING, "B"),
            (b_arrival, 5, "SERVICE_START", S.WAITING, S.IN_SERVICE, "B"),

            (departure, 0, "SERVICE_END", S.IN_SERVICE, S.IN_SERVICE, "B"),
            (departure, 1, "RESOURCE_RELEASE", S.IN_SERVICE, S.FINISHED, "B"),
            (departure, 3, "DEPARTURE", S.FINISHED, S.FINISHED, None),
        ]

    expected_traces = {
        "u1": expected_patient_trace(a_start=0.0, a_end=4.0, b_arrival=5.0, departure=8.0),
        "u2": expected_patient_trace(a_start=4.0, a_end=8.0, b_arrival=9.0, departure=12.0),
    }

    for patient_id in ("u1", "u2"):
        patient_records = [record for record in records if record.patient_id == patient_id]

        assert len(patient_records) == 19

        actual_trace = [
            (
                record.sim_time,
                record.phase,
                record.event_type,
                record.prior_state,
                record.new_state,
                record.station_id,
            )
            for record in patient_records
        ]

        assert actual_trace == expected_traces[patient_id], (
            f"T02 trace differs for {patient_id}; " f"registration_order={registration_order!r}"
        )

    actual_t0 = [
        (record.phase, record.patient_id, record.event_type, record.station_id)
        for record in records
        if record.sim_time == 0.0
    ]

    expected_t0 = [
        (2, "u1", "ARRIVAL", None),
        (2, "u2", "ARRIVAL", None),

        (3, "u1", "NEEDS_ROUTING", None),
        (3, "u1", "DECIDING", None),
        (3, "u1", "ROUTE_DECISION", None),
        (3, "u1", "TRAVEL_START", "A"),

        (3, "u2", "NEEDS_ROUTING", None),
        (3, "u2", "DECIDING", None),
        (3, "u2", "ROUTE_DECISION", None),
        (3, "u2", "TRAVEL_START", "A"),

        (3, "u1", "TRAVEL_END", "A"),
        (3, "u2", "TRAVEL_END", "A"),

        (4, "u1", "QUEUE_ENTRY", "A"),
        (4, "u2", "QUEUE_ENTRY", "A"),

        (5, "u1", "SERVICE_START", "A"),
    ]

    assert actual_t0 == expected_t0

    actual_t4 = [
        (record.phase, record.patient_id, record.event_type, record.station_id)
        for record in records
        if record.sim_time == 4.0
    ]

    assert actual_t4 == [
        (0, "u1", "SERVICE_END", "A"),
        (1, "u1", "RESOURCE_RELEASE", "A"),
        (3, "u1", "DECIDING", None),
        (3, "u1", "ROUTE_DECISION", None),
        (3, "u1", "TRAVEL_START", "B"),
        (5, "u2", "SERVICE_START", "A"),
    ]

    actual_t8 = [
        (record.phase, record.patient_id, record.event_type, record.station_id)
        for record in records
        if record.sim_time == 8.0
    ]

    # Final departures precede onward routing in Phase 3.
    assert actual_t8 == [
        (0, "u2", "SERVICE_END", "A"),
        (0, "u1", "SERVICE_END", "B"),
        (1, "u2", "RESOURCE_RELEASE", "A"),
        (1, "u1", "RESOURCE_RELEASE", "B"),
        (3, "u1", "DEPARTURE", None),
        (3, "u2", "DECIDING", None),
        (3, "u2", "ROUTE_DECISION", None),
        (3, "u2", "TRAVEL_START", "B"),
    ]

    assert [
        (record.patient_id, record.sim_time)
        for record in events("QUEUE_ENTRY", station_id="A")
    ] == [("u1", 0.0), ("u2", 0.0)]

    assert [
        (record.patient_id, record.sim_time)
        for record in events("SERVICE_START", station_id="A")
    ] == [("u1", 0.0), ("u2", 4.0)]

    assert [
        (record.patient_id, record.sim_time)
        for record in events("SERVICE_END", station_id="A")
    ] == [("u1", 4.0), ("u2", 8.0)]

    assert [
        (record.patient_id, record.sim_time)
        for record in events("QUEUE_ENTRY", station_id="B")
    ] == [("u1", 5.0), ("u2", 9.0)]

    assert [
        (record.patient_id, record.sim_time)
        for record in events("SERVICE_START", station_id="B")
    ] == [("u1", 5.0), ("u2", 9.0)]

    assert [
        (record.patient_id, record.sim_time)
        for record in events("SERVICE_END", station_id="B")
    ] == [("u1", 8.0), ("u2", 12.0)]

    queue_entries = events("QUEUE_ENTRY")
    service_starts = events("SERVICE_START")
    service_ends = events("SERVICE_END")
    releases = events("RESOURCE_RELEASE")

    assert len(queue_entries) == 4
    assert len(service_starts) == 4
    assert len(service_ends) == 4
    assert len(releases) == 4

    def visit_key(record):
        return (record.patient_id, record.station_id, record.visit_id)

    # Match lifecycle events by composite visit identity.
    expected_visit_keys = {visit_key(record) for record in queue_entries}

    assert len(expected_visit_keys) == 4

    assert {(record.patient_id, record.station_id) for record in queue_entries} == {("u1", "A"), ("u1", "B"), ("u2", "A"), ("u2", "B")}

    for lifecycle_records in (service_starts, service_ends, releases):
        assert {visit_key(record) for record in lifecycle_records} == expected_visit_keys

    for key in expected_visit_keys:
        lifecycle = [
            record
            for record in records
            if record.event_type in (
                "QUEUE_ENTRY",
                "SERVICE_START",
                "SERVICE_END",
                "RESOURCE_RELEASE",
            )
            and visit_key(record) == key
        ]

        assert [record.event_type for record in lifecycle] == ["QUEUE_ENTRY", "SERVICE_START", "SERVICE_END", "RESOURCE_RELEASE"]

        entry, start, end, release = lifecycle

        assert entry.visit_id
        assert entry.resource_token_or_server_id

        assert all(
            record.resource_token_or_server_id == entry.resource_token_or_server_id
            for record in lifecycle
        )

        assert (
            entry.sequence_id < start.sequence_id < end.sequence_id < release.sequence_id
        )

        assert entry.sim_time <= start.sim_time

        assert end.sim_time - start.sim_time == (stations[entry.station_id].config.service_duration)

        assert release.sim_time == end.sim_time

    expected_durations = {"u1": (0.0, 7.0, 1.0), "u2": (4.0, 7.0, 1.0)}

    expected_station_waiting = {"u1": {"A": 0.0, "B": 0.0}, "u2": {"A": 4.0, "B": 0.0}}

    expected_travel_intervals = {
        "u1": [("A", 0.0, 0.0), ("B", 4.0, 5.0)],
        "u2": [("A", 0.0, 0.0), ("B", 8.0, 9.0)],
    }

    for patient_id in ("u1", "u2"):
        decisions = events("ROUTE_DECISION", patient_id=patient_id)

        assert [(record.recommended_station, record.chosen_station,) for record in decisions] == [("A", "A"), ("B", "B")]

        entries = events("QUEUE_ENTRY", patient_id=patient_id)

        starts = events("SERVICE_START", patient_id=patient_id)

        ends = events("SERVICE_END", patient_id=patient_id)

        travel_starts = events("TRAVEL_START", patient_id=patient_id)

        travel_ends = events("TRAVEL_END", patient_id=patient_id)

        assert len(entries) == 2
        assert len(starts) == 2
        assert len(ends) == 2
        assert len(travel_starts) == 2
        assert len(travel_ends) == 2

        waiting_by_station = {}

        for entry, start in zip(entries, starts, strict=True):
            assert visit_key(entry) == visit_key(start)

            waiting_by_station[entry.station_id] = (
                start.sim_time - entry.sim_time
            )

        assert waiting_by_station == (expected_station_waiting[patient_id])

        actual_travel_intervals = []

        for start, end in zip(travel_starts, travel_ends, strict=True):
            assert start.station_id == end.station_id

            actual_travel_intervals.append((start.station_id, start.sim_time, end.sim_time,))

        assert actual_travel_intervals == (expected_travel_intervals[patient_id])

        waiting_duration = sum(waiting_by_station.values())

        service_duration = sum(
            end.sim_time - start.sim_time
            for start, end in zip(starts, ends, strict=True)
        )

        travel_duration = sum(
            end.sim_time - start.sim_time
            for start, end in zip(travel_starts, travel_ends, strict=True)
        )

        assert (waiting_duration, service_duration, travel_duration) == expected_durations[patient_id]

        arrivals = events("ARRIVAL", patient_id=patient_id)

        departures = events("DEPARTURE", patient_id=patient_id)

        assert len(arrivals) == 1
        assert len(departures) == 1

        assert (
            departures[0].sim_time - arrivals[0].sim_time
        ) == (
            waiting_duration + service_duration + travel_duration
        )

    departures = events("DEPARTURE")

    assert [
        (record.patient_id, record.sim_time, record.prior_state, record.new_state)
        for record in departures
    ] == [("u1", 8.0, S.FINISHED, S.FINISHED), ("u2", 12.0, S.FINISHED, S.FINISHED)]

    for patient in patients.values():
        assert patient.state == S.FINISHED
        assert patient.location == "B"
        assert patient.completed_tests == {"A", "B"}
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    assert coordinator.pending_arrivals == []
    assert coordinator.pending_travels == []
    assert coordinator.next_event_time() is None

    expected_usage = {"A": (2, 1), "B": (2, 1), "C": (0, 0)}

    for station_id, station in stations.items():
        assert station.waiting == []
        assert station.active == {}

        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

        assert (station.release_count, station.peak_resource_count,) == expected_usage[station_id]

    assert not any(record.station_id == "C" for record in records)

    assert env.now == 12.0


def test_t06_abc_same_time_completion_arrivals_and_waiter():
    """T06: complete and release before admissions, then serve the old waiter."""
    env = simpy.Environment()
    stations = {
        station_id: AOnlyCoordinatedStation(env, station_id)
        for station_id in ("A", "B", "C")
    }
    log = EventLog(run_id="ENTRY_T06")
    coordinator = MultiStationCoordinator(env, stations, log)
    assert coordinator.station_ids == ("A", "B", "C")
    patients = {
        f"u{rank}": PatientAgent(f"u{rank}", rank, P1_CONFIG)
        for rank in range(1, 5)
    }
    # Register the t=4 arrivals in reverse rank order.
    for patient_id, at in (("u1", 0.0), ("u2", 1.0), ("u4", 4.0), ("u3", 4.0)):
        coordinator.register_arrival(ScheduledArrival(at, patients[patient_id]))
    assert env.now == 0.0 and log.records == []

    process = env.process(coordinator.run())
    env.run()
    records = log.records
    print("\n=== T06 RAW EVENT LOG (APPEND ORDER) ===")
    for record in records:
        print(repr(record))
    print("=== END T06 RAW EVENT LOG ===")

    assert process.triggered and process.ok
    assert env.now == 20.0
    assert len(records) == 76
    assert [r.sequence_id for r in records] == list(range(1, 77))
    assert all(r.run_id == "ENTRY_T06" for r in records)
    assert {r.patient_id for r in records} == set(patients)
    for before, after in zip(records, records[1:]):
        assert (before.sim_time, before.phase) <= (after.sim_time, after.phase)

    assert [(r.patient_id, r.sim_time) for r in records if r.event_type == "ARRIVAL"] == [
        ("u1", 0.0), ("u2", 1.0), ("u3", 4.0), ("u4", 4.0),
    ]

    # Filter in append order; do not sort simultaneous events.
    t4 = [r for r in records if r.sim_time == 4.0]
    assert [
        (r.phase, r.patient_id, r.event_type, r.station_id)
        for r in t4 if r.phase != 3
    ] == [
        (0, "u1", "SERVICE_END", "A"),
        (1, "u1", "RESOURCE_RELEASE", "A"),
        (2, "u3", "ARRIVAL", None),
        (2, "u4", "ARRIVAL", None),
        (4, "u3", "QUEUE_ENTRY", "A"),
        (4, "u4", "QUEUE_ENTRY", "A"),
        (5, "u2", "SERVICE_START", "A"),
    ]
    assert [
        (r.phase, r.patient_id, r.station_id)
        for r in t4 if r.event_type == "TRAVEL_END"
    ] == [(3, "u3", "A"), (3, "u4", "A")]

    for at, finished, continuing in (
        (8.0, "u1", "u2"), (12.0, "u2", "u3"), (16.0, "u3", "u4")
    ):
        assert [
            (r.patient_id, r.event_type, r.station_id)
            for r in records if r.sim_time == at and r.phase == 3
        ] == [
            (finished, "DEPARTURE", None),
            (continuing, "DECIDING", None),
            (continuing, "ROUTE_DECISION", None),
            (continuing, "TRAVEL_START", "B"),
        ]

    expected_visits = [
        ("u1", "A", 0.0, 0.0, 4.0),
        ("u2", "A", 1.0, 4.0, 8.0),
        ("u3", "A", 4.0, 8.0, 12.0),
        ("u4", "A", 4.0, 12.0, 16.0),
        ("u1", "B", 5.0, 5.0, 8.0),
        ("u2", "B", 9.0, 9.0, 12.0),
        ("u3", "B", 13.0, 13.0, 16.0),
        ("u4", "B", 17.0, 17.0, 20.0),
    ]
    visit_types = {"QUEUE_ENTRY", "SERVICE_START", "SERVICE_END", "RESOURCE_RELEASE"}
    queue_entries = [r for r in records if r.event_type == "QUEUE_ENTRY"]
    assert len(queue_entries) == 8
    assert len({(r.patient_id, r.station_id, r.visit_id) for r in queue_entries}) == 8
    for event_type in visit_types:
        assert sum(r.event_type == event_type for r in records) == 8

    for patient_id, station_id, queued_at, start, end in expected_visits:
        lifecycle = [
            r for r in records
            if r.patient_id == patient_id and r.station_id == station_id
            and r.event_type in visit_types
        ]
        assert [(r.sim_time, r.phase, r.event_type) for r in lifecycle] == [
            (queued_at, 4, "QUEUE_ENTRY"),
            (start, 5, "SERVICE_START"),
            (end, 0, "SERVICE_END"),
            (end, 1, "RESOURCE_RELEASE"),
        ], (patient_id, station_id)
        entry = lifecycle[0]
        assert entry.visit_id and entry.resource_token_or_server_id
        assert all(r.visit_id == entry.visit_id for r in lifecycle)
        assert all(
            r.resource_token_or_server_id == entry.resource_token_or_server_id
            for r in lifecycle
        )

    expected_travel = [
        ("u1", 0.0, 4.0, 5.0),
        ("u2", 1.0, 8.0, 9.0),
        ("u3", 4.0, 12.0, 13.0),
        ("u4", 4.0, 16.0, 17.0),
    ]
    for patient_id, arrival, a_end, b_arrival in expected_travel:
        patient_records = [r for r in records if r.patient_id == patient_id]
        assert len(patient_records) == 19
        assert [
            (r.recommended_station, r.chosen_station)
            for r in patient_records if r.event_type == "ROUTE_DECISION"
        ] == [("A", "A"), ("B", "B")]
        assert [
            (r.sim_time, r.event_type, r.station_id)
            for r in patient_records if r.event_type in {"TRAVEL_START", "TRAVEL_END"}
        ] == [
            (arrival, "TRAVEL_START", "A"),
            (arrival, "TRAVEL_END", "A"),
            (a_end, "TRAVEL_START", "B"),
            (b_arrival, "TRAVEL_END", "B"),
        ]

    assert [
        (r.patient_id, r.sim_time, r.phase, r.prior_state, r.new_state)
        for r in records if r.event_type == "DEPARTURE"
    ] == [
        ("u1", 8.0, 3, PatientState.FINISHED, PatientState.FINISHED),
        ("u2", 12.0, 3, PatientState.FINISHED, PatientState.FINISHED),
        ("u3", 16.0, 3, PatientState.FINISHED, PatientState.FINISHED),
        ("u4", 20.0, 3, PatientState.FINISHED, PatientState.FINISHED),
    ]
    for patient in patients.values():
        assert patient.state == PatientState.FINISHED
        assert patient.location == "B"
        assert patient.completed_tests == {"A", "B"}
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    assert coordinator.pending_arrivals == []
    assert coordinator.pending_travels == []
    assert coordinator.next_event_time() is None
    expected_usage = {"A": (4, 1), "B": (4, 1), "C": (0, 0)}
    for station_id, station in stations.items():
        assert station.waiting == [] and station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == [] and station.resource.queue == []
        assert (station.release_count, station.peak_resource_count) == expected_usage[
            station_id
        ]
    assert not any(r.station_id == "C" for r in records)


def _make_t08_abc_fixture(run_id):
    env = simpy.Environment()
    stations = {
        name: AOnlyCoordinatedStation(env, name)
        for name in ("A", "B", "C")
    }
    log = EventLog(run_id=run_id)
    coordinator = MultiStationCoordinator(env, stations, log)
    assert coordinator.station_ids == ("A", "B", "C")
    # Test-only package; the standard P1 package is unchanged.
    a_only = PackageConfig(frozenset({"A"}), ("A",), frozenset())
    patients = {
        "u1": PatientAgent("u1", 1, a_only),
        "u2": PatientAgent("u2", 2, a_only),
    }
    coordinator.register_arrival(ScheduledArrival(0.0, patients["u1"]))
    coordinator.register_arrival(ScheduledArrival(1.0, patients["u2"]))
    assert env.now == 0.0 and log.records == []
    return env, coordinator, stations, patients, log


def _assert_t08_trace_and_drain(env, coordinator, stations, patients, log):
    records = log.records
    print(f"\n=== T08 RAW EVENT LOG ({log.run_id}, APPEND ORDER) ===")
    for record in records:
        print(repr(record))
    print("=== END T08 RAW EVENT LOG ===")

    assert len(records) == 22
    assert [r.sequence_id for r in records] == list(range(1, 23))
    assert all(r.run_id == log.run_id for r in records)
    assert {r.patient_id for r in records} == {"u1", "u2"}
    for before, after in zip(records, records[1:]):
        assert (before.sim_time, before.phase) <= (after.sim_time, after.phase)

    timeline_types = {
        "ARRIVAL", "QUEUE_ENTRY", "SERVICE_START",
        "SERVICE_END", "RESOURCE_RELEASE", "DEPARTURE",
    }
    assert [
        (r.sim_time, r.phase, r.patient_id, r.event_type)
        for r in records if r.event_type in timeline_types
    ] == [
        (0.0, 2, "u1", "ARRIVAL"),
        (0.0, 4, "u1", "QUEUE_ENTRY"),
        (0.0, 5, "u1", "SERVICE_START"),
        (1.0, 2, "u2", "ARRIVAL"),
        (1.0, 4, "u2", "QUEUE_ENTRY"),
        (4.0, 0, "u1", "SERVICE_END"),
        (4.0, 1, "u1", "RESOURCE_RELEASE"),
        (4.0, 3, "u1", "DEPARTURE"),
        (4.0, 5, "u2", "SERVICE_START"),
        (8.0, 0, "u2", "SERVICE_END"),
        (8.0, 1, "u2", "RESOURCE_RELEASE"),
        (8.0, 3, "u2", "DEPARTURE"),
    ]

    visit_types = {"QUEUE_ENTRY", "SERVICE_START", "SERVICE_END", "RESOURCE_RELEASE"}
    entries = [r for r in records if r.event_type == "QUEUE_ENTRY"]
    assert len({(r.patient_id, r.station_id, r.visit_id) for r in entries}) == 2
    for patient_id, arrival, start, end, wait in (
        ("u1", 0.0, 0.0, 4.0, 0.0),
        ("u2", 1.0, 4.0, 8.0, 3.0),
    ):
        patient_records = [r for r in records if r.patient_id == patient_id]
        assert len(patient_records) == 11
        assert [
            (r.recommended_station, r.chosen_station)
            for r in patient_records if r.event_type == "ROUTE_DECISION"
        ] == [("A", "A")]
        assert [
            (r.sim_time, r.event_type, r.station_id)
            for r in patient_records if r.event_type in {"TRAVEL_START", "TRAVEL_END"}
        ] == [(arrival, "TRAVEL_START", "A"), (arrival, "TRAVEL_END", "A")]

        lifecycle = [r for r in patient_records if r.event_type in visit_types]
        assert [(r.sim_time, r.phase, r.event_type, r.station_id) for r in lifecycle] == [
            (arrival, 4, "QUEUE_ENTRY", "A"),
            (start, 5, "SERVICE_START", "A"),
            (end, 0, "SERVICE_END", "A"),
            (end, 1, "RESOURCE_RELEASE", "A"),
        ]
        entry = lifecycle[0]
        assert entry.visit_id and entry.resource_token_or_server_id
        assert all(r.visit_id == entry.visit_id for r in lifecycle)
        assert all(
            r.resource_token_or_server_id == entry.resource_token_or_server_id
            for r in lifecycle
        )
        assert lifecycle[1].sim_time - entry.sim_time == wait
        assert lifecycle[2].sim_time - lifecycle[1].sim_time == 4.0

    for patient in patients.values():
        assert patient.state == PatientState.FINISHED
        assert patient.location == "A"
        assert patient.completed_tests == {"A"}
        assert patient.active_visit_id is None
        assert patient.active_station_id is None
    assert env.now == 8.0
    assert coordinator.pending_arrivals == []
    assert coordinator.pending_travels == []
    assert coordinator.next_event_time() is None
    expected_usage = {"A": (2, 1), "B": (0, 0), "C": (0, 0)}
    for name, station in stations.items():
        assert station.waiting == [] and station.active == {}
        assert station.resource.count == 0
        assert station.resource.users == [] and station.resource.queue == []
        assert (station.release_count, station.peak_resource_count) == expected_usage[name]
    assert not any(r.station_id in {"B", "C"} for r in records)


def test_t08_abc_release_serves_the_existing_waiter():
    """End-to-end T08 through the packaged run() entry."""
    env, coordinator, stations, patients, log = _make_t08_abc_fixture("ENTRY_T08")
    process = env.process(coordinator.run())
    env.run()
    assert process.triggered and process.ok
    _assert_t08_trace_and_drain(env, coordinator, stations, patients, log)


def test_t08_stale_release_preserves_the_current_owner():
    """Component negative case alongside the formal entry; no manual phase driving."""
    env, coordinator, stations, patients, log = _make_t08_abc_fixture("ENTRY_T08_STALE")
    station = stations["A"]
    u1, u2 = patients["u1"], patients["u2"]
    process = env.process(coordinator.run())

    # Pause between domain event times to retain u1's old ownership handle.
    env.run(until=3.0)
    (old_visit,) = station.active.values()
    assert old_visit.patient is u1
    assert old_visit.ends_at == 4.0
    assert u2.state == PatientState.WAITING

    env.run(until=5.0)
    (current_visit,) = station.active.values()
    assert current_visit.patient is u2
    assert current_visit.ends_at == 8.0
    assert u2.state == PatientState.IN_SERVICE
    assert station.release_count == 1
    current_id, current_request = current_visit.visit_id, current_visit.request
    assert station.resource.users == [current_request]
    before_log = list(log.records)

    def patient_snapshot(patient):
        return (
            patient.state, patient.location, frozenset(patient.completed_tests),
            patient.active_visit_id, patient.active_station_id,
        )

    before_patients = (patient_snapshot(u1), patient_snapshot(u2))
    with pytest.raises(RuntimeError, match="Visit was not active at release"):
        station.release_services([old_visit], log)

    assert env.now == 5.0
    assert tuple(station.active) == (current_id,)
    assert station.active[current_id] is current_visit
    assert current_visit.patient is u2 and current_visit.visit_id == current_id
    assert current_visit.request is current_request and current_visit.ends_at == 8.0
    assert station.resource.users == [current_request]
    assert station.resource.count == 1 and station.resource.queue == []
    assert station.waiting == []
    assert station.release_count == 1 and station.peak_resource_count == 1
    assert (patient_snapshot(u1), patient_snapshot(u2)) == before_patients
    assert log.records == before_log

    env.run()
    assert process.triggered and process.ok
    _assert_t08_trace_and_drain(env, coordinator, stations, patients, log)


def test_t10_abc_reproduces_raw_trace_across_fresh_runs():
    """T10: two fresh T06 runs produce identical normalized ordered records."""
    traces = []
    instances = []
    for run_id in ("ENTRY_T10_FIRST", "ENTRY_T10_SECOND"):
        env = simpy.Environment()
        stations = {
            name: AOnlyCoordinatedStation(env, name)
            for name in ("A", "B", "C")
        }
        log = EventLog(run_id=run_id)
        coordinator = MultiStationCoordinator(env, stations, log)
        assert coordinator.station_ids == ("A", "B", "C")
        patients = {
            f"u{rank}": PatientAgent(f"u{rank}", rank, P1_CONFIG)
            for rank in range(1, 5)
        }
        assert all(patient.completed_tests == set() for patient in patients.values())
        for patient_id, at in (("u1", 0.0), ("u2", 1.0), ("u4", 4.0), ("u3", 4.0)):
            coordinator.register_arrival(ScheduledArrival(at, patients[patient_id]))
        assert env.now == 0.0 and log.records == []

        process = env.process(coordinator.run())
        env.run()
        records = log.records
        print(f"\n=== T10 RAW EVENT LOG ({run_id}, APPEND ORDER) ===")
        for record in records:
            print(repr(record))
        print("=== END T10 RAW EVENT LOG ===")

        assert process.triggered and process.ok
        assert env.now == 20.0
        assert len(records) == 76
        assert [r.sequence_id for r in records] == list(range(1, 77))
        assert all(r.run_id == run_id for r in records)
        assert {r.patient_id for r in records} == set(patients)
        for before, after in zip(records, records[1:]):
            assert (before.sim_time, before.phase) <= (after.sim_time, after.phase)

        assert [
            (r.patient_id, r.sim_time)
            for r in records if r.event_type == "DEPARTURE"
        ] == [("u1", 8.0), ("u2", 12.0), ("u3", 16.0), ("u4", 20.0)]
        assert [
            (r.phase, r.patient_id, r.event_type, r.station_id)
            for r in records if r.sim_time == 4.0 and r.phase != 3
        ] == [
            (0, "u1", "SERVICE_END", "A"),
            (1, "u1", "RESOURCE_RELEASE", "A"),
            (2, "u3", "ARRIVAL", None),
            (2, "u4", "ARRIVAL", None),
            (4, "u3", "QUEUE_ENTRY", "A"),
            (4, "u4", "QUEUE_ENTRY", "A"),
            (5, "u2", "SERVICE_START", "A"),
        ]
        for patient in patients.values():
            assert patient.state == PatientState.FINISHED
            assert patient.location == "B"
            assert patient.completed_tests == {"A", "B"}
            assert patient.active_visit_id is None
            assert patient.active_station_id is None
        assert coordinator.pending_arrivals == []
        assert coordinator.pending_travels == []
        assert coordinator.next_event_time() is None
        expected_usage = {"A": (4, 1), "B": (4, 1), "C": (0, 0)}
        for name, station in stations.items():
            assert station.waiting == [] and station.active == {}
            assert station.resource.count == 0
            assert station.resource.users == [] and station.resource.queue == []
            assert (station.release_count, station.peak_resource_count) == expected_usage[
                name
            ]
        assert not any(r.station_id == "C" for r in records)

        # Keep every domain field and its order; remove only the run identifier.
        traces.append([replace(record, run_id="") for record in records])
        assert all(record.run_id == run_id for record in records)
        instances.append((env, coordinator, stations, patients, log))

    first_env, first_coordinator, first_stations, first_patients, first_log = instances[0]
    second_env, second_coordinator, second_stations, second_patients, second_log = instances[1]
    assert first_env is not second_env
    assert first_coordinator is not second_coordinator
    assert first_log is not second_log and first_log.records is not second_log.records
    for name in ("A", "B", "C"):
        assert first_stations[name] is not second_stations[name]
        assert first_stations[name].resource is not second_stations[name].resource
    for patient_id in first_patients:
        assert first_patients[patient_id] is not second_patients[patient_id]
    assert traces[0] == traces[1]
