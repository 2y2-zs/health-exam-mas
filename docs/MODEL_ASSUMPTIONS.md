# Model Assumptions & Evidence Register v1.3

**Project:** PSP305 — Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres

**Status:** Working design and evidence register. See [project progress](../PROJECT_PROGRESS.md) for implementation and verification evidence.  
**Updated:** 2026-11-20

## 1. Purpose and evidence labels

This register makes every consequential design choice traceable and distinguishes **(a) what a source actually reports**, **(b) what we adapt from it**, and **(c) what remains a hypothetical scenario**.

Evidence types:
- **L-DATA — Literature-reported case data:** a published case's observed/reported numerical inputs; limited to the original setting. Primary tables must be checked before transcription.
- **H-PUBLIC — Hospital-published information:** an authentic public hospital source, such as a package list; supports only the stated items and setting, not unreported operational data. Check the source and record its URL/access date before use.
- **L-MECHANISM — Literature-supported mechanism:** a paper demonstrates or discusses a design concept, but does *not* necessarily validate our particular implementation.
- **DESIGN — Project design choice:** proposed integration, interface or simplification, not directly established by the citation.
- **SYNTHETIC — Artificial verification input:** invented solely to verify software behaviour.
- **ASSUMPTION — Uncalibrated experimental parameter:** use only with sensitivity tests or subsequent calibration.
- **TO-CONFIRM — Operational rule or source detail not yet independently verified.**

**Evidence status.** `identified` records a relevant source. `needs-primary-check` and `needs-hospital-check` identify missing source or local evidence. `source-checked` applies to a specific passage, table or public page. A development check records a software result for one implementation and commit. `verified-in-code` requires student-led verification. `validated-empirically` requires comparison with relevant observations. Record these statuses separately for each claim.

## 2. Core research and modelling decisions

| ID | Choice | Evidence type | Grounding and limits | Status / next action |
|---|---|---|---|---|
| R01 | Ongoing daily health examination centre, with sequential/walk-in arrivals | DESIGN | Deliberately different from Lv et al. 2026 **batch centralized** examination case. Its batch input does not establish our daily arrival process. | Confirm operational pattern with supervisor / partner centre |
| R02 | 50% Agent simulation/verification, 40% existing-policy evaluation, 10% optional improvement | DESIGN | Agreed project scope, not a literature statistic. | Retain unless supervisor changes scope |
| R03 | Patient and Examination Station/Resource agents, with queue scheduling separated from Routing/flow decisions | L-MECHANISM + DESIGN | Munavalli et al. 2020 motivates multi-agent real-time clinic coordination; our decomposition and decision interfaces are project choices. Patient state, heterogeneity, observable information, decisions/actions and interactions are central; complex behaviour is not mandatory. | Specify service-selection and next-station interfaces and observation boundaries |
| R04 | Discrete-event clock underneath agent decisions, Python + SimPy | L-MECHANISM + DESIGN | Hybrid discrete-event and agent-based work exists in physical examination centres (Ying & Kittipittayakorn 2018). The Python/SimPy implementation choice is ours, not the cited paper's implementation. | Retain Model 0 verification gate before stochastic extensions |
| R05 | Patient state/requirements -> common legal flow -> queue entry -> station service selection -> updated patient/resource states | DESIGN; optional behaviour informed by L-MECHANISM | Queue Scheduling selects who is served next; Routing selects the next station. Pre-queue override remains an optional unvalidated hypothesis. Li et al. 2025 does not establish our pre-queue choice rule. | Keep flow and B0 common for initial queue-policy comparisons; assess B1/B2 separately |
| R06 | Multiple exam packages and heterogeneous required tests | L-MECHANISM + DESIGN; candidate L-DATA / H-PUBLIC inputs | Ho et al. 2021 supports modelling differentiated exam sets/resources, not our synthetic P1–P3 lists. Checked literature or authentic hospital-published packages are acceptable sources. | Record source, items, station mapping and adaptations; do not infer package mix or operating data |
| R07 | Existing Queue Scheduling Policies compared from an operational perspective under a common environment | DESIGN; policy sources need checking | FCFS is the only confirmed baseline. Chiu & Yeh 2010 and Jain et al. 2022 must be checked for their actual decision objects/rules before any queue-policy attribution; “scheduling” alone is insufficient. | Select other candidates later; define service-selection information and source fidelity |

