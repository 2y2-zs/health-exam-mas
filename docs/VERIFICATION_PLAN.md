# Model 0 Verification Plan v1.1 — proposed hand-calculated test oracle

**Status:** This document specifies the deterministic test cases and expected traces. All inputs below are artificial. The student should independently calculate and review expected results before using them as test oracles. See [project progress](../PROJECT_PROGRESS.md) for execution evidence and [MODEL_SPEC](MODEL_SPEC.md) and [MODEL_ASSUMPTIONS](MODEL_ASSUMPTIONS.md) for the design baseline.

**Scope of this oracle:** the fixture, I1–I9 and T01–T10 below retain the deterministic **Model 0 FCFS baseline**. RQ2 now concerns which queued patient a station serves next; routing/flow still chooses the next station and remains a separate mechanism. T04's test-only alternative route continues to check independent eligibility, not an RQ2 routing comparison. Future non-FCFS policies need their own service-order expectations and verification evidence; the FCFS ordering clause of I6 and the exact baseline traces are not universal requirements for those policies. Capacity, legal service, unique ownership and other applicable safety requirements continue to hold.

## 1. Shared fixture and invariants

Default model: A capacity 1 / service 4 min; B capacity 1 / service 3 min; C capacity 2 / service 5 min. Travel A↔B=1, B↔C=1, A↔C=2, entrance→first=0. Default routes: P1 A→B, P2 B→C, P3 A→B→C; P3 hard constraint only A-before-C. B0 accepts all legal recommendations; decisions take zero simulated time; single FCFS queue per station. Patient tie rank u1<u2<u3<u4; half-open service intervals [start,end). Same-time domain **proposed** order: service completions → resource release/progress commit → admissions → travel/routing/request-intent collection → queue commits → service starts. Exact SimPy enforcement is pending implementation decision. Each test creates a fresh empty environment unless specifically noted.

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

Keep for each test: configuration, manual independent derivation, expected trace, actual event trace, assertions used, result (pass/fail only **after execution**), and explanation for discrepancies. Include negative tests in evidence without classifying expected exception as a simulation failure.

Do not claim these cases have passed merely because time-lines have been specified.

## 4. SimPy-specific risks to verify

- SimPy event scheduler ordering is not automatically the domain's six-phase ordering; test exact handling of simultaneous completions, arrivals, queue entries and starts.
- SimPy Resource capacity requests can be granted immediately. The Station Agent must retain a single effective scheduling authority: a custom station queue and SimPy's own waiting/grant queue must not independently reorder the same requests, introduce hidden FCFS selection or grant service contrary to the selected queue policy. The formal implementation must demonstrate a single selection authority. A complex priority queue is outside this verification plan.
- Distinguish station queue selection (which queued patient is served next) from routing/flow (which eligible station a patient visits next) and from SimPy event ordering. Changing one does not establish correctness of the others.
- Distinguish process resume and domain state commits; ensure release occurs exactly once per visit and ownership is clear.
- Choose a stable SimPy version and test contract. Decide whether native processes suffice or a minimal dispatcher is required; a custom global six-phase coordinator remains **optional**, not a mandatory Model 0 feature.
- Verify inclusive cutoff by domain admission checks and drain-to-completion termination, not an abrupt `env.run(until=H)`.

## 5. Verification and evaluation gates

- Gate 1: Model 0 deterministic implementation and independently evidenced verification.
- Gate 2: Model 1 stochastic model (the existing six-station configuration remains a candidate), literature numbers rechecked against primary source, calibrated or labelled assumptions, repeated runs and verification of its extended behaviour with the FCFS baseline.
- Initial RQ2 may follow verified Model 1 under common routing/flow rules and B0: compare subsequently specified existing queue scheduling policies using paired exogenous inputs, appropriate policy-specific checks and uncertainty estimates. FCFS is the only currently defined policy; other candidates remain pending review.
- Model 2 is a possible later behavioural extension: assess whether B1/B2 are needed, then review and verify/validate any chosen responses and their observation boundaries before studying their interaction with queue policies. It is not a prerequisite for every RQ2 comparison.
- Candidate RQ2 outcomes include waiting time, device/resource utilization, completion count or throughput, clearance time and fairness, with cycle time also available for consideration. Metric definitions and experimental scenarios remain open; agree them before experiments rather than treating this verification plan as a finalized evaluation design.

**Gate status:** Prototype test results and outstanding issues are recorded in [project progress](../PROJECT_PROGRESS.md). Gate 1 remains open until the formal Model 0 entry point has independently recorded verification evidence.
