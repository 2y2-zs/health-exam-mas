# Model Assumptions & Evidence Register v1.0

**Project:** PSP305 — Agent-Based Simulation and Comparative Evaluation of Routing Policies for Daily Health Examination Centres  
**Status:** Working design document; NOT a validated operational model  
**Updated:** 2026-11-05

## 1. Purpose and evidence labels

This register makes every consequential design choice traceable and distinguishes **(a) what a source actually reports**, **(b) what we adapt from it**, and **(c) what remains a hypothetical scenario**.

Evidence types:
- **L-DATA — Literature-reported case data:** a published case's observed/reported numerical inputs; limited to the original setting. Primary tables must be checked before transcription.
- **L-MECHANISM — Literature-supported mechanism:** a paper demonstrates or discusses a design concept, but does *not* necessarily validate our particular implementation.
- **DESIGN — Project design choice:** proposed integration, interface or simplification, not directly established by the citation.
- **SYNTHETIC — Artificial verification input:** invented solely to verify software behaviour.
- **ASSUMPTION — Uncalibrated experimental parameter:** use only with sensitivity tests or subsequent calibration.
- **TO-CONFIRM — Operational rule or source detail not yet independently verified.**

**Evidence status:** `identified` = relevant publication known; `needs-primary-check` = exact item/table/formulation should be verified from full original source; `needs-hospital-check` = requires partner process/data; `verified-in-code` and `validated-empirically` must only be used after student-led work actually establishes them. None has yet been demonstrated.

## 2. Core research and modelling decisions

| ID | Choice | Evidence type | Grounding and limits | Status / next action |
|---|---|---|---|---|
| R01 | Ongoing daily health examination centre, with sequential/walk-in arrivals | DESIGN | Deliberately different from Lv et al. 2026 **batch centralized** examination case. Its batch input does not establish our daily arrival process. | Confirm operational pattern with supervisor / partner centre |
| R02 | 50% Agent simulation/verification, 40% existing-policy evaluation, 10% optional improvement | DESIGN | Agreed project scope, not a literature statistic. | Retain unless supervisor changes scope |
| R03 | Patient, Examination Station/Resource and Routing agents | L-MECHANISM + DESIGN | Munavalli et al. 2020 motivates multi-agent real-time clinic coordination. Exact three-agent decomposition is ours. | Specify interfaces and observation boundaries |
| R04 | Discrete-event clock underneath agent decisions, provisionally Python + SimPy | L-MECHANISM + DESIGN | Hybrid discrete-event and agent-based work exists in physical examination centres (Ying & Kittipittayakorn 2018). The Python/SimPy implementation choice is ours, not the cited paper's implementation. | Model 0 design review, then student implementation |
| R05 | Route recommendation -> patient accepts/overrides **before queue entry** -> queue changes -> later recommendations | L-MECHANISM + DESIGN | Li et al. 2025 studies discretionary **queue switching** at a physical exam centre. Pre-queue recommendation override is a distinct behaviour; the paper does not, by itself, validate our pre-queue choice function. | Confirm workflow feasibility and separately calibrate behaviour |
| R06 | Multiple exam packages and heterogeneous required tests | L-MECHANISM + DESIGN | Ho et al. 2021 documents differentiated health-exam sets/resources. Our proposed P1–P3 item lists are NOT that centre's observed packages. | Seek actual package list |
| R07 | Existing online routing algorithms compared under common environment | L-MECHANISM + DESIGN | Chiu & Yeh 2010 and Jain et al. 2022 address dynamic / online scheduling. Specific baselines and reproductions need exact definition and fidelity checks. | Define shared policy API and faithful baseline sources |

## 3. Model 0: synthetic software-verification fixture

**Every item in this section is SYNTHETIC; none is a medical-centre observation or clinical recommendation.**

| ID | Parameter / rule | Proposed fixture | Why it is used | Status |
|---|---|---|---|---|
| M0-01 | Stations | A, B, C | Small independently checkable environment | Design-only |
| M0-02 | Capacities | A=1, B=1, C=2 | Test single/multi-server constraints | Design-only |
| M0-03 | Service times | A=4, B=3, C=5 minutes, deterministic | Hand-computable event traces | Design-only |
| M0-04 | Packages | P1={A,B}, P2={B,C}, P3={A,B,C} | Exercise heterogeneous job sets | Design-only |
| M0-05 | Fixed-route baseline | P1: A->B; P2: B->C; P3: A->B->C | Initial routing-policy fixture; **not** a clinical hard constraint | v1.1 clarification pending |
| M0-06 | Precedence example | A must finish before C may begin for P3 | Test legality independently of routing policy; fictitious | Strengthen negative tests |
| M0-07 | Travel times | A<->B=1; B<->C=1; A<->C=2 minutes; entry->first=0 | Verify travel events and time accounting | Design-only |
| M0-08 | Queue discipline | Shared FCFS queue; non-preemptive service | Minimal resource model | Design-only |
| M0-09 | Patient behaviour | B0 full recommendation compliance | Isolate event and capacity correctness | Design-only |
| M0-10 | Arrivals | Explicit deterministic times | Independent manual expected outcomes | Need test-by-test schedules |
| M0-11 | Same-time event ordering, cutoff boundary | Provisional: completions/releases ahead of new admission/queue actions; admit at time <= cutoff | Make expected traces reproducible | **TO-CONFIRM** implementation feasibility and precise priorities in SimPy |

