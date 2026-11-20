# Project progress

Reviewed on 2026-11-20. [Design baseline on `main`](https://github.com/2y2-zs/health-exam-mas/tree/ee5753f195dc71aee7d468a5814d6457d967c699) · [Initial development checkpoint](https://github.com/2y2-zs/health-exam-mas/commit/ea7e73d32d8351f5e6c219d19680e4457182708b)

## Completed

| Work | Evidence |
| --- | --- |
| Defined the research direction and deterministic Model 0 | [Research context](docs/RESEARCH_CONTEXT.md) · [Specification](docs/MODEL_SPEC.md) · [Rule and evidence register](docs/MODEL_ASSUMPTIONS.md) |
| Built the native path and moved the coordinated Model 0 path into the package | [Native patient and station](src/health_exam_mas/model0.py) · [Coordinated station (46388e3)](src/health_exam_mas/model0_station.py) · [Coordinator (18855bf)](src/health_exam_mas/model0_coordinator.py) |
| Added executable T01–T10 cases | [Expected traces](docs/VERIFICATION_PLAN.md#2-test-cases-t01t10) · [Coordinated tests at checkpoint](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_ab_coordinator.py#L5664) · [T08 single-station test at checkpoint](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_a_only_coordinator.py#L2728) |

### Recorded development checks

| Check | Recorded result |
| --- | --- |
| Package migration at `18855bf` | 146 passed, 2 failed, matching `ea7e73d`. The coordinated suites had 140 passes, including 11 checks covering T01–T10. T04 has two cases and T08 uses the single-station harness. |
| Arrival validation and event ordering at `5abfe6e` | 160 passed, 2 failed. The 14 new regression cases passed. A later comment cleanup reproduced the full-suite totals and all 38 events in the B-station run. |
| Single mixed-arrivals check at `b70b485` | Passed. [Configuration, assisted calculation and original log](docs/MODEL0_MIXED_B_TRACE.md) |
| Model 0 verification at `fd71ade` | 154 coordinated checks passed, including the 11 cases for T01–T10. The full suite reported 160 passed and 2 native-path failures. [Run record and original traces](docs/MODEL0_VERIFICATION_RECORD.md) |

The two open failures are on the native SimPy path. The coordinated path served u1 before u2 under both registration orders and matched the T06 raw order. The package-only T01 smoke check logged departure at t=8. [Simultaneous-request assertion](tests/test_model0_same_time_probe.py#L57) · [T06 raw order assertion](tests/test_model0_t06.py#L311)

The checks used Python 3.12.10, SimPy 4.1.2 and pytest 9.2.0. Run from the repository root in PowerShell.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider -o pythonpath=src
```

**Gate 1 is open.** The student acceptance record should include the chosen entry point, commit, environment, run commands, independent expected traces, actual traces and results. [Evidence checklist](docs/VERIFICATION_PLAN.md#3-evidence-required-for-each-student-run-test)

## In progress

| Work | Next evidence |
| --- | --- |
| Model 0 formal entry point and verification | Build one environment with A/B/C, register arrivals with `MultiStationCoordinator`, run and drain. Record independent traces for the same-time and input checks below. |
| Model 1 data source and scope | Confirm usable operational data with the supervisor. If access remains unresolved at the end of December, agree on the scope of a literature-based scenario. [Evidence priorities](docs/MODEL_ASSUMPTIONS.md#7-priority-evidence-gaps-and-mitigation) |
| Interim Poster | Prepare reviewed evidence and the five-minute presentation. [Submission checklist](poster/README.md) · [Gantt chart](poster/gantt.md) |

### Phase ordering and input checks

- **Mixed arrivals at B.** At t=5, travel completions are u2 then u1 and queue entries are u1 then u2. [Mixed-B trace](docs/MODEL0_MIXED_B_TRACE.md)
- **Input validation.** The coordinated path rejects invalid arrival times and checks all registered packages before the first event bucket. A bad package for a later arrival stops the run before any admission. [Configuration contract](docs/MODEL_SPEC.md#5-configuration-observation-and-logging-contracts) · [Regression cases](tests/test_model0_coordinated_arrivals.py)

## Not started

| Work | Dependency |
| --- | --- |
| Model 1 implementation, calibration and validation | Formal Model 0 verification and a documented data-source decision. Calibrate and compare against observed data where available. |
| RQ2 policy experiments and findings | A verified Model 1 FCFS baseline, a sourced comparison policy, common routing, matched inputs and agreed outcome definitions. Interpret waiting and fairness together when relevant. |
| Optional Model 2 behaviour and RQ3 improvement | Review their value after the baseline work. Their implementation is outside the draft milestone. |

## Schedule priorities

Access to operational data and student verification of same-time behaviour are the main schedule risks. Write the research context, literature review and methods alongside implementation. [Internal milestones](poster/gantt.md) · [Official deadlines](docs/RESEARCH_CONTEXT.md#schedule)
