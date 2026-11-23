# Model Assumptions & Evidence Register v1.2

**Project:** PSP305 — Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres

**Status:** Working design and evidence register. See [project progress](../PROJECT_PROGRESS.md) for implementation and verification evidence.  
**Updated:** 2026-11-24

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

**Evidence status:** `identified` = relevant publication known; `needs-primary-check` = exact item/table/formulation should be verified from full original source; `source-checked` = the particular claim has been checked against the original text/table, not every claim in that paper; `needs-hospital-check` = requires partner process/data. `verified-in-code` and `validated-empirically` must only be used after student-led work actually establishes them. Current verification evidence is recorded in the [project progress report](../PROJECT_PROGRESS.md).

**Method basis reviewed on 2026-11-24:** [ODD (Grimm et al., 2020)](https://doi.org/10.18564/jasss.4259), §1.4/§2.3 and §3.6–3.8, supports describing agents, process order, inputs and design rationale; [STRESS (Monks et al., 2019)](https://doi.org/10.1080/17477778.2018.1442155), Table 4 and §5.4–5.6, supports transparent logic, provenance, random sampling and experiment reporting; [Collins et al. (2024)](https://doi.org/10.18564/jasss.5258), §2.3/§4.29–4.32, supports purpose-specific Verification/Validation and iterative evidence. These are methodological support, not hospital evidence for our numbers, six-phase order or B1/B2. They do not change existing DESIGN, SYNTHETIC or ASSUMPTION labels. Reading boundaries are in [LITERATURE_LIBRARY](LITERATURE_LIBRARY.md).

## 2. Core research and modelling decisions

| ID | Choice | Evidence type | Grounding and limits | Status / next action |
|---|---|---|---|---|
| R01 | Ongoing daily health examination centre, with sequential/walk-in arrivals | DESIGN | Deliberately different from Lv et al. 2026 **batch centralized** examination case. Its batch input does not establish our daily arrival process. | Confirm operational pattern with supervisor / partner centre |
| R02 | 50% Agent simulation/verification, 40% existing-policy evaluation, 10% optional improvement | DESIGN | Agreed project scope, not a literature statistic. | Retain unless supervisor changes scope |
| R03 | Patient and Examination Station/Resource agents, with queue scheduling separated from Routing/flow decisions | L-MECHANISM + DESIGN | Munavalli et al. 2020 motivates coordination but describes passive Patient Agents; our decomposition/interfaces remain project choices. ODD/STRESS support explicit state, heterogeneity, permitted information, decisions and interactions, not a claim of validated autonomy. | Specify service-selection and next-station interfaces and observation boundaries; no compulsory complex behaviour |
| R04 | Discrete-event clock underneath agent decisions, Python + SimPy | L-MECHANISM + DESIGN | Kittipittayakorn & Ying 2016 provides a full-text DES + ABS precedent in orthopedics; Ying & Kittipittayakorn 2018 is an examination-centre lead with full text still unavailable. Python/SimPy is our implementation choice. | Retain Model 0 verification gate before stochastic extensions; do not infer unseen implementation details from P12 metadata |
| R05 | Patient state/requirements -> common legal flow -> queue entry -> station service selection -> updated patient/resource states | DESIGN; optional behaviour informed by L-MECHANISM | Queue Scheduling selects who is served next; Routing selects the next station. Pre-queue override remains an optional unvalidated hypothesis. Li et al. 2025 does not establish our pre-queue choice rule. | Keep flow and B0 common for initial queue-policy comparisons; assess B1/B2 separately |
| R06 | Multiple exam packages and heterogeneous required tests | L-MECHANISM + DESIGN; candidate L-DATA / H-PUBLIC inputs | Ho et al. 2021 supports modelling differentiated exam sets/resources, not our synthetic P1–P3 lists. Checked literature or authentic hospital-published packages are acceptable sources. | Record source, items, station mapping and adaptations; do not infer package mix or operating data |
| R07 | Existing Queue Scheduling Policies compared from an operational perspective under a common environment | DESIGN + candidate L-MECHANISM | FCFS is the only confirmed baseline. Lin et al. 2017 D3 and Chen et al. 2024 explicitly select the next queued patient; Chiu & Yeh 2010 is Routing, while Jain 2022/Zuo 2024 use joint decisions. | SPT/LST/SERPT registered as candidates only; define service-selection information, ties and source fidelity before selection |

## 3. Model 0: synthetic software-verification fixture

**Every item in this section is SYNTHETIC; none is a medical-centre observation or clinical recommendation.**

| ID | Parameter / rule | Proposed fixture | Why it is used | Design status |
|---|---|---|---|---|
| M0-01 | Stations | A, B, C | Small independently checkable environment | Design-only |
| M0-02 | Capacities | A=1, B=1, C=2 | Test single/multi-server constraints | Design-only |
| M0-03 | Service times | A=4, B=3, C=5 minutes, deterministic | Hand-computable event traces | Design-only |
| M0-04 | Packages | P1={A,B}, P2={B,C}, P3={A,B,C} | Exercise heterogeneous job sets | Design-only |
| M0-05 | Fixed-route baseline | P1: A->B; P2: B->C; P3: A->B->C | Initial routing-policy fixture; **not** a clinical hard constraint or a queue-policy baseline | Design agreed in §9 |
| M0-06 | Precedence example | A must finish before C may begin for P3 | Test legality independently of routing policy; fictitious | T04 negative/positive semantics specified in §9 |
| M0-07 | Travel times | A<->B=1; B<->C=1; A<->C=2 minutes; entry->first=0 | Verify travel events and time accounting | Design-only |
| M0-08 | Queue discipline | Shared FCFS queue; non-preemptive service | Minimal resource model | Design-only |
| M0-09 | Patient behaviour | B0 full recommendation compliance | Isolate event and capacity correctness | Design-only |
| M0-10 | Arrivals | Explicit deterministic times | Independent manual expected outcomes | Candidate test schedules/traces documented; student must independently recalculate (§9) |
| M0-11 | Same-time event ordering, cutoff boundary | Provisional: completions/releases ahead of new admission/queue actions; admit at time <= cutoff | Make expected traces reproducible | **TO-CONFIRM** implementation feasibility and precise priorities in SimPy |

**Test-design clarification (specified in §9):** Three arrivals at the centre do not necessarily imply three simultaneous arrivals at C when every route goes through B. Resource test T03 uses three simultaneous *eligible service requests at C* in a station-level fixture. T04 includes rejection of an illegal next exam and a positive legality check; simply following the fixed order is insufficient. The student must independently derive expected event times.

### Fixed route vs precedence

A routing policy chooses *which* eligible exam to visit next; a precedence graph defines which exams are *allowed*. Queue scheduling separately selects *which waiting patient* is served next at a station. Never silently equate an A->B->C fixed-route policy with medical precedence A->B->C. In Model 0 the only example hard constraint is A-before-C for P3, unless a test explicitly sets a different synthetic graph.

## 4. Model 1: candidate examination-centre configuration

These are **candidate** inputs, not yet a validated day-to-day centre dataset.

| ID | Parameter | Candidate setting | Type / original context | Verification need |
|---|---|---|---|---|
| M1-01 | Six examination stations | Ultrasound (US), ECG, blood draw, internal medicine, X-ray, ophthalmology | L-DATA + DESIGN; subset selected from Lv et al. 2026 centralized case | Confirm exact case tables and nomenclature |
| M1-02 | Parallel capacities in that case | US=4, ECG=2, Blood=3, Internal=1, X-ray=1, Ophthalmology=1 | L-DATA **reported in prior research notes**, not independently re-transcribed for this register | Cross-check original Table 12; do not generalize to all centres |
| M1-03 | Mean exam time, minutes, case-specific | US male 7.32 / female 11.37; ECG 3.00; Blood 0.80; Internal 1.25; X-ray 1.00; Ophthalmology 1.30 | L-DATA **reported in prior research notes**; published means ≠ distributions | Cross-check units, population and original Table 12 |
| M1-04 | Directed inter-item travel-time matrix | Candidate six-station submatrix of Lv et al. 2026 case | L-DATA + DESIGN; directed/asymmetric values in Table 11 | Full-text review found a missing gynecology-origin row; do not invent cells or force symmetry. Check every selected submatrix entry before configuration |
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

Lv's main text and key tables were reviewed on 2026-11-23, but that does not validate a day-to-day configuration. The batch case uses limited duration samples; printed constraints (6)/(7) raise a device-ordering consistency question, not proof that the authors' implementation is wrong. Retain case-specific capacity/mean candidates and check each used cell, unit and mapping. ODD/STRESS motivate the provenance record, not the input values. If several papers are combined, report a literature-informed scenario with explicit adaptations rather than one hospital's calibrated dataset.

## 5. Model 2: autonomous patient behaviour

Patient state, heterogeneous requirements/attributes, observable information, decisions/actions and interactions belong to RQ1 from the initial model; Model 2 is an optional extension to richer behaviour, not the point at which patients first become agents. Simple explicit B0 behaviour is sufficient initially. After Model 0 verification, a verified Model 1 with common flow and B0 can support initial RQ2 queue-policy comparisons without waiting for Model 2. B1/B2 remain hypotheses to assess, not required or calibrated behaviours.

| ID | Behaviour | Type | Evidence and limitation | Verification / validation |
|---|---|---|---|---|
| B0 | Always obey a legal recommendation | DESIGN baseline | Operational compliance simplifying assumption, not necessarily actual behaviour | Confirm chosen==recommended in all B0 traces |
| B1 | Independent acceptance with patient-specific probability p; if reject, choose a different **eligible** next station | ASSUMPTION | Do not use Li 2025 as proof of any specific p or independence assumption | Explore sensitivity; no legal alternative => recommended station |
| B2 | State-dependent choice using perceived queue/wait, travel and individual tolerance/preferences | L-MECHANISM + ASSUMPTION | Li 2025 motivates examining behaviour and queues, but the proposed perceived-cost equation and weights are **our candidate rule**, not a published fitted Li model | Define observable information, functional form and parameter provenance |
| B3 (deferred) | Leave a queue after having joined it (true queue switching) | L-MECHANISM; deferred implementation | Closer to Li 2025, but may require cancellation/priority/order changes and operational permission | Research separately; not a Model 0/1 requirement |

Observation boundary: agents cannot access future realized random service times. Specify whether “queue length” includes active service and whether expected incoming travellers are observable. Routing agent and patient perceived information need not be identical.

**Li et al. 2025 source-case clarification (§4.1–4.2):** automatic queue assignment follows completion of the previous examination and occurs before physical travel; later switching requests enter the chosen queue's end, and skipped examinations remain required. This claim is source-checked from the main text, not a new Model 0 rule: Model 0 still enters its queue when travel ends. Person-level ever-switching proportions, request/queue-record proportions and observational GEE associations are not interchangeable B1/B2 decision probabilities. The separate Appendix remains unread. ODD Sensing/Observation helps document agent information versus research logs; it supplies no behaviour parameter.

## 6. Evaluation assumptions (RQ2)

RQ2 concerns service order within station queues. Fixed route, shortest observed queue and shortest estimated wait were earlier routing candidates, not queue scheduling baselines; do not relabel them. Keep routing/flow common when isolating queue-policy effects.

| ID | Decision | Evidence classification | Open issue |
|---|---|---|---|
| E01 | FCFS is the only confirmed Queue Scheduling baseline; other policies remain undecided | DESIGN | Identify candidate service-order rules, their information requirements, tie-breaks and primary sources before selection |
| E02 | SPT, LST and SERPT are sourced candidates, not final algorithms | Candidate L-MECHANISM: Lin 2017 §2.3 D3/§3.4; Chen 2024 §5.1; project selection remains DESIGN | SPT: current-station expected service demand; LST: elapsed time since centre arrival; SERPT: expected demand of all unfinished exams (call + service in Chen's case). Define permitted estimates/ties; extracting ACP ranking rules is an adaptation, not full ACP reproduction |
| E03 | Initial comparisons may use verified Model 1, common flow and B0; optional B1/B2 extensions require separate assessment/verification | DESIGN | Do not make Model 2 a prerequisite or freeze behavioural factors and demand scenarios now |
| E04 | Keep exogenous randomness paired between strategies | DESIGN experimental control | Same seed alone is insufficient if strategies consume RNG differently; use keyed streams / prerecorded arrivals, packages and per-patient per-station service samples |
| E05 | Candidate outcomes: waiting (e.g., mean/P95), cycle time, equipment/resource utilization, completion at cutoff, clearance time and fairness | DESIGN; definitions not frozen | Select appropriate measures and define unit of analysis, time windows, censoring, denominators and fairness interpretation before experiments |
| E06 | Independently repeated stochastic scenarios and uncertainty estimates | DESIGN | Specify replication count / interval computation before final evaluation |
| E07 | Assess whether behaviour changes policy performance or ranking | **Unproven research hypothesis** | Do not presume ranking changes or significant effects |

STRESS §5.5–5.6 supports documenting random streams/seeds and output uncertainty; keyed streams or prerecorded inputs remain our implementation choices. No fixed 30 replications or automatic warm-up is prescribed. Collins §3.29–3.32 supports sensitivity checks, not inference that assumed inputs are true. Hold the routing mechanism common; congestion-dependent realized routes need not be identical. Buffer/appointment/resource interventions require separate factors if queue effects are to be isolated. Metrics, thresholds (including any 20-minute waiting threshold), fairness definitions and statistical tests remain undecided.

## 7. Priority evidence gaps and mitigation

1. **Operational validity:** obtain sample day arrivals, service durations, package proportions, resource counts and station locations if supervisor's hospital collaboration permits. Record confidentiality and data constraints.
2. **Behavioural validity:** Li's main-text queue-assignment/switching timing is now checked, but the Appendix and any transfer/calibration of behavioural rules remain open; do not equate post-assignment switching with pre-queue override.
3. **Primary source transcription:** after the Lv main-text review, verify every selected capacity, mean and matrix entry before numerical use, retain table/constraint limitations, and decide whether the batch inputs fit the intended daily scenario.
4. **Verification traceability:** Model 0 v1.1 policy/constraint separation, T03/T04 and cutoff semantics are design specified in §9. Confirm the still-open event/resource implementation approach, then independently recalculate expected traces and record actual tests.
5. **Algorithm fairness:** verify sources and decision objects for queue-policy candidates; predefine shared flow, observable state, any behavioural assumptions, independent random streams, metric windows and statistical uncertainty before RQ2.
6. **Package provenance:** checked literature packages and hospital-published lists are acceptable. Record source/URL, table/page or access date, original items, model-station mapping and assumptions. Such lists do not establish arrivals, package proportions, demographics, clinical order or service durations.

## 8. Reference register

Citations below identify supporting literature for **the particular concepts noted above**; they do not imply those papers endorse the project's synthetic parameters.

This is not a verified catalogue of Queue Scheduling Policies. Retain routing, batch-scheduling and behavioural studies for their actual claims; check the original decision object and rule before attributing any station-level service-order algorithm.

- **Lv et al. (2026)**, *Optimization of Batch Centralized Health Examination Scheduling Considering Inter-Item Transition Time and Sex Differences*. https://doi.org/10.1002/hsr2.72912
- **Munavalli et al. (2020)**, *An Intelligent Real-Time Scheduler for Out-Patient Clinics: A Multi-Agent System Model*. https://doi.org/10.1177/1460458220905380
- **Ying & Kittipittayakorn (2018)**, *Combining discrete event and agent-based simulation for reducing draftees waiting time in physical examination centers*. https://ntut.elsevierpure.com/en/publications/combining-discrete-event-and-agent-based-simulation-for-reducing-/
- **Li et al. (2025)**, *When Do People Switch Queues? An Empirical Study of Discretionary Queue Switching at a Physical Examination Center*. https://doi.org/10.1111/deci.12646
- **Ho et al. (2021)**, *Overbooking for Physical Examination Considering Late Cancellation and Set-Resource Relationship*. https://doi.org/10.1186/s12913-021-07148-y
- **Chiu & Yeh (2010)**, *Fuzzy-Based Dynamic Scheduling System for Health Examination*. https://doi.org/10.1109/ICMLC.2010.5580551
- **Jain et al. (2022)**, *Improving Patient Satisfaction and Outpatient Diagnostic Center Efficiency Using Novel Online Real-Time Scheduling*. https://doi.org/10.1016/j.orhc.2022.100338
- **Kittipittayakorn & Ying (2016)**, *Using the Integration of Discrete Event and Agent-Based Simulation to Enhance Outpatient Service Quality in an Orthopedic Department*. https://doi.org/10.1155/2016/4189206
- **Lin, Ling & Yeung (2017)**, *Resource Allocation and Outpatient Appointment Scheduling Using Simulation Optimization*. https://doi.org/10.1155/2017/9034737
- **Chen et al. (2024)**, *Frontiers in Operations: Waiting Experience in Open-Shop Service Networks: Improvements via Flow Analytics and Automation*. https://doi.org/10.1287/msom.2022.0590
- **Grimm et al. (2020)**, *The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism*. https://doi.org/10.18564/jasss.4259
- **Monks et al. (2019)**, *Strengthening the reporting of empirical simulation studies: Introducing the STRESS guidelines*. https://doi.org/10.1080/17477778.2018.1442155
- **Collins, Koehler & Lynch (2024)**, *Methods That Support the Validation of Agent-Based Models: An Overview and Discussion*. https://doi.org/10.18564/jasss.5258

## 9. Model 0 v1.1 decisions and evidence status (2026-11-05)

This section supersedes any earlier v1.0 phrasing on Model 0 policy, precedence and test semantics. For full rules see [MODEL_SPEC.md](MODEL_SPEC.md); for test inputs/expected traces see [VERIFICATION_PLAN.md](VERIFICATION_PLAN.md).

| ID | Updated statement | Evidence class | Status / caveat |
|---|---|---|---|
| V11-01 | Fixed Route is a **replaceable routing policy** and not a clinical precedence graph. P1 A→B, P2 B→C, P3 A→B→C are default synthetic policy routes. | SYNTHETIC + DESIGN | **Design agreed**; implement/test separately from eligibility |
| V11-02 | Hard precedence for P3 is only **A-before-C**. Initially eligible {A,B}; after A eligible {B,C}; A→C→B is legal. | SYNTHETIC | **Design agreed**; T04 includes both negative and positive checks |
| V11-03 | Three simultaneous requests to capacity-2 C require C-only **test fixture** (T03), not three ordinary P2 arrivals upstream of B. | SYNTHETIC | **Design agreed**; avoids invalid test setup |
| V11-04 | Stable patient rank, shared FCFS queue excluding patients in service, homogeneous servers, unlimited waiting space, non-preemptive service. | DESIGN engineering simplification | Needs actual implementation verification |
| V11-05 | Service intervals are half-open [start,end), zero-time routing/decisions, no resource reservations while travelling. | DESIGN engineering simplification | Needs actual implementation verification |
| V11-06 | Completion → release/commit → admission → travel/routing intents → queue entries → dispatch proposed for same-time event processing. | DESIGN event semantics | **Proposed domain contract; exact SimPy mechanism still TO-CONFIRM** |
| V11-07 | Native SimPy queue scheduling cannot simply be assumed to enforce all domain phases; full global six-phase coordinator is **optional**, not a compulsory development milestone. | DESIGN implementation choice | Review native process-based and minimal coordination approaches; verify T06 event trace, not just finish times |
| V11-08 | Admission attempts exactly at time H accepted; later attempts rejected, previously admitted patients continue to completion. | DESIGN synthetic cutoff convention | Test T09; do not use `env.run(until=H)` to truncate the day |
| V11-09 | One Station Agent owns each visit's queue/token/release; deny duplicate queue entry, completion and release. | DESIGN engineering invariant | Implement and independently test before claiming correctness |
| V11-10 | T01–T10 have independently checkable **candidate handwritten expected traces**. | SYNTHETIC verification oracle | Student must recalculate expected traces and record actual results for Gate 1 |
| V11-11 | The SimPy version and resource/dispatch approach for the formal Model 0 entry point require confirmation. | TO-CONFIRM | Record the version and approach used for Gate 1 verification |

**Source audit clarification:** `L-DATA` and `H-PUBLIC` identify source types, not a source-checked status. Use a separate proposed `source-checked` status only after actually examining the original full text/table or hospital page. `verified-in-code` and `validated-empirically` are separate claims and require separate evidence.

- **Munavalli et al. 2020:** multi-agent healthcare coordination is supported; our agent decomposition and active autonomous examinees are project choices, not direct observations from that work.
- **Ying & Kittipittayakorn 2018:** metadata/abstract identifies examination-centre DES + agent-based modelling; full text is unavailable and does not establish our Python/SimPy architecture or unseen implementation details. DOI: https://doi.org/10.23055/ijietap.2018.25.2.3458.
- **Li et al. 2025:** main-text automatic queue-assignment and later switching timing is now **source-checked** as described in §5; this does not calibrate our pre-queue B1/B2 rules or complete the unread Appendix.
- **Ho et al. 2021:** multiple examination sets support modelling heterogeneous required tests, but not the specific synthetic P1–P3 definitions.
- **Lv et al. 2026:** original centralized-batch numeric case is not evidence for daily Poisson arrivals, Gamma service durations, candidate demand rates or assumed patient demographics. Recheck original tables before numerical use.

### Implementation gate

Model 0 v1.1 has a prototype on the development branch. Gate 1 remains open. Finalizing an event-handling approach, keeping state and resource ownership coherent, validating negative-case semantics, pinning the SimPy version and deriving expected traces independently are prerequisites to closing it. See [project progress](../PROJECT_PROGRESS.md) for the current evidence.

**Queue ownership design risk (not an observed runtime failure):** if a Station Agent's custom waiting list selects service order while native SimPy Resource requests also wait internally, two orderings may conflict. Choose a coherent owner of service selection and verify the custom-queue/resource interaction, capacity and FCFS traces. A full six-phase coordinator remains optional; no implementation approach is established by this warning.

### Research direction update (2026-11-10)

The working title and RQ2 now concern **Queue Scheduling Policies** (who is served next), separately from Routing (next station). FCFS alone is confirmed; other algorithms, metric definitions and experimental factors remain undecided. Patient Agent state, heterogeneity, observable information, behaviour and interactions remain central to RQ1, with no mandatory complex behaviour. Checked literature/hospital-public packages are allowed with provenance and explicit adaptations. Initial RQ2 may use verified Model 1 + common flow + B0; B1/B2 remain optional hypotheses. This research direction update retained the Model 0 numerical rules and T01–T10. See [project progress](../PROJECT_PROGRESS.md) for subsequent development evidence.

## 10. Update procedure

For each changed setting, record: **ID -> prior value -> new value -> supporting evidence or experiment purpose -> impact on agents/routes/tests -> verification or validation status**. Keep this document aligned with `MODEL_SPEC.md` and `VERIFICATION_PLAN.md`.

**Current outcome:** a documented set of assumptions and open verification tasks; no software tests or empirical validations have been completed by producing this file.
