# Simulation Model Specification v1.1 — design, not implementation

**Scope:** PSP305 FYP; ongoing daily health examination centre. Research allocation remains RQ1 50% agent-based simulation, RQ2 40% existing **Queue Scheduling Policy** evaluation from the centre's operational perspective, optional RQ3 10% improvement. See [RESEARCH_CONTEXT](RESEARCH_CONTEXT.md) and [MODEL_ASSUMPTIONS](MODEL_ASSUMPTIONS.md). **No source code or test results are implied by this specification.**

## 1. Architecture and separation of responsibilities

- **Patient Agent**: owns required/completed examinations, heterogeneous package, lifecycle state, location and active visit; perceives only defined observable information and decides/acts on the next legal step. Responses to route recommendations and additional autonomous behaviour remain candidates for later assessment. A patient cannot be queued or served in multiple stations simultaneously.
- **Examination Station / Resource Agent**: owns a shared waiting queue, server capacity, active visit/token ownership, start/completion and resource release. It is the single authority for queue membership, resource ownership and release; its queue policy selects **which already-queued patient is served next**. Model 0 uses FCFS only.
- **Routing / Flow Agent**: uses `recommend(patient, observable_state) -> station` to select **which eligible station a patient visits next**; recommendations are checked against the independent legal-eligibility function. In Model 0 the only routing policy is fixed route. Patient flow remains a separate mechanism held common across RQ2 queue-policy comparisons.
- **SimPy event engine**: drives simulated time, arrival, travel completion, service and departure events. SimPy events/process states and domain Patient Agent states must not be conflated.

RQ1 concerns patient state, heterogeneity, observable information, decisions and interactions with stations and the flow mechanism. Model 0 verifies a deliberately synthetic process, **not** empirically validated human autonomy. The Patient Agent is B0 compliant; whether B1/B2 add useful autonomous behaviour will be assessed later and does not block all RQ2 work.

### Queue policy boundary (design only)

A replaceable queue policy receives the station's committed waiting visits and explicitly permitted current observations, and selects the next waiting visit when service capacity is available. It does not choose a patient's next station, create a second waiting queue, change resource ownership or release resources. The Station Agent applies the selection and retains authority over the visit lifecycle. FCFS is the **only currently defined queue-policy baseline**; other existing policies, their information requirements and tie rules remain to be selected and reviewed. No complex priority queue or implementation mechanism is prescribed here.

There must be **one effective scheduling authority**: SimPy's native Resource waiting/grant order and a custom station queue must not independently reorder the same requests. Their combination can otherwise introduce hidden FCFS selection, double ordering or grants that disagree with the selected policy. The student must choose and document a coherent queue/resource approach; the mechanism remains pending.

Sections 2–5 retain the **Model 0 FCFS baseline contract**, including its dispatch order and same-time semantics. They do not require every future queue policy to be FCFS. Any later change to service selection needs its own documented expectations; changes to non-preemption, immediate dispatch or event coordination require separate review. A full six-phase coordinator remains optional, with the Model 0 SimPy mapping pending.

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

**Implementation status:** The development branch has a coordinated prototype. Acceptance through the formal Model 0 entry point is pending. See [project progress](../PROJECT_PROGRESS.md) for evidence. Do **not** assume native SimPy event processing intrinsically obeys these hospital/domain phases. SimPy schedules events by time, priority and insertion order; native Resource request/release callbacks may execute in different micro-orders. A full six-phase coordinator is **not mandatory at project outset**. The student should choose and document the smallest correct event coordination approach, then demonstrate with T06 and other same-time tests that the **observable domain outcome AND event trace** meet the selected semantics. If simple native processes cannot enforce the intended contract, either explicitly revise the domain rule and rederive the expected traces **before experiments**, or add suitable coordination. Merely sorting logged events afterwards does not count.

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

**Model 1:** six candidate stations from Lv et al. 2026 (ultrasound, ECG, blood draw, internal medicine, X-ray, ophthalmology); heterogeneous **hypothetical** P1/P2/P3 packages; continuous arrival candidates (e.g. Poisson), uncertain service durations (e.g. Gamma with assumed CV), travel-time matrix and resource capacity references. These remain candidate inputs. Verify original paper tables before transcription; batch-case inputs must not be advertised as day-to-day observed parameters. No unevidenced clinical precedence. Choose demand only after load screening `rho_j ≈ lambda Pr(package includes j) E[S_j] / capacity_j`. Start with common flow rules, B0 and the FCFS queue baseline. Once Model 1 has been verified and its input provenance reviewed, it can support comparisons of subsequently specified queue policies without requiring Model 2 first.

The existing synthetic package lists are provisional examples. Packages may instead be drawn from checked primary literature or authentic hospital-published lists, recording source/URL, table/page or access date, original items, station mappings and adaptations. Package lists alone do not establish package proportions, clinical precedence, arrival patterns or service durations.

**Model 2:** possible behavioural extensions to assess, not mandatory prerequisites for all queue-policy evaluation. B0 always accepts; candidate B1 accepts with hypothetical configurable probability or selects another eligible station; candidate B2 uses hypothetical observed/perceived state and tolerance. Behavioural inputs and rules require separate review and verification/validation. Pre-queue recommendation override is **not** equivalent to switching after already joining a queue, nor is either the station's selection of the next patient. Consult Li et al. 2025 full study before attributing exact switching timing or a response function to it. Mid-queue switching deferred.

## 7. RQ2 Queue Scheduling Policy evaluation (deferred)

RQ2 asks which already-queued patient a station serves next when capacity becomes available, from the centre's operational perspective. FCFS is the only defined baseline; other existing queue scheduling policies are **pending selection**, primary-source review and precise specification. Fixed route, shortest observed queue and shortest estimated waiting time as next-station choices are routing/flow policies, not interchangeable names for station queue scheduling. Hold flow rules and B0 common for initial queue-policy comparisons; any later behavioural extension is a separately controlled question.

For each later queue policy, define permitted observations, the selected waiting-patient rule and ties. Distinguish an observable service-time estimate from a future realized service duration; the latter must not be used to make decisions. Any reproduction must be checked for fidelity or explicitly described as literature-inspired. No new algorithm or priority-queue implementation is specified at this stage.

Compare matched exogenous arrivals, packages and per-patient/station service demands; same global random seed alone does not guarantee matched random streams when policies change event order. Multiple independent replications and uncertainty intervals remain planned. Candidate outcomes include waiting time, cycle time, device/resource utilization, completion count or throughput, clearance time and fairness. Their precise definitions, units, population/groups, time windows, denominators and experimental scenarios remain open and must be agreed before experiments. No policy ranking or behavioural effect is presumed.

## 8. Status

Model 0 v1.1: **design baseline on `main`**. Implementation and tests are on the development branch. See [project progress](../PROJECT_PROGRESS.md) for the verification evidence and outstanding checks.
Model 1 and Model 2: candidate design only, not calibrated or validated.
RQ2: station queue-scheduling focus specified; FCFS baseline defined, other policies and experiment details pending. Model 2 is an optional behavioural extension, not a universal RQ2 prerequisite.
Research experiments and empirical validation are pending.
