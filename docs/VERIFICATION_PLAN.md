# Verification plan v1.0 (no tests yet executed)

Purpose: verify that the student-written Model 0 satisfies its *specified* synthetic rules, before claiming any external validity.

## Deterministic tests

| ID | Scenario | Expected property |
|---|---|---|
| T01 | One P1 patient | Exactly A then B, each once, then FINISHED |
| T02 | Two patients compete for A | No overlapping service beyond A capacity=1 |
| T03 | Three patients compete for C | C busy servers <=2; at least one waits if all arrive together |
| T04 | P3 test | A completed before C begins |
| T05 | A->B trip | B queue entry cannot precede travel completion after specified delay |
| T06 | Simultaneous arrivals | Stable, documented FCFS tie-break behaviour |
| T07 | All required tests completed | Patient leaves and never requests another station |
| T08 | Service completion | Resource released; waiting eligible patient can start |
| T09 | Intake cutoff with unfinished patients | No new arrivals after cutoff; existing patients may finish |
| T10 | Identical configuration | Deterministic event traces match across runs |

## Invariants

1. For each station j at all event boundaries: `0 <= busy_j <= capacity_j`.
2. Each patient has exactly one active lifecycle state and at most one station/resource assignment.
3. For a FINISHED patient: `CompletedTests == RequiredTests`, with no duplicate services.
4. All configured predecessor examinations completed before any dependent service begins.
5. In no-abandonment runs: `Arrived == Active + Finished`; when drained, `Active == 0`.

## Test evidence to record

For each test, the student should record: configuration, expected outcome calculated independently, actual event trace, pass/fail, and explanation for any discrepancy. Do not record fabricated pass statuses.

## Validation versus verification

Passing these tests supports internal model correctness relative to the specification, not realism of arrival/service distributions, patient compliance parameters or hospital processes. External validation requires trustworthy operational data, expert review or carefully qualified literature-based comparisons.

## Follow-on gates

- Gate 1: Model 0 deterministically verified.
- Gate 2: Model 1 introduces observed-vs-assumed parameters and stochastic replications.
- Gate 3: Model 2 validates the consistency of autonomous patient choices and queue feedback.
- Only then: RQ2 policy evaluation.
