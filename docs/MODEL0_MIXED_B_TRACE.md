# Model 0 verification record — mixed arrivals at B

**Development check, 2026-11-20.** The coordinated [mixed-arrivals test](../tests/test_model0_coordinated_arrivals.py#L16) passed at commit `b70b48559d6b97029b875c0b891280e896bf5864` on `model0/development-checkpoint`. The calculation below was prepared with assistant support. Independent student acceptance for Gate 1 remains open.

## Fixture and calculation

The simulation starts empty. Rank-2 u2 enters at t=0 with package P1 (A→B). Rank-1 u1 enters at t=5 with P2 (B→C). Times are in minutes. [Model 0 rules](MODEL_ASSUMPTIONS.md#3-model-0-synthetic-software-verification-fixture)

- **Arrival at B.** u2 uses A from 0 to 4 and travels for 1 minute. u1 travels from the entrance to B in 0 minutes. Both reach B at t=5. Phase 3 records the end of u2's existing trip before it records the end of u1's entry trip.
- **Queue position.** Phase 4 considers both patients together. Their queue-entry times tie at 5, so the lower rank places u1 first. B is idle and has one server.
- **Service and waiting.** With a 3-minute service time, u1 occupies B over `[5,8)` and u2 over `[8,11)`. Their waits from queue entry are `5 − 5 = 0` and `8 − 5 = 3` minutes respectively.

## Comparison with the same run

| B-station observation | Expected from rules | Actual sequence IDs and values |
|---|---|---|
| Travel ends at t=5 | u2, u1 | #15 u2, #20 u1 |
| Queue entries at t=5 | u1, u2 | #21 u1, #22 u2 |
| Service starts | u1 at 5, u2 at 8 | #23 u1 at 5, #29 u2 at 8 |
| Waiting from entry to start | u1 waits 0, u2 waits 3 | u1: 5 − 5 = 0 (#21, #23). u2: 8 − 5 = 3 (#22, #29). |

The test checks the order of the five selected events at t=5 and both B service starts over the run. The waits above were calculated from the recorded timestamps. Other log rows provide context beyond the assertions of this case. The full log also contains u1's zero-duration `TRAVEL_START` at sequence #19. Sequence IDs are global and include events outside B.

## Execution evidence

Python 3.12.10, SimPy 4.1.2, pytest 9.2.0. The selected node returned `1 passed in 0.10s` (exit code 0). A read-only observer captured `log.records` when the test returned. The command below reruns the same node with the same pytest options from the repository root. To inspect the live records with a debugger, stop immediately after `env.run()` in the linked test.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider -o pythonpath=src tests/test_model0_coordinated_arrivals.py::test_mixed_travel_sources_join_the_same_b_queue_by_rank
```

<details>
<summary>All 38 emitted events, in original sequence (CSV)</summary>

Empty cells represent null fields. Read the sequence from top to bottom.

```csv
sequence_id,sim_time,phase,event_type,patient_id,station_id,prior_state,new_state,visit_id,resource_token_or_server_id,recommended_station,chosen_station,run_id
1,0,2,ARRIVAL,u2,,,ARRIVED,,,,,coordinated-arrivals
2,0,3,NEEDS_ROUTING,u2,,ARRIVED,NEEDS_ROUTING,,,,,coordinated-arrivals
3,0,3,DECIDING,u2,,NEEDS_ROUTING,DECIDING,,,,,coordinated-arrivals
4,0,3,ROUTE_DECISION,u2,,DECIDING,DECIDING,,,A,A,coordinated-arrivals
5,0,3,TRAVEL_START,u2,A,DECIDING,TRAVELLING,,,,,coordinated-arrivals
6,0,3,TRAVEL_END,u2,A,TRAVELLING,TRAVELLING,,,,,coordinated-arrivals
7,0,4,QUEUE_ENTRY,u2,A,TRAVELLING,WAITING,u2:visit:1,A:u2:u2:visit:1,,,coordinated-arrivals
8,0,5,SERVICE_START,u2,A,WAITING,IN_SERVICE,u2:visit:1,A:u2:u2:visit:1,,,coordinated-arrivals
9,4,0,SERVICE_END,u2,A,IN_SERVICE,IN_SERVICE,u2:visit:1,A:u2:u2:visit:1,,,coordinated-arrivals
10,4,1,RESOURCE_RELEASE,u2,A,IN_SERVICE,NEEDS_ROUTING,u2:visit:1,A:u2:u2:visit:1,,,coordinated-arrivals
11,4,3,DECIDING,u2,,NEEDS_ROUTING,DECIDING,,,,,coordinated-arrivals
12,4,3,ROUTE_DECISION,u2,,DECIDING,DECIDING,,,B,B,coordinated-arrivals
13,4,3,TRAVEL_START,u2,B,DECIDING,TRAVELLING,,,,,coordinated-arrivals
14,5,2,ARRIVAL,u1,,,ARRIVED,,,,,coordinated-arrivals
15,5,3,TRAVEL_END,u2,B,TRAVELLING,TRAVELLING,,,,,coordinated-arrivals
16,5,3,NEEDS_ROUTING,u1,,ARRIVED,NEEDS_ROUTING,,,,,coordinated-arrivals
17,5,3,DECIDING,u1,,NEEDS_ROUTING,DECIDING,,,,,coordinated-arrivals
18,5,3,ROUTE_DECISION,u1,,DECIDING,DECIDING,,,B,B,coordinated-arrivals
19,5,3,TRAVEL_START,u1,B,DECIDING,TRAVELLING,,,,,coordinated-arrivals
20,5,3,TRAVEL_END,u1,B,TRAVELLING,TRAVELLING,,,,,coordinated-arrivals
21,5,4,QUEUE_ENTRY,u1,B,TRAVELLING,WAITING,u1:visit:1,B:u1:u1:visit:1,,,coordinated-arrivals
22,5,4,QUEUE_ENTRY,u2,B,TRAVELLING,WAITING,u2:visit:1,B:u2:u2:visit:1,,,coordinated-arrivals
23,5,5,SERVICE_START,u1,B,WAITING,IN_SERVICE,u1:visit:1,B:u1:u1:visit:1,,,coordinated-arrivals
24,8,0,SERVICE_END,u1,B,IN_SERVICE,IN_SERVICE,u1:visit:1,B:u1:u1:visit:1,,,coordinated-arrivals
25,8,1,RESOURCE_RELEASE,u1,B,IN_SERVICE,NEEDS_ROUTING,u1:visit:1,B:u1:u1:visit:1,,,coordinated-arrivals
26,8,3,DECIDING,u1,,NEEDS_ROUTING,DECIDING,,,,,coordinated-arrivals
27,8,3,ROUTE_DECISION,u1,,DECIDING,DECIDING,,,C,C,coordinated-arrivals
28,8,3,TRAVEL_START,u1,C,DECIDING,TRAVELLING,,,,,coordinated-arrivals
29,8,5,SERVICE_START,u2,B,WAITING,IN_SERVICE,u2:visit:1,B:u2:u2:visit:1,,,coordinated-arrivals
30,9,3,TRAVEL_END,u1,C,TRAVELLING,TRAVELLING,,,,,coordinated-arrivals
31,9,4,QUEUE_ENTRY,u1,C,TRAVELLING,WAITING,u1:visit:1,C:u1:u1:visit:1,,,coordinated-arrivals
32,9,5,SERVICE_START,u1,C,WAITING,IN_SERVICE,u1:visit:1,C:u1:u1:visit:1,,,coordinated-arrivals
33,11,0,SERVICE_END,u2,B,IN_SERVICE,IN_SERVICE,u2:visit:1,B:u2:u2:visit:1,,,coordinated-arrivals
34,11,1,RESOURCE_RELEASE,u2,B,IN_SERVICE,FINISHED,u2:visit:1,B:u2:u2:visit:1,,,coordinated-arrivals
35,11,3,DEPARTURE,u2,,FINISHED,FINISHED,,,,,coordinated-arrivals
36,14,0,SERVICE_END,u1,C,IN_SERVICE,IN_SERVICE,u1:visit:1,C:u1:u1:visit:1,,,coordinated-arrivals
37,14,1,RESOURCE_RELEASE,u1,C,IN_SERVICE,FINISHED,u1:visit:1,C:u1:u1:visit:1,,,coordinated-arrivals
38,14,3,DEPARTURE,u1,,FINISHED,FINISHED,,,,,coordinated-arrivals
```

</details>
