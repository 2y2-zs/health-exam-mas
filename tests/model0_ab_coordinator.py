
"""A/B multi-station Coordinator: incremental coordination prototype.

Supported:
- A/B registration and Environment validation
- Phase 0/1: batch service completion and release
- Phase 2: batch arrival commitment
- Phase 3: validated zero-time entry routing and travel
- Phase 5: synchronous service dispatch
- Service and arrival next-time queries
- Component-only SimPy generators

Not yet supported:
- Phase 4 unified queue entry
- Positive-duration travel in the unified coordinator
- Phase 3 continuation after service release
- Full six-phase run() loop
"""

import simpy

from health_exam_mas.model0 import (
    ENTRY_LOCATION,
    MODEL0_TRAVEL_TIMES,
    EventLog,
    PatientAgent,
    PatientState,
    eligible_stations,
    recommend_fixed_route,
    transition_patient_state,
)

from model0_a_only_prototype import (
    AOnlyCoordinatedStation,
    ScheduledArrival,
)


class MultiStationCoordinator:
    """Manage A/B using deterministic, separately callable phases."""

    STATION_ORDER = ("A", "B")

    def __init__(
        self,
        env: simpy.Environment,
        stations: dict[str, AOnlyCoordinatedStation],
        event_log: EventLog,
    ) -> None:
        if not isinstance(stations, dict):
            raise TypeError("stations must be a dictionary")

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

        self.stations: dict[str, AOnlyCoordinatedStation] = {
            station_id: stations[station_id]
            for station_id in self.station_ids
        }

        self.pending_arrivals: list[ScheduledArrival] = []

        # Persistent ID history, including consumed arrival plans.
        self._registered_arrival_ids: set[str] = set()

        # Actual Phase 2 admissions, with object identity preserved.
        # Registration alone does NOT populate this dictionary.
        self._admitted_patients_by_id: dict[
            str, PatientAgent
        ] = {}

        # A patient may complete ENTRY travel only once.
        self._entry_routed_ids: set[str] = set()

    def register_arrival(
        self,
        arrival: ScheduledArrival,
    ) -> None:
        """Register an arrival plan, without admitting the patient."""

        if arrival.at < self.env.now:
            raise ValueError("Arrival time cannot be in the past")

        patient_id = arrival.patient.patient_id

        if patient_id in self._registered_arrival_ids:
            raise ValueError(
                "Duplicate arrival for patient_id "
                f"{patient_id!r}"
            )

        self.pending_arrivals.append(arrival)
        self._registered_arrival_ids.add(patient_id)

    def commit_due_arrivals(self) -> list[PatientAgent]:
        """Phase 2: validate and commit all arrivals due at env.now."""

        now = self.env.now

        if any(
            arrival.at < now
            for arrival in self.pending_arrivals
        ):
            raise RuntimeError("Overdue pending arrival")

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

        # Complete prevalidation before the first ARRIVAL record.
        seen_ids: set[str] = set()

        for arrival in due:
            patient = arrival.patient
            patient_id = patient.patient_id

            if patient_id in seen_ids:
                raise ValueError(
                    "Duplicate patient ID in due arrival batch: "
                    f"{patient_id!r}"
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

        # Commit every ARRIVAL in stable order.
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

        # Keep future plans; retain ID registration history.
        self.pending_arrivals = [
            arrival
            for arrival in self.pending_arrivals
            if arrival.at != now
        ]

        # Phase 3 must be able to distinguish an actually admitted
        # patient from a merely registered or duplicate-ID object.
        for arrival in due:
            patient = arrival.patient
            self._admitted_patients_by_id[
                patient.patient_id
            ] = patient

        return [arrival.patient for arrival in due]

    def route_entry_arrivals(
        self,
        arrived_patients: list[PatientAgent],
    ) -> list[PatientAgent]:
        """Phase 3: route admitted patients from ENTRY with zero travel.

        Entire-batch validation precedes every state or log mutation.

        Phase 3 writes, in rank/ID order:
            NEEDS_ROUTING
            DECIDING
            ROUTE_DECISION
            TRAVEL_START

        It then completes the whole zero-time travel batch:
            TRAVEL_END

        No yield, time advancement, queue entry or Resource request.
        """

        batch = sorted(
            arrived_patients,
            key=lambda patient: (
                patient.patient_rank,
                patient.patient_id,
            ),
        )

        # First pass: validate EVERY patient and destination.
        # No events, locations, patient states or resources are changed.
        planned_moves: list[tuple[PatientAgent, str]] = []
        seen_ids: set[str] = set()

        for patient in batch:
            patient_id = patient.patient_id

            if patient_id in seen_ids:
                raise ValueError(
                    "Duplicate patient ID in Phase 3 entry batch: "
                    f"{patient_id!r}"
                )
            seen_ids.add(patient_id)

            admitted = self._admitted_patients_by_id.get(
                patient_id
            )
            if admitted is not patient:
                raise ValueError(
                    f"Patient {patient_id!r} has not been "
                    "admitted by Phase 2 as this object"
                )

            if patient_id in self._entry_routed_ids:
                raise ValueError(
                    f"Entry travel already committed for {patient_id!r}"
                )

            if patient.state != PatientState.ARRIVED:
                raise ValueError(
                    f"Patient {patient_id!r} must be ARRIVED "
                    "before Phase 3 entry routing"
                )

            if patient.location != ENTRY_LOCATION:
                raise ValueError(
                    f"Patient {patient_id!r} must be at ENTRY "
                    "before Phase 3 entry routing"
                )

            if (
                patient.active_visit_id is not None
                or patient.active_station_id is not None
            ):
                raise ValueError(
                    f"Patient {patient_id!r} has an active visit"
                )

            if patient.completed_tests:
                raise ValueError(
                    f"Patient {patient_id!r} is not at "
                    "the beginning of the fixed route"
                )

            # The existing helper also checks the package's
            # fixed-route eligibility constraints.
            destination = recommend_fixed_route(
                patient.package,
                patient.completed_tests,
            )

            if destination not in self.stations:
                raise ValueError(
                    f"Entry route destination {destination!r} "
                    "is not managed by this A/B Coordinator"
                )

            if destination not in eligible_stations(
                patient.package,
                patient.completed_tests,
            ):
                raise ValueError(
                    f"Entry route destination {destination!r} "
                    f"is not eligible for {patient_id!r}"
                )

            try:
                duration = MODEL0_TRAVEL_TIMES[
                    (ENTRY_LOCATION, destination)
                ]
            except KeyError as exc:
                raise ValueError(
                    "Unknown ENTRY travel route"
                ) from exc

            if duration != 0.0:
                raise ValueError(
                    "Entry routing requires zero travel duration"
                )

            planned_moves.append((patient, destination))

        # All validation has passed. Phase 3 is now synchronous.

        # Second pass: routing and TRAVEL_START for every patient.
        for patient, destination in planned_moves:
            transition_patient_state(
                patient=patient,
                event_log=self.event_log,
                sim_time=self.env.now,
                event_type="NEEDS_ROUTING",
                new_state=PatientState.NEEDS_ROUTING,
                phase=3,
            )

            transition_patient_state(
                patient=patient,
                event_log=self.event_log,
                sim_time=self.env.now,
                event_type="DECIDING",
                new_state=PatientState.DECIDING,
                phase=3,
            )

            self.event_log.record(
                sim_time=self.env.now,
                event_type="ROUTE_DECISION",
                patient_id=patient.patient_id,
                prior_state=PatientState.DECIDING,
                new_state=PatientState.DECIDING,
                recommended_station=destination,
                chosen_station=destination,
                phase=3,
            )

            transition_patient_state(
                patient=patient,
                event_log=self.event_log,
                sim_time=self.env.now,
                event_type="TRAVEL_START",
                new_state=PatientState.TRAVELLING,
                station_id=destination,
                phase=3,
            )

        # Third pass: commit all zero-duration travel completions.
        for patient, destination in planned_moves:
            patient.location = destination

            self.event_log.record(
                sim_time=self.env.now,
                event_type="TRAVEL_END",
                patient_id=patient.patient_id,
                prior_state=PatientState.TRAVELLING,
                new_state=PatientState.TRAVELLING,
                station_id=destination,
                phase=3,
            )

        # Persist one-time entry-travel ownership after completion.
        self._entry_routed_ids.update(
            patient.patient_id
            for patient, _ in planned_moves
        )

        return [
            patient
            for patient, _ in planned_moves
        ]

    def complete_due_services(self) -> list[PatientAgent]:
        """Phase 0/1: commit all due completions before any release."""

        due_by_station = {}

        # Phase 0: SERVICE_END across all stations.
        for station_id in self.station_ids:
            station = self.stations[station_id]

            due_by_station[station_id] = station.close_services(
                self.event_log
            )

        # Phase 1: RESOURCE_RELEASE across all stations.
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
        """Pure query: earliest active service completion."""

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
        """Pure query: earliest pending arrival or active service end."""

        now = self.env.now
        candidates: list[float] = []

        for arrival in self.pending_arrivals:
            if arrival.at < now:
                raise RuntimeError("Overdue pending arrival")
            candidates.append(arrival.at)

        service_time = self.next_service_completion_time()

        if service_time is not None:
            candidates.append(service_time)

        if not candidates:
            return None

        return min(candidates)

    def process_next_service_completion(self):
        """Service-only generator, retained for component testing."""

        next_time = self.next_service_completion_time()

        if next_time is None:
            return []

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        return self.complete_due_services()

    def process_next_event_bucket(self):
        """Generator for one time bucket, Phase 0 through Phase 2 only.

        Returns (released_patients, arrived_patients).

        Phase 3 is NOT automatically invoked here.
        """

        next_time = self.next_event_time()

        if next_time is None:
            return ([], [])

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        # No yield between Phase 0/1 and Phase 2.
        released = self.complete_due_services()
        arrived = self.commit_due_arrivals()

        return (released, arrived)

    def dispatch_available_services(self) -> None:
        """Phase 5: synchronously start services, A then B."""

        for station_id in self.station_ids:
            self.stations[station_id].start_available(
                self.event_log
            )
