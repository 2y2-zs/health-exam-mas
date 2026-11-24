# Project progress

Reviewed on 2026-11-24. [Design baseline on `main`](https://github.com/2y2-zs/health-exam-mas/tree/ee5753f195dc71aee7d468a5814d6457d967c699) · [Initial development checkpoint](https://github.com/2y2-zs/health-exam-mas/commit/ea7e73d32d8351f5e6c219d19680e4457182708b)

## Completed

| Work | Evidence |
| --- | --- |
| Defined the research direction and Model 0 fixture | [Research context](docs/RESEARCH_CONTEXT.md) · [Specification](docs/MODEL_SPEC.md) |
| Packaged the coordinator, added executable cases and fixed station guards | [Model 0 entry](docs/MODEL_SPEC.md#1-architecture-and-separation-of-responsibilities) · [Development history](docs/MODEL0_VERIFICATION_RECORD.md#guard-and-entry-preparation-history) |
| Consolidated the P01–P18 reading record | [Literature library](docs/LITERATURE_LIBRARY.md) |

### Recorded development checks

The formal-entry selection and full suite have recorded assistant-supported runs at `10ac833`. [Actual results, historical Native diagnostics and original output](docs/MODEL0_VERIFICATION_RECORD.md) · [Mixed-B evidence](docs/MODEL0_MIXED_B_TRACE.md)

## In progress

| Work | Next evidence |
| --- | --- |
| Model 0 Gate 1 | **Open.** Student independent execution and review pending. [Acceptance steps and evidence checklist](docs/VERIFICATION_PLAN.md#3-evidence-required-for-each-student-run-test) |
| Model 1 data source and scope | Confirm usable operational data with the supervisor. If access remains unresolved at the end of December, agree on the scope of a literature-based scenario. [Evidence priorities](docs/MODEL_ASSUMPTIONS.md#7-priority-evidence-gaps-and-mitigation) |
| Interim Poster | Prepare reviewed evidence and the five-minute presentation. [Submission checklist](poster/README.md) · [Gantt chart](poster/gantt.md) |

## Not started

| Work | Dependency |
| --- | --- |
| Model 1 implementation, calibration and validation | Formal Model 0 verification and a documented data-source decision. Calibrate and compare against observed data where available. |
| RQ2 policy experiments and findings | A verified Model 1 FCFS baseline, a sourced comparison policy, common routing, matched inputs and agreed outcome definitions. Interpret waiting and fairness together when relevant. |
| Optional Model 2 behaviour and RQ3 improvement | Review their value after the baseline work. Their implementation is outside the draft milestone. |

## Schedule priorities

Access to operational data and student verification of same-time behaviour are the main schedule risks. Write the research context, literature review and methods alongside implementation. [Internal milestones](poster/gantt.md) · [Official deadlines](docs/RESEARCH_CONTEXT.md#schedule)
