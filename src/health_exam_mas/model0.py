from dataclasses import dataclass, field
from enum import Enum

import simpy


class PatientState(str, Enum):
    ARRIVED = "ARRIVED"
    NEEDS_ROUTING = "NEEDS_ROUTING"
    DECIDING = "DECIDING"
    TRAVELLING = "TRAVELLING"
    WAITING = "WAITING"
    IN_SERVICE = "IN_SERVICE"
    FINISHED = "FINISHED"


@dataclass(frozen=True)
class EventRecord:
    sim_time: float
    sequence_id: int
    event_type: str
    patient_id: str
    run_id: str

    prior_state: PatientState | None = None
    new_state: PatientState | None = None
    station_id: str | None = None
    visit_id: str | None = None
    recommended_station: str | None = None
    chosen_station: str | None = None
    resource_token_or_server_id: str | None = None
    phase: int | None = None


@dataclass(frozen=True)
class StationConfig:
    capacity: int
    service_duration: float


MODEL0_STATIONS: dict[str, StationConfig] = {
    "A": StationConfig(capacity=1, service_duration=4.0),
    "B": StationConfig(capacity=1, service_duration=3.0),
    "C": StationConfig(capacity=2, service_duration=5.0),
}


@dataclass(frozen=True)
class PackageConfig:
    required_tests: frozenset[str]
    fixed_route: tuple[str, ...]
    hard_precedence: frozenset[tuple[str, str]]


P1_CONFIG = PackageConfig(
    required_tests=frozenset({"A", "B"}),
    fixed_route=("A", "B"),
    hard_precedence=frozenset(),
)


ENTRY_LOCATION = "ENTRY"

MODEL0_TRAVEL_TIMES: dict[tuple[str, str], float] = {
    (ENTRY_LOCATION, "A"): 0.0,
    (ENTRY_LOCATION, "B"): 0.0,
    (ENTRY_LOCATION, "C"): 0.0,

    ("A", "A"): 0.0,
    ("B", "B"): 0.0,
    ("C", "C"): 0.0,

    ("A", "B"): 1.0,
    ("B", "A"): 1.0,
    ("B", "C"): 1.0,
    ("C", "B"): 1.0,
    ("A", "C"): 2.0,
    ("C", "A"): 2.0,
}


@dataclass
class PatientAgent:
    patient_id: str
    patient_rank: int
    package: PackageConfig

    state: PatientState = PatientState.ARRIVED
    location: str = ENTRY_LOCATION
    completed_tests: set[str] = field(default_factory=set)
    active_visit_id: str | None = None
    active_station_id: str | None = None


def eligible_stations(
    package: PackageConfig,
    completed_tests: set[str],
) -> frozenset[str]:
    remaining = package.required_tests - completed_tests

    return frozenset(
        station
        for station in remaining
        if all(
            predecessor in completed_tests
            for predecessor, successor in package.hard_precedence
            if successor == station
        )
    )


def recommend_fixed_route(
    package: PackageConfig,
    completed_tests: set[str],
) -> str | None:
    if package.required_tests.issubset(completed_tests):
        return None

    next_station = None
    for station in package.fixed_route:
        if station not in completed_tests:
            next_station = station
            break

    if next_station is None:
        raise ValueError(
            "Fixed route has no remaining station, "
            "but required tests are not all completed."
        )

    # The fixed route must still satisfy the package's hard predecessors.
    eligible = eligible_stations(package, completed_tests)
    if next_station not in eligible:
        raise ValueError(
            f"Fixed route recommends station {next_station!r}, "
            f"but it is not eligible. "
            f"Eligible stations: {sorted(eligible)}"
        )

    return next_station


