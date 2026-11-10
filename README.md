# health-exam-mas

**Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres**

面向日常体检中心的多智能体仿真与排队调度策略比较研究（PSP305 FYP）。

## Research scope

- **50%**: Multi-agent simulation, verification and validation of daily health examination flows. Patient Agent states, heterogeneity, autonomous decisions, observable information and interactions are important modelling concerns; specific behavioural rules remain to be justified.
- **40%**: Comparative evaluation of existing Queue Scheduling Policies from a centre-operations perspective in a common environment. FCFS is the confirmed baseline; other policies remain undecided.
- **10% optional**: A focused improvement only if experiments reveal a reproducible limitation.

The proposed architecture separates Patient and Examination Station/Resource Agents and a Routing/Flow Mechanism, with Python + SimPy providing the discrete-event simulation (DES) engine. Routing determines the next eligible examination station; queue scheduling determines who is served next at a station. The Station Agent retains queue/resource ownership and delegates service selection to a replaceable Queue Scheduling Policy. The policy interface is a design provision, not an implemented priority queue.

Model 0 retains its deterministic three-station fixture, fixed routes, FCFS, full compliance (B0) and T01–T10 verification scenarios. A verified stochastic Model 1 can support initial queue-policy comparisons with common flow and B0; Model 2 extends Patient Agent behaviour and is not a prerequisite for every comparison. B1/B2 remain candidate behavioural hypotheses. Candidate outcomes include waiting time, equipment utilization, completions, clearance time and fairness; metric definitions and experimental design are not yet frozen.

Later packages may use checked literature or authentic hospital public package information. Source-supported items, adaptations and synthetic assumptions must be distinguished; final packages, behaviour rules and experiment parameters remain undecided.

## Project documents

- [Research background and literature](docs/RESEARCH_CONTEXT.md)
- [Literature library: verified titles, DOIs, links and research notes](docs/LITERATURE_LIBRARY.md)
- [Simulation and Agent specification](docs/MODEL_SPEC.md)
- [Model assumptions and evidence register](docs/MODEL_ASSUMPTIONS.md)
- [Model 0 verification plan](docs/VERIFICATION_PLAN.md)
- [Codex collaboration guidance](AGENTS.md)

## Development status

**Design-only initialization.** No core simulation code has been implemented, no verification tests have been executed, and no experimental findings have been generated.

`src/` and `tests/` are placeholders for student-authored assessed work. `requirements.txt` lists planned Python dependencies; pin versions after setting up the development environment.

## Academic integrity

Use AI for learning, architecture discussions, design critique and debugging support. Assessed source code, simulation experiments, analysis and conclusions must be completed independently by the student in accordance with PSP305 requirements.
