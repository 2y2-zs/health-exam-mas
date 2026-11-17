
"""Single-station, deterministic, six-phase coordination prototype for Model 0.

This module is separate from the legacy model0.py processes.

The coordinator manages one station at a time. Predeclared entry arrivals
support zero-duration ENTRY -> station travel. Registered positive-duration
travels can also be completed and admitted to the managed station.

The six domain phases are:

    0. SERVICE_END
    1. RESOURCE_RELEASE and progress commit
    2. ARRIVAL
    3. Routing, Travel and DEPARTURE
    4. QUEUE_ENTRY
    5. SERVICE_START

There is no yield between phases of the same simulated time bucket.

The Station releases all completed visits, including patients who still
need another test. The Coordinator currently rejects unsupported multi-station
continuation rather than silently dropping those patients.

This is still a single-station prototype, not full A -> B coordination.
"""

from dataclasses import dataclass
from typing import Iterable

import simpy

from health_exam_mas.model0 import (
    ENTRY_LOCATION,
    MODEL0_STATIONS,
    MODEL0_TRAVEL_TIMES,
    EventLog,
    PatientAgent,
    PatientState,
    eligible_stations,
    recommend_fixed_route,
    transition_patient_state,
)


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
class WaitingVisit:
    patient: PatientAgent
    visit_id: str
    entered_at: float


@dataclass
class ActiveVisit:
    patient: PatientAgent
    visit_id: str
    request: object
    ends_at: float


