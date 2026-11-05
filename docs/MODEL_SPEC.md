# Simulation model specification v1.0 (design only)

## Architecture

- **Patient Agent**: package and progress, current status/location, perceived information and response to route recommendations.
- **Examination Station / Resource Agent**: FCFS queue, parallel-server capacity, busy/idle servers and service completions.
- **Routing Agent**: uniform interface `recommend(patient, observable_state) -> eligible_station`, supporting interchangeable established policies.
- **SimPy event engine**: advances simulated time for arrival, travel, queue entry, service start/end and departure.

Agent cognition/decision logic is separate from event scheduling. SimPy alone does not confer agency: Patient Agent must actually perceive, decide and act.

## Patient lifecycle

`ARRIVED -> NEEDS_ROUTING -> DECIDING -> TRAVELLING -> WAITING -> IN_SERVICE -> (NEEDS_ROUTING or FINISHED)`

Initial Model 0 always accepts the legal recommendation. Once the system works, compare:
- B0: always accept.
- B1: accept with configurable probability, otherwise select an alternative **eligible** next station if one exists.
- B2: hypothetical state-dependent behavioural choice based on perceived wait, travel time and preferences; parameters require calibration/sensitivity analysis.

A pre-queue recommendation override is different from abandoning a joined queue. Mid-queue switching is deferred.

Legal next tests: `Eligible = {station in RemainingTests: all predecessors are CompletedTests}`. No patient may occupy multiple resources at once. Agents must not use future realized service times as observations.

## Model 0 (deterministic verification)

All quantities below are **synthetic software test inputs**, not medical-centre observations.

| Station | Server capacity | Fixed service duration (minutes) |
|---|---:|---:|
| A | 1 | 4 |
| B | 1 | 3 |
| C | 2 | 5 |

Packages: `P1={A,B}` fixed order A->B; `P2={B,C}` B->C; `P3={A,B,C}` A->B->C. P3 additionally has an example precedence A before C (not a medical claim).

Travel times, minutes (from row, to column): A->B=1, A->C=2, B->A=1, B->C=1, C->A=2, C->B=1; same station=0. Entry->first station=0. Scheduled deterministic arrivals; nonpreemptive service, one FCFS queue per station, stable tie-breaking.

Record timestamp, patient id, event, station/resource id, previous/new state, recommended and chosen next station, run id.

## Model 1 (stochastic daily-centre environment)

Candidate six stations drawn from Lv et al. (2026): ultrasound, ECG, blood draw, internal medicine, X-ray, ophthalmology. Its case-specific capacities, means and travel times are candidate inputs; transcribe and verify against the primary article tables before use.

Candidate **synthetic** package definitions:
- P1 Basic: blood draw, ECG, internal medicine, ophthalmology.
- P2 Standard: P1 + X-ray.
- P3 Comprehensive: P2 + ultrasound.

Do NOT label those as medically recommended or actual hospital packages. Clinical precedence defaults to none unless evidenced. Candidate arrivals: Poisson with sensitivity to demand; candidate service variability: deterministic first, then positive-valued distributions such as Gamma with explicitly assumed CV. A published mean does not identify a distribution or variance. Separate intake closure (e.g., 480 minutes) from simulation termination: finish servicing everyone admitted before cutoff.

Before selecting arrival rates, check station load `rho_j ~ lambda * p_j * E[S_j] / c_j` with consistent time units. Report whether scenarios are stable/overloaded; do not assume 20/35/45 arrivals/hour are realistic for the chosen resource configuration.

## Routing comparison (RQ2)

Start with fixed route, shortest observed queue, shortest estimated wait; potentially add a faithfully reproduced or explicitly literature-inspired existing dynamic policy. Do not describe a simplified reproduction as an exact published algorithm.

Compare under paired exogenous scenarios: aligned arrivals, packages and service random streams, multiple independent replications, confidence intervals, checks for state observability and no future information. Measure mean/P95 wait, cycle time, throughput and utilization where appropriate. Policy rankings and behaviour effects are research questions, not expected outcomes.

## Status

DES/Agent architecture: specified, not implemented.
Model 0: planned, not verified.
Model 1/2: candidate design, not calibrated or implemented.
Research results: none yet.
