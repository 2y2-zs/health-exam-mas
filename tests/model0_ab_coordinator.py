
"""A/B multi-station Coordinator: incremental coordination prototype.

Supported:
- A/B registration and Environment validation
- Phase 0/1: batch service completion and release
- Phase 2: batch arrival commitment
- Phase 3: validated zero-time entry routing and travel
- Phase 4: atomic prevalidation and deterministic queue commitment
- Phase 5: synchronous service dispatch
- Positive-duration travel registration and Phase 3 start (no arrival commit)
- Service and arrival next-time queries
- Component-only SimPy generators

Not yet supported:
- Positive-duration travel commitment/time selection in the unified coordinator
- Positive-duration travel completion and Phase 4 continuation
- Full six-phase run() loop
"""

from dataclasses import dataclass

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
    ScheduledTravel,
)


@dataclass(frozen=True)
class ReadyQueueEntry:
    """A committed TRAVEL_END awaiting its Phase 4 QUEUE_ENTRY."""

    patient: PatientAgent
    station_id: str
    travel_ended_at: float


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

        # Positive-duration travel plans are registered, not executed.
        # Scheduling/travel commitment will be handled in a later phase.
        self.pending_travels: list[ScheduledTravel] = []

        # Persistent ID history, including consumed arrival plans.
        self._registered_arrival_ids: set[str] = set()

        # Actual Phase 2 admissions, with object identity preserved.
        # Registration alone does NOT populate this dictionary.
        self._admitted_patients_by_id: dict[
            str, PatientAgent
        ] = {}

        # A patient may complete ENTRY travel only once.
        self._entry_routed_ids: set[str] = set()

        # Phase 3 produces these ready records after TRAVEL_END.
        # Phase 4 consumes each one exactly once.
        self._ready_for_queue: dict[str, ReadyQueueEntry] = {}

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

    def register_travel(self, travel: ScheduledTravel) -> None:
        """Register a positive-duration move without executing it.

        Only the exact object admitted by Phase 2 can schedule a move.
        Travel must start now from the patient's current location,
        have a managed/eligible destination, and end at precisely the
        travel-matrix-defined time. No overlapping pending travel is
        allowed for the same patient ID.

        All validation precedes the single append. In particular this
        method does not advance time, change any patient, write a log,
        reserve a Resource or emit TRAVEL_START / TRAVEL_END.
        """
        patient = travel.patient
        patient_id = patient.patient_id

        if self._admitted_patients_by_id.get(patient_id) is not patient:
            raise ValueError(
                "Travel patient must be the original "
                "Phase 2 admitted object"
            )

        if (
            patient.active_visit_id is not None
            or patient.active_station_id is not None
        ):
            raise ValueError(
                "Cannot register travel with an active visit"
            )

        if travel.started_at != self.env.now:
            raise ValueError(
                "Travel must start at current simulation time"
            )

        if travel.origin != patient.location:
            raise ValueError(
                "Travel origin must match patient location"
            )

        if travel.destination not in self.stations:
            raise ValueError(
                "Travel destination is not managed by this Coordinator"
            )

        if travel.destination not in eligible_stations(
            patient.package, patient.completed_tests
        ):
            raise ValueError(
                "Travel destination is not eligible for patient"
            )

        try:
            duration = MODEL0_TRAVEL_TIMES[
                (travel.origin, travel.destination)
            ]
        except KeyError as exc:
            raise ValueError("Unknown directed travel route") from exc

        if duration <= 0:
            raise ValueError(
                "register_travel requires positive travel duration"
            )

        if travel.ends_at != travel.started_at + duration:
            raise ValueError(
                "Travel completion time does not match travel matrix"
            )

        if any(
            pending.patient.patient_id == patient_id
            for pending in self.pending_travels
        ):
            raise ValueError("Patient already has a pending travel")

        # No mutation occurs before this append.
        self.pending_travels.append(travel)

    def start_next_travel(
        self,
        patient: PatientAgent,
    ) -> ScheduledTravel:
        """Phase 3: start the next positive-duration fixed-route move.

        Called after Phase 1 releases an unfinished patient. Prevalidate
        identity, state, visit ownership, fixed route, eligibility, and
        directed travel duration. Register the plan before writing any
        Phase 3 event, so registration failures leave patient/log intact.

        Only TRAVEL_START occurs here; TRAVEL_END and Phase 4 queue entry
        are deliberately deferred. No time advance or Resource request.
        """
        patient_id = patient.patient_id

        if self._admitted_patients_by_id.get(patient_id) is not patient:
            raise ValueError(
                "Travel patient must be the original "
                "Phase 2 admitted object"
            )

        if patient.state != PatientState.NEEDS_ROUTING:
            raise ValueError(
                f"Patient {patient_id!r} must be NEEDS_ROUTING "
                "before starting continued travel"
            )

        if (
            patient.active_visit_id is not None
            or patient.active_station_id is not None
        ):
            raise ValueError(
                f"Patient {patient_id!r} has an active visit"
            )

        destination = recommend_fixed_route(
            patient.package,
            patient.completed_tests,
        )
        if destination is None:
            raise ValueError(
                f"Patient {patient_id!r} has no remaining fixed-route test"
            )
        if destination not in self.stations:
            raise ValueError(
                f"Travel destination {destination!r} "
                "is not managed by this Coordinator"
            )
        if destination not in eligible_stations(
            patient.package,
            patient.completed_tests,
        ):
            raise ValueError(
                f"Travel destination {destination!r} "
                f"is not eligible for patient {patient_id!r}"
            )

        origin = patient.location
        try:
            duration = MODEL0_TRAVEL_TIMES[(origin, destination)]
        except KeyError as exc:
            raise ValueError(
                f"Unknown directed travel route {origin!r} -> "
                f"{destination!r}"
            ) from exc
        if duration <= 0:
            raise ValueError(
                "start_next_travel requires positive travel duration"
            )

        travel = ScheduledTravel(
            patient=patient,
            origin=origin,
            destination=destination,
            started_at=self.env.now,
            ends_at=self.env.now + duration,
        )

        # The single plan-append is committed before any Phase 3 log
        # or patient state change. It rejects an existing pending move.
        self.register_travel(travel)

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
            patient_id=patient_id,
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

        return travel

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

        # Record the completed move only after all Phase 3 events.
        # Phase 4 will verify the original patient, station and time.
        for patient, destination in planned_moves:
            self._ready_for_queue[patient.patient_id] = ReadyQueueEntry(
                patient=patient,
                station_id=destination,
                travel_ended_at=self.env.now,
            )

        return [
            patient
            for patient, _ in planned_moves
        ]

    def commit_queue_entries(
        self,
        ready_patients: list[PatientAgent],
    ) -> list[PatientAgent]:
        """Phase 4: batch-enqueue completed travels, A then B.

        Validate the ENTIRE batch without side effects before starting
        any Station.enqueue call. Every patient must have a matching,
        unconsumed TRAVEL_END ready record for the CURRENT time bucket.

        Station.enqueue owns the WAITING state, visit ownership and
        Phase 4 QUEUE_ENTRY log. This method never acquires Resource.
        Phase 5 remains a separate explicit call.
        """

        now = self.env.now
        station_order = {
            station_id: index
            for index, station_id in enumerate(self.station_ids)
        }

        # First pass: no patient state, queue, log or ready-record mutations.
        seen_ids: set[str] = set()
        validated: list[ReadyQueueEntry] = []

        for patient in ready_patients:
            patient_id = patient.patient_id

            if patient_id in seen_ids:
                raise ValueError(
                    "Duplicate patient ID in Phase 4 queue batch: "
                    f"{patient_id!r}"
                )
            seen_ids.add(patient_id)

            if self._admitted_patients_by_id.get(patient_id) is not patient:
                raise ValueError(
                    f"Patient {patient_id!r} is not the "
                    "original Phase 2 admitted object"
                )

            if patient_id not in self._entry_routed_ids:
                raise ValueError(
                    f"Patient {patient_id!r} has no "
                    "completed Phase 3 entry travel"
                )

            ready = self._ready_for_queue.get(patient_id)
            if ready is None:
                raise ValueError(
                    "No unconsumed TRAVEL_END ready record "
                    f"for patient {patient_id!r}"
                )
            if ready.patient is not patient:
                raise ValueError(
                    "Ready record patient identity mismatch "
                    f"for {patient_id!r}"
                )

            destination = ready.station_id
            if destination not in self.stations:
                raise ValueError(
                    f"Queue destination {destination!r} "
                    "is not managed by this A/B Coordinator"
                )

            if ready.travel_ended_at != now:
                raise RuntimeError(
                    f"TRAVEL_END time mismatch for {patient_id!r}: "
                    f"recorded={ready.travel_ended_at}, now={now}"
                )

            if patient.state != PatientState.TRAVELLING:
                raise ValueError(
                    f"Patient {patient_id!r} must be TRAVELLING "
                    "before Phase 4"
                )
            if patient.location != destination:
                raise ValueError(
                    f"Patient {patient_id!r} location "
                    f"{patient.location!r} does not match "
                    f"queue destination {destination!r}"
                )
            if (
                patient.active_visit_id is not None
                or patient.active_station_id is not None
            ):
                raise ValueError(
                    f"Patient {patient_id!r} already has an active visit"
                )

            if destination not in eligible_stations(
                patient.package, patient.completed_tests
            ):
                raise ValueError(
                    f"Queue destination {destination!r} "
                    f"is not eligible for patient {patient_id!r}"
                )

            validated.append(ready)

        # Second pass: deterministic queue order. Do not sort EventLog.
        validated.sort(
            key=lambda ready: (
                station_order[ready.station_id],
                ready.patient.patient_rank,
                ready.patient.patient_id,
            )
        )

        committed: list[PatientAgent] = []
        for ready in validated:
            patient = ready.patient
            self.stations[ready.station_id].enqueue(
                patient, self.event_log
            )
            del self._ready_for_queue[patient.patient_id]
            committed.append(patient)

        return committed

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
