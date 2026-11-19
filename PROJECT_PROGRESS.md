# Project progress

Reviewed on 2026-11-20. The [design baseline](https://github.com/2y2-zs/health-exam-mas/tree/ee5753f195dc71aee7d468a5814d6457d967c699) is on `main`. The [Model 0 development checkpoint](https://github.com/2y2-zs/health-exam-mas/commit/ea7e73d32d8351f5e6c219d19680e4457182708b) contains the implementation, prototypes and tests summarized below.

## Completed

| Work | Evidence |
| --- | --- |
| Agreed research direction and deterministic Model 0 specification | [Research context](docs/RESEARCH_CONTEXT.md), [Model 0 specification](docs/MODEL_SPEC.md) and [T01–T10 expected traces](docs/VERIFICATION_PLAN.md). RQ2 compares station queue scheduling policies with FCFS as the baseline. Routing remains a separate decision. |
| Committed the initial Model 0 simulation and station coordination prototypes | [Patient and station implementation](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/src/health_exam_mas/model0.py), [single-station prototype](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/model0_a_only_prototype.py), and [multi-station prototype](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/model0_ab_coordinator.py). The coordinated path is exercised from `tests/`. |
| Added executable cases covering the Model 0 fixture | [Coordinated test cases](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_ab_coordinator.py#L5664) and [T08 single-station handoff](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_a_only_coordinator.py#L2728). These files record the scenarios and assertions. |

### Recorded development checks

The local development check reported for `ea7e73d` had **146 passed and 2 failed**. The coordinated subset had **11 passing tests covering T01–T10**. T04 has two cases and T08 uses the single-station prototype. The failures were in the native SimPy path and concern [patient ordering for simultaneous requests](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_same_time_probe.py#L67) and [T06 raw same-time event order](https://github.com/2y2-zs/health-exam-mas/blob/ea7e73d32d8351f5e6c219d19680e4457182708b/tests/test_model0_t06.py#L336).

Source for the counts is the historical local development run reported in the project conversation. The test sources above are committed. The run output is not archived in GitHub. The student should independently reproduce and record the commit, environment, command, actual traces and pass/fail results before using these numbers as assessment evidence. The cases use synthetic inputs and assess software behaviour.

## In progress

| Work | Next evidence |
| --- | --- |
| Model 0 formal entry point and verification | Reuse the coordinated prototype through a documented entry point in `src/`. Preserve the original assertions for the same-time cases and record the student-led run against the deterministic fixture. |
| Model 1 data source and scope decision | Confirm what operational data can be used with the supervisor. Record provenance for patient arrivals, packages, service durations, capacity and flow rules. If data access remains unresolved at the end of December, agree whether a literature-based scenario is suitable and document its assumptions and limits. See the [evidence register](docs/MODEL_ASSUMPTIONS.md#7-priority-evidence-gaps-and-mitigation). |
| Interim Poster planning | [Course requirements and materials](poster/README.md) and [Gantt chart](poster/gantt.md). Use verified traces to demonstrate progress and explain the remaining same-time verification work. |

## Not started

| Work | Dependency |
| --- | --- |
| Model 1 implementation, calibration and validation | Formal Model 0 verification and a documented data-source decision. Calibrate and compare against observed data where available. |
| RQ2 policy experiments and findings | A verified Model 1 FCFS baseline, a sourced comparison policy, common routing, matched inputs and agreed outcome definitions. Interpret waiting and fairness together when relevant. |
| Optional Model 2 behaviour and RQ3 improvement | Review their value after the baseline work. Their implementation is outside the draft milestone. |

## Schedule priorities

The [Gantt chart](poster/gantt.md) places initial RQ2 experiments in January and sets **2027-02-05** as the target to send a full Dissertation draft to the supervisor. Writing the research context, literature review and methods runs alongside implementation. S2 is reserved for feedback, follow-up verification and sensitivity analysis, the Oral Project Demonstration and final revisions. The [official submission dates](docs/RESEARCH_CONTEXT.md#schedule) are recorded separately.

The main schedule risks are the same-time acceptance issues and access to operational data. Confirm data access early, use only approved de-identified records if available, and keep any literature-based findings scoped to the stated scenario.
