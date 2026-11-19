
"""Single-station, deterministic coordination prototype for Model 0.

Domain phases commit synchronously within each time bucket. Entry travel is
zero-time; registered positive-duration travel joins the same station queue.
This is separate from the native processes; multi-station flow is still pending.
"""

from dataclasses import dataclass
from typing import Iterable

import simpy

from health_exam_mas.model0 import (
    ENTRY_LOCATION,
    MODEL0_TRAVEL_TIMES,
    P1_CONFIG,
    EventLog,
    PatientAgent,
    PatientState,
    eligible_stations,
    recommend_fixed_route,
    transition_patient_state,
)
from health_exam_mas.model0_station import ActiveVisit, AOnlyCoordinatedStation


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


class AOnlyCoordinator:
    """Own the six synchronous phases for one configured station."""

    def __init__(
        self,
        env: simpy.Environment,
        station: AOnlyCoordinatedStation,
        event_log: EventLog,
        arrivals: Iterable[ScheduledArrival],
    ):
        if station.env is not env:
            raise ValueError(
                "Station and coordinator must share an Environment"
            )

        self.env = env
        self.station = station
        self.event_log = event_log

        self.pending = list(arrivals)

        # Planned moves do not belong to the station waiting queue.
        self.pending_travels: list[ScheduledTravel] = []

        patient_ids = [
            item.patient.patient_id
            for item in self.pending
        ]

        if len(patient_ids) != len(set(patient_ids)):
            raise ValueError(
                "Each patient may arrive once"
            )

        for item in self.pending:
            if item.at < env.now:
                raise ValueError(
                    "Arrival time cannot be in the past"
                )

            patient = item.patient

            if (
                patient.package.required_tests
                != frozenset({station.station_id})
            ):
                raise ValueError(
                    "This prototype supports only "
                    "the configured station in entry arrivals"
                )

            if patient.package.fixed_route != (
                station.station_id,
            ):
                raise ValueError(
                    "This prototype requires "
                    "a single-station fixed route"
                )

            if patient.state != PatientState.ARRIVED:
                raise ValueError(
                    "Patient must begin in ARRIVED state"
                )

        # Keep identities after their pending events have been consumed.
        self._patients_by_id: dict[str, PatientAgent] = {}
        initial_patients = [item.patient for item in self.pending]
        initial_patients.extend(visit.patient for visit in station.active.values())
        initial_patients.extend(visit.patient for visit in station.waiting)
        for patient in initial_patients:
            known = self._patients_by_id.get(patient.patient_id)
            if known is not None and known is not patient:
                raise ValueError("Patient ID belongs to another patient object")
            self._patients_by_id[patient.patient_id] = patient

    def register_travel(
        self,
        travel: ScheduledTravel,
    ) -> None:
        """Register a positive travel plan without state, log or resource changes."""

        if travel.started_at != self.env.now:
            raise ValueError(
                "Travel must start at current simulation time"
            )

        if travel.destination != self.station.station_id:
            raise ValueError(
                "Travel destination must match managed station"
            )

        if travel.destination not in eligible_stations(
            travel.patient.package,
            travel.patient.completed_tests,
        ):
            raise ValueError(
                "Travel destination is not eligible for patient"
            )

        if travel.origin != travel.patient.location:
            raise ValueError(
                "Travel origin must match patient location"
            )

        try:
            duration = MODEL0_TRAVEL_TIMES[
                (travel.origin, travel.destination)
            ]
        except KeyError as exc:
            raise ValueError(
                "Unknown directed travel route"
            ) from exc

        if duration <= 0:
            raise ValueError(
                "register_travel requires positive travel duration"
            )

        if travel.ends_at != travel.started_at + duration:
            raise ValueError(
                "Travel completion time does not "
                "match travel matrix"
            )

        if (
            travel.patient.active_visit_id is not None
            or travel.patient.active_station_id is not None
        ):
            raise ValueError(
                "Cannot register travel with an active visit"
            )

        if any(
            pending.patient.patient_id
            == travel.patient.patient_id
            for pending in self.pending_travels
        ):
            raise ValueError(
                "Patient already has a pending travel"
            )

        known = self._patients_by_id.get(travel.patient.patient_id)
        if known is not None and known is not travel.patient:
            raise ValueError("Patient ID belongs to another patient object")
        if any(item.patient is travel.patient for item in self.pending):
            raise ValueError("Patient already has a pending arrival")

        # Register only after every validation succeeds.
        self.pending_travels.append(travel)
        self._patients_by_id[travel.patient.patient_id] = travel.patient

    def start_next_travel(self, patient: PatientAgent) -> ScheduledTravel:
        """Phase 3 boundary: start P1 travel A -> B without advancing time.

        Register the complete plan before emitting routing/travel events.
        Failed validation leaves patient, log, and pending travel unchanged.
        """
        if patient.state != PatientState.NEEDS_ROUTING:
            raise ValueError("start_next_travel requires NEEDS_ROUTING")
        if patient.active_visit_id is not None or patient.active_station_id is not None:
            raise ValueError("Cannot start next travel with an active visit")
        if patient.package != P1_CONFIG:
            raise ValueError("start_next_travel currently supports P1 only")
        if self.station.station_id != "B":
            raise ValueError("P1 continuation requires Coordinator station B")
        if patient.location != "A":
            raise ValueError("P1 continuation must originate at A")
        if patient.completed_tests != {"A"}:
            raise ValueError("P1 continuation requires completed tests {'A'}")

        destination = recommend_fixed_route(
            patient.package,
            patient.completed_tests,
        )
        if destination != self.station.station_id:
            raise ValueError(
                "Fixed Route recommendation must match managed station"
            )
        if destination not in eligible_stations(
            patient.package,
            patient.completed_tests,
        ):
            raise ValueError("Recommended next station is not eligible")

        origin = patient.location
        try:
            duration = MODEL0_TRAVEL_TIMES[(origin, destination)]
        except KeyError as exc:
            raise ValueError("Unknown directed travel route") from exc

        if duration <= 0:
            raise ValueError("Next travel requires positive duration")

        travel = ScheduledTravel(
            patient=patient,
            origin=origin,
            destination=destination,
            started_at=self.env.now,
            ends_at=self.env.now + duration,
        )

        # Complete registration before changing state or writing events.
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

        return travel

    def commit_due_travels(self) -> list[PatientAgent]:
        """Phase 3: validate due moves, then commit locations without queue entry."""

        now = self.env.now

        if any(
            travel.ends_at < now
            for travel in self.pending_travels
        ):
            raise RuntimeError(
                "Overdue pending travel completion"
            )

        due = sorted(
            (
                travel
                for travel in self.pending_travels
                if travel.ends_at == now
            ),
            key=lambda travel: (
                travel.patient.patient_rank,
                travel.patient.patient_id,
            ),
        )

        # Validate the full batch before committing.
        for travel in due:
            patient = travel.patient

            if patient.location != travel.origin:
                raise ValueError(
                    "Patient location no longer "
                    "matches travel origin"
                )

            if patient.state != PatientState.TRAVELLING:
                raise ValueError(
                    "Patient must be TRAVELLING "
                    "at travel completion"
                )

            if travel.destination != self.station.station_id:
                raise ValueError(
                    "Travel destination must match managed station"
                )

            if travel.destination not in eligible_stations(
                patient.package,
                patient.completed_tests,
            ):
                raise ValueError(
                    "Travel destination is no longer "
                    "eligible for patient"
                )

            if (
                patient.active_visit_id is not None
                or patient.active_station_id is not None
            ):
                raise ValueError(
                    "Cannot commit travel with an active visit"
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

        # Remove consumed plans; leave future plans intact.
        self.pending_travels = [
            travel
            for travel in self.pending_travels
            if travel.ends_at != now
        ]

        return [
            travel.patient
            for travel in due
        ]

    def commit_departures(
        self,
        released: Iterable[PatientAgent],
    ) -> None:
        """Phase 3: validate the released batch before recording any departure."""

        released = list(released)

        for patient in released:
            if patient.state == PatientState.NEEDS_ROUTING:
                raise NotImplementedError(
                    "多站续程尚未接入：患者 "
                    f"{patient.patient_id!r} 仍需后续检查"
                )

            if patient.state != PatientState.FINISHED:
                raise RuntimeError(
                    "Unexpected patient state after "
                    f"resource release: {patient.state}"
                )

        for patient in released:
            self.event_log.record(
                sim_time=self.env.now,
                event_type="DEPARTURE",
                patient_id=patient.patient_id,
                prior_state=PatientState.FINISHED,
                new_state=PatientState.FINISHED,
                phase=3,
            )

    def _next_event_time(self) -> float:
        """Select a time bucket and reject stalled or overdue work."""

        times = [
            arrival.at
            for arrival in self.pending
        ]

        times.extend(
            travel.ends_at
            for travel in self.pending_travels
        )

        times.extend(
            visit.ends_at
            for visit in self.station.active.values()
        )

        if not times:
            raise RuntimeError(
                "Waiting visitors without future events"
            )

        if any(
            travel.ends_at < self.env.now
            for travel in self.pending_travels
        ):
            raise RuntimeError(
                "Overdue pending travel completion"
            )

        return min(times)

    def _commit_arrivals(self) -> list[PatientAgent]:
        """Phase 2: record all arrivals before routing any patient."""

        batch = sorted(
            (
                item.patient
                for item in self.pending
                if item.at == self.env.now
            ),
            key=lambda patient: (
                patient.patient_rank,
                patient.patient_id,
            ),
        )

        self.pending = [
            item
            for item in self.pending
            if item.at != self.env.now
        ]

        for patient in batch:
            self.event_log.record(
                sim_time=self.env.now,
                event_type="ARRIVAL",
                patient_id=patient.patient_id,
                prior_state=None,
                new_state=PatientState.ARRIVED,
                phase=2,
            )
        return batch

    def _route_entry_arrivals(
        self,
        batch: list[PatientAgent],
    ) -> list[PatientAgent]:
        """Phase 3: route entry arrivals and finish their zero-time moves."""

        zero_travel_completions: list[
            tuple[PatientAgent, str]
        ] = []

        for patient in batch:
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

            station_id = recommend_fixed_route(
                patient.package,
                patient.completed_tests,
            )

            if station_id != self.station.station_id:
                raise ValueError(
                    "Fixed Route recommendation must "
                    "match the station"
                )

            self.event_log.record(
                sim_time=self.env.now,
                event_type="ROUTE_DECISION",
                patient_id=patient.patient_id,
                prior_state=PatientState.DECIDING,
                new_state=PatientState.DECIDING,
                recommended_station=station_id,
                chosen_station=station_id,
                phase=3,
            )

            if patient.location != ENTRY_LOCATION:
                raise ValueError(
                    "Single-station entry travel "
                    "must start at ENTRY"
                )

            travel_duration = MODEL0_TRAVEL_TIMES[
                (patient.location, station_id)
            ]

            if travel_duration != 0.0:
                raise ValueError(
                    "Entry arrivals in this prototype require "
                    f"ENTRY -> {station_id} travel of 0.0"
                )

            transition_patient_state(
                patient=patient,
                event_log=self.event_log,
                sim_time=self.env.now,
                event_type="TRAVEL_START",
                new_state=PatientState.TRAVELLING,
                station_id=station_id,
                phase=3,
            )

            zero_travel_completions.append(
                (patient, station_id)
            )

        # Commit all entry zero-time travel in Phase 3.
        # No timeout(0), no yield.
        for patient, station_id in zero_travel_completions:
            patient.location = station_id

            self.event_log.record(
                sim_time=self.env.now,
                event_type="TRAVEL_END",
                patient_id=patient.patient_id,
                prior_state=PatientState.TRAVELLING,
                new_state=PatientState.TRAVELLING,
                station_id=station_id,
                phase=3,
            )
        return [patient for patient, _ in zero_travel_completions]

    def run(self):
        """Run synchronous phases, yielding only between time buckets."""

        while (
            self.pending
            or self.pending_travels
            or self.station.active
            or self.station.waiting
        ):
            next_time = self._next_event_time()
            if next_time > self.env.now:
                yield self.env.timeout(next_time - self.env.now)
            if next_time != self.env.now:
                raise RuntimeError("Coordinator failed to reach next time bucket")

            # Phase 0: complete every due service before any release.
            completed = self.station.close_services(self.event_log)

            # Phase 1: release resources and commit patient progress.
            released = self.station.release_services(completed, self.event_log)

            # Phase 2: admit all arrivals in the current time bucket.
            batch = self._commit_arrivals()

            # Phase 3: departures, due travel, then entry routing and zero moves.
            self.commit_departures(released)
            positive_travel_completions = self.commit_due_travels()
            zero_travel_completions = self._route_entry_arrivals(batch)

            # Phase 4: merge all ready patients before queue entry.
            ready_to_queue = positive_travel_completions + zero_travel_completions
            ready_ids = [patient.patient_id for patient in ready_to_queue]
            if len(ready_ids) != len(set(ready_ids)):
                raise ValueError("Duplicate patient ID in Phase 4 queue-entry batch")

            ready_to_queue.sort(
                key=lambda patient: (patient.patient_rank, patient.patient_id)
            )
            for patient in ready_to_queue:
                self.station.enqueue(patient, self.event_log)

            # Phase 5: select FCFS visits and request only available capacity.
            self.station.start_available(self.event_log)
            if self.station.resource.queue:
                raise RuntimeError("Unexpected Resource waiting requests")
