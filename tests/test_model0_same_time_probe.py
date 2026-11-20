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


A_ONLY_PACKAGE = PackageConfig(
    required_tests=frozenset({"A"}),
    fixed_route=("A",),
    hard_precedence=frozenset(),
)


RELEVANT_EVENTS = {"QUEUE_ENTRY", "SERVICE_START", "SERVICE_END"}


def _run_scenario(start_order: tuple[str, str], run_id: str):
    env = simpy.Environment()
    stations = {
        "A": StationAgent(env, "A", MODEL0_STATIONS["A"]),
    }
    event_log = EventLog(run_id=run_id)
    patients = {
        "u1": PatientAgent("u1", patient_rank=1, package=A_ONLY_PACKAGE),
        "u2": PatientAgent("u2", patient_rank=2, package=A_ONLY_PACKAGE),
    }

    assert stations["A"].resource.capacity == 1
    assert stations["A"].config.service_duration == 4.0

    for patient_id in start_order:
        env.process(patient_process(env, patients[patient_id], stations, event_log))
    env.run()

    return env, stations, event_log, patients


def _only(records, patient_id: str, event_type: str):
    matches = [
        record
        for record in records
        if record.patient_id == patient_id
        and record.event_type == event_type
        and (record.station_id == "A" or event_type == "DEPARTURE")
    ]
    assert len(matches) == 1, (patient_id, event_type, matches)
    return matches[0]


def test_same_time_a_requests_follow_patient_rank_regardless_of_start_order():
    scenarios = (
        ("scenario 1", ("u1", "u2")),
        ("scenario 2", ("u2", "u1")),
    )
    outcomes = []

    for label, start_order in scenarios:
        env, stations, event_log, patients = _run_scenario(
            start_order, run_id=f"SAME_TIME_PROBE_{label[-1]}"
        )
        raw_events = [
            record
            for record in event_log.records
            if record.station_id == "A"
            and record.event_type in RELEVANT_EVENTS
        ]

        print(f"\n{label}: process start order = {' -> '.join(start_order)}")
        for record in raw_events:
            print(
                f"  seq={record.sequence_id} "
                f"patient={record.patient_id} "
                f"event={record.event_type} "
                f"time={record.sim_time:g}"
            )

        outcomes.append((label, env, stations, event_log, patients, raw_events))

    expected_intervals = {
        "u1": (0.0, 4.0),
        "u2": (4.0, 8.0),
    }
    expected_departures = {"u1": 4.0, "u2": 8.0}

    for label, env, stations, event_log, patients, raw_events in outcomes:
        records = event_log.records

        actual_start_order = [
            record.patient_id
            for record in raw_events
            if record.event_type == "SERVICE_START"
        ]
        assert actual_start_order == ["u1", "u2"], (
            f"{label}: same-time tie must follow patient_rank, "
            f"not process creation order; actual={actual_start_order!r}"
        )

        for patient_id, (expected_start, expected_end) in expected_intervals.items():
            entry = _only(records, patient_id, "QUEUE_ENTRY")
            start = _only(records, patient_id, "SERVICE_START")
            end = _only(records, patient_id, "SERVICE_END")
            departure = _only(records, patient_id, "DEPARTURE")

            assert entry.sim_time == 0.0, (label, patient_id, "QUEUE_ENTRY")
            assert (start.sim_time, end.sim_time) == (
                expected_start,
                expected_end,
            ), (label, patient_id, "service interval")
            assert departure.sim_time == expected_departures[patient_id], (
                label, patient_id, "DEPARTURE"
            )
            assert entry.sequence_id < start.sequence_id < end.sequence_id

        assert env.now == 8.0, label
        for patient in patients.values():
            assert patient.state == PatientState.FINISHED, label
            assert patient.location == "A", label
            assert patient.completed_tests == {"A"}, label
            assert patient.active_visit_id is None, label
            assert patient.active_station_id is None, label

        resource = stations["A"].resource
        assert resource.count == 0, label
        assert resource.users == [], label
        assert resource.queue == [], label
