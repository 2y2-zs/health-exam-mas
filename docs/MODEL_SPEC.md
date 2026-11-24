# Simulation Model Specification v1.1 — design, not implementation

Model contract for the PSP305 daily health examination centre simulation. [Research scope](RESEARCH_CONTEXT.md) · [Rule evidence](MODEL_ASSUMPTIONS.md)

## 1. Architecture and separation of responsibilities

- **Patient Agent**: owns required/completed examinations, heterogeneous package, lifecycle state, location and active visit; perceives only defined observable information and decides/acts on the next legal step. Responses to route recommendations and additional autonomous behaviour remain candidates for later assessment. A patient cannot be queued or served in multiple stations simultaneously.
- **Examination Station / Resource Agent**: owns a shared waiting queue, server capacity, active visit/token ownership, start/completion and resource release. It is the single authority for queue membership, resource ownership and release; its queue policy selects **which already-queued patient is served next**. Model 0 uses FCFS only.
- **Routing / Flow Agent**: uses `recommend(patient, observable_state) -> station` to select **which eligible station a patient visits next**; recommendations are checked against the independent legal-eligibility function. In Model 0 the only routing policy is fixed route. Patient flow remains a separate mechanism held common across RQ2 queue-policy comparisons.
- **SimPy event engine**: drives simulated time, arrival, travel completion, service and departure events. SimPy events/process states and domain Patient Agent states must not be conflated.

