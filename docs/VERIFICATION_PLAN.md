# Model 0 Verification Plan v1.1

Use this plan to derive and check the Model 0 FCFS traces independently. Future policies need their own service-order expectations. Capacity, legal service and unique ownership still apply. [Recorded development results](../PROJECT_PROGRESS.md#recorded-development-checks)

## 1. Shared fixture and invariants

Use the Model 0 fixture, service intervals and event order in the specification. Start each test with a fresh empty environment unless noted, with stable rank u1 < u2 < u3 < u4. [Fixture and event contract](MODEL_SPEC.md#2-model-0-deterministic-synthetic-fixture)

| ID | Invariant |
|---|---|
| I1 | 0 ≤ Busy_j(t) ≤ Capacity_j for all station event boundaries |
| I2 | Each patient has one lifecycle state and at most one active visit/resource assignment |
| I3 | CompletedTests ⊆ RequiredTests, no duplicate services; FINISHED iff all required tests are completed |
| I4 | Recommendation, queue entry and service start respect hard predecessors |
| I5 | Each travel/service lasts the specified duration; no queue entry before travel completes; waiting ≥0 |
| I6 | FCFS ordered by (queue entry time, patient rank); idle servers do not leave eligible waiting patients idle |
| I7 | Admitted = Active + Finished; rejected arrival attempts are separate; drained simulation has Active=0 |
| I8 | A successful visit has exactly one queue entry, grant/start, completion and release; no requests after FINISHED |
| I9 | Nondecreasing event timestamps, valid causal relationships and agreed same-time domain event order |

A deliberately invalid request should be rejected before changing station state; it is an expected **negative test outcome**, not a successfully drained run.

## 2. Test cases T01–T10

### T01 — single P1 patient, no waiting

- **Initial:** empty A/B/C; u1 required {A,B}; fixed route A→B.
- **Arrivals:** u1@0.
- **Expected trace:** t0 admit, queue A and start A; t4 complete/release A and start A→B travel; t5 queue B/start B; t8 complete/release B, FINISHED/depart.
- **Expected:** A [0,4), travel [4,5), B [5,8); wait=0; service=7, travel=1; cycle=8 minutes.
- **Key invariants:** I3, I5, I7, I8.

### T02 — two P1 patients compete for A

- **Initial:** empty model, u1/u2 both P1.
- **Arrivals:** u1@0, u2@0 (tie u1 before u2).
- **Expected:** u1 A [0,4), A→B [4,5), B [5,8), FINISHED@8; u2 queues A@0, starts A@4 and finishes @8, A→B [8,9), B [9,12), FINISHED@12. u2's A wait=4.
- **Key invariants:** I1, I2, I6, I8.

### T03 — direct three-way competition for two-server C

- **Initial:** **test-only** C-only fixture: each of u1,u2,u3 requires {C}, fixed route C, no hard predecessors; C capacity=2; do NOT require these patients to pass B.
- **Arrivals:** all request C at t0.
- **Expected trace:** queue entries for all three at t0; u1 and u2 service [0,5); u3 waits [0,5), service [5,10).
- **Expected:** finishes u1@5, u2@5, u3@10; waits 0,0,5; maximum busy(C)=2; drained busy(C)=0.
- **Key invariants:** I1, I6, I8, I9.
- **Rationale:** three simultaneous *centre* arrivals on P2 routes would traverse single-server B and do not force a C queue.

### T04 — independent legal eligibility and illegal recommendation rejection

Use **separate fresh environments** for negative and positive subcases.

- **Initial:** P3 with Required={A,B,C}, Completed=∅; hard predecessor A-before-C only. Initial Eligible={A,B}.
- **Arrivals:** u1@0 in each subcase.
- **Negative case:** inject a proposed recommendation of C at t0; must raise/record a clear illegal recommendation error with no travel, C queue entry, resource grant or service; Completed stays empty. Not required to drain.
- **Positive case:** **test-only policy** route A→C→B; A [0,4), travel A→C [4,6), C [6,11), travel C→B [11,12), B [12,15), FINISHED@15.
- **Eligibility assertions:** B is legal initially; after A, both B and C are legal. This excludes accidental extra hard A-before-B or B-before-C.
- **Key invariants:** I2, I3, I4, I8.

### T05 — distinguish travel time and waiting time

- **Initial:** empty model; u1=P1, u2=P2.
- **Arrivals:** u1@0, u2@4.
- **Expected:** u1 A [0,4), A→B [4,5), B queue@5, waits [5,7), B [7,10), finish@10. u2 B [4,7), B→C [7,8), C [8,13), finish@13.
- **Accounting:** u1 cycle=10 = service 7 + travel 1 + waiting 2; **B Queue Entry=5, not 4**.
- **Key invariants:** I2, I5, I6, I8.

### T06 — same-time completion, arrivals and old FCFS queue

- **Initial:** empty model; all four patients=P1; stable tie u3 before u4.
- **Arrivals:** u1@0, u2@1, u3@4, u4@4.
- **Expected at t4:** u1 completes A and releases; new admissions u3/u4 occur; u2 (waiting since t1) is served before newly queued patients; do not let u3/u4 overtake u2. Domain event log should reflect **the actually selected and enforced** same-time ordering, not retrospective sorting.
- **Expected A intervals:** u1 [0,4), u2 [4,8), u3 [8,12), u4 [12,16).
- **Expected B intervals:** u1 [5,8), u2 [9,12), u3 [13,16), u4 [17,20).
- **Finishes:** 8, 12, 16, 20.
- **Key invariants:** I6, I8, I9.

**Companion regression for mixed arrivals at B.** Let rank-2 u2 (P1) enter at t=0 and rank-1 u1 (P2) enter at t=5. Both reach B at t=5. In the raw log, the Phase 3 travel completions are u2 then u1. Phase 4 queue entries are u1 then u2. With B initially idle, u1 starts at t=5 and u2 at t=8. See [coordinated arrival checks](../tests/test_model0_coordinated_arrivals.py).

### T07 — final completion stops new requests

- **Initial:** u1=P3, default A→B→C.
- **Arrivals:** u1@0.
- **Expected:** A [0,4), A→B [4,5), B [5,8), B→C [8,9), C [9,14), FINISHED@14. Completed={A,B,C}; no new request, route, station entry or service for u1 after t14.
- **Key invariants:** I3, I7, I8.

### T08 — release at t can serve an old waiting patient at t

- **Initial:** synthetic **test-only** A-only station fixture, capacity=1, service=4.
- **Arrivals:** u1@0, u2@1.
- **Expected:** u1 A [0,4); u2 queue@1, waits [1,4), serves A [4,8), finish@8; u2 wait=3.
- **Optional negative subcase:** duplicate release of u1's stale ownership token must be refused and leave u2's resource ownership intact.
- **Key invariants:** I1, I6, I8.

### T09 — inclusive intake cutoff, then drain

- **Initial:** all P1, synthetic cutoff H=4; admission iff arrival_time≤4.
- **Arrival attempts:** u1@3, u2@4, u3@5.
- **Expected:** u1 admitted, A [3,7), A→B [7,8), B [8,11), FINISHED@11; u2 admitted, waits A [4,7), A [7,11), A→B [11,12), B [12,15), FINISHED@15; u3 rejected@5, no queues or service.
- **Accounting:** Admitted=2; after cutoff Active=2 (until completions); ultimately Finished=2, Active=0, all resources/queues empty. Rejected=1 not counted in Admitted.
- **Key invariants:** I7, I8, I9.
- **Note:** `env.run(until=H)` is not equivalent to allowing arrivals at H and then draining.

### T10 — deterministic reproducibility of normalized **actual** event trace

- **Initial:** two fresh identical environments, fixture of T06, stable creation/iteration order and patient rank.
- **Arrivals:** u1@0, u2@1, u3@4, u4@4 in both runs.
- **Expected:** actual ordered domain traces match exactly, including timestamp, event order, patient/station, transition and ordering marker; finish times 8,12,16,20 in both.
- **Normalization:** exclude run ID, wall-clock time and memory addresses; **do not sort** logged events before comparison.
- **Key invariants:** all, especially I6, I8, I9.

## 3. Evidence required for each student-run test

Record the configuration, independent calculation, expected and actual ordered traces, assertions and execution result. Explain discrepancies and record expected rejections as negative test outcomes.

### Fixed formal-entry selection

Run the [fixed pytest node selection](../tests/model0_acceptance_nodes.txt) through the [formal Model 0 entry](MODEL_SPEC.md#1-architecture-and-separation-of-responsibilities). T03 and T08 use test-only C-only/A-only packages within the full station registry.

This is **12 end-to-end checks plus one component negative**, covering ten scenario definitions. T02 expands to two checks, T04 has two subcases, and T10 compares two fresh runs within one check. T04's expected recommendation rejection does not require a drained successful simulation.

From the repository root in PowerShell:

```powershell
$evidenceDir = Join-Path $env:TEMP ('model0-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $evidenceDir | Out-Null
$acceptanceNodes = Get-Content .\tests\model0_acceptance_nodes.txt
.\.venv\Scripts\python.exe -B -m pytest -q -s -p no:cacheprovider -o pythonpath=src @acceptanceNodes 2>&1 | Tee-Object -FilePath (Join-Path $evidenceDir 'model0-entry-console.txt')
$LASTEXITCODE | Set-Content (Join-Path $evidenceDir 'model0-entry-exit.txt')
$evidenceDir
```

Retain the following with the student's run:

- Full commit hash, branch, `git status --short`, Python/SimPy/pytest versions and interpreter path; identify any uncommitted changes.
- Exact command, console output, exit code and selected node file. Do not infer a pass from a prior checkpoint.
- Independently derived expectations from §2, then original append-order EventRecords with every field. Do not sort records; normalize only `run_id` and nondomain metadata for T10. Visit identity is `(patient_id, station_id, visit_id)`, not `visit_id` alone.
- I1–I9 review: capacity/ownership, legal and unique completion, exact travel/service and waiting, FCFS ties, patient conservation, once-only visit events and causal/phase order. Trace checks and final-state assertions complement each other; neither alone proves every intermediate state.
- Expected negative outcomes and any discrepancies, including the two known native failures; label component negatives separately from end-to-end runs. Record the student's review and Gate 1 decision explicitly.

Run the full suite separately and retain its actual result. [Development evidence and known Native failures](MODEL0_VERIFICATION_RECORD.md)

### Station guard regressions

[Completion checks](../tests/test_model0_station_completion.py) and [release checks](../tests/test_model0_station_release.py) are component regressions, outside the 13-check selection. `close_services()` refuses a repeated completion before mutating a due batch. `release_services()` preserves whole-batch duplicate/active-identity validation, then requires every visit to end at the current time with completion already recorded before any release. Early, missing-completion, late and mixed invalid batches must be refused without partial mutation. These guards enforce the existing phase 0/1 contract and I8; they do not define a new patient-flow rule.

## 4. SimPy-specific risks to verify

- Check raw order at simultaneous completions, arrivals, queue entries and service starts.
- Confirm a single service-selection authority. SimPy Resource can grant a request immediately, so a station queue and a Resource queue can conflict.
- Compare domain state and ownership across process resumes. Verify exactly one release per visit.
- Record the SimPy version and the selected coordination approach. [Event contract](MODEL_SPEC.md#4-same-time-event-ordering)
- Verify admission at cutoff H and drain-to-completion. T09 covers both.

## 5. Verification and evaluation gates

- **Gate 1** requires independent verification through the formal Model 0 entry point. [Current acceptance status](../PROJECT_PROGRESS.md#in-progress)
- **Gate 2** requires a verified stochastic Model 1 FCFS baseline, checked primary inputs, calibrated or labelled assumptions, and repeated runs. [Model 1 inputs](MODEL_ASSUMPTIONS.md#4-model-1-candidate-examination-centre-configuration)

See the specification for later RQ2 verification and evaluation design. [RQ2 plan](MODEL_SPEC.md#7-rq2-queue-scheduling-policy-evaluation-deferred)