**Known test-design issue:** Three arrivals at the centre do not necessarily imply three simultaneous arrivals at C when every route goes through B. Resource test T03 should inject three simultaneous *eligible service requests at C* in a station-level fixture. T04 must deliberately test rejection of an illegal next exam; simply following the fixed order is insufficient. The student must independently derive expected event times.

### Fixed route vs precedence

A policy chooses *which* eligible exam to visit next; a precedence graph defines which exams are *allowed*. Never silently equate an A->B->C fixed-route policy with medical precedence A->B->C. In Model 0 the only example hard constraint is A-before-C for P3, unless a test explicitly sets a different synthetic graph.

## 4. Model 1: candidate examination-centre configuration

These are **candidate** inputs, not yet a validated day-to-day centre dataset.

| ID | Parameter | Candidate setting | Type / original context | Verification need |
|---|---|---|---|---|
| M1-01 | Six examination stations | Ultrasound (US), ECG, blood draw, internal medicine, X-ray, ophthalmology | L-DATA + DESIGN; subset selected from Lv et al. 2026 centralized case | Confirm exact case tables and nomenclature |
| M1-02 | Parallel capacities in that case | US=4, ECG=2, Blood=3, Internal=1, X-ray=1, Ophthalmology=1 | L-DATA **reported in prior research notes**, not independently re-transcribed for this register | Cross-check original Table 12; do not generalize to all centres |
| M1-03 | Mean exam time, minutes, case-specific | US male 7.32 / female 11.37; ECG 3.00; Blood 0.80; Internal 1.25; X-ray 1.00; Ophthalmology 1.30 | L-DATA **reported in prior research notes**; published means ≠ distributions | Cross-check units, population and original Table 12 |
| M1-04 | Directed inter-item travel-time matrix | Candidate six-station submatrix of Lv et al. 2026 case | L-DATA + DESIGN; asymmetric values possible | Verify original Table 11 and extraction before storing numbers in configuration |
| M1-05 | Synthetic P1/P2/P3 packages | P1=Blood+ECG+Internal+Ophthalmology; P2=P1+X-ray; P3=P2+Ultrasound | ASSUMPTION informed by multi-package literature; **not** observed medical packages | Ask partner centre; sensitivity to package mix |
| M1-06 | Clinical precedence | No assumed clinical order by default; configurable verified constraints | TO-CONFIRM | Obtain medically/operationally grounded rules; do not infer from test fixture |
| M1-07 | Arrival process | Initially homogeneous Poisson; later time-varying arrivals if evidenced | ASSUMPTION, **not** established by Lv batch arrival case | Collect timestamps or compare plausible alternative arrival processes |
| M1-08 | Demand-rate scenarios | 20 / 35 / 45 examinees per hour were discussed as **tentative stress-test values** | ASSUMPTION, not empirical operating rates | **Do not freeze** without capacity/load check; vary demand systematically |
| M1-09 | Service-duration variability | Deterministic then hypothetical Gamma distribution with CV=0.2 or 0.4 in sensitivity scenarios | ASSUMPTION; Lv case mean values do NOT identify a Gamma shape or CV | Fit from repeated durations if possible; otherwise label scenarios synthetic |
| M1-10 | Queue discipline | One shared FCFS queue per station, parallel servers | DESIGN | Verify whether real centre has separate device queues/priority service |
| M1-11 | Service interruption | No preemption, no failures initially | DESIGN simplification | Revisit only if operationally material |
| M1-12 | Intake cutoff | Example 480 min for admitting patients; continue model until admitted patients complete | ASSUMPTION / experiment convention | Check actual opening hours; report late-service and clearance time |
| M1-13 | Patient demographics / ultrasound timing | Sex-dependent case means possible, but do **not** import Lv's batch cohort composition as a daily-centre population model | L-DATA + ASSUMPTION | Obtain representative demographics or report scenario dependence |

**Load sanity check, before choosing arrival rates:** for each station j, approximate offered load `rho_j = arrival_rate * Pr(package includes j) * mean_service_time_j / capacity_j`, with consistent time units. This is only a first-order screening formula; it does not replace the simulation.

## 5. Model 2: autonomous patient behaviour

