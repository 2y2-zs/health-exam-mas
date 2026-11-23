# Project progress

Reviewed on **2026-11-24**. This update reconciles research reading and development evidence; it does not execute tests, complete independent acceptance or merge simulation code.

## Research work completed

| Work | Evidence and limits |
| --- | --- |
| Retained the agreed research direction and deterministic Model 0 | [Research context](docs/RESEARCH_CONTEXT.md), [specification](docs/MODEL_SPEC.md) and [verification plan](docs/VERIFICATION_PLAN.md). RQ1 concerns a grounded, verifiable multi-agent model; RQ2 compares station Queue Scheduling with FCFS as the only confirmed baseline. |
| Reviewed the available main texts and revised their research classification | [Literature library](docs/LITERATURE_LIBRARY.md), reviewed 2026-11-23/24: 18 records, 16 available main texts reviewed; P01/P12 remain without full text. Independent supplements and reproduction gaps are recorded per paper. |
| Added methods and policy evidence to the research documents | ODD, STRESS and ABM V&V support transparent description, reporting and evaluation. Chen 2024 and Lin 2017 provide direct service-selection candidates. SPT/LST/SERPT remain candidates; no new policy, experiment or empirically calibrated parameter has been implemented by this update. |

## Repository and checkout snapshots

The snapshots below were checked on 2026-11-24; they must not be treated as one synchronized version.

