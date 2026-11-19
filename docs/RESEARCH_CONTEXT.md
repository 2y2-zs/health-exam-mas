# Research context (working v1.1)

Updated: 2026-11-10. Research direction revised; no implementation, executed tests or experimental results are established by this update.

## Working title

**Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres**

中文：面向日常体检中心的多智能体仿真与排队调度策略比较研究。

## Research allocation and questions

- **RQ1 (50%)**: Develop a realistically grounded and verifiable multi-agent simulation of a daily health examination centre using Python + SimPy. Patient Agent state, heterogeneous requirements/attributes, observable information, decisions/actions and interactions with stations/resources are central modelling concerns. Simple explicit behaviour is sufficient initially; complex autonomous behaviour is not compulsory. Verify the implementation and qualify external validation according to available evidence.
- **RQ2 (40%)**: Compare existing **Queue Scheduling Policies** from an operational perspective under a common simulation environment: when a station can serve, **which waiting patient is served next**? This is separate from **Routing**, which selects the patient's next station. **FCFS is the only confirmed baseline**; other policies remain to be selected from verified sources.
- **RQ3 (optional 10%)**: Only if RQ1/RQ2 yield reproducible limitations, investigate a focused policy improvement. A new algorithm is NOT mandatory.

## Decision scope and proposed research mechanism

Patient state and examination requirements -> common legal flow/routing rule -> station queue entry -> queue scheduling selects a waiting patient when capacity is available -> service completion updates patient and resource states -> subsequent agent interactions and service decisions.

Keep flow/routing, information access, resource configuration and patient assumptions common across initial queue-policy comparisons. Fixed route, shortest observed queue and shortest estimated wait were earlier routing candidates; they must not be renamed as queue scheduling algorithms. The design interface in MODEL_SPEC separates station service selection from next-station choice; its concrete SimPy queue/resource implementation remains to be selected and verified.

After Model 0 verification, a verified Model 1 with common flow and B0 full routing compliance can support initial RQ2 comparisons. Model 2 is not a prerequisite for those comparisons. B1/B2 pre-queue routing override/choice remain hypotheses to assess before any optional behavioural extension; they are not confirmed patient behaviour or the required mechanism of RQ2.

Candidate operational outcomes include waiting time, equipment/resource utilization, completed examinations/patients, clearance time and fairness. Exact metric definitions, policy candidates and experiments are not frozen. Policy performance, rankings and behavioural effects are research questions, not predetermined conclusions.

## Packages and evidence

Examination packages may be drawn from checked primary literature or authentic hospital-published package lists. Record the original source/URL, relevant table/page or access date, package items, their mapping to model stations, and any omissions, aggregation or assumptions. A package list alone does not establish arrival patterns, package proportions, patient demographics, clinical precedence or service durations. Synthetic Model 0 packages remain software-verification inputs.

## Literature to consult (verify details before citation)

- Chern, Chien & Chen (2008), A Heuristic Algorithm for the Hospital Health Examination Scheduling Problem. https://doi.org/10.1016/j.ejor.2007.02.029
- Chiu & Yeh (2010), Fuzzy-Based Dynamic Scheduling System for Health Examination. https://doi.org/10.1109/ICMLC.2010.5580551
- Jain et al. (2022), Improving Patient Satisfaction and Outpatient Diagnostic Center Efficiency Using Novel Online Real-Time Scheduling. https://doi.org/10.1016/j.orhc.2022.100338
- Munavalli et al. (2020), An Intelligent Real-Time Scheduler for Out-Patient Clinics: A Multi-Agent System Model. https://doi.org/10.1177/1460458220905380
- Kittipittayakorn & Ying (2016), Using the Integration of Discrete Event and Agent-Based Simulation to Enhance Outpatient Service Quality in an Orthopedic Department. https://doi.org/10.1155/2016/4189206
- Ying & Kittipittayakorn (2018), Combining discrete event and agent-based simulation for reducing draftees waiting time in physical examination centers. https://ntut.elsevierpure.com/en/publications/combining-discrete-event-and-agent-based-simulation-for-reducing-/
- Li et al. (2025), When Do People Switch Queues? An Empirical Study of Discretionary Queue Switching at a Physical Examination Center. https://doi.org/10.1111/deci.12646
- Lv et al. (2026), Optimization of Batch Centralized Health Examination Scheduling Considering Inter-Item Transition Time and Sex Differences. https://doi.org/10.1002/hsr2.72912
- Ho et al. (2021), Overbooking for Physical Examination Considering Late Cancellation and Set-Resource Relationship. https://doi.org/10.1186/s12913-021-07148-y

**Literature caution:** ABM in physical examinations, online scheduling, and patient deviation behaviour already exist individually. The proposed integration/gap is a hypothesis to assess by critical comparison, not a claim of being first. Batch-examination parameters cannot simply be treated as observations of ongoing daily arrivals.

The references remain a reading list, not a verified queue-policy catalogue. A paper's use of “scheduling” does not establish that it selects the next waiting patient for service. Check its decision object, information requirements and exact rule before using it as evidence for a queue scheduling policy; retain routing, batch scheduling and behavioural studies only for the claims they actually support.

## Schedule

- Interim Poster Presentation (poster + video): 2026-12-16 12:00 (PSP305 Module Handbook, 2026/27, PDF p. 4).
- Oral Project Demonstration: 2027-04-05 23:59 (PSP305 Module Handbook, 2026/27, PDF p. 6).
- Dissertation: 2027-05-09 23:59 (PSP305 Module Handbook, 2026/27, PDF p. 6).

See the [project Gantt chart](../poster/gantt.md) for internal milestones, including the target for sending the Dissertation draft to the supervisor.

## Academic integrity

PSP305 requires the student to perform assessed implementation, technical analysis, evaluation and conclusions. AI may assist with learning, design discussion, code review and debugging explanations, but must not substitute for the student's assessed work. Do not mark any component verified or any experiment completed until the student has performed and recorded it.
