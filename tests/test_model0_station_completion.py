"""Component regressions for exactly-once service completion."""

import pytest
import simpy

from health_exam_mas.model0 import EventLog, PackageConfig, PatientAgent, PatientState
from health_exam_mas.model0_station import AOnlyCoordinatedStation


def _ready_patient(patient_id, rank, station_id):
    package = PackageConfig(frozenset({station_id}), (station_id,), frozenset())
    return PatientAgent(
        patient_id, rank, package,
        state=PatientState.TRAVELLING, location=station_id,
    )


@pytest.mark.parametrize(
    ("station_id", "patient_count", "duration"),
    [("A", 1, 4.0), ("C", 2, 5.0)],
    ids=["single_server", "parallel_servers"],
)
def test_duplicate_close_rejects_without_mutating_the_completed_batch(
    station_id, patient_count, duration
):
    env = simpy.Environment()
    station = AOnlyCoordinatedStation(env, station_id)
    log = EventLog("completion-guard")
    patients = [
        _ready_patient(f"u{rank}", rank, station_id)
        for rank in range(1, patient_count + 1)
    ]
    for patient in patients:
        station.enqueue(patient, log)
    station.start_available(log)
    env.run(until=duration)

    due = station.close_services(log)
    assert len(due) == patient_count
    assert [r.patient_id for r in log.records if r.event_type == "SERVICE_END"] == [
        patient.patient_id for patient in patients
    ]
    before_log = list(log.records)
    before_active = dict(station.active)
    before_users = list(station.resource.users)
    before_patients = [
        (patient.state, frozenset(patient.completed_tests),
         patient.active_visit_id, patient.active_station_id)
        for patient in patients
    ]

    for _ in range(2):
        with pytest.raises(RuntimeError, match="already recorded"):
            station.close_services(log)
        assert env.now == duration
        assert log.records == before_log
        assert tuple(station.active) == tuple(before_active)
        assert all(station.active[key] is visit for key, visit in before_active.items())
        assert station.resource.users == before_users
        assert station.resource.count == patient_count
        assert station.resource.queue == [] and station.waiting == []
        assert station.release_count == 0
        assert [
            (patient.state, frozenset(patient.completed_tests),
             patient.active_visit_id, patient.active_station_id)
            for patient in patients
        ] == before_patients

    assert station.release_services(due, log) == patients
    assert station.release_count == patient_count
    assert station.active == {} and station.resource.count == 0
    assert station.resource.users == [] and station.resource.queue == []
    assert sum(r.event_type == "SERVICE_END" for r in log.records) == patient_count
    assert sum(r.event_type == "RESOURCE_RELEASE" for r in log.records) == patient_count
    assert all(patient.state == PatientState.FINISHED for patient in patients)
    assert all(patient.completed_tests == {station_id} for patient in patients)


def test_mixed_due_batch_rejects_before_logging_other_completions():
    env = simpy.Environment()
    station = AOnlyCoordinatedStation(env, "C")
    log = EventLog("completion-batch-guard")
    patients = [_ready_patient(f"u{rank}", rank, "C") for rank in (1, 2)]
    for patient in patients:
        station.enqueue(patient, log)
    station.start_available(log)
    env.run(until=5.0)
    visits = sorted(station.active.values(), key=lambda visit: visit.patient.patient_rank)

    # Inject a partial-completion state to check rejection of the whole batch.
    visits[0].completion_recorded = False
    visits[1].completion_recorded = True
    before_log = list(log.records)
    before_users = list(station.resource.users)
    with pytest.raises(RuntimeError, match="already recorded"):
        station.close_services(log)

    assert log.records == before_log
    assert [visit.completion_recorded for visit in visits] == [False, True]
    assert all(station.active[visit.visit_id] is visit for visit in visits)
    assert station.resource.users == before_users and station.resource.count == 2
    assert station.waiting == [] and station.resource.queue == []
    assert station.release_count == 0
    assert all(patient.state == PatientState.IN_SERVICE for patient in patients)
    assert all(patient.completed_tests == set() for patient in patients)


def test_completion_guard_does_not_block_the_next_visit():
    env = simpy.Environment()
    station = AOnlyCoordinatedStation(env, "A")
    log = EventLog("completion-handoff")
    u1 = _ready_patient("u1", 1, "A")
    u2 = _ready_patient("u2", 2, "A")
    station.enqueue(u1, log)
    station.start_available(log)
    env.run(until=1.0)
    station.enqueue(u2, log)

    env.run(until=4.0)
    due = station.close_services(log)
    assert [visit.patient for visit in due] == [u1]
    assert station.release_services(due, log) == [u1]
    station.start_available(log)
    before_log = list(log.records)
    assert station.close_services(log) == []
    assert log.records == before_log

    env.run(until=8.0)
    due = station.close_services(log)
    assert [visit.patient for visit in due] == [u2]
    assert station.release_services(due, log) == [u2]
    assert [(r.patient_id, r.sim_time) for r in log.records
            if r.event_type == "SERVICE_START"] == [("u1", 0.0), ("u2", 4.0)]
    assert [(r.patient_id, r.sim_time) for r in log.records
            if r.event_type == "SERVICE_END"] == [("u1", 4.0), ("u2", 8.0)]
    assert station.release_count == 2 and station.peak_resource_count == 1
    assert station.active == {} and station.waiting == []
    assert station.resource.count == 0
    assert station.resource.users == [] and station.resource.queue == []
    for patient in (u1, u2):
        assert patient.state == PatientState.FINISHED
        assert patient.completed_tests == {"A"}
        assert patient.active_visit_id is None and patient.active_station_id is None