class StationAgent:
    def __init__(
        self,
        env: simpy.Environment,
        station_id: str,
        config: StationConfig,
    ):
        self.env = env
        self.station_id = station_id
        self.config = config
        self.resource = simpy.Resource(env, capacity=config.capacity)

    def serve(
        self,
        patient: PatientAgent,
        event_log: "EventLog",
        visit_id: str,
    ):
        if patient.location != self.station_id:
            raise ValueError(
                f"Patient {patient.patient_id!r} is at "
                f"{patient.location!r}, "
                f"not at station {self.station_id!r}."
            )

        if self.station_id not in MODEL0_STATIONS:
            raise ValueError(f"Unknown station: {self.station_id!r}")

        if self.station_id not in eligible_stations(
            patient.package,
            patient.completed_tests,
        ):
            raise ValueError(
                f"Station {self.station_id!r} is not eligible "
                f"for patient {patient.patient_id!r}."
            )

        if (
            patient.active_visit_id is not None
            or patient.active_station_id is not None
        ):
            raise ValueError(
                f"Patient {patient.patient_id!r} "
                f"already has an active visit."
            )

        resource_token = f"{self.station_id}:{patient.patient_id}:{visit_id}"

        patient.active_visit_id = visit_id
        patient.active_station_id = self.station_id

        transition_patient_state(
            patient=patient,
            event_log=event_log,
            sim_time=self.env.now,
            event_type="QUEUE_ENTRY",
            new_state=PatientState.WAITING,
            station_id=self.station_id,
            visit_id=visit_id,
            resource_token_or_server_id=resource_token,
        )

        with self.resource.request() as request:
            yield request

            transition_patient_state(
                patient=patient,
                event_log=event_log,
                sim_time=self.env.now,
                event_type="SERVICE_START",
                new_state=PatientState.IN_SERVICE,
                station_id=self.station_id,
                visit_id=visit_id,
                resource_token_or_server_id=resource_token,
            )

            yield self.env.timeout(self.config.service_duration)

            event_log.record(
                sim_time=self.env.now,
                event_type="SERVICE_END",
                patient_id=patient.patient_id,
                prior_state=PatientState.IN_SERVICE,
                new_state=PatientState.IN_SERVICE,
                station_id=self.station_id,
                visit_id=visit_id,
                resource_token_or_server_id=resource_token,
            )

            patient.completed_tests.add(self.station_id)

        # Commit patient progress before another process can observe the release.
        patient.active_visit_id = None
        patient.active_station_id = None

        if patient.package.required_tests.issubset(patient.completed_tests):
            new_state = PatientState.FINISHED
        else:
            new_state = PatientState.NEEDS_ROUTING

        transition_patient_state(
            patient=patient,
            event_log=event_log,
            sim_time=self.env.now,
            event_type="RESOURCE_RELEASE",
            new_state=new_state,
            station_id=self.station_id,
            visit_id=visit_id,
            resource_token_or_server_id=resource_token,
        )


class EventLog:
    def __init__(self, run_id: str):
        self.run_id: str = run_id
        self.records: list[EventRecord] = []
        self._next_sequence_id: int = 1

    def record(
        self,
        *,
        sim_time: float,
        event_type: str,
        patient_id: str,
        prior_state: PatientState | None = None,
        new_state: PatientState | None = None,
        station_id: str | None = None,
        visit_id: str | None = None,
        recommended_station: str | None = None,
        chosen_station: str | None = None,
        resource_token_or_server_id: str | None = None,
        phase: int | None = None,
    ) -> EventRecord:
        event = EventRecord(
            sim_time=sim_time,
            sequence_id=self._next_sequence_id,
            event_type=event_type,
            patient_id=patient_id,
            run_id=self.run_id,
            prior_state=prior_state,
            new_state=new_state,
            station_id=station_id,
            visit_id=visit_id,
            recommended_station=recommended_station,
            chosen_station=chosen_station,
            resource_token_or_server_id=resource_token_or_server_id,
            phase=phase,
        )

        self.records.append(event)
        self._next_sequence_id += 1
        return event