| Location | Revision inspected | Actual scope |
| --- | --- | --- |
| Remote `main`, before this documentation update | [`2fa4a86`](https://github.com/2y2-zs/health-exam-mas/commit/2fa4a863b341eecdcce36c88117151cdcaac09a4) | Research documents and placeholders in `src/` and `tests/`; no Model 0 implementation in this tree. |
| Remote `model0/development-checkpoint` | [`f974fd4`](https://github.com/2y2-zs/health-exam-mas/tree/f974fd4070e811cbdce65fa5a7f9ffb56b0884de) | Native simulation in `src/health_exam_mas/model0.py`; A-only and multi-station coordination prototypes and tests under `tests/`. The coordinated classes have not been migrated into package modules in this remote snapshot. |
| Local development checkout, `E:\chrome下载\PSP305\health-exam-mas` | `c7c7b2097fc66598924f3908f0672f52038ab38a` | Includes packaged `model0_station.py` / `model0_coordinator.py`, the mixed-B trace and the Model 0 verification archive. These newer files are absent from the inspected remote development tree. |

The local history contains the remote snapshots, but its newer development commits have not been published to the inspected remote development branch. This documentation update leaves that branch and the local checkout unchanged. The remote development README still says design-only despite containing implementation; that separate branch's README was not updated here.

A read-only local audit compared all 32 HEAD-tracked files against their Git blobs with the checkout's CRLF normalization and found no tracked content differences. It found one additional, untracked file: `docs/CHEN_2024_REPLICATION_CHECKLIST.md`, which was preserved. Ordinary `git status` did not succeed in this environment, so this is not a blanket clean-worktree claim.

## Model 0 implementation and historical checks

The remote development snapshot contains the [native patient/station path](https://github.com/2y2-zs/health-exam-mas/blob/f974fd4070e811cbdce65fa5a7f9ffb56b0884de/src/health_exam_mas/model0.py), [A-only prototype](https://github.com/2y2-zs/health-exam-mas/blob/f974fd4070e811cbdce65fa5a7f9ffb56b0884de/tests/model0_a_only_prototype.py) and [multi-station prototype](https://github.com/2y2-zs/health-exam-mas/blob/f974fd4070e811cbdce65fa5a7f9ffb56b0884de/tests/model0_ab_coordinator.py). Its coordinated cases cover T01–T10: T04 has two subcases and T08 uses the single-station harness. [Coordinated T01 definition](https://github.com/2y2-zs/health-exam-mas/blob/f974fd4070e811cbdce65fa5a7f9ffb56b0884de/tests/test_model0_ab_coordinator.py#L5664)

| Historical record | Result recorded | Evidence status |
| --- | --- | --- |
| Initial development checkpoint `ea7e73d` | 146 passed / 2 failed; 14 targeted checks passed. The earlier progress record reports 11 coordinated cases covering T01–T10. | [Committed verification statement](https://github.com/2y2-zs/health-exam-mas/commit/ea7e73d32d8351f5e6c219d19680e4457182708b). The raw terminal output is not archived in that remote snapshot. |
| Local run dated 2026-11-20, code `fd71adee7c583677dfdf1f7e47283d249e8ddb3f`; archive committed locally at `c7c7b20` | 154 coordinated checks passed, including 11 cases for T01–T10; full suite 160 passed / 2 failed, exit code 1. | Local `docs/MODEL0_VERIFICATION_RECORD.md` and `docs/evidence/model0-fd71ade-events.csv`. Assistant-supported development verification, not independent student acceptance. Neither archive is present at remote development HEAD. |

The local archive records Python 3.12.10, SimPy 4.1.2 and pytest 9.2.0. Its full-suite command was:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q --tb=no -p no:cacheprovider -o pythonpath=src
```

The CSV was inspected during this documentation audit: **861 event rows**, **21 `(case, run_id)` logs**, SHA-256 `d525b8646b17b517e9c3d30ec8dcc7550c436b679552e5880f34dcc15fd2f631`. This checks the existing archive's contents; it is not a fresh simulation run or independent confirmation of the historical pass counts. The record reports T01 departure at 8, a T06 raw trace matching the selected order, repeatable normalized T10 traces and additional A/B/C probes. The local mixed-B record reports travel ends u2 then u1 at t=5, queue entries u1 then u2, and B service starts at 5 and 8 respectively.

The local candidate packaged entry point is `MultiStationCoordinator.run()`. Its adoption and independent acceptance remain pending; the remote prototypes must not be described as an already accepted packaged entry point.

### Two unresolved native-path issues

| Issue | Contract and recorded discrepancy |
| --- | --- |
| Stable ordering of simultaneous requests | u1 should precede u2 under either process creation order. With u2 created first, the native path served u2 first. [Remote diagnostic](https://github.com/2y2-zs/health-exam-mas/blob/f974fd4070e811cbdce65fa5a7f9ffb56b0884de/tests/test_model0_same_time_probe.py#L67) |
| T06 raw order at t=4 | Completion/release should precede the new admissions. The native trace recorded u3/u4 admissions first, although departure times matched. [Remote T06 assertion](https://github.com/2y2-zs/health-exam-mas/blob/f974fd4070e811cbdce65fa5a7f9ffb56b0884de/tests/test_model0_t06.py#L302) |

Both remain visible; this update fixes neither and relaxes no assertion. Decide whether the native path remains supported or is retained as a historical prototype. A supported path must meet the selected domain contract. Literature does not mandate a global six-phase coordinator or settle the native/coordinated choice.

**Gate 1 remains open.** Independent student evidence must identify the selected entry point, code revision, environment, commands, independently derived expected results, raw traces, discrepancies and acceptance decision. See the [evidence requirements](docs/VERIFICATION_PLAN.md#3-evidence-required-for-each-student-run-test).

## In progress and not started

| Work | Current status / next evidence |
| --- | --- |
| Model 0 formal entry point and acceptance | Local packaged candidate and development records exist; independent Gate 1 acceptance and native-path support decision are pending. |
| Model 1 source and scope decision | Six stations and literature inputs remain candidates. Confirm operational data with the supervisor, or agree an explicitly adapted literature-informed synthetic scenario; preserve provenance and limits. [Evidence register](docs/MODEL_ASSUMPTIONS.md) |
| Queue policy and experiment specification | FCFS confirmed; SPT/LST/SERPT registered only as candidates. Select a small justified set, define allowed observations/ties, matched exogenous inputs, outcomes, uncertainty and fairness before implementation/experiments. |
| Interim Poster | Use reviewed evidence and distinguish completed checks from plans. [Poster materials](poster/README.md) and [Gantt chart](poster/gantt.md). |
| Model 1 implementation, calibration and validation | Not started according to the inspected development records. Requires Model 0 acceptance and a documented input-source decision. |
| RQ2 experiments and findings | Not executed. Requires a verified baseline and agreed policies/experiment protocol. No policy ranking or improvement is established. |
| Optional Model 2 behaviour / RQ3 | Not implemented or evaluated. B1/B2 remain uncalibrated hypotheses; Model 2 is not a prerequisite for all RQ2 comparisons. |

## Schedule priorities

The Interim Poster deadline remains **2026-12-16 12:00**. The internal target for a full Dissertation draft is **2027-02-05**, distinct from the official final submission date. [Official dates](docs/RESEARCH_CONTEXT.md#schedule) · [Internal milestones](poster/gantt.md)

Prioritize Model 0 acceptance, an operational-data decision, source-traceable Model 1 scope and a small policy shortlist. Write the literature review and methods alongside this work. If data access is unresolved at the end of December, agree the permissible literature-based scenario and claims with the supervisor.
