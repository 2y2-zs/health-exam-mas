# Model 0 development verification

## Latest development checkpoint — 2026-11-24

- **Code/test revision:** `10ac83310db02563947f836bf5406455a15fc60f`, local `model0/development-checkpoint`.
- **Formal entry:** packaged `MultiStationCoordinator.run()` with A/B/C, registered case arrivals, `env.process(coordinator.run())`, then `env.run()` to drain (except the expected T04 negative).
- **Environment:** Python 3.12.10, SimPy 4.1.2, pytest 9.2.0.
- **Operator/status:** assistant-supported development checks. **Gate 1 remains open for independent student acceptance.** No Model 1/2 or RQ2 experiment was run.

| Check at this revision | Actual result |
|---|---|
| [Fixed T01–T10 selection](../tests/model0_acceptance_nodes.txt) | 13 passed, exit 0: 12 formal-entry end-to-end checks plus the T08 stale-release component negative. |
| Full `tests/` suite | 178 passed, 2 failed, exit 1; no skips or collection errors. Both failures are the unchanged native diagnostics listed below. |
| Raw selected output | 14 original logs, 532 EventRecords. T10 contributes two runs; the T04 negative contributes only ARRIVAL. Records remain in append order. |

Evidence retained for this exact code/test revision:

- [Version, environment, commands with portable path placeholders, results, per-case counts and source/test SHA-256 hashes](evidence/model0-20261124-checks.json).
- [Original selected EventRecord output](evidence/model0-20261124-entry-events.txt), including phases, sequence IDs, state transitions and ownership identifiers.
- [Full-suite console with local output path replaced and both failure explanations preserved](evidence/model0-20261124-full-console.txt).

All 532 records matched the corresponding [2026-11-20 archived traces](evidence/model0-fd71ade-events.csv) field by field in append order after excluding run IDs and normalizing representations. This checks for behavioural changes across revisions. The student still derives the expected traces independently.

