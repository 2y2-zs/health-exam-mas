
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

Routing, travel scheduling, departure processing and
the unified six-phase run() loop are not implemented yet.
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
        # The station registry must be a dictionary.
        if not isinstance(stations, dict):
            raise TypeError(
                "stations must be a dictionary"
            )

        # This prototype manages exactly A and B.
        if set(stations) != set(self.STATION_ORDER):
            raise ValueError(
                "MultiStationCoordinator requires exactly stations A and B"
            )

        # Validate each station before committing initialization.
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

        # Copy in fixed A -> B order, independent of input insertion order.
        self.stations: dict[
            str, AOnlyCoordinatedStation
        ] = {
            station_id: stations[station_id]
            for station_id in self.station_ids
        }

        # Pending work: consumed plans will be removed from this list.
        self.pending_arrivals: list[ScheduledArrival] = []

        # Persistent arrival-registration history.
        # IDs are NOT removed when Phase 2 consumes an arrival.
        self._registered_arrival_ids: set[str] = set()

    def register_arrival(
        self,
        arrival: ScheduledArrival,
    ) -> None:
        """Register an arrival plan, without committing Phase 2.

        The arrival time may be equal to env.now or in the future.
        The same patient_id cannot be registered twice, regardless
        of whether the PatientAgent objects are identical.

        Registered IDs remain reserved after their plans are consumed.
        Validation failures leave plans, history and domain state intact.
        """

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

        # Only after validation succeeds, commit the registration.
        self.pending_arrivals.append(arrival)
        self._registered_arrival_ids.add(patient_id)

    def commit_due_arrivals(self) -> list[PatientAgent]:
        """Phase 2: synchronously commit arrivals due at env.now.

        Reject any overdue pending plan before processing the batch.
        Validate every due patient before recording the first ARRIVAL.
        Record all due arrivals by rank and patient ID, then remove
        their plans while retaining the persistent ID history.

        Does not advance time, route, move, enqueue or start service.
        """

        now = self.env.now

        # An unprocessed past arrival is a scheduling error.
        # Never silently skip or retroactively record it.
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

        # Validate the complete batch before mutating plans or logs.
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

        # The entire batch is valid. Emit Phase 2 records in stable
        # order, with no yield or other phase interleaving.
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

        # Consume only current-time plans; retain all future plans.
        # The persistent ID registry is deliberately unchanged.
        self.pending_arrivals = [
            arrival
            for arrival in self.pending_arrivals
            if arrival.at != now
        ]

        return [arrival.patient for arrival in due]

    def complete_due_services(self) -> list[PatientAgent]:
        """Synchronously commit due services across A and B.

        Phase 0 records all SERVICE_END events in A -> B order.
        Phase 1 then releases the visits in A -> B order.

        No yield, routing or departure occurs.
        """

        due_by_station = {}

        # Phase 0: collect and record every service completion.
        for station_id in self.station_ids:
            station = self.stations[station_id]

            due_by_station[station_id] = station.close_services(
                self.event_log
            )

        released: list[PatientAgent] = []

        # Phase 1: release only after all Phase 0 events.
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
        """Return the earliest active service completion across A and B.

        This is a pure query. Raise RuntimeError on an overdue
        active visit. None means no active service, not necessarily
        that all simulation work is finished.
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
        """SimPy generator: process only the next service completion.

        Returns released patients through Process.value.
        No active service returns [] without advancing time.

        Deliberately does not commit arrivals or dispatch Phase 5.
        """

        next_time = self.next_service_completion_time()

        if next_time is None:
            return []

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        return self.complete_due_services()

    def dispatch_available_services(self) -> None:
        """Phase 5: synchronously start available services, A then B.

        Each Station owns FCFS and Resource allocation.
        Does not advance time or perform Phases 0-4.
        """

        for station_id in self.station_ids:
            self.stations[station_id].start_available(
                self.event_log
            )
