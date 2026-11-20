import pytest
import simpy

from health_exam_mas.model0 import EventLog, P1_CONFIG, PackageConfig, PatientAgent
from health_exam_mas.model0_coordinator import MultiStationCoordinator, ScheduledArrival
from health_exam_mas.model0_station import AOnlyCoordinatedStation


def make_coordinator(station_ids=("A", "B", "C")):
    env = simpy.Environment()
    stations = {name: AOnlyCoordinatedStation(env, name) for name in station_ids}
    log = EventLog("coordinated-arrivals")
    return env, MultiStationCoordinator(env, stations, log), log


def test_mixed_travel_sources_join_the_same_b_queue_by_rank():
    env, coordinator, log = make_coordinator()
    p2 = PackageConfig(frozenset({"B", "C"}), ("B", "C"), frozenset())
    coordinator.register_arrival(ScheduledArrival(0, PatientAgent("u2", 2, P1_CONFIG)))
    coordinator.register_arrival(ScheduledArrival(5, PatientAgent("u1", 1, p2)))

    env.process(coordinator.run())
    env.run()

    b_events = [event for event in log.records if event.station_id == "B"]
    assert [
        (event.phase, event.event_type, event.patient_id)
        for event in b_events
        if event.sim_time == 5
        and event.event_type in {"TRAVEL_END", "QUEUE_ENTRY", "SERVICE_START"}
    ] == [
        (3, "TRAVEL_END", "u2"),
        (3, "TRAVEL_END", "u1"),
        (4, "QUEUE_ENTRY", "u1"),
        (4, "QUEUE_ENTRY", "u2"),
        (5, "SERVICE_START", "u1"),
    ]
    assert [
        (event.sim_time, event.patient_id)
        for event in b_events if event.event_type == "SERVICE_START"
    ] == [(5, "u1"), (8, "u2")]


@pytest.mark.parametrize("at", [float("nan"), float("inf"), float("-inf"), -1.0])
def test_invalid_arrival_time_does_not_consume_patient_id(at):
    env, coordinator, log = make_coordinator()
    patient = PatientAgent("u1", 1, P1_CONFIG)
    with pytest.raises(ValueError, match="finite and nonnegative"):
        coordinator.register_arrival(ScheduledArrival(at, patient))

    assert coordinator.pending_arrivals == []
    assert env.now == 0 and log.records == []
    corrected = ScheduledArrival(0, patient)
    coordinator.register_arrival(corrected)
    assert coordinator.pending_arrivals == [corrected]


@pytest.mark.parametrize(("required", "route", "edges", "message"), [
    ({"A", "B"}, ("A", "A", "B"), (), "permutation"),
    ({"A", "B"}, ("A",), (), "permutation"),
    ({"A", "B"}, ("A", "C"), (), "permutation"),
    ({"A", "C"}, ("A", "C"), (), "unmanaged"),
    ({"A", "B"}, ("A", "B"), (("C", "B"),), "outside"),
    ({"A", "B"}, ("A", "B"), (("A", "C"),), "outside"),
    ({"A", "B"}, ("B", "A"), (("A", "B"),), "precedence"),
    ({"A", "B"}, ("A", "B"), (("A", "B"), ("B", "A")), "precedence"),
    ({"A"}, ("A",), (("A", "A"),), "precedence"),
])
def test_run_rejects_invalid_future_package_before_first_arrival(
    required, route, edges, message
):
    env, coordinator, log = make_coordinator(("A", "B"))
    package = PackageConfig(frozenset(required), route, frozenset(edges))
    first = ScheduledArrival(0, PatientAgent("u1", 1, P1_CONFIG))
    later = ScheduledArrival(10, PatientAgent("u2", 2, package))
    coordinator.register_arrival(first)
    coordinator.register_arrival(later)

    env.process(coordinator.run())
    with pytest.raises(ValueError, match=message):
        env.run()

    assert env.now == 0
    assert log.records == []
    assert coordinator.pending_arrivals == [first, later]
