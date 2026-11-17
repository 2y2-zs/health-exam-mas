
"""A/B multi-station Coordinator: incremental coordination components.

Current responsibilities:
- Register exactly stations A and B
- Validate that both stations share the Coordinator Environment
- Validate dictionary keys against station.station_id
- Preserve deterministic iteration order: A, then B
- Commit all due SERVICE_END events before any RESOURCE_RELEASE
- Query the earliest active service completion across A and B
- Process the next service-completion bucket with a SimPy generator
- Dispatch available services synchronously in Phase 5
- Register future or current-time arrivals without admitting patients

Arrival commitment, routing, travel scheduling, departure processing and
the unified six-phase run() loop are not implemented yet.
"""

import simpy

from health_exam_mas.model0 import EventLog, PatientAgent

from model0_a_only_prototype import (
    AOnlyCoordinatedStation,
    ScheduledArrival,
)


class MultiStationCoordinator:
    """Register A/B and coordinate service completion and dispatch."""

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

            # Both stations must use the SAME Environment object.
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

        # Copy the registry in A -> B order.
        self.stations: dict[
            str, AOnlyCoordinatedStation
        ] = {
            station_id: stations[station_id]
            for station_id in self.station_ids
        }

        # Registration only. Plans are not ARRIVAL events or queue entries.
        self.pending_arrivals: list[ScheduledArrival] = []

    def register_arrival(
        self,
        arrival: ScheduledArrival,
    ) -> None:
        """Register an arrival plan without committing Phase 2.

        An arrival may be scheduled for the current time or the future.
        A patient_id may have only one registered arrival, even when
        separate PatientAgent objects share that ID.

        Validation occurs before any modification. Registration does
        not advance time, mutate patients, write events or enter queues.
        """

        if arrival.at < self.env.now:
            raise ValueError(
                "Arrival time cannot be in the past"
            )

        if any(
            pending.patient.patient_id == arrival.patient.patient_id
            for pending in self.pending_arrivals
        ):
            raise ValueError(
                "Duplicate arrival for patient_id "
                f"{arrival.patient.patient_id!r}"
            )

        self.pending_arrivals.append(arrival)

    def complete_due_services(self) -> list[PatientAgent]:
        """Synchronously commit due services across A and B.

        Phase 0:
            Collect and log every due SERVICE_END, in A -> B order.

        Phase 1:
            Release every collected batch, in A -> B order.

        All SERVICE_END records precede every RESOURCE_RELEASE.
        No yield, time advancement, routing or departure occurs.
        """

        # Phase 0: collect and record all completions first.
        due_by_station = {}

        for station_id in self.station_ids:
            station = self.stations[station_id]

            due_by_station[station_id] = station.close_services(
                self.event_log
            )

        # Phase 1: release only after all Phase 0 work is complete.
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

        Only reads active visits. Does not advance simulation time,
        change patient or station state, or write events.

        Raise RuntimeError if any active service is overdue.
        None means no active service; other work may remain.
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

    def process_next_service_completion(self):
        """SimPy generator: process only the next service completion bucket.

        Returns released patients through Process.value.

        With no active services, returns [] without a timeout.
        If completion is due now, commits without yielding.
        Otherwise, yields to the earliest completion time.

        No yield occurs within the synchronous Phase 0/1 batch.
        This method deliberately does NOT invoke Phase 5.
        """

        next_time = self.next_service_completion_time()

        if next_time is None:
            return []

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        return self.complete_due_services()

    def dispatch_available_services(self) -> None:
        """Phase 5: start available services at A, then B.

        Each Station owns its FCFS queue and Resource allocation.
        This method does not yield, advance time or process other phases.

        The caller must complete Phases 2-4 before invoking Phase 5
        when a unified time-bucket scheduler is introduced.
        """

        for station_id in self.station_ids:
            self.stations[station_id].start_available(
                self.event_log
            )
