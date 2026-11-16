
"""T06: simultaneous completion, arrivals, and an existing FCFS queue.

This test intentionally checks both the fixed hand-derived timeline and the
original EventLog append order at t=4. No event log sorting is permitted.
"""

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


def test_t06_simultaneous_completion_arrivals_and_waiting_queue():
    env = simpy.Environment()

    stations = {
        station_id: StationAgent(env, station_id, config)
        for station_id, config in MODEL0_STATIONS.items()
    }

    event_log = EventLog(run_id="T06")

    patients = {
        patient_id: PatientAgent(
            patient_id=patient_id,
            patient_rank=rank,
            package=P1_CONFIG,
        )
        for rank, patient_id in enumerate(
            ("u1", "u2", "u3", "u4"),
            start=1,
        )
    }

    def start_patient_at(patient_id: str, arrival_time: float):
        yield env.timeout(arrival_time)
        yield env.process(
            patient_process(
                env,
                patients[patient_id],
                stations,
                event_log,
            )
        )

    # Start u1 first. u3 is scheduled before u4.
    env.process(
        patient_process(env, patients["u1"], stations, event_log)
    )
    env.process(start_patient_at("u2", 1.0))
    env.process(start_patient_at("u3", 4.0))
    env.process(start_patient_at("u4", 4.0))

    env.run()

    # Preserve the original append order.
    records = event_log.records

    def matching(
        patient_id: str,
        event_type: str,
        station_id: str | None = None,
    ):
        return [
            record
            for record in records
            if record.patient_id == patient_id
            and record.event_type == event_type
            and (
                station_id is None
                or record.station_id == station_id
            )
        ]

    def only(
        patient_id: str,
        event_type: str,
        station_id: str | None = None,
    ):
        found = matching(patient_id, event_type, station_id)
        assert len(found) == 1, (
            patient_id,
            event_type,
            station_id,
            found,
        )
        return found[0]

    # Fixed manual expectations.
    expected_arrivals = {
        "u1": 0.0,
        "u2": 1.0,
        "u3": 4.0,
        "u4": 4.0,
    }

    expected_a_intervals = {
        "u1": (0.0, 4.0),
        "u2": (4.0, 8.0),
        "u3": (8.0, 12.0),
        "u4": (12.0, 16.0),
    }

    expected_b_intervals = {
        "u1": (5.0, 8.0),
        "u2": (9.0, 12.0),
        "u3": (13.0, 16.0),
        "u4": (17.0, 20.0),
    }

    expected_departures = {
        "u1": 8.0,
        "u2": 12.0,
        "u3": 16.0,
        "u4": 20.0,
    }

    # Check arrivals.
    for patient_id, arrival_time in expected_arrivals.items():
        assert only(
            patient_id,
            "ARRIVAL",
        ).sim_time == arrival_time

    # Check all service intervals.
    for station_id, intervals in (
        ("A", expected_a_intervals),
        ("B", expected_b_intervals),
    ):
        for patient_id, expected_interval in intervals.items():
            start = only(
                patient_id,
                "SERVICE_START",
                station_id,
            )
            end = only(
                patient_id,
                "SERVICE_END",
                station_id,
            )

            assert (
                start.sim_time,
                end.sim_time,
            ) == expected_interval

            assert start.visit_id == end.visit_id
            assert start.sequence_id < end.sequence_id

        # Service intervals must not overlap.
        ordered_intervals = [
            intervals[p]
            for p in ("u1", "u2", "u3", "u4")
        ]

        assert all(
            start < end
            for start, end in ordered_intervals
        )

        assert all(
            earlier_end <= later_start
            for (_, earlier_end), (later_start, _) in zip(
                ordered_intervals,
                ordered_intervals[1:],
            )
        )

    # Check A queue entry order.
    a_entries = [
        record
        for record in records
        if record.event_type == "QUEUE_ENTRY"
        and record.station_id == "A"
    ]

    assert [
        (r.patient_id, r.sim_time)
        for r in a_entries
    ] == [
        ("u1", 0.0),
        ("u2", 1.0),
        ("u3", 4.0),
        ("u4", 4.0),
    ]

    # Check A service start order.
    a_starts = [
        record
        for record in records
        if record.event_type == "SERVICE_START"
        and record.station_id == "A"
    ]

    assert [
        (r.patient_id, r.sim_time)
        for r in a_starts
    ] == [
        ("u1", 0.0),
        ("u2", 4.0),
        ("u3", 8.0),
        ("u4", 12.0),
    ]

    # u2 must not be overtaken by u3/u4.
    assert only(
        "u2",
        "QUEUE_ENTRY",
        "A",
    ).sequence_id < only(
        "u3",
        "QUEUE_ENTRY",
        "A",
    ).sequence_id

    assert only(
        "u2",
        "SERVICE_START",
        "A",
    ).sequence_id < only(
        "u3",
        "SERVICE_START",
        "A",
    ).sequence_id

    # Check waiting times at A.
    expected_a_waits = {
        "u1": 0.0,
        "u2": 3.0,
        "u3": 4.0,
        "u4": 8.0,
    }

    for patient_id, expected_wait in expected_a_waits.items():
        entry = only(patient_id, "QUEUE_ENTRY", "A")
        start = only(patient_id, "SERVICE_START", "A")

        assert start.sim_time - entry.sim_time == expected_wait
        assert entry.visit_id == start.visit_id

    # Check zero waiting times at B.
    for patient_id, (start_time, _) in expected_b_intervals.items():
        entry = only(patient_id, "QUEUE_ENTRY", "B")
        start = only(patient_id, "SERVICE_START", "B")

        assert entry.sim_time == start_time
        assert start.sim_time - entry.sim_time == 0.0

    # Check departure times.
    departures = [
        r for r in records
        if r.event_type == "DEPARTURE"
    ]

    assert len(departures) == 4

    for patient_id, expected_time in expected_departures.items():
        assert only(
            patient_id,
            "DEPARTURE",
        ).sim_time == expected_time

    # Check final simulation time.
    assert env.now == 20.0

    # Check patient cleanup.
    for patient in patients.values():
        assert patient.state == PatientState.FINISHED
        assert patient.location == "B"
        assert patient.completed_tests == {"A", "B"}
        assert patient.active_visit_id is None
        assert patient.active_station_id is None

    # Check resource cleanup.
    assert set(stations) == {"A", "B", "C"}

    for station in stations.values():
        assert station.resource.count == 0
        assert station.resource.users == []
        assert station.resource.queue == []

    # Check log sequence and monotonic time.
    assert [
        r.sequence_id for r in records
    ] == list(range(1, len(records) + 1))

    assert all(
        a.sim_time <= b.sim_time
        for a, b in zip(records, records[1:])
    )

    # Strict t=4 event-order assertion.
    # Do not sort the raw log.
    expected_t4_order = [
        ("u1", "SERVICE_END", "A"),
        ("u1", "RESOURCE_RELEASE", "A"),
        ("u3", "ARRIVAL", None),
        ("u4", "ARRIVAL", None),
        ("u3", "QUEUE_ENTRY", "A"),
        ("u4", "QUEUE_ENTRY", "A"),
        ("u2", "SERVICE_START", "A"),
    ]

    wanted = set(expected_t4_order)

    actual_t4_order = [
        (r.patient_id, r.event_type, r.station_id)
        for r in records
        if r.sim_time == 4.0
        and (
            r.patient_id,
            r.event_type,
            r.station_id,
        ) in wanted
    ]

    # Preserve complete original t=4 log for diagnosis.
    raw_t4_log = "\n".join(
        f"seq={r.sequence_id} "
        f"t={r.sim_time:g} "
        f"patient={r.patient_id} "
        f"event={r.event_type} "
        f"station={r.station_id}"
        for r in records
        if r.sim_time == 4.0
    )

    assert actual_t4_order == expected_t4_order, (
        "T06 t=4 raw event order differs "
        "from the documented order.\n"
        f"Expected relevant order: {expected_t4_order!r}\n"
        f"Actual relevant order: {actual_t4_order!r}\n"
        f"Original unsorted t=4 log:\n{raw_t4_log}"
    )