The selected cases preserve the expected traces in [the verification plan](VERIFICATION_PLAN.md#2-test-cases-t01t10). T02 runs forward/reverse registration orders; T03 uses three C-only patients at C; T04 separately checks an illegal runtime recommendation and legal A→C→B; T08 separates normal flow from stale-release misuse. These are synthetic software checks, not hospital observations or empirical validation.

### Guard and entry preparation history

| Revision | Work and evidence status |
|---|---|
| `c1363aa` | Added the packaged A/B/C entry file. The student reported 7 passed in 0.18s; the complete student console was not supplied. This report is separate from the assistant reruns above. |
| `487d3b0` | Added a completion-recorded flag and whole-batch duplicate-completion guard. New regressions changed from 3 failed / 1 passed to 4 passed. Full suite: 171 passed / 2 native failures. |
| `74a1cba` | Added due-now/completed-before-release guards, preserving the prior whole-batch identity checks. New release regressions changed from 5 failed / 2 passed to 7 passed; the completion/release files together had 11 passes. Full suite: 178 passed / 2 native failures. |
| `10ac833` | Added the explicit entry selection and raw output in six existing ABC scenarios. Original test logic and assertions were unchanged by an AST comparison. The results and raw output above were then captured at this committed revision. |

The guard regressions are development component evidence; the student's Gate 1 record still needs independent expectations, actual execution and a review decision. The raw logs cannot by themselves prove unlogged internal state. Existing drain/ownership assertions and the component checks remain part of the review.

## Historical checkpoint — 2026-11-20

- **Run date** 2026-11-20
- **Code revision** `fd71adee7c583677dfdf1f7e47283d249e8ddb3f`
- **Environment** Python 3.12.10, SimPy 4.1.2, pytest 9.2.0

The coordinated suites passed all **154** checks, including **11 cases for T01–T10**. The full suite reported **160 passed, 2 failed** (exit code 1). Both failures came from the native SimPy path. These checks were executed with assistant support. **Gate 1 remains open for independent student acceptance.**

## Entry point and execution

At this historical checkpoint, the candidate packaged entry point was `MultiStationCoordinator.run()`. Create one SimPy environment, configure A/B/C, register the case's arrivals, start the coordinator with `env.process(coordinator.run())`, and drain with `env.run()`. The existing tests for T01, T02, T06 and T10 configure A/B. T08 uses a standalone A station. Direct A/B/C runs covered these five cases, with C idle and only A requested in T08. Their ordered records matched the original test records after removing `run_id`. [Model specification](MODEL_SPEC.md)

From the repository root, the full-suite command uses the same options as the recorded run.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q --tb=no -p no:cacheprovider -o pythonpath=src
```

The run used a temporary pytest observer to retain each selected `EventLog.records` in append order. The observer called the original log constructor and left test assertions intact. The A/B/C probes imported the packaged classes directly. For T08, the probe retained u1's active visit at t=3, attempted stale release at t=5 while u2 owned the server, then drained. [Original ordered events and fields](evidence/model0-fd71ade-events.csv)

## T01–T10 results

Expected times and the checks below are in minutes. T04 has two subcases. The CSV `case` column identifies each trace and `run_id` distinguishes repeats.

| Case | Expected from the verification plan | Observed in the run |
|---|---|---|
| T01 | A [0,4), travel [4,5), B [5,8), no wait, departure 8 | Matched with A/B and A/B/C. The packaged log has 19 events. |
| T02 | A serves u1 before u2 at 0 and 4. Departures 8 and 12. | Matched even with u2 registered first. u2 waited 4 minutes at A. |
| T03 | At C, u1/u2 use the two servers at 0. u3 starts at 5. | Peak C occupancy was 2. Departures 5, 5 and 10. |
| T04 negative | Refuse the recommendation of C before A. | Raised the expected eligibility error. Only ARRIVAL was recorded. No trip or visit was started. |
| T04 positive | A→C→B is legal. Departure 15. | Visits occurred in that order and the patient departed at 15. |
| T05 | u1 enters B at 5 and starts at 7. Departures 10 and 13. | Matched. u1's cycle was 7 minutes of service, 1 of travel and 2 of waiting. |
| T06 | At t=4 finish and release u1, admit u3/u4, queue them, serve u2 first. | The raw trace matched and departures were 8, 12, 16 and 20. The A/B/C trace reproduced the A/B trace. |
| T07 | Finish C and depart at 14. | Final release preceded departure. The log ended with DEPARTURE. |
| T08 | u2 starts at 4 after waiting since 1. Stale release cannot affect u2. | u2 waited 3 minutes. The standalone station test and the A/B/C probe both refused the stale release. Departures were 4 and 8. |
| T09 | Admit attempts at 3 and 4, reject at 5. Drain to departures 11 and 15. | Matched. Two admitted patients finished and resources drained. |
| T10 | Two fresh T06 runs yield identical normalized ordered traces. | Both A/B traces and both A/B/C traces matched across all 76 events after removing `run_id`. |

The archive has 861 event rows from 21 logs, including the mixed-B regression, both native diagnostics and the five additional A/B/C logs. Complementary coordinated checks in the same suite cover invalid arrival times, invalid registered packages and stall detection. [Scenario definitions and expected traces](VERIFICATION_PLAN.md#2-test-cases-t01t10) · [Mixed-B evidence](MODEL0_MIXED_B_TRACE.md)

## Open native-path failures

| Check | Expected | Native result |
|---|---|---|
| Same-time ordering at A | u1 starts first in either process creation order. | With the processes created u2 then u1, service also started u2 then u1. |
| T06 at t=4 | u1's SERVICE_END and RESOURCE_RELEASE precede admissions u3 and u4. | The native log recorded both admissions before SERVICE_END and RESOURCE_RELEASE. Departure times still matched. |

The selected formal entry point is now the packaged coordinated path. Native execution remains a historical comparison prototype; it is not an alternative formal Model 0 runner. Its known failures violate the unchanged contract and are not accepted behaviour of the formal entry. The original failure assertions remain visible in the full suite. [Same-time probe](../tests/test_model0_same_time_probe.py#L57) · [Native T06 assertion](../tests/test_model0_t06.py#L311)

## Independent acceptance

The student should reproduce the checks on the recorded entry point, derive expected event orders independently, compare the raw records and record a decision for Gate 1. [Acceptance requirements](VERIFICATION_PLAN.md#3-evidence-required-for-each-student-run-test)
