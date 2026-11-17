
"""A/B multi-station Coordinator: incremental coordination components.

Current responsibilities:
- Register exactly stations A and B
- Validate the shared Environment and station registry
- Preserve deterministic station order: A, then B
- Commit all due SERVICE_END events before RESOURCE_RELEASE
- Query the earliest active service completion
- Process one service-completion bucket with a SimPy generator
- Dispatch available services synchronously in Phase 5
- Register arrivals with persistent patient-ID history
- Commit due arrivals synchronously in Phase 2
- Query the next event time across arrivals and services
- Process one unified event bucket through Phase 2

Routing, travel scheduling, departure processing and the
complete six-phase run() loop are not implemented yet.
"""

import simpy

from health_exam_mas.model0 import (
    ENTRY_LOCATION,
    EventLog,
    PatientAgent,
    PatientState,
)

from model0_a_only_prototype import (
    AOnlyCoordinatedStation,
    ScheduledArrival,
)


class MultiStationCoordinator:
    """Register A/B and coordinate individual scheduling phases."""

    STATION_ORDER = ("A", "B")

    def __init__(
        self,
        env: simpy.Environment,
        stations: dict[str, AOnlyCoordinatedStation],
        event_log: EventLog,
    ) -> None:
        if not isinstance(stations, dict):
            raise TypeError(
                "stations must be a dictionary"
            )

        if set(stations) != set(self.STATION_ORDER):
            raise ValueError(
                "MultiStationCoordinator requires exactly stations A and B"
            )

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

            if station.station_id != station_id:
                raise ValueError(
                    f"Station dictionary key {station_id!r} "
                    f"does not match station_id {station.station_id!r}"
                )

            if station.env is not env:
                raise ValueError(
                    f"Station {station_id!r} must share "
                    "the Coordinator Environment"
                )

        self.env = env
        self.event_log = event_log

        self.station_ids: tuple[str, str] = self.STATION_ORDER

        self.stations: dict[
            str, AOnlyCoordinatedStation
        ] = {
            station_id: stations[station_id]
            for station_id in self.station_ids
        }

        # Unconsumed arrival plans.
        self.pending_arrivals: list[ScheduledArrival] = []

        # Persistent history, including consumed arrivals.
        self._registered_arrival_ids: set[str] = set()

    def register_arrival(
        self,
        arrival: ScheduledArrival,
    ) -> None:
        """Register an arrival plan without committing Phase 2."""

        if arrival.at < self.env.now:
            raise ValueError(
                "Arrival time cannot be in the past"
            )

        patient_id = arrival.patient.patient_id

        if patient_id in self._registered_arrival_ids:
            raise ValueError(
                "Duplicate arrival for patient_id "
                f"{patient_id!r}"
            )

        self.pending_arrivals.append(arrival)
        self._registered_arrival_ids.add(patient_id)

    def commit_due_arrivals(self) -> list[PatientAgent]:
        """Phase 2: commit all current-time arrivals synchronously.

        Reject overdue plans before committing anything.
        Validate the whole due batch before recording ARRIVAL.
        Retain future plans and persistent patient-ID history.

        No time advance, routing, travel, queue or service start.
        """

        now = self.env.now

        if any(
            arrival.at < now
            for arrival in self.pending_arrivals
        ):
            raise RuntimeError(
                "Overdue pending arrival"
            )

        due = sorted(
            (
                arrival
                for arrival in self.pending_arrivals
                if arrival.at == now
            ),
            key=lambda arrival: (
                arrival.patient.patient_rank,
                arrival.patient.patient_id,
            ),
        )

        seen_ids: set[str] = set()

        for arrival in due:
            patient = arrival.patient
            patient_id = patient.patient_id

            if patient_id in seen_ids:
                raise ValueError(
                    f"Duplicate patient ID in due arrival batch: {patient_id!r}"
                )

            seen_ids.add(patient_id)

            if patient_id not in self._registered_arrival_ids:
                raise RuntimeError(
                    f"Arrival registration history missing {patient_id!r}"
                )

            if patient.state != PatientState.ARRIVED:
                raise ValueError(
                    f"Patient {patient_id!r} must be ARRIVED "
                    "before Phase 2"
                )

            if patient.location != ENTRY_LOCATION:
                raise ValueError(
                    f"Patient {patient_id!r} must be at ENTRY "
                    "before Phase 2"
                )

            if patient.completed_tests:
                raise ValueError(
                    f"Patient {patient_id!r} already has completed tests"
                )

            if (
                patient.active_visit_id is not None
                or patient.active_station_id is not None
            ):
                raise ValueError(
                    f"Patient {patient_id!r} already has an active visit"
                )

        for arrival in due:
            patient = arrival.patient

            self.event_log.record(
                sim_time=now,
                event_type="ARRIVAL",
                patient_id=patient.patient_id,
                prior_state=None,
                new_state=PatientState.ARRIVED,
                phase=2,
            )

        self.pending_arrivals = [
            arrival
            for arrival in self.pending_arrivals
            if arrival.at != now
        ]

        return [arrival.patient for arrival in due]

    def complete_due_services(self) -> list[PatientAgent]:
        """Phase 0/1: commit all due services without yielding.

        First emit all SERVICE_END events in A -> B order.
        Then emit RESOURCE_RELEASE events in A -> B order.
        Return released PatientAgent objects.
        """

        due_by_station = {}

        # Phase 0: all completions first.
        for station_id in self.station_ids:
            station = self.stations[station_id]

            due_by_station[station_id] = station.close_services(
                self.event_log
            )

        released: list[PatientAgent] = []

        # Phase 1: only after every Phase 0 completion.
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
        """Pure query: earliest active service completion.

        Raise RuntimeError for any overdue active visit.
        None means no active service, not necessarily no work.
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

    def next_event_time(self) -> float | None:
        """Pure query: earliest arrival or service completion.

        Reject overdue pending arrivals and overdue services.
        Does not advance time or commit any event.

        None means neither supported source has an event.
        Travel completion is not included yet.
        """

        now = self.env.now
        candidates: list[float] = []

        for arrival in self.pending_arrivals:
            if arrival.at < now:
                raise RuntimeError(
                    "Overdue pending arrival"
                )

            candidates.append(arrival.at)

        service_time = self.next_service_completion_time()

        if service_time is not None:
            candidates.append(service_time)

        if not candidates:
            return None

        return min(candidates)

    def process_next_service_completion(self):
        """Service-only SimPy generator, retained for component tests.

        Does not consider earlier arrivals and must not be used
        as the unified event scheduler.
        """

        next_time = self.next_service_completion_time()

        if next_time is None:
            return []

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        return self.complete_due_services()

    def process_next_event_bucket(self):
        """SimPy generator: process the next event bucket through Phase 2.

        Return:
            (released_patients, arrived_patients)

        Algorithm:
        1. Query the earliest Arrival or Service Completion time.
        2. Yield a timeout only if that time is in the future.
        3. Commit all Phase 0/1 service completions.
        4. Commit all Phase 2 arrivals.

        There is no yield between steps 3 and 4.

        With no scheduled event, return ([], []) without advancing
        simulation time. This does not mean the simulation is drained.

        No routing, travel, queuing, dispatch or departure occurs.
        """

        next_time = self.next_event_time()

        if next_time is None:
            return ([], [])

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        # Once the target time is reached, keep the entire
        # Phase 0 -> Phase 1 -> Phase 2 boundary synchronous.
        released = self.complete_due_services()
        arrived = self.commit_due_arrivals()

        return (released, arrived)

    def dispatch_available_services(self) -> None:
        """Phase 5: start available services at A, then B.

        Each Station owns FCFS and Resource allocation.
        This method is NOT invoked by process_next_event_bucket().
        """

        for station_id in self.station_ids:
            self.stations[station_id].start_available(
                self.event_log
            )
