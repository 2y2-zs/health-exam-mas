from dataclasses import dataclass
from math import isfinite

import simpy

from .model0 import (
    ENTRY_LOCATION,
    MODEL0_TRAVEL_TIMES,
    EventLog,
    PatientAgent,
    PatientState,
    eligible_stations,
    recommend_fixed_route,
    transition_patient_state,
)

from .model0_station import AOnlyCoordinatedStation


@dataclass(frozen=True)
class ScheduledArrival:
    at: float
    patient: PatientAgent


@dataclass(frozen=True)
class ScheduledTravel:
    patient: PatientAgent
    origin: str
    destination: str
    started_at: float
    ends_at: float


@dataclass(frozen=True)
class ReadyQueueEntry:
    patient: PatientAgent
    station_id: str
    travel_ended_at: float


class MultiStationCoordinator:
    """Commit the six domain phases at each simulation timestamp."""

    STATION_ORDER = ("A", "B", "C")

    def __init__(
        self,
        env: simpy.Environment,
        stations: dict[str, AOnlyCoordinatedStation],
        event_log: EventLog,
        *,
        intake_cutoff: float | None = None,
    ) -> None:
        if not isinstance(stations, dict):
            raise TypeError("stations must be a dictionary")

        if set(stations) not in ({"A", "B"}, set(self.STATION_ORDER)):
            raise ValueError(
                "MultiStationCoordinator requires stations A and B, with C optional"
            )

        station_ids = tuple(
            station_id for station_id in self.STATION_ORDER if station_id in stations
        )
        for station_id in station_ids:
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

        if intake_cutoff is not None and (
            not isfinite(intake_cutoff) or intake_cutoff < 0
        ):
            raise ValueError("intake_cutoff must be finite and nonnegative")

        self.env = env
        self.event_log = event_log
        self.intake_cutoff = intake_cutoff

        self.station_ids = station_ids

        self.stations: dict[str, AOnlyCoordinatedStation] = {
            station_id: stations[station_id]
            for station_id in self.station_ids
        }

        self.pending_arrivals: list[ScheduledArrival] = []

        self.pending_travels: list[ScheduledTravel] = []

        self._registered_arrival_ids: set[str] = set()

        self._admitted_patients_by_id: dict[
            str, PatientAgent
        ] = {}

        self._entry_routed_ids: set[str] = set()

        self._ready_for_queue: dict[str, ReadyQueueEntry] = {}

        self._pending_final_releases: dict[str, float] = {}
        self._departed_patient_ids: set[str] = set()

    def register_arrival(
        self,
        arrival: ScheduledArrival,
    ) -> None:
        if not isfinite(arrival.at) or arrival.at < 0:
            raise ValueError("Arrival time must be finite and nonnegative")
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
        """Reserve a travel plan in the calendar without starting the trip."""
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

        self.pending_travels.append(travel)

    def start_next_travel(
        self,
        patient: PatientAgent,
    ) -> ScheduledTravel:
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

    def commit_due_travels(self) -> list[PatientAgent]:
        now = self.env.now

        if any(travel.ends_at < now for travel in self.pending_travels):
            raise RuntimeError("Overdue pending travel completion")

        due = sorted(
            (travel for travel in self.pending_travels if travel.ends_at == now),
            key=lambda travel: (
                travel.patient.patient_rank,
                travel.patient.patient_id,
            ),
        )

        # Reject a bad travel plan before committing any arrival in the batch.
        seen_ids: set[str] = set()
        for travel in due:
            patient = travel.patient
            patient_id = patient.patient_id

            if patient_id in seen_ids:
                raise ValueError(
                    f"Duplicate patient ID in due travel batch: {patient_id!r}"
                )
            seen_ids.add(patient_id)

            if self._admitted_patients_by_id.get(patient_id) is not patient:
                raise ValueError(
                    f"Travel patient {patient_id!r} is not the original "
                    "Phase 2 admitted object"
                )

            if patient.state != PatientState.TRAVELLING:
                raise ValueError(
                    f"Patient {patient_id!r} must be TRAVELLING "
                    "before travel completion"
                )

            if patient.location != travel.origin:
                raise ValueError(
                    f"Patient {patient_id!r} travel origin "
                    "does not match patient location"
                )

            if (
                patient.active_visit_id is not None
                or patient.active_station_id is not None
            ):
                raise ValueError(
                    f"Patient {patient_id!r} has an active visit"
                )

            if travel.destination not in self.stations:
                raise ValueError(
                    f"Travel destination {travel.destination!r} "
                    "is not managed by this Coordinator"
                )

            if travel.destination not in eligible_stations(
                patient.package, patient.completed_tests
            ):
                raise ValueError(
                    f"Travel destination {travel.destination!r} "
                    f"is not eligible for patient {patient_id!r}"
                )

            try:
                duration = MODEL0_TRAVEL_TIMES[
                    (travel.origin, travel.destination)
                ]
            except KeyError as exc:
                raise ValueError("Unknown directed travel route") from exc

            if duration <= 0 or travel.ends_at != travel.started_at + duration:
                raise ValueError(
                    f"Travel duration does not match matrix for {patient_id!r}"
                )

            if patient_id in self._ready_for_queue:
                raise ValueError(
                    f"Conflicting ready queue record for {patient_id!r}"
                )

            started = any(
                record.event_type == "TRAVEL_START"
                and record.phase == 3
                and record.patient_id == patient_id
                and record.sim_time == travel.started_at
                and record.station_id == travel.destination
                and record.prior_state == PatientState.DECIDING
                and record.new_state == PatientState.TRAVELLING
                for record in self.event_log.records
            )
            if not started:
                raise ValueError(
                    f"Travel for {patient_id!r} was registered but not started"
                )

        for travel in due:
            patient = travel.patient
            patient.location = travel.destination
            self.event_log.record(
                sim_time=now,
                event_type="TRAVEL_END",
                patient_id=patient.patient_id,
                prior_state=PatientState.TRAVELLING,
                new_state=PatientState.TRAVELLING,
                station_id=travel.destination,
                phase=3,
            )
            self._ready_for_queue[patient.patient_id] = ReadyQueueEntry(
                patient=patient,
                station_id=travel.destination,
                travel_ended_at=now,
            )

        self.pending_travels = [
            travel for travel in self.pending_travels if travel.ends_at != now
        ]
        return [travel.patient for travel in due]

    def commit_due_arrivals(self) -> list[PatientAgent]:
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

        intake_open = self.intake_cutoff is None or now <= self.intake_cutoff
        event_type = "ARRIVAL" if intake_open else "ARRIVAL_REJECTED"
        new_state = PatientState.ARRIVED if intake_open else None
        for arrival in due:
            self.event_log.record(
                sim_time=now,
                event_type=event_type,
                patient_id=arrival.patient.patient_id,
                new_state=new_state,
                phase=2,
            )

        self.pending_arrivals = [
            arrival
            for arrival in self.pending_arrivals
            if arrival.at != now
        ]

        admitted = [arrival.patient for arrival in due] if intake_open else []
        for patient in admitted:
            self._admitted_patients_by_id[patient.patient_id] = patient
        return admitted

    def route_entry_arrivals(
        self,
        arrived_patients: list[PatientAgent],
    ) -> list[PatientAgent]:
        batch = sorted(
            arrived_patients,
            key=lambda patient: (
                patient.patient_rank,
                patient.patient_id,
            ),
        )

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

            destination = recommend_fixed_route(
                patient.package,
                patient.completed_tests,
            )

            if destination not in self.stations:
                raise ValueError(
                    f"Entry route destination {destination!r} "
                    "is not managed by this Coordinator"
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

        self._entry_routed_ids.update(
            patient.patient_id
            for patient, _ in planned_moves
        )

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
        now = self.env.now
        station_order = {
            station_id: index
            for index, station_id in enumerate(self.station_ids)
        }

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
                    "is not managed by this Coordinator"
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

        # Merge entry trips and transfers before applying the station tie-break.
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
        """Record every due completion before releasing any station."""

        due_by_station = {}

        for station_id in self.station_ids:
            station = self.stations[station_id]

            due_by_station[station_id] = station.close_services(
                self.event_log
            )

        released: list[PatientAgent] = []

        for station_id in self.station_ids:
            station = self.stations[station_id]

            released.extend(
                station.release_services(
                    due_by_station[station_id],
                    self.event_log,
                )
            )

        for patient in released:
            if (
                patient.state == PatientState.FINISHED
                and self._admitted_patients_by_id.get(patient.patient_id) is patient
            ):
                self._pending_final_releases[patient.patient_id] = self.env.now

        return released

    def commit_departures(self, finished_patients: list[PatientAgent]) -> None:
        now = self.env.now
        seen_ids: set[str] = set()
        travelling_ids = {travel.patient.patient_id for travel in self.pending_travels}

        for patient in finished_patients:
            patient_id = patient.patient_id
            if patient_id in seen_ids:
                raise ValueError(f"Duplicate departure for patient {patient_id!r}")
            seen_ids.add(patient_id)

            if self._admitted_patients_by_id.get(patient_id) is not patient:
                raise ValueError(f"Patient {patient_id!r} is not the admitted object")
            if (
                patient.state != PatientState.FINISHED
                or patient.completed_tests != patient.package.required_tests
            ):
                raise ValueError(f"Patient {patient_id!r} has unfinished examinations")
            if self._pending_final_releases.get(patient_id) != now:
                raise ValueError(
                    f"Patient {patient_id!r} has no unconsumed final release at t={now}"
                )
            if (
                patient.active_visit_id is not None
                or patient.active_station_id is not None
                or patient_id in travelling_ids
                or patient_id in self._ready_for_queue
            ):
                raise ValueError(f"Patient {patient_id!r} still has outstanding work")

        for patient in sorted(
            finished_patients, key=lambda item: (item.patient_rank, item.patient_id)
        ):
            self.event_log.record(
                sim_time=now,
                event_type="DEPARTURE",
                patient_id=patient.patient_id,
                prior_state=PatientState.FINISHED,
                new_state=PatientState.FINISHED,
                phase=3,
            )
            del self._pending_final_releases[patient.patient_id]
            self._departed_patient_ids.add(patient.patient_id)

    def next_service_completion_time(self) -> float | None:
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
        now = self.env.now
        candidates: list[float] = []

        for arrival in self.pending_arrivals:
            if arrival.at < now:
                raise RuntimeError("Overdue pending arrival")
            candidates.append(arrival.at)

        service_time = self.next_service_completion_time()
        if service_time is not None:
            candidates.append(service_time)

        for travel in self.pending_travels:
            if travel.ends_at < now:
                raise RuntimeError(
                    "Overdue pending travel completion: "
                    f"patient {travel.patient.patient_id!r}, "
                    f"ends_at={travel.ends_at}, now={now}"
                )
            candidates.append(travel.ends_at)

        return min(candidates) if candidates else None

    def process_next_service_completion(self):
        next_time = self.next_service_completion_time()

        if next_time is None:
            return []

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        return self.complete_due_services()

    def process_next_event_bucket(self):
        """Advance through service completions, releases and admissions only."""

        next_time = self.next_event_time()

        if next_time is None:
            return ([], [])

        if next_time > self.env.now:
            yield self.env.timeout(next_time - self.env.now)

        released = self.complete_due_services()
        arrived = self.commit_due_arrivals()

        return (released, arrived)

    def dispatch_available_services(self) -> None:
        for station_id in self.station_ids:
            self.stations[station_id].start_available(
                self.event_log
            )

    def _assert_drained(self) -> None:
        remaining = self._admitted_patients_by_id.keys() - self._departed_patient_ids
        busy_stations = [
            station_id
            for station_id, station in self.stations.items()
            if (
                station.waiting
                or station.active
                or station.resource.count
                or station.resource.queue
            )
        ]
        if (
            self.pending_arrivals
            or self.pending_travels
            or remaining
            or busy_stations
            or self._ready_for_queue
            or self._pending_final_releases
        ):
            raise RuntimeError(
                f"Simulation stalled at t={self.env.now}: "
                f"patients without departures={sorted(remaining)}, "
                f"stations with pending work={busy_stations}"
            )

    def _validate_pending_packages(self) -> None:
        for arrival in self.pending_arrivals:
            patient = arrival.patient
            package = patient.package
            required = package.required_tests
            route = package.fixed_route
            unmanaged = required.difference(self.stations)
            if unmanaged:
                raise ValueError(
                    f"Patient {patient.patient_id!r} requires unmanaged stations: "
                    f"{sorted(unmanaged)}"
                )

            position = {station: index for index, station in enumerate(route)}
            if len(position) != len(route) or position.keys() != required:
                raise ValueError(
                    f"Fixed route for {patient.patient_id!r} must be a "
                    "permutation of the required stations"
                )

            for predecessor, successor in package.hard_precedence:
                if predecessor not in required or successor not in required:
                    raise ValueError(
                        "Precedence references a station outside the package "
                        f"for {patient.patient_id!r}: {predecessor!r} -> {successor!r}"
                    )
                if position[predecessor] >= position[successor]:
                    raise ValueError(
                        f"Fixed route for {patient.patient_id!r} violates "
                        f"precedence: {predecessor!r} must precede {successor!r}"
                    )

    def run(self):
        self._validate_pending_packages()
        if self._ready_for_queue or self._pending_final_releases:
            raise RuntimeError(
                f"Simulation stalled in an incomplete bucket at t={self.env.now}"
            )

        while True:
            released, arrived = yield from self.process_next_event_bucket()

            # Finish trips already underway before handling zero-time entry travel.
            ready = self.commit_due_travels()
            if not (released or arrived or ready):
                # A rejected arrival can leave later events pending.
                next_time = self.next_event_time()
                if next_time is not None and next_time > self.env.now:
                    continue
                self._assert_drained()
                return

            ready.extend(self.route_entry_arrivals(arrived))
            finished: list[PatientAgent] = []
            continuing: list[PatientAgent] = []
            for patient in released:
                if patient.state == PatientState.FINISHED:
                    finished.append(patient)
                elif patient.state == PatientState.NEEDS_ROUTING:
                    continuing.append(patient)
                else:
                    raise RuntimeError(
                        f"Unexpected state after release for {patient.patient_id!r}: "
                        f"{patient.state}"
                    )

            self.commit_departures(finished)
            for patient in sorted(
                continuing, key=lambda item: (item.patient_rank, item.patient_id)
            ):
                self.start_next_travel(patient)

            self.commit_queue_entries(ready)
            self.dispatch_available_services()
