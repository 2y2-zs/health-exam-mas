# Research context (working v1.1)

Research direction agreed on 2026-11-10. [Current implementation and test evidence](../PROJECT_PROGRESS.md)

## Working title

**Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres**

中文：面向日常体检中心的多智能体仿真与排队调度策略比较研究。

## Research allocation and questions

- **RQ1 (50%)**: Develop a realistically grounded and verifiable multi-agent simulation of a daily health examination centre using Python + SimPy. Patient Agent state, heterogeneous requirements/attributes, observable information, decisions/actions and interactions with stations/resources are central modelling concerns. Simple explicit behaviour is sufficient initially; complex autonomous behaviour is not compulsory. Verify the implementation and qualify external validation according to available evidence.
- **RQ2 (40%)**: Compare existing **Queue Scheduling Policies** from an operational perspective under a common simulation environment: when a station can serve, **which waiting patient is served next**? This is separate from **Routing**, which selects the patient's next station. **FCFS is the only confirmed baseline**; other policies remain to be selected from verified sources.
- **RQ3 (optional 10%)**: Only if RQ1/RQ2 yield reproducible limitations, investigate a focused policy improvement. A new algorithm is NOT mandatory.

## Decision scope and proposed research mechanism

Routing selects the next eligible examination station. Queue scheduling selects the next waiting patient for service. Initial RQ2 comparisons can use verified Model 1 with common flow, information access, resources and B0 full routing compliance. Model 2 examines optional pre-queue behaviour under B1/B2. [Model specification](MODEL_SPEC.md) · [Evaluation assumptions](MODEL_ASSUMPTIONS.md#6-evaluation-assumptions-rq2)

Candidate outcomes include waiting time, resource utilization, completed examinations or patients, clearance time and fairness. Exact metrics, comparison policies and experiment settings are pending.

## Packages and evidence

Use checked primary literature or public hospital package lists and document the original items, station mapping and adaptations. Source operating inputs and precedence separately. [Model 1 evidence priorities](MODEL_ASSUMPTIONS.md#7-priority-evidence-gaps-and-mitigation)

## Literature to consult (verify details before citation)

Check prior work before making a novelty claim. The proposed combination of agent-based modelling, online scheduling and patient behaviour is a research direction to compare with existing studies. [Literature library](LITERATURE_LIBRARY.md)

## Schedule

- Interim Poster Presentation (poster + video): 2026-12-16 12:00 (PSP305 Module Handbook, 2026/27, PDF p. 4).
- Oral Project Demonstration: 2027-04-05 23:59 (PSP305 Module Handbook, 2026/27, PDF p. 6).
- Dissertation: 2027-05-09 23:59 (PSP305 Module Handbook, 2026/27, PDF p. 6).

Internal milestones, including the target to send the Dissertation draft to the supervisor, are maintained in the [Gantt chart](../poster/gantt.md).

## Academic integrity

PSP305 requires the student to perform assessed implementation, technical analysis, evaluation and conclusions. AI may assist with learning, design discussion, code review and debugging explanations, but must not substitute for the student's assessed work. Do not mark any component verified or any experiment completed until the student has performed and recorded it.