## 3. Model 0: synthetic software-verification fixture

Model 0 uses synthetic patients, stations and times so that a reader can derive a complete day by hand. The rules below apply to Model 0. Each row gives the rule, its purpose or source, the limit of that evidence, a check, and what remains open. Case links lead to development assertions. The [verification plan](VERIFICATION_PLAN.md) gives the expected traces and invariants I1–I9. The [development record](../PROJECT_PROGRESS.md#recorded-development-checks) and the student's pending Gate 1 acceptance are tracked separately.

### Patients, routes and time inputs

| ID | Rule | Basis and purpose | Scope of evidence | Check | Follow-up |
|---|---|---|---|---|---|
| M0-01 | The full fixture has stations A, B and C. | SYNTHETIC. Three locations allow alternate routes and shared bottlenecks. | Smaller harnesses isolate individual mechanisms. | [T01], [T03], [T08] | Identify actual stations for Model 1. |
| M0-02 | A and B each have one server. C has two interchangeable servers. | SYNTHETIC. Three requests at C exercise both parallel service and a wait. | T03 sends all three directly to C with test-only C packages. Arrivals through B would reach C at different times. | [T03], I1 | Check staffed capacity by time of day in Model 1. |
| M0-03 | Service lasts exactly 4, 3 and 5 minutes at A, B and C respectively. | SYNTHETIC. These values make service, travel and waits independently calculable. | Numerical verification fixture only. | [T01], [T03], [T05] | Obtain measured service intervals for Model 1. |
| M0-04 | P1 requires {A,B}, P2 {B,C} and P3 {A,B,C}. Each patient maintains their own required and completed sets. | SYNTHETIC. Different sets exercise patient heterogeneity and competing demand. | The item sets carry no clinical meaning. | [T05], [T07], I3 | Map real package items to Model 1 stations. |
| M0-05 | Fixed routing chooses the first unfinished station on P1 A→B, P2 B→C or P3 A→B→C. | DESIGN + SYNTHETIC. A predictable next destination isolates station scheduling. | Uses the patient's package and completed exams. Queue length and future service information play no part in this decision. | [T01], [T05], [T07] | Keep the flow rule common in initial queue-policy comparisons. |
| M0-06 | Only P3 has a hard predecessor, A before C. An unfinished exam is eligible when all its predecessors are complete. Check each recommendation before travel. | SYNTHETIC. With P3, B is eligible at entry and both B and C are eligible after A. | The test-only A→C→B route is legal. Recommending C first is an error with no C visit. | [T04 negative], [T04 positive], I4 | Source each proposed real precedence separately. |
| M0-07 | Travel takes 1 minute A↔B and B↔C, 2 minutes A↔C, and 0 from entry to the first station or within a station. Routing and B0 decisions take 0 minutes. | SYNTHETIC + DESIGN. This separates walking, waiting and service in a hand trace. | No server or queue place is reserved during travel. | [T01], [T04 positive], [T05], I5 | Identify travel start/end and any remote queue registration in Model 1. |
| M0-09 | B0 accepts every legal recommendation. The patient progresses through ARRIVED, NEEDS_ROUTING, DECIDING, TRAVELLING, WAITING and IN_SERVICE, then needs routing again or becomes FINISHED. | DESIGN. State and chosen/recommended station can be checked at each interaction. | B0 removes behavioural variation during verification. B1/B2 remain hypotheses (§5). | [T01], [T04 negative], [T07], I2–I4 | Check chosen equals recommended on the student's traces. |
| M0-10 | Each test specifies arrival times and patient identities. Registration requires a unique patient ID and a finite nonnegative time at or after the current clock time. | SYNTHETIC + DESIGN. Hand-specified demand permits independent replay. An invalid time must leave the ID available. | A valid time after cutoff still schedules an admission attempt. The fixture supplies no arrival-rate estimate. | [Arrival guards], [duplicate ID], [past time], [T09] | Source daily arrivals separately for Model 1. |

### Station queue and service

| ID | Rule | Basis and purpose | Scope of evidence | Check | Follow-up |
|---|---|---|---|---|---|
| M0-08 | Each station selects the earliest queued patient (FCFS). Routing selects a destination separately. | L-MECHANISM + DESIGN. Chen et al. explicitly model FIFO in screening waiting areas. [Simulation assumptions, item 2][Chen] | Precedent for the baseline in a high-end screening model. Local priority and appointment exceptions remain unknown. | [T02], [T06], I6 | Confirm who can be called ahead at one Model 1 station. |
| M0-08a | A patient obtains a place at the destination when travel ends and the station commits QUEUE_ENTRY at that timestamp. Station wait = SERVICE_START time minus QUEUE_ENTRY time, including zero. | DESIGN. Keeps time spent moving separate from time eligible to be served. | In T05, A releases at 4, B queue entry is at 5 and B service starts at 7. B waiting time is 2 minutes. | [T01], [T05], I5 | Establish the event that actually grants queue position (§7). |
| M0-08b | Merge all new entries for a station at the current time. Order ties by stable patient rank. People already waiting keep their places. | DESIGN. Equal-time ordering makes a hand trace reproducible across registration orders and arrival sources. | Rank is synthetic. The coordinator uses patient ID as a final fallback for equal ranks. The cited scenarios use distinct ranks. | [T02], [T06], [mixed B], I6 | Ask about queue sequence and timestamp precision before selecting a Model 1 tie rule. |
| M0-08c | Each station has one unbounded waiting queue shared by its servers. Patients in service are excluded. Dispatch immediately while an eligible patient and an idle server are available. | DESIGN. Waiting and busy counts can be reconciled independently. | Assumes identical servers at a station, continuous availability and no waiting-space limit. | [T03], [T08], I1/I6 | Check actual queues, staffing and dedicated resources. |
| M0-08d | Service is non-preemptive and occupies `[start,end)`. Capacity released at t can serve another patient at t. | DESIGN. Adjacent service intervals do not double-count the server. | Model 0 omits breaks, failures, setup/cleaning, cross-station staffing and overtime limits. | [T03], [T08], I1/I5 | Check which omissions affect resource availability in Model 1. |
| M0-08e | The Station Agent owns the waiting visit, capacity grant and release. Each (patient, station, visit) can enter, start, end and release once. At most one visit per patient is active. | DESIGN. A second scheduler or a stale release could grant one server twice or reorder patients. | The coordinated station selects from its own waiting list, then requests idle SimPy capacity. Its native Resource waiting queue should remain empty. | [Station implementation], [duplicate entry], [T08], I2/I8 | Check queue ownership and stale releases at Gate 1. |

### Simultaneous events, closure and trace checks

| ID | Rule | Basis and purpose | Scope of evidence | Check | Follow-up |
|---|---|---|---|---|---|
| M0-11 | At each timestamp process (0) service ends, (1) releases and progress updates, (2) admissions, (3) travel and routing, (4) queue entries, then (5) service starts. | DESIGN. Patients can act on released capacity and committed state. [SimPy scheduling] explains why same-time engine events still run sequentially. | The six phases are a project convention. The coordinated path implements them. A global coordinator is an implementation choice. | [T06], [T10], I9 | Compare the actual raw trace with the independent timeline. |
| M0-11a | In phase 3 finish due positive-time travel, handle new admissions' entry routes and zero-time travel, record final departures, then start continuing patients' onward travel. Use stable rank within each group. | DESIGN. A journey already underway and a new entry can reach the same station together. Grouping preserves their causal history. | At B at t=5 the sample travel completions are u2 then u1. Phase 4 commits stations A/B/C in order and applies M0-08b at each station. B queues u1 then u2, who start at 5 and 8. | [mixed B], [T06], I6/I9 | Derive travel, queue and service orders separately at Gate 1. |
| M0-11b | Admit arrivals at or before cutoff H. Record and reject later attempts. All admitted patients may finish after H. | DESIGN. Makes admission at the boundary and workload remaining after closure observable. | H=4 is specific to T09. Rejected attempts have no visits and are counted separately. | [T09], I7 | Obtain intake and end-of-service practice for Model 1. |
| M0-11c | On release, record the completed exam, clear visit ownership and update the patient's state before the next decision. After the final release, log departure and allow no further requests. | DESIGN. A patient can continue only after the preceding visit is fully committed. | A final release sets FINISHED in phase 1. The departure record follows in phase 3 of that timestamp. | [T01], [T07], [T08], I2/I3/I8 | Reconcile each admitted patient's completed exams and departure. |
| M0-11d | End a normal run when all attempts are processed, all admitted patients have departed and queues, travel and resources have drained. Report stalled work if the calendar is empty earlier. | DESIGN. Ensures admitted = active + finished and prevents premature termination. | T04's deliberately rejected recommendation is a negative test with no successful drain requirement. | [T09], [stalled run], I7 | Reconcile patient and resource counts at Gate 1. |
| M0-12 | Use one time unit, unique managed station IDs, positive capacities and service times, and nonnegative travel times. Before running, check each registered route visits each required, managed station once and respects all in-package predecessors. | DESIGN. Preflight catches missing stations, repeats and cycles before the first admission. Runtime eligibility is checked separately (M0-06). | The linked negative cases exercise arrival/package and registry checks. An invalid package for a later arrival stops the run before the first admission. | [Package guards], [registry checks], [T04 negative], I3/I4 | Audit numerical station/travel configuration coverage separately from the package checks. |
| M0-13 | Log committed events in order with time, sequence, phase or ordering marker, patient, station/visit, state change, recommendation/choice and ownership identifiers as applicable. Compare two fresh runs in original order. | DESIGN. An audit trace must distinguish “ended travel” from “joined queue” and expose same-time errors even when finish times agree. | Exclude run ID and wall-clock metadata from deterministic comparisons. T10 uses the T06 inputs. | [T10], [mixed B], I9 | Retain raw and normalized traces with the commit and environment. |

[T01]: ../tests/test_model0_entry_acceptance.py#L20
[T02]: ../tests/test_model0_entry_acceptance.py#L204
[T03]: ../tests/test_model0_ab_coordinator.py#L5690
[T04 negative]: ../tests/test_model0_ab_coordinator.py#L5787
[T04 positive]: ../tests/test_model0_ab_coordinator.py#L5820
[T05]: ../tests/test_model0_ab_coordinator.py#L5883
[T06]: ../tests/test_model0_entry_acceptance.py#L621
[T07]: ../tests/test_model0_ab_coordinator.py#L5614
[T08]: ../tests/test_model0_entry_acceptance.py#L894
[T09]: ../tests/test_model0_ab_coordinator.py#L5988
[T10]: ../tests/test_model0_entry_acceptance.py#L954
[mixed B]: ../tests/test_model0_coordinated_arrivals.py#L16
[Arrival guards]: ../tests/test_model0_coordinated_arrivals.py#L45
[Package guards]: ../tests/test_model0_coordinated_arrivals.py#L69
[registry checks]: ../tests/test_model0_ab_coordinator.py#L149
[duplicate ID]: ../tests/test_model0_ab_coordinator.py#L1809
[past time]: ../tests/test_model0_ab_coordinator.py#L1904
[duplicate entry]: ../tests/test_model0_ab_coordinator.py#L3640
[stalled run]: ../tests/test_model0_ab_coordinator.py#L5410
[Station implementation]: ../src/health_exam_mas/model0_station.py#L231
[Chen]: https://link.springer.com/article/10.1186/s12913-021-06949-5
[SimPy scheduling]: https://simpy.readthedocs.io/en/stable/topical_guides/time_and_scheduling.html

## 4. Model 1: candidate examination-centre configuration

These are **candidate** inputs, not yet a validated day-to-day centre dataset.

| ID | Parameter | Candidate setting | Type / original context | Verification need |
|---|---|---|---|---|
| M1-01 | Six examination stations | Ultrasound (US), ECG, blood draw, internal medicine, X-ray, ophthalmology | L-DATA + DESIGN; subset selected from Lv et al. 2026 centralized case | Table 12 station labels checked on 2026-11-20. Confirm target-centre scope. |
| M1-02 | Rooms/devices reported in the batch case | US=4, ECG=2, Blood=3, Internal=1, X-ray=1, Ophthalmology=1 | L-DATA, source-checked against Lv et al. Table 12 on 2026-11-20 | Confirm simultaneous staffing before treating rooms/devices as operational capacity. |
| M1-03 | Mean exam time, minutes, case-specific | US male 7.32 / female 11.37; ECG 3.00; Blood 0.80; Internal 1.25; X-ray 1.00; Ophthalmology 1.30 | L-DATA, source-checked against Lv et al. §6.2 and Table 12 on 2026-11-20. Means from small field samples (5–6 examinees per item). | Check transfer to the daily setting. Variability needs separate evidence. |
| M1-04 | Directed inter-item travel-time matrix | Candidate six-station submatrix of Lv et al. 2026 case | L-DATA + DESIGN; asymmetric values possible | Verify original Table 11 and extraction before storing numbers in configuration |
| M1-05 | Earlier synthetic P1/P2/P3 package candidates; sourced packages may replace them after checking | P1=Blood+ECG+Internal+Ophthalmology; P2=P1+X-ray; P3=P2+Ultrasound remain unconfirmed examples | ASSUMPTION; checked literature or authentic hospital-published lists may provide L-DATA / H-PUBLIC item inputs | Record source, item-to-station mapping, omissions/aggregation and assumptions; package proportions, arrivals and service durations require separate evidence |
| M1-06 | Clinical precedence | No assumed clinical order by default; configurable verified constraints | TO-CONFIRM | Obtain medically/operationally grounded rules; do not infer from test fixture |
| M1-07 | Arrival process | Initially homogeneous Poisson; later time-varying arrivals if evidenced | ASSUMPTION, **not** established by Lv batch arrival case | Collect timestamps or compare plausible alternative arrival processes |
| M1-08 | Demand-rate scenarios | 20 / 35 / 45 examinees per hour were discussed as **tentative stress-test values** | ASSUMPTION, not empirical operating rates | **Do not freeze** without capacity/load check; vary demand systematically |
| M1-09 | Service-duration variability | Deterministic then hypothetical Gamma distribution with CV=0.2 or 0.4 in sensitivity scenarios | ASSUMPTION; Lv case mean values do NOT identify a Gamma shape or CV | Fit from repeated durations if possible; otherwise label scenarios synthetic |
| M1-10 | Queue discipline | One shared queue per station, parallel servers; FCFS confirmed baseline, other policies undecided | DESIGN | Verify real queue organization; keep service selection separate from routing |
| M1-11 | Service interruption | No preemption, no failures initially | DESIGN simplification | Revisit only if operationally material |
| M1-12 | Intake cutoff | Example 480 min for admitting patients; continue model until admitted patients complete | ASSUMPTION / experiment convention | Check actual opening hours; report late-service and clearance time |
| M1-13 | Patient demographics / ultrasound timing | Sex-dependent case means possible, but do **not** import Lv's batch cohort composition as a daily-centre population model | L-DATA + ASSUMPTION | Obtain representative demographics or report scenario dependence |

**Load sanity check, before choosing arrival rates:** for each station j, approximate offered load `rho_j = arrival_rate * Pr(package includes j) * mean_service_time_j / capacity_j`, with consistent time units. This is only a first-order screening formula; it does not replace the simulation.

## 5. Model 2: autonomous patient behaviour

Model 2 explores optional behaviour beyond B0. The observation and behavioural hypotheses below require their own evidence. [Research context](RESEARCH_CONTEXT.md#decision-scope-and-proposed-research-mechanism)

| ID | Behaviour | Type | Evidence and limitation | Verification / validation |
|---|---|---|---|---|
| B0 | Always obey a legal recommendation | DESIGN baseline | Operational compliance simplifying assumption, not necessarily actual behaviour | Confirm chosen==recommended in all B0 traces |
| B1 | Independent acceptance with patient-specific probability p; if reject, choose a different **eligible** next station | ASSUMPTION | Do not use Li 2025 as proof of any specific p or independence assumption | Explore sensitivity; no legal alternative => recommended station |
| B2 | State-dependent choice using perceived queue/wait, travel and individual tolerance/preferences | L-MECHANISM + ASSUMPTION | Li 2025 motivates examining behaviour and queues, but the proposed perceived-cost equation and weights are **our candidate rule**, not a published fitted Li model | Define observable information, functional form and parameter provenance |
| B3 (deferred) | Leave a queue after having joined it (true queue switching) | L-MECHANISM; deferred implementation | Closer to Li 2025, but may require cancellation/priority/order changes and operational permission | Check when queue entry and exit occur, including whether the queue is physical or virtual. Research separately |

Observation boundary: agents cannot access future realized random service times. Specify whether “queue length” includes active service and whether expected incoming travellers are observable. Routing agent and patient perceived information need not be identical.

## 6. Evaluation assumptions (RQ2)

Keep routing and B0 common in the initial comparisons. [Research scope](RESEARCH_CONTEXT.md#decision-scope-and-proposed-research-mechanism)

| ID | Decision | Evidence classification | Open issue |
|---|---|---|---|
| E01 | FCFS is the only confirmed Queue Scheduling baseline; other policies remain undecided | DESIGN | Identify candidate service-order rules, their information requirements, tie-breaks and primary sources before selection |
| E02 | Consider additional existing queue scheduling policies only after source/decision-object checks | DESIGN; candidate L-MECHANISM subject to checking | Do not infer queue-policy evidence from a routing/batch-scheduling paper or from its title; distinguish reproduction from an explicitly labelled adaptation |
| E03 | Initial comparisons may use verified Model 1, common flow and B0; optional B1/B2 extensions require separate assessment/verification | DESIGN | Do not make Model 2 a prerequisite or freeze behavioural factors and demand scenarios now |
| E04 | Keep exogenous randomness paired between strategies | DESIGN experimental control | Same seed alone is insufficient if strategies consume RNG differently; use keyed streams / prerecorded arrivals, packages and per-patient per-station service samples |
| E05 | Candidate outcomes: waiting (e.g., mean/P95), cycle time, equipment/resource utilization, completion at cutoff, clearance time and fairness | DESIGN; definitions not frozen | Select appropriate measures and define unit of analysis, time windows, censoring, denominators and fairness interpretation before experiments |
| E06 | Independently repeated stochastic scenarios and uncertainty estimates | DESIGN | Specify replication count / interval computation before final evaluation |
| E07 | Assess whether behaviour changes policy performance or ranking | **Unproven research hypothesis** | Do not presume ranking changes or significant effects |

## 7. Priority evidence gaps and mitigation

Start with these three questions for one named daily centre. Record the site, station or package, date/version and precise meaning of each timestamp or item. A source check applies only to the claim cited. Use approved, de-identified records if available.

| Priority / related rules | Evidence available, checked 2026-11-20 | What to obtain for Model 1 | If local evidence is unavailable |
|---|---|---|---|
| 1. When does a patient obtain queue position? M0-08/08a/08b, M1-10 | Jiangmen Wuyi Hospital describes a doctor sending the patient to the next room through its calling system. The description leaves the exact queue-entry trigger and tie rule open. [Hospital workflow, “智能导检系统有什么用呢？”](https://www.51ht.com/ksjs/qt/tjk_13079/ksdt_13185/202209/t662465.html) | For one new arrival and one transfer at the same station, ask staff which event grants a place. Where permitted, match referral/push, physical check-in or scan, ticket sequence, call and service start. Record time precision, priority exceptions and what happens when a patient has yet to arrive. | Label entry on arrival as an assumption. If remote entry is plausible, assess its effect on queue order and measured waiting in a separate scenario. |
| 2. Which exams does each package require? R06, M1-05/06 | The National Taiwan University Hospital Health Management Center lists the items in a dated women's basic package. Ho et al. relate their centre's sets to resources (Tables 2 and 13). [Hospital package list](https://hmc.ntuh.gov.tw/examination-items-and-pricing/0m246043633122453305) · [Ho et al.](https://doi.org/10.1186/s12913-021-07148-y) | Record a current target-centre list, inclusion/optional status, item-to-station mapping and omissions or grouping. Record service order constraints and package uptake from separate evidence. | Use a named published package as a scenario. Label local station mapping, assumed mix and any adaptations individually. |
| 3. How long is a station occupied? M0-03/08d, M1-02/03/09 | Chen et al. describe room-entry/exit sensors and exclusions, and give fitted inputs in Table 4. Lv et al. §6.2 and Table 12 report mean exam durations and room/device counts in a batch setting. [Chen et al.][Chen] · [Lv et al.](https://doi.org/10.1002/hsr2.72912) | Obtain matched service start/end times by exam, time units, sample size and time of day. Ask whether preparation or cleaning holds the resource and which rooms are staffed. Check missing scans and distinguish time in the room from time receiving service. | Carry each published input with its original setting and measurement definition. If only means are available, label any variability scenario as assumed. Keep inputs from different centres identifiable. |

Other evidence gaps remain open. Obtain arrival times and package frequencies to estimate daily demand. Check the original Table 11 travel entries before transcribing a station subset. Review Li et al. for observed queue switching before specifying B1/B2, and check each candidate RQ2 policy's decision object, permitted observations, tie rule and fairness measures. The [verification plan](VERIFICATION_PLAN.md) covers independent derivation and testing of the Model 0 rules.

## 8. Reference register

The literature library records full references and their original research settings. Rule-level evidence and limits are linked in the tables above. [Literature library](LITERATURE_LIBRARY.md)

## 9. Model 0 v1.1 decisions and evidence status (2026-11-05)

<details>
<summary>Earlier decision IDs and their current rules</summary>

| v1.1 ID | Decision | Current rule or record |
|---|---|---|
| V11-01 | Replaceable fixed route | M0-04/05 |
| V11-02 | Independent hard precedence and legal alternatives | M0-06, M0-12 |
| V11-03 | C-only competition fixture | M0-02, [T03] |
| V11-04 | Shared queue, stable rank, homogeneous servers and non-preemption | M0-02, M0-08 through M0-08d |
| V11-05 | Zero-time decisions, travel without reservation and half-open service intervals | M0-07, M0-08a/08d |
| V11-06 | Same-time domain event order | M0-11/11a/11c, M0-13 |
| V11-07 | Choice of SimPy coordination mechanism | M0-08e, M0-11 and [development record](../PROJECT_PROGRESS.md#recorded-development-checks) |
| V11-08 | Inclusive admission cutoff and drain | M0-10, M0-11b/11d |
| V11-09 | Visit ownership and release authority | M0-08e, M0-11c |
| V11-10 | Independent manual expectations for T01–T10 | M0-13 and [required student evidence](VERIFICATION_PLAN.md#3-evidence-required-for-each-student-run-test) |
| V11-11 | Record SimPy version and resource/dispatch approach for formal acceptance | M0-08e and [implementation gate](#implementation-gate) |

</details>

### Implementation gate

Gate 1 requires the actual environment, commit, independently derived expectations and ordered logs. [Current results and open issues](../PROJECT_PROGRESS.md#recorded-development-checks) · [Required student evidence](VERIFICATION_PLAN.md#3-evidence-required-for-each-student-run-test)

### Research direction update (2026-11-10)

[Agreed research questions](RESEARCH_CONTEXT.md#research-allocation-and-questions)

## 10. Update procedure

For each rule, record its ID, applicable model, prior and new values, rationale or source, impact on agents and tests, and verification or validation status. Date source checks and link recorded results to the tested commit. [Specification](MODEL_SPEC.md) · [Verification plan](VERIFICATION_PLAN.md)
