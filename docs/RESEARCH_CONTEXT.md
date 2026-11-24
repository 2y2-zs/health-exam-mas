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

After Model 0 acceptance, a verified Model 1 can support the first queue-policy comparison under common flow, information, resources and B0. Model 2 explores optional patient behaviour. [Model stages](MODEL_SPEC.md#6-model-1-and-model-2-deferred) · [RQ2 experiment assumptions and candidate outcomes](MODEL_ASSUMPTIONS.md#6-evaluation-assumptions-rq2)

## Modelling and evaluation methods

- Use ODD to describe entities, states, available information, decisions, interactions and process order. Use STRESS to report inputs, run boundaries, implementation and uncertainty. [P15–P16](LITERATURE_LIBRARY.md#c-模型描述报告与验证方法)
- Verify the implementation against its specification and assess validity for its intended use with the available evidence. Model 0 synthetic traces support software verification. [P17](LITERATURE_LIBRARY.md#c-模型描述报告与验证方法) · [Acceptance plan](VERIFICATION_PLAN.md)

Compare the proposed integration with prior work before making a novelty claim. [Literature findings and candidate policies](LITERATURE_LIBRARY.md) · [Rule and input evidence](MODEL_ASSUMPTIONS.md)

## Schedule

- Interim Poster Presentation (poster + video): 2026-12-16 12:00 (PSP305 Module Handbook, 2026/27, PDF p. 4).
- Oral Project Demonstration: 2027-04-05 23:59 (PSP305 Module Handbook, 2026/27, PDF p. 6).
- Dissertation: 2027-05-09 23:59 (PSP305 Module Handbook, 2026/27, PDF p. 6).

Internal milestones, including the target to send the Dissertation draft to the supervisor, are maintained in the [Gantt chart](../poster/gantt.md).
