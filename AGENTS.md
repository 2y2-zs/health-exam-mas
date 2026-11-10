# Codex collaboration guidance

Read `docs/RESEARCH_CONTEXT.md`, `docs/MODEL_SPEC.md`, `docs/VERIFICATION_PLAN.md`, and `docs/MODEL_ASSUMPTIONS.md` before proposing changes.

This is an assessed PSP305 final-year project. The student is responsible for independently writing the core simulation, queue-scheduling algorithms and flow mechanisms, conducting experiments, and interpreting results. Codex should focus on explaining concepts, reviewing specifications, pointing out bugs, suggesting verification approaches, and commenting on student-written code. Do not generate the assessed core implementation or fabricate data, test passes, literature, or findings.

Project scope:
- Daily (ongoing, walk-in) health examination centre, NOT a general outpatient hospital or a single batch of examinees.
- 50% multi-agent simulation, verification and validation; 40% comparative evaluation of existing Queue Scheduling Policies from a centre-operations perspective; 10% optional policy improvement.
- Patient and Examination Station/Resource Agents, with a Routing Agent / Flow Mechanism; Python + SimPy DES underneath. Patient states, heterogeneity, autonomy, observable information and interactions are important to RQ1, but no unvalidated complex behaviour is compulsory.
- Queue Scheduling selects who receives service next at a station; Routing/Flow selects the patient's next eligible station. Keep these decisions separate. FCFS is the only confirmed scheduling baseline; other policies remain undecided.
- Start with Model 0 deterministic three-station verification. Preserve its numerical fixture, fixed routes, independent precedence, FCFS, full compliance (B0), T01–T10 and event semantics unless an explicit technical contradiction requires review. A global six-phase coordinator is not mandatory; the SimPy mapping remains open.
- Model 1 extends the stochastic environment; the existing six-station configuration remains a candidate. Once appropriately verified, Model 1 with common flow and B0 can support RQ2 comparisons. Model 2 extends autonomous Patient Agent behaviour; B1/B2 are hypotheses to assess, not prerequisites for every comparison.
- Reserve a replaceable Queue Scheduling Policy interface while keeping the Station Agent responsible for queues, resource ownership and release. Record the risk of conflicting native SimPy Resource and custom scheduling queues; do not assume two independent selection authorities are consistent or implement a priority queue prematurely.
- Differentiate route override BEFORE joining a queue from queue switching AFTER queue join. The latter is optional.
- Separate verifiable research facts, model assumptions and hypothetical experiments.
- Packages may come from checked literature or authentic hospital public information. Record provenance and adaptations; a public package list does not establish arrival patterns, package proportions, service durations or clinical precedence.
- Do not assert empirical patient behaviour probabilities or service-time distributions without validation.
- Waiting time, equipment utilization, completions, clearance time and fairness are candidate RQ2 outcomes. Specific metrics, algorithms, behaviours and experiment parameters remain undecided until explicitly agreed; never mark a design as tested merely because expected traces exist.

Before altering source or experimental design, give a concise explanation of the impact, assumptions and relevant verification tests. Prefer small reviewable changes and avoid changing these scope decisions without explicit approval.
