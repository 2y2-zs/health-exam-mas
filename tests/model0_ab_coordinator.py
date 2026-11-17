
"""A/B multi-station Coordinator: initialization and service completion.

Current responsibilities:
- Register exactly stations A and B
- Validate that both stations share the Coordinator Environment
- Validate dictionary keys against station.station_id
- Preserve deterministic iteration order: A, then B
- Commit all due SERVICE_END events before any RESOURCE_RELEASE
- Query the earliest active service completion across A and B

Arrivals, routing, travel scheduling, departure processing and
the unified six-phase run() loop are not implemented yet.
"""

import simpy

from health_exam_mas.model0 import EventLog, PatientAgent

from model0_a_only_prototype import AOnlyCoordinatedStation


class MultiStationCoordinator:
    """Register A/B and coordinate synchronous service completion."""

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

    def complete_due_services(self) -> list[PatientAgent]:
        """Synchronously commit due services across A and B.

        Phase 0:
            Collect and log every due SERVICE_END, in A -> B order.

        Phase 1:
            Release every collected batch, in A -> B order.

        All SERVICE_END records precede every RESOURCE_RELEASE.
        No yield, time advancement, routing or departure occurs.
        """

        # Phase 0: collect and record all service completions first.
        due_by_station = {}

        for station_id in self.station_ids:
            station = self.stations[station_id]

            due_by_station[station_id] = station.close_services(
                self.event_log
            )

        # Phase 1: only after Phase 0 is fully completed,
        # release resources and commit patient progress.
        released: list[PatientAgent] = []

        for station_id in self.station_ids:
            station = self.stations[station_id]

            released.extend(
                station.release_services(
                    due_by_station[station_id],
                    self.event_log,
                )
            )

        return released

    def next_service_completion_time(self) -> float | None:
        """Return the earliest active service end time across A and B.

        This method only reads active visits. It does not advance
        simulation time, update patient or station state, or write logs.

        Raise RuntimeError if any active service has already expired.
        None means no active service; other simulation work may remain.
        """

        earliest: float | None = None

        for station_id in self.station_ids:
            station = self.stations[station_id]

            for visit in station.active.values():
                if visit.ends_at < self.env.now:
                    raise RuntimeError(
                        "Overdue active service completion "
                        f"at station {station_id!r}"
                    )

                if earliest is None or visit.ends_at < earliest:
                    earliest = visit.ends_at

        return earliest
