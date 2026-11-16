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
    # Required fields
    sim_time: float
    sequence_id: int
    event_type: str
    patient_id: str
    run_id: str

    # Optional fields
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
    # Entry to stations
    (ENTRY_LOCATION, "A"): 0.0,
    (ENTRY_LOCATION, "B"): 0.0,
    (ENTRY_LOCATION, "C"): 0.0,

    # Same-station travel
    ("A", "A"): 0.0,
    ("B", "B"): 0.0,
    ("C", "C"): 0.0,

    # Travel between A and B
    ("A", "B"): 1.0,
    ("B", "A"): 1.0,

    # Travel between B and C
    ("B", "C"): 1.0,
    ("C", "B"): 1.0,

    # Travel between A and C
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
    # 1. All required tests completed
    if package.required_tests.issubset(completed_tests):
        return None

    # 2. Find the first unfinished station in fixed route
    next_station = None

    for station in package.fixed_route:
        if station not in completed_tests:
            next_station = station
            break

    # 3. No next station despite unfinished required tests
    if next_station is None:
        raise ValueError(
            "Fixed route has no remaining station, "
            "but required tests are not all completed."
        )

    # 4. Check hard-precedence eligibility
    eligible = eligible_stations(package, completed_tests)

    if next_station not in eligible:
        raise ValueError(
            f"Fixed route recommends station {next_station!r}, "
            f"but it is not eligible. "
            f"Eligible stations: {sorted(eligible)}"
        )

    # 5. Return the recommended station
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
        self.resource = simpy.Resource(
            env,
            capacity=config.capacity,
        )

    def serve(
        self,
        patient: PatientAgent,
        event_log: "EventLog",
        visit_id: str,
    ):
        # 1. Validate before changing patient state
        if patient.location != self.station_id:
            raise ValueError(
                f"Patient {patient.patient_id!r} is at "
                f"{patient.location!r}, "
                f"not at station {self.station_id!r}."
            )

        if self.station_id not in MODEL0_STATIONS:
            raise ValueError(
                f"Unknown station: {self.station_id!r}"
            )

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

        # Stable resource-request identifier
        resource_token = (
            f"{self.station_id}:"
            f"{patient.patient_id}:"
            f"{visit_id}"
        )

        # 2. Activate visit and commit QUEUE_ENTRY
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

        # 3. Request capacity through native SimPy Resource
        with self.resource.request() as request:
            yield request

            # 4. Commit SERVICE_START
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

            # 5. Perform uninterrupted service
            yield self.env.timeout(
                self.config.service_duration
            )

            # 6. Record SERVICE_END
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

            # Mark this test as completed
            patient.completed_tests.add(
                self.station_id
            )

        # Resource automatically released exactly once
        # when exiting the context manager.

        # Clear active visit and station
        patient.active_visit_id = None
        patient.active_station_id = None

        # 7. Determine the next patient state
        if patient.package.required_tests.issubset(
            patient.completed_tests
        ):
            new_state = PatientState.FINISHED
        else:
            new_state = PatientState.NEEDS_ROUTING

        # Commit RESOURCE_RELEASE and next state
        # No yield occurs between SERVICE_END and here
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
        # 1. Create an immutable event record
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

        # 2. Preserve actual recording order
        self.records.append(event)

        # 3. Increment sequence ID
        self._next_sequence_id += 1

        # 4. Return the created record
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
    # 1. Save the previous state
    prior_state = patient.state

    # 2. Update the patient state
    patient.state = new_state

    # 3. Immediately commit the event record
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

    # 4. Return the committed event
    return event


def travel_to_station(
    env: simpy.Environment,
    patient: PatientAgent,
    station_id: str,
    event_log: EventLog,
):
    # 1. Validate destination before state changes
    if station_id not in MODEL0_STATIONS:
        raise ValueError(
            f"Unknown station: {station_id!r}"
        )

    eligible = eligible_stations(
        patient.package,
        patient.completed_tests,
    )

    if station_id not in eligible:
        raise ValueError(
            f"Station {station_id!r} is not eligible "
            f"for patient {patient.patient_id!r}. "
            f"Eligible stations: {sorted(eligible)}"
        )

    # 2. Look up directed travel time
    travel_duration = MODEL0_TRAVEL_TIMES[
        (patient.location, station_id)
    ]

    # 3. Commit TRAVELLING and TRAVEL_START
    transition_patient_state(
        patient=patient,
        event_log=event_log,
        sim_time=env.now,
        event_type="TRAVEL_START",
        new_state=PatientState.TRAVELLING,
        station_id=station_id,
    )

    # 4. Wait for travel, including zero duration
    yield env.timeout(travel_duration)

    # 5. Update location after travel completes
    patient.location = station_id

    # 6. Record TRAVEL_END without changing state
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
    # 1. Record initial arrival
    event_log.record(
        sim_time=env.now,
        event_type="ARRIVAL",
        patient_id=patient.patient_id,
        prior_state=None,
        new_state=PatientState.ARRIVED,
    )

    # 2. Enter NEEDS_ROUTING
    transition_patient_state(
        patient=patient,
        event_log=event_log,
        sim_time=env.now,
        event_type="NEEDS_ROUTING",
        new_state=PatientState.NEEDS_ROUTING,
    )

    visit_number = 0

    while True:
        # Enter DECIDING
        transition_patient_state(
            patient=patient,
            event_log=event_log,
            sim_time=env.now,
            event_type="DECIDING",
            new_state=PatientState.DECIDING,
        )

        # 3. Obtain Fixed Route recommendation
        recommended_station = recommend_fixed_route(
            patient.package,
            patient.completed_tests,
        )

        if recommended_station is None:
            raise ValueError(
                "No station was recommended for an unfinished patient."
            )

        # B0 policy: chosen station equals recommendation
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

        # 4. Wait until travel completes
        yield env.process(
            travel_to_station(
                env,
                patient,
                chosen_station,
                event_log,
            )
        )

        # 5. Generate a stable visit ID
        visit_number += 1
        visit_id = f"{patient.patient_id}:visit:{visit_number}"

        # Wait until station service and release complete
        yield env.process(
            stations[chosen_station].serve(
                patient,
                event_log,
                visit_id,
            )
        )

        # 6. Check the state after service
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

        # NEEDS_ROUTING: continue to the next decision
