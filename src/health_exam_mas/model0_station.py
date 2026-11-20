from dataclasses import dataclass

import simpy

from .model0 import (
    MODEL0_STATIONS,
    EventLog,
    PatientAgent,
    PatientState,
    eligible_stations,
    transition_patient_state,
)


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

        # Queue entry establishes the visit. Service start grants capacity.
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
        # Reject stale releases before freeing any server in this batch.
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

            self.resource.release(visit.request)
            self.release_count += 1

            patient.completed_tests.add(self.station_id)

            patient.active_visit_id = None
            patient.active_station_id = None

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

            released.append(patient)

        return released

    def start_available(
        self,
        event_log: EventLog,
    ) -> None:
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

            # The station chooses the patient. SimPy grants the available slot.
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