def transition_patient_state(
    patient: PatientAgent,
    event_log: EventLog,
    sim_time: float,
    event_type: str,
    new_state: PatientState,
    *,
    station_id: str | None = None,
    visit_id: str | None = None,
    recommended_station: str | None = None,
    chosen_station: str | None = None,
    resource_token_or_server_id: str | None = None,
    phase: int | None = None,
) -> EventRecord:
    prior_state = patient.state
    patient.state = new_state
    event = event_log.record(
        sim_time=sim_time,
        event_type=event_type,
        patient_id=patient.patient_id,
        prior_state=prior_state,
        new_state=new_state,
        station_id=station_id,
        visit_id=visit_id,
        recommended_station=recommended_station,
        chosen_station=chosen_station,
        resource_token_or_server_id=resource_token_or_server_id,
        phase=phase,
    )

    return event


def travel_to_station(
    env: simpy.Environment,
    patient: PatientAgent,
    station_id: str,
    event_log: EventLog,
):
    if station_id not in MODEL0_STATIONS:
        raise ValueError(f"Unknown station: {station_id!r}")

    eligible = eligible_stations(patient.package, patient.completed_tests)
    if station_id not in eligible:
        raise ValueError(
            f"Station {station_id!r} is not eligible "
            f"for patient {patient.patient_id!r}. "
            f"Eligible stations: {sorted(eligible)}"
        )

    travel_duration = MODEL0_TRAVEL_TIMES[(patient.location, station_id)]

    transition_patient_state(
        patient=patient,
        event_log=event_log,
        sim_time=env.now,
        event_type="TRAVEL_START",
        new_state=PatientState.TRAVELLING,
        station_id=station_id,
    )

    # A zero-duration trip still yields to other native SimPy events.
    yield env.timeout(travel_duration)
    patient.location = station_id

    event_log.record(
        sim_time=env.now,
        event_type="TRAVEL_END",
        patient_id=patient.patient_id,
        prior_state=PatientState.TRAVELLING,
        new_state=PatientState.TRAVELLING,
        station_id=station_id,
    )


def patient_process(
    env: simpy.Environment,
    patient: PatientAgent,
    stations: dict[str, StationAgent],
    event_log: EventLog,
):
    event_log.record(
        sim_time=env.now,
        event_type="ARRIVAL",
        patient_id=patient.patient_id,
        prior_state=None,
        new_state=PatientState.ARRIVED,
    )

    transition_patient_state(
        patient=patient,
        event_log=event_log,
        sim_time=env.now,
        event_type="NEEDS_ROUTING",
        new_state=PatientState.NEEDS_ROUTING,
    )

    visit_number = 0

    while True:
        transition_patient_state(
            patient=patient,
            event_log=event_log,
            sim_time=env.now,
            event_type="DECIDING",
            new_state=PatientState.DECIDING,
        )

        recommended_station = recommend_fixed_route(
            patient.package,
            patient.completed_tests,
        )

        if recommended_station is None:
            raise ValueError(
                "No station was recommended for an unfinished patient."
            )

        chosen_station = recommended_station

        event_log.record(
            sim_time=env.now,
            event_type="ROUTE_DECISION",
            patient_id=patient.patient_id,
            prior_state=PatientState.DECIDING,
            new_state=PatientState.DECIDING,
            recommended_station=recommended_station,
            chosen_station=chosen_station,
        )

        yield env.process(
            travel_to_station(env, patient, chosen_station, event_log)
        )

        visit_number += 1
        visit_id = f"{patient.patient_id}:visit:{visit_number}"

        yield env.process(
            stations[chosen_station].serve(patient, event_log, visit_id)
        )

        if patient.state == PatientState.FINISHED:
            event_log.record(
                sim_time=env.now,
                event_type="DEPARTURE",
                patient_id=patient.patient_id,
                prior_state=PatientState.FINISHED,
                new_state=PatientState.FINISHED,
            )
            return

        if patient.state != PatientState.NEEDS_ROUTING:
            raise ValueError(
                f"Unexpected patient state after service: "
                f"{patient.state!r}"
            )
