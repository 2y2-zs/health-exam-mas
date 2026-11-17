
"""Initialization-only tests for the A/B multi-station coordinator."""

import pytest
import simpy

from health_exam_mas.model0 import EventLog

from model0_a_only_prototype import AOnlyCoordinatedStation

from model0_ab_coordinator import MultiStationCoordinator


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
