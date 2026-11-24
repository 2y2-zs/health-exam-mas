"""Component regressions for release timing and completion prerequisites."""

from dataclasses import replace

import pytest
import simpy

from health_exam_mas.model0 import EventLog, PackageConfig, PatientAgent, PatientState
from health_exam_mas.model0_station import AOnlyCoordinatedStation


def _patient(patient_id, rank, station_id):
    package = PackageConfig(frozenset({station_id}), (station_id,), frozenset())
    return PatientAgent(
        patient_id, rank, package,
        state=PatientState.TRAVELLING, location=station_id,
    )


def _started_station(station_id="A", count=1):
    env = simpy.Environment()
    station = AOnlyCoordinatedStation(env, station_id)
    log = EventLog("release-guard")
    patients = [_patient(f"u{rank}", rank, station_id) for rank in range(1, count + 1)]
    for patient in patients:
        station.enqueue(patient, log)
    station.start_available(log)
    return env, station, log, patients


def _snapshot(station, log, patients):
    return {
        "time": station.env.now,
        "records": list(log.records),
        "active": dict(station.active),
        "visit_fields": {
            key: (visit.patient.patient_id, visit.visit_id, visit.request,
                  visit.ends_at, visit.completion_recorded)
            for key, visit in station.active.items()
        },
        "waiting": list(station.waiting),
        "users": list(station.resource.users),
        "resource_queue": list(station.resource.queue),
        "resource_count": station.resource.count,
        "counts": (station.release_count, station.peak_resource_count),
        "patients": [
            (p.state, p.location, frozenset(p.completed_tests),
             p.active_visit_id, p.active_station_id)
            for p in patients
        ],
    }


def _assert_unchanged(station, log, patients, before):
    assert _snapshot(station, log, patients) == before
    assert all(station.active[key] is visit for key, visit in before["active"].items())


def _assert_released(station, patients):
    assert station.active == {} and station.waiting == []
    assert station.resource.count == 0
    assert station.resource.users == [] and station.resource.queue == []
    assert station.release_count == len(patients)
    for patient in patients:
        assert patient.state == PatientState.FINISHED
        assert patient.completed_tests == {station.station_id}
        assert patient.active_visit_id is None and patient.active_station_id is None


def test_release_before_service_end_is_rejected_without_mutation():
    env, station, log, patients = _started_station()
    env.run(until=2.0)
    (visit,) = station.active.values()
    before = _snapshot(station, log, patients)
    with pytest.raises(RuntimeError, match="not due"):
        station.release_services([visit], log)
    _assert_unchanged(station, log, patients, before)

    env.run(until=4.0)
    due = station.close_services(log)
    assert station.release_services(due, log) == patients
    _assert_released(station, patients)


def test_release_at_end_requires_a_recorded_completion():
    env, station, log, patients = _started_station()
    env.run(until=4.0)
    (visit,) = station.active.values()
    before = _snapshot(station, log, patients)
    with pytest.raises(RuntimeError, match="not recorded"):
        station.release_services([visit], log)
    _assert_unchanged(station, log, patients, before)

    due = station.close_services(log)
    assert station.release_services(due, log) == patients
    _assert_released(station, patients)


def test_release_after_the_completion_timestamp_is_rejected():
    env, station, log, patients = _started_station()
    env.run(until=4.0)
    due = station.close_services(log)
    env.run(until=5.0)
    before = _snapshot(station, log, patients)
    with pytest.raises(RuntimeError, match="not due"):
        station.release_services(due, log)
    _assert_unchanged(station, log, patients, before)


def test_mixed_release_times_reject_before_releasing_any_patient():
    env, station, log, patients = _started_station("C")
    env.run(until=1.0)
    patients.append(_patient("u2", 2, "C"))
    station.enqueue(patients[1], log)
    station.start_available(log)
    env.run(until=5.0)
    due = station.close_services(log)
    assert [visit.patient for visit in due] == [patients[0]]
    later = next(visit for visit in station.active.values() if visit.patient is patients[1])
    before = _snapshot(station, log, patients)
    with pytest.raises(RuntimeError, match="not due"):
        station.release_services([due[0], later], log)
    _assert_unchanged(station, log, patients, before)

    assert station.release_services(due, log) == [patients[0]]
    env.run(until=6.0)
    assert station.release_services(station.close_services(log), log) == [patients[1]]
    _assert_released(station, patients)


def test_mixed_completion_flags_reject_before_releasing_any_patient():
    env, station, log, patients = _started_station("C", count=2)
    env.run(until=5.0)
    due = station.close_services(log)
    # Inject a missing completion flag after the valid Phase 0 batch.
    due[1].completion_recorded = False
    before = _snapshot(station, log, patients)
    with pytest.raises(RuntimeError, match="not recorded"):
        station.release_services(due, log)
    _assert_unchanged(station, log, patients, before)

    due[1].completion_recorded = True
    assert station.release_services(due, log) == patients
    _assert_released(station, patients)


@pytest.mark.parametrize(
    ("invalid_kind", "message"),
    [("duplicate", "Duplicate visit"), ("foreign", "not active at release")],
)
def test_existing_ownership_errors_precede_timing_checks(invalid_kind, message):
    env, station, log, patients = _started_station()
    env.run(until=2.0)
    (visit,) = station.active.values()
    invalid = [visit, visit] if invalid_kind == "duplicate" else [replace(visit)]
    before = _snapshot(station, log, patients)
    with pytest.raises(RuntimeError, match=message):
        station.release_services(invalid, log)
    _assert_unchanged(station, log, patients, before)