class AOnlyCoordinatedStation:
    """Own one domain waiting queue and one capacity-only Resource."""

    def __init__(
        self,
        env: simpy.Environment,
        station_id: str = "A",
    ):
        self.env = env
        self.station_id = station_id
        self.config = MODEL0_STATIONS[station_id]

        if self.config.service_duration <= 0:
            raise ValueError(
                "This prototype requires positive service duration"
            )

        self.resource = simpy.Resource(
            env,
            capacity=self.config.capacity,
        )

        self.waiting: list[WaitingVisit] = []
        self.active: dict[str, ActiveVisit] = {}

        self.peak_resource_count = 0
        self.release_count = 0

    def _token(
        self,
        patient: PatientAgent,
        visit_id: str,
    ) -> str:
        return (
            f"{self.station_id}:"
            f"{patient.patient_id}:{visit_id}"
        )

    def enqueue(
        self,
        patient: PatientAgent,
        event_log: EventLog,
    ) -> None:
        """Phase 4: enqueue after travel completion."""

        if patient.location != self.station_id:
            raise ValueError(
                f"Patient {patient.patient_id!r} must be at "
                f"{self.station_id!r} before QUEUE_ENTRY"
            )

        if patient.state != PatientState.TRAVELLING:
            raise ValueError(
                f"Patient {patient.patient_id!r} "
                "must be TRAVELLING before QUEUE_ENTRY"
            )

        if self.station_id not in eligible_stations(
            patient.package,
            patient.completed_tests,
        ):
            raise ValueError(
                f"{self.station_id} is not eligible "
                f"for {patient.patient_id!r}"
            )

        if (
            patient.active_visit_id is not None
            or patient.active_station_id is not None
        ):
            raise ValueError(
                f"Patient {patient.patient_id!r} "
                "already has an active visit"
            )

        visit_id = f"{patient.patient_id}:visit:1"

        # Active visit fields belong to Phase 4,
        # not Phase 3 travel.
        patient.active_visit_id = visit_id
        patient.active_station_id = self.station_id

        self.waiting.append(
            WaitingVisit(
                patient=patient,
                visit_id=visit_id,
                entered_at=self.env.now,
            )
        )

        transition_patient_state(
            patient=patient,
            event_log=event_log,
            sim_time=self.env.now,
            event_type="QUEUE_ENTRY",
            new_state=PatientState.WAITING,
            station_id=self.station_id,
            visit_id=visit_id,
            resource_token_or_server_id=self._token(
                patient,
                visit_id,
            ),
            phase=4,
        )

    def close_services(
        self,
        event_log: EventLog,
    ) -> list[ActiveVisit]:
        """Phase 0: log due SERVICE_END without progress mutation."""

        due = sorted(
            (
                visit
                for visit in self.active.values()
                if visit.ends_at == self.env.now
            ),
            key=lambda visit: (
                visit.patient.patient_rank,
                visit.patient.patient_id,
            ),
        )

        for visit in due:
            patient = visit.patient

            event_log.record(
                sim_time=self.env.now,
                event_type="SERVICE_END",
                patient_id=patient.patient_id,
                prior_state=PatientState.IN_SERVICE,
                new_state=PatientState.IN_SERVICE,
                station_id=self.station_id,
                visit_id=visit.visit_id,
                resource_token_or_server_id=self._token(
                    patient,
                    visit.visit_id,
                ),
                phase=0,
            )

        return due

    def release_services(
        self,
        due: list[ActiveVisit],
        event_log: EventLog,
    ) -> list[PatientAgent]:
        """Phase 1: release every due visit and commit patient progress.

        Return all released patients, including those in NEEDS_ROUTING.
        Station does not decide whether continuation is supported.

        No yield occurs inside this method.
        """

        # Validate the whole batch before changing any visit or resource.
        visit_ids: set[str] = set()
        for visit in due:
            if visit.visit_id in visit_ids:
                raise RuntimeError("Duplicate visit in release batch")
            if self.active.get(visit.visit_id) is not visit:
                raise RuntimeError("Visit was not active at release")
            visit_ids.add(visit.visit_id)

        released: list[PatientAgent] = []
        for visit in due:
            patient = visit.patient
            del self.active[visit.visit_id]

            # Release the Resource exactly once.
            self.resource.release(visit.request)
            self.release_count += 1

            # Commit this Station's completed test.
            patient.completed_tests.add(self.station_id)

            # Clear the active visit fields.
            patient.active_visit_id = None
            patient.active_station_id = None

            # The Station commits the next patient state.
            new_state = (
                PatientState.FINISHED
                if patient.package.required_tests.issubset(
                    patient.completed_tests
                )
                else PatientState.NEEDS_ROUTING
            )

            transition_patient_state(
                patient=patient,
                event_log=event_log,
                sim_time=self.env.now,
                event_type="RESOURCE_RELEASE",
                new_state=new_state,
                station_id=self.station_id,
                visit_id=visit.visit_id,
                resource_token_or_server_id=self._token(
                    patient,
                    visit.visit_id,
                ),
                phase=1,
            )

            # Both FINISHED and NEEDS_ROUTING are valid
            # Station release outcomes.
            released.append(patient)

        return released

    def start_available(
        self,
        event_log: EventLog,
    ) -> None:
        """Phase 5: FCFS by entry time, rank and patient ID."""

        while (
            self.waiting
            and self.resource.count < self.resource.capacity
        ):
            next_visit = min(
                self.waiting,
                key=lambda visit: (
                    visit.entered_at,
                    visit.patient.patient_rank,
                    visit.patient.patient_id,
                ),
            )

            self.waiting.remove(next_visit)
            patient = next_visit.patient

            # Request capacity only after domain queue selection.
            request = self.resource.request()

            if not request.triggered:
                request.cancel()
                raise RuntimeError(
                    "Unexpected native Resource queueing"
                )

            if self.resource.queue:
                raise RuntimeError(
                    "Native Resource queue must remain empty"
                )

            self.active[next_visit.visit_id] = ActiveVisit(
                patient=patient,
                visit_id=next_visit.visit_id,
                request=request,
                ends_at=(
                    self.env.now
                    + self.config.service_duration
                ),
            )

            self.peak_resource_count = max(
                self.peak_resource_count,
                self.resource.count,
            )

            transition_patient_state(
                patient=patient,
                event_log=event_log,
                sim_time=self.env.now,
                event_type="SERVICE_START",
                new_state=PatientState.IN_SERVICE,
                station_id=self.station_id,
                visit_id=next_visit.visit_id,
                resource_token_or_server_id=self._token(
                    patient,
                    next_visit.visit_id,
                ),
                phase=5,
            )


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

        # Planned positive-duration travel completions.
        # This list is NOT the Station waiting queue.
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
        """Validate and register a positive-duration travel plan.

        This method only appends a validated plan.
        It does not move patients, advance time,
        write events or allocate resources.
        """

        # 1. Travel starts now.
        if travel.started_at != self.env.now:
            raise ValueError(
                "Travel must start at current simulation time"
            )

        # 2. Destination must match the managed station
        #    and be eligible for the patient.
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

        # 3. Origin must match the patient's location.
        if travel.origin != travel.patient.location:
            raise ValueError(
                "Travel origin must match patient location"
            )

        # 4. Duration must match the directed matrix.
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

        # 5. No active visit.
        if (
            travel.patient.active_visit_id is not None
            or travel.patient.active_station_id is not None
        ):
            raise ValueError(
                "Cannot register travel with an active visit"
            )

        # 6. No other pending plan for this patient.
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

    def commit_due_travels(self) -> list[PatientAgent]:
        """Phase 3: commit due positive-duration travel completions.

        Validate the entire batch before any mutations.
        Do not enqueue, reserve capacity, reroute or record TRAVEL_START.
        """

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

        # Commit the completed moves in stable patient order.
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
        """Phase 3: commit departures for fully completed patients only.

        Validate the entire released batch before logging any DEPARTURE.
        NEEDS_ROUTING is explicitly unsupported by this Coordinator.
        """

        released = list(released)

        # Validate every released patient first.
        # Never silently discard NEEDS_ROUTING patients.
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

        # Only a fully validated batch may depart.
        for patient in released:
            self.event_log.record(
                sim_time=self.env.now,
                event_type="DEPARTURE",
                patient_id=patient.patient_id,
                prior_state=PatientState.FINISHED,
                new_state=PatientState.FINISHED,
                phase=3,
            )

    def run(self):
        """Run all six phases, yielding only between time buckets."""

        while (
            self.pending
            or self.pending_travels
            or self.station.active
            or self.station.waiting
        ):
            # -----------------------------------------
            # Select the next simulation time
            # -----------------------------------------
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

            next_time = min(times)

            if next_time > self.env.now:
                yield self.env.timeout(
                    next_time - self.env.now
                )

            if next_time != self.env.now:
                raise RuntimeError(
                    "Coordinator failed to reach next time bucket"
                )

            # No yield from Phase 0 through Phase 5.

            # -----------------------------------------
            # Phase 0: SERVICE_END
            # -----------------------------------------
            completed = self.station.close_services(
                self.event_log
            )

            # -----------------------------------------
            # Phase 1: RESOURCE_RELEASE
            # -----------------------------------------
            released = self.station.release_services(
                completed,
                self.event_log,
            )

            # -----------------------------------------
            # Phase 2: ARRIVAL
            # -----------------------------------------
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

            # -----------------------------------------
            # Phase 3: Routing / Departure / Travel
            # -----------------------------------------

            # Coordinator rejects any unsupported continuation.
            # No DEPARTURE is logged for NEEDS_ROUTING.
            self.commit_departures(released)

            # Positive-duration travel completions do not
            # repeat ARRIVAL, Routing, or TRAVEL_START.
            positive_travel_completions = (
                self.commit_due_travels()
            )

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

            # -----------------------------------------
            # Phase 4: QUEUE_ENTRY
            # -----------------------------------------

            ready_to_queue = (
                positive_travel_completions
                + [
                    patient
                    for patient, _ in zero_travel_completions
                ]
            )

            ready_ids = [
                patient.patient_id
                for patient in ready_to_queue
            ]

            if len(ready_ids) != len(set(ready_ids)):
                raise ValueError(
                    "Duplicate patient ID in Phase 4 "
                    "queue-entry batch"
                )

            ready_to_queue.sort(
                key=lambda patient: (
                    patient.patient_rank,
                    patient.patient_id,
                )
            )

            for patient in ready_to_queue:
                self.station.enqueue(
                    patient,
                    self.event_log,
                )

            # -----------------------------------------
            # Phase 5: SERVICE_START
            # -----------------------------------------
            self.station.start_available(
                self.event_log
            )

            if self.station.resource.queue:
                raise RuntimeError(
                    "Unexpected Resource waiting requests"
                )