| ID | Behaviour | Type | Evidence and limitation | Verification / validation |
|---|---|---|---|---|
| B0 | Always obey a legal recommendation | DESIGN baseline | Operational compliance simplifying assumption, not necessarily actual behaviour | Confirm chosen==recommended in all B0 traces |
| B1 | Independent acceptance with patient-specific probability p; if reject, choose a different **eligible** next station | ASSUMPTION | Do not use Li 2025 as proof of any specific p or independence assumption | Explore sensitivity; no legal alternative => recommended station |
| B2 | State-dependent choice using perceived queue/wait, travel and individual tolerance/preferences | L-MECHANISM + ASSUMPTION | Li 2025 motivates examining behaviour and queues, but the proposed perceived-cost equation and weights are **our candidate rule**, not a published fitted Li model | Define observable information, functional form and parameter provenance |
| B3 (deferred) | Leave a queue after having joined it (true queue switching) | L-MECHANISM; deferred implementation | Closer to Li 2025, but may require cancellation/priority/order changes and operational permission | Research separately; not a Model 0/1 requirement |

Observation boundary: agents cannot access future realized random service times. Specify whether “queue length” includes active service and whether expected incoming travellers are observable. Routing agent and patient perceived information need not be identical.

## 6. Evaluation assumptions (RQ2)

| ID | Decision | Evidence classification | Open issue |
|---|---|---|---|
| E01 | Baselines: fixed route, shortest observed queue, shortest estimated waiting time | DESIGN; motivated by routing literature | Formal tie-breaks, eligibility, expected-wait formula and source fidelity |
| E02 | Optionally add literature-derived fuzzy/dynamic policy | L-MECHANISM + DESIGN | Exact reproduction vs explicitly labelled literature-inspired approximation |
| E03 | Compare B0, B1, B2 across routing strategies and multiple demand scenarios | DESIGN | Factorial experiment design and behaviour calibration |
| E04 | Keep exogenous randomness paired between strategies | DESIGN experimental control | Same seed alone is insufficient if strategies consume RNG differently; use keyed streams / prerecorded arrivals, packages and per-patient per-station service samples |
| E05 | Outcomes: mean and P95 waiting, cycle time, utilization, completion at cutoff and clearance time | DESIGN | Freeze unit of analysis, time windows, censoring and denominators before experiment |
| E06 | Independently repeated stochastic scenarios and uncertainty estimates | DESIGN | Specify replication count / interval computation before final evaluation |
| E07 | Assess whether behaviour changes policy performance or ranking | **Unproven research hypothesis** | Do not presume ranking changes or significant effects |

## 7. Priority evidence gaps and mitigation

1. **Operational validity:** obtain sample day arrivals, service durations, package proportions, resource counts and station locations if supervisor's hospital collaboration permits. Record confidentiality and data constraints.
2. **Behavioural validity:** inspect Li et al. 2025 full study carefully for what exactly is switched, when, and what predictors are measured; do not equate queue abandonment with pre-queue override.
3. **Primary source transcription:** verify every capacity, mean and matrix entry against original Lv 2026 tables before using Model 1 as literature-grounded numerical configuration.
4. **Verification traceability:** finalize Model 0 v1.1 (policy/constraint separation, direct C capacity test, negative precedence test, exact same-time priorities, cutoff rule), then calculate expected traces independently.
5. **Algorithm fairness:** predefine observable state, behaviour choice rules, independent random streams, metric windows and statistical uncertainty before RQ2.

## 8. Reference register

Citations below identify supporting literature for **the particular concepts noted above**; they do not imply those papers endorse the project's synthetic parameters.

- **Lv et al. (2026)**, *Optimization of Batch Centralized Health Examination Scheduling Considering Inter-Item Transition Time and Sex Differences*. https://doi.org/10.1002/hsr2.72912
- **Munavalli et al. (2020)**, *An Intelligent Real-Time Scheduler for Out-Patient Clinics: A Multi-Agent System Model*. https://doi.org/10.1177/1460458220905380
- **Ying & Kittipittayakorn (2018)**, *Combining discrete event and agent-based simulation for reducing draftees waiting time in physical examination centers*. https://ntut.elsevierpure.com/en/publications/combining-discrete-event-and-agent-based-simulation-for-reducing-/
- **Li et al. (2025)**, *When Do People Switch Queues? An Empirical Study of Discretionary Queue Switching at a Physical Examination Center*. https://doi.org/10.1111/deci.12646
- **Ho et al. (2021)**, *Overbooking for Physical Examination Considering Late Cancellation and Set-Resource Relationship*. https://doi.org/10.1186/s12913-021-07148-y
- **Chiu & Yeh (2010)**, *Fuzzy-Based Dynamic Scheduling System for Health Examination*. https://doi.org/10.1109/ICMLC.2010.5580551
- **Jain et al. (2022)**, *Improving Patient Satisfaction and Outpatient Diagnostic Center Efficiency Using Novel Online Real-Time Scheduling*. https://doi.org/10.1016/j.orhc.2022.100338

## 9. Update procedure

For each changed setting, record: **ID -> prior value -> new value -> supporting evidence or experiment purpose -> impact on agents/routes/tests -> verification or validation status**. Keep this document aligned with `MODEL_SPEC.md` and `VERIFICATION_PLAN.md`.

**Current outcome:** a documented set of assumptions and open verification tasks; no software tests or empirical validations have been completed by producing this file.
