# Codex collaboration guidance

Read `docs/RESEARCH_CONTEXT.md`, `docs/MODEL_SPEC.md`, and `docs/VERIFICATION_PLAN.md` before proposing changes.

This is an assessed PSP305 final-year project. The student is responsible for independently writing the core simulation, routing algorithms, conducting experiments, and interpreting results. Codex should focus on explaining concepts, reviewing specifications, pointing out bugs, suggesting verification approaches, and commenting on student-written code. Do not generate the assessed core implementation or fabricate data, test passes, literature, or findings.

Project scope:
- Daily (ongoing, walk-in) health examination centre, NOT a general outpatient hospital or a single batch of examinees.
- 50% agent-based simulation and verification; 40% comparative evaluation of existing routing policies; 10% optional policy improvement.
- Patient, Examination Station/Resource, Routing agents; event-driven SimPy underneath.
- Start with Model 0 deterministic three-station verification, then six-station stochastic Model 1, then autonomous Patient Agent behaviour Model 2.
- Differentiate route override BEFORE joining a queue from queue switching AFTER queue join. The latter is optional.
- Separate verifiable research facts, model assumptions and hypothetical experiments.
- Do not assert empirical patient behaviour probabilities or service-time distributions without validation.

Before altering source or experimental design, give a concise explanation of the impact, assumptions and relevant verification tests. Prefer small reviewable changes and avoid changing these scope decisions without explicit approval.
