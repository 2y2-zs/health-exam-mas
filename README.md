# health-exam-mas

**Agent-Based Simulation and Comparative Evaluation of Routing Policies for Daily Health Examination Centres**

面向日常体检中心的基于 Agent 的仿真建模与路径调度策略比较研究（PSP305 FYP）。

## Research scope

- **50%**: Agent-based simulation, verification and validation of daily health examination flows.
- **40%**: Comparative evaluation of existing online routing/scheduling policies in a common environment.
- **10% optional**: A focused improvement only if experiments reveal a reproducible limitation.

The proposed architecture separates autonomous Patient, Examination Station/Resource and Routing Agents, with a SimPy discrete-event engine for time and resource events.

## Project documents

- [Research background and literature](docs/RESEARCH_CONTEXT.md)
- [Simulation and Agent specification](docs/MODEL_SPEC.md)
- [Model 0 verification plan](docs/VERIFICATION_PLAN.md)
- [Codex collaboration guidance](AGENTS.md)

## Development status

**Design-only initialization.** No core simulation code has been implemented, no verification tests have been executed, and no experimental findings have been generated.

`src/` and `tests/` are placeholders for student-authored assessed work. `requirements.txt` lists planned Python dependencies; pin versions after setting up the development environment.

## Academic integrity

Use AI for learning, architecture discussions, design critique and debugging support. Assessed source code, simulation experiments, analysis and conclusions must be completed independently by the student in accordance with PSP305 requirements.