Model 0 uses the synthetic B0 compliance baseline. [Behaviour assumptions](MODEL_ASSUMPTIONS.md#5-model-2-autonomous-patient-behaviour)

### Queue policy boundary (design only)

A replaceable queue policy receives the station's committed waiting visits and explicitly permitted current observations, and selects the next waiting visit when service capacity is available. It does not choose a patient's next station, create a second waiting queue, change resource ownership or release resources. The Station Agent applies the selection and retains authority over the visit lifecycle. FCFS is the **only currently defined queue-policy baseline**; other existing policies, their information requirements and tie rules remain to be selected and reviewed. No complex priority queue or implementation mechanism is prescribed here.

There must be **one effective scheduling authority**: SimPy's native Resource waiting/grant order and a custom station queue must not independently reorder the same requests. Their combination can otherwise introduce hidden FCFS selection, double ordering or grants that disagree with the selected policy. The selected Model 0 coordinated path chooses from the station's committed waiting list and requests only available native Resource capacity; the native Resource waiting queue must remain empty. Future policies must preserve one effective selection authority.

Sections 2–5 retain the **Model 0 FCFS baseline contract**, including its dispatch order and same-time semantics. They do not require every future queue policy to be FCFS. Any later change to service selection needs its own documented expectations; changes to non-preemption, immediate dispatch or event coordination require separate review. The selected formal Model 0 entry is the packaged `MultiStationCoordinator.run()` with A/B/C, applying the six phases below. Native patient-process execution is retained as a historical comparison prototype, not the formal entry. This implementation choice does not prescribe a coordinator for every future model.

## 2. Model 0 deterministic synthetic fixture

All Model 0 quantities are **SYNTHETIC software-verification inputs**, not actual medical parameters, clinical ordering advice or observed hospital operations.

| Station | Parallel capacity | Deterministic service time (minutes) |
|---|---:|---:|
| A | 1 | 4 |
| B | 1 | 3 |
| C | 2 | 5 |

Travel time (minutes): A↔B=1, B↔C=1, A↔C=2; same station=0; centre entrance to first station=0. Synthetic arrivals are individually specified for each test. A station has homogeneous parallel servers, a **single unbounded FCFS waiting queue**, non-preemptive service and no break, failure, setup/cleaning time, cross-station shared staff or overtime restriction. An idle station with an eligible waiting patient dispatches immediately.

| Package | RequiredTests (unordered set) | Model 0 Fixed Route Policy | Hard precedence constraints |
|---|---|---|---|
| P1 | {A,B} | A→B | None |
| P2 | {B,C} | B→C | None |
| P3 | {A,B,C} | A→B→C | Only A-before-C |

**Important:** A fixed route is a **policy-selected ordering**, not a medical precedence constraint. For P3 initially `Eligible={A,B}`; after A completes, `Eligible={B,C}`. A→C→B is also legal. A→B→C is the default policy, not mandatory clinical order.

`Remaining_i = Required_i - Completed_i` and `Eligible_i = {j in Remaining_i : Pred_i(j) subset of Completed_i}`. Check that a configured fixed route is a permutation of required tests and a topological order under the hard precedence graph; check recommendations again at runtime. If Remaining is nonempty but Eligible is empty, report a configuration/state error rather than looping. A deliberately illegal recommendation is **rejected**, never travelled to or queued.

## 3. Patient states and lifecycle

`ARRIVED → NEEDS_ROUTING → DECIDING → TRAVELLING → WAITING → IN_SERVICE → (NEEDS_ROUTING or FINISHED)`.

A successful visit has a unique `(patient_id, station_id, visit_id)`. Each required examination is completed at most once. At most one active station visit/request/resource token per patient. No new visit after FINISHED.

- Arrivals at time `t` first pass admission; a patient is considered admitted only once.
- Routing and B0 decision take **zero simulated time** and reserve no server capacity.
- Travel ends at the Queue Entry timestamp. Even if service begins immediately, both Queue Entry and Service Start are logged; WAITING may have zero duration.
- Station waiting queue **excludes active services**; an idle server can accept at its current timestamp once requests are committed.
- Non-preemptive service occupies interval **[start,end)**, so one visit ending at `t` and another beginning at `t` do not overlap.
- Completion, ownership clearing, release and patient progress update must form a coherent domain-level transaction, without intervening decisions observing inconsistent state. Station Agent is the **unique release authority**; guard duplicate completion, queue entry and release. A patient may request the next route after its prior visit is fully committed.
- FINISHED follows final successful release; no outstanding request or resource ownership may remain.

## 4. Same-time event ordering: domain semantics and open implementation decision

**Proposed v1.1 domain-level order for any simulation timestamp t:**

| Phase | Domain action |
|---:|---|
| 0 | Complete all service visits due at t |
| 1 | Release their resources, commit CompletedTests, clear active visit and update states |
| 2 | Process arrival/admission attempts; `arrival_time <= cutoff` is admitted |
| 3 | Handle due travel completions and zero-time routing/decision/entrance movement; collect request intents |
| 4 | Commit queue entries, ordered by `(queue_entry_time, patient_rank)` |
| 5 | Dispatch idle station capacity FCFS and log service start |

Causal prerequisites precede dependent actions. In Phase 3, first finish positive-duration travel due at t, then route newly admitted patients and complete their zero-time entry travel. Next record final departures and plan onward travel for continuing patients released in Phase 1. Use stable patient rank within each of these groups. Record events in commit order.

In Phase 4, collect all patients ready to join a station at t across all travel sources. Commit station queues in **A,B,C** order and simultaneous entries at each station by patient rank. Patients already waiting keep their place. Phase 5 then dispatches available capacity from the head of each queue.

**Implementation.** SimPy orders events by time, priority and insertion order. Native Resource callbacks can produce a different order from the table. The formal coordinated entry commits domain actions in the stated phases and retains the original append order; it does not sort completed logs to match an expected trace. The native comparison prototype still has two known contract failures, retained in the full test suite. If the domain contract changes, document the change and rederive the expected traces before experiments. [Development status](../PROJECT_PROGRESS.md#recorded-development-checks)

Intake closes at synthetic cutoff H with **inclusive admission at t=H**; no patient first arriving after H is admitted. Existing admitted patients may finish after H. Do not use `env.run(until=H)` as the whole simulation termination rule. Run until the intake is closed/all attempts considered and all admitted patients have FINISHED, with no waiting or active services. Detect stalled patients; a bare empty event queue alone is not sufficient evidence of success.

## 5. Configuration, observation and logging contracts

Pre-run configuration checks:
- unique existing station IDs, positive capacities, strictly positive service durations and nonnegative travel times;
- each package contains valid station IDs; every fixed route is a no-duplicate permutation of its package;
- all hard predecessor references are in scope, precedence graph is acyclic, and fixed route obeys its hard predecessors;
- arrival times are finite and nonnegative and must be at or after the current simulation time at registration. A finite arrival beyond the intake cutoff remains a scheduled admission attempt. Patient ranks are stable and all times use the same unit.

The coordinated run checks every preregistered package against its managed stations before processing the first event bucket. It checks the declared route independently of the routing decision made during the run.

Record domain event log at minimum: `sim_time`, `phase` (or other verified event ordering marker), `sequence_id`, `patient_id`, `station_id`, `visit_id`, `event_type`, `prior_state`, `new_state`, `recommended_station`, `chosen_station`, `resource_token_or_server_id` (if applicable), `run_id`. `run_id` and wall-clock metadata must be excluded when comparing normalized traces for determinism.

At domain **commit boundaries**, check capacity, uniqueness of active visit/resource, eligibility, no duplicate completed exams, and patient conservation. A Patient Process waiting on a SimPy event is distinct from domain status WAITING/IN_SERVICE.

## 6. Model 1 and Model 2 (deferred)

Extend the verified baseline with stochastic inputs and common flow, B0 and FCFS for Model 1. Review provenance and screen offered load before selecting demand. [Candidate inputs and load check](MODEL_ASSUMPTIONS.md#4-model-1-candidate-examination-centre-configuration)

Model 2 can examine what patients do before joining a queue. B1/B2 require separate evidence. Queue switching after entry is deferred. RQ2 can begin with a verified Model 1 baseline. [Behaviour assumptions](MODEL_ASSUMPTIONS.md#5-model-2-autonomous-patient-behaviour)

## 7. RQ2 Queue Scheduling Policy evaluation (deferred)

FCFS is the confirmed baseline. For each candidate policy, verify its decision object and source fidelity. Record permitted observations, the selection rule and the tie rule. A policy may use a permitted service-time estimate. Future realized service durations are unavailable to it.

Hold routing and B0 common in the initial comparison. Pair exogenous arrivals, packages and service demands across policies, accounting for differences in event order, and plan repeated runs with uncertainty estimates. Policy selection, metric definitions and scenario settings are open. [Evaluation assumptions](MODEL_ASSUMPTIONS.md#6-evaluation-assumptions-rq2)

## 8. Status

The Model 0 design baseline is on `main`. Development checks and formal acceptance status are tracked in the progress record. Model 1 and Model 2 remain candidates. Research experiments and empirical validation are pending. [Project progress](../PROJECT_PROGRESS.md)
