"""A/B multi-station Coordinator: initialization and validation only.

This is the foundation for a future unified six-phase coordinator.

Current responsibilities:
- Register exactly stations A and B
- Validate that both stations share the Coordinator Environment
- Validate dictionary keys against station.station_id
- Preserve deterministic iteration order: A, then B

No arrivals, travel scheduling, event processing or run() yet.
"""

import simpy

from health_exam_mas.model0 import EventLog

from model0_a_only_prototype import AOnlyCoordinatedStation


class MultiStationCoordinator:
    """Register A and B in deterministic order.

    Scheduling and six-phase event processing will be implemented
    in later steps.
    """

    STATION_ORDER = ("A", "B")

    def __init__(
        self,
        env: simpy.Environment,
        stations: dict[str, AOnlyCoordinatedStation],
        event_log: EventLog,
    ) -> None:
        # 1. The station registry must be a dictionary.
        if not isinstance(stations, dict):
            raise TypeError(
                "stations must be a dictionary"
            )

        # 2. This prototype manages exactly A and B.
        if set(stations) != set(self.STATION_ORDER):
            raise ValueError(
                "MultiStationCoordinator requires exactly stations A and B"
            )

        # 3. Validate every station before storing Coordinator state.
        # Validation order is deterministic, regardless of input dict order.
        for station_id in self.STATION_ORDER:
            station = stations[station_id]

            if not isinstance(
                station,
                AOnlyCoordinatedStation,
            ):
                raise TypeError(
                    f"Station {station_id!r} must be "
                    "an AOnlyCoordinatedStation"
                )

            # Dictionary key must match the Station's own ID.
            if station.station_id != station_id:
                raise ValueError(
                    f"Station dictionary key {station_id!r} "
                    f"does not match station_id {station.station_id!r}"
                )

            # Identity check: both stations must use the SAME Environment.
            if station.env is not env:
                raise ValueError(
                    f"Station {station_id!r} must share "
                    "the Coordinator Environment"
                )

        # 4. Commit initialization after all checks succeed.
        self.env = env
        self.event_log = event_log

        # Fixed station traversal order.
        self.station_ids: tuple[str, str] = self.STATION_ORDER

        # Make an independent mapping in A -> B order.
        # Do not depend on the caller's dictionary insertion order.
        self.stations: dict[
            str, AOnlyCoordinatedStation
        ] = {
            station_id: stations[station_id]
            for station_id in self.station_ids
        }

