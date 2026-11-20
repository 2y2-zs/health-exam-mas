# Project progress

Reviewed on 2026-11-20. The [design baseline](https://github.com/2y2-zs/health-exam-mas/tree/ee5753f195dc71aee7d468a5814d6457d967c699) is on `main`. The [Model 0 development checkpoint](https://github.com/2y2-zs/health-exam-mas/commit/ea7e73d32d8351f5e6c219d19680e4457182708b) contains the implementation, prototypes and tests summarized below.

## Completed

| Work | Evidence |
| --- | --- |
| Agreed research direction and deterministic Model 0 specification | [Research context](docs/RESEARCH_CONTEXT.md), [Model 0 specification](docs/MODEL_SPEC.md) and [T01–T10 expected traces](docs/VERIFICATION_PLAN.md). RQ2 compares station queue scheduling policies with FCFS as the baseline. Routing remains a separate decision. |
| Committed the initial Model 0 simulation and station coordination prototypes | [Patient and station implementation](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/src/health_exam_mas/model0.py), [single-station prototype](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/model0_a_only_prototype.py), and [multi-station prototype](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/model0_ab_coordinator.py). The [coordinated station](src/health_exam_mas/model0_station.py) and [multi-station coordinator](src/health_exam_mas/model0_coordinator.py) were subsequently moved into `src/` at `46388e3` and `18855bf`. The migration retained the simulation method bodies and the existing test assertions. |
| Added executable cases covering the Model 0 fixture | [Coordinated test cases](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_ab_coordinator.py#L5664) and [T08 single-station handoff](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_a_only_coordinator.py#L2728). These files record the scenarios and assertions. |

### Recorded development checks

The previous local development check reported 146 passes and two failures at `ea7e73d`. After moving the existing station and coordinator into the package, local development checks at `18855bf` reproduced **146 passed and 2 failed** using Python 3.12.10, SimPy 4.1.2 and pytest 9.2.0. The coordinated suites had **140 passes**, including **11 tests covering T01–T10**. T04 has two cases and T08 uses the single-station harness.

From the repository root in PowerShell, the full development check is:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider -o pythonpath=src
```

The two failures are in the native SimPy path: [patient ordering on simultaneous requests](tests/test_model0_same_time_probe.py#L57) and [T06 raw order at t=4](tests/test_model0_t06.py#L311). Both scenarios were also checked through the migrated coordinator with A/B/C configured. In the first, A served u1 then u2 under both registration orders. In T06, the original relevant t=4 event order was preserved and departures occurred at t=8, 12, 16 and 20. The package-only T01 smoke check used A/B/C and recorded departure at t=8.

These are development diagnostics using synthetic inputs. The student's acceptance record should include the commit, environment, commands, independently derived expectations, raw traces and pass/fail results.

## In progress

| Work | Next evidence |
| --- | --- |
| Model 0 formal entry point and verification | For the deterministic fixture, create one environment and the A/B/C stations, register arrivals with `MultiStationCoordinator`, then run the coordinator and drain the environment. Record independent expected and actual traces for the coordinated path, including the mixed-source B case and the input checks below. |
| Model 1 data source and scope decision | Confirm what operational data can be used with the supervisor. Record provenance for patient arrivals, packages, service durations, capacity and flow rules. If data access remains unresolved at the end of December, agree whether a literature-based scenario is suitable and document its assumptions and limits. See the [evidence register](docs/MODEL_ASSUMPTIONS.md#7-priority-evidence-gaps-and-mitigation). |
| Interim Poster planning | [Course requirements and materials](poster/README.md) and [Gantt chart](poster/gantt.md). Use verified traces to demonstrate progress and explain the remaining same-time verification work. |

### Phase ordering and input checks

- **Phase 3 ordering.** With rank-2 P1 at t=0, A-to-B travel ends at t=5. Rank-1 P2 enters at t=5 and travels immediately to B. The raw log records u2 then u1 for travel completion. Once both arrivals are ready, Phase 4 queues u1 then u2. The B service starts are u1 at t=5 and u2 at t=8. The [regression](tests/test_model0_coordinated_arrivals.py) checks these events in their original order.
- **Pre-run input checks.** The coordinated entry rejects nonfinite or negative arrival times at registration. Before the first event bucket it checks every preregistered package for managed stations, a route containing each required station exactly once, and valid precedence edges in route order. An invalid future package leaves the clock, pending arrivals and log untouched. See the [configuration contract](docs/MODEL_SPEC.md#5-configuration-observation-and-logging-contracts).

The 14 new development regression cases passed. The full development suite reported **160 passed and 2 failed**. The 11 coordinated T01–T10 checks passed and the two native failures described above remain open. Independent student acceptance is pending.

### Candidate Model 1 sources

Chen et al. (2021) report high-end screening package flows and examination duration inputs in Tables 2–4. Ho et al. (2021) give examination-set and resource mappings in Tables 2 and 13 and booking percentages in Table 11. These are separate centre-specific sources. Record the provenance of each adopted value and check what is observed, fitted or assumed. Daily walk-in arrival patterns and active parallel capacity still need local evidence or explicit scenario assumptions. [Chen et al.](https://link.springer.com/article/10.1186/s12913-021-06949-5) · [Ho et al.](https://link.springer.com/article/10.1186/s12913-021-07148-y)

## Not started

| Work | Dependency |
| --- | --- |
| Model 1 implementation, calibration and validation | Formal Model 0 verification and a documented data-source decision. Calibrate and compare against observed data where available. |
| RQ2 policy experiments and findings | A verified Model 1 FCFS baseline, a sourced comparison policy, common routing, matched inputs and agreed outcome definitions. Interpret waiting and fairness together when relevant. |
| Optional Model 2 behaviour and RQ3 improvement | Review their value after the baseline work. Their implementation is outside the draft milestone. |

## Schedule priorities

The [Gantt chart](poster/gantt.md) places initial RQ2 experiments in January and sets **2027-02-05** as the target to send a full Dissertation draft to the supervisor. Writing the research context, literature review and methods runs alongside implementation. S2 is reserved for feedback, follow-up verification and sensitivity analysis, the Oral Project Demonstration and final revisions. The [official submission dates](docs/RESEARCH_CONTEXT.md#schedule) are recorded separately.

The main schedule risks are the same-time acceptance issues and access to operational data. Confirm data access early, use only approved de-identified records if available, and keep any literature-based findings scoped to the stated scenario.
