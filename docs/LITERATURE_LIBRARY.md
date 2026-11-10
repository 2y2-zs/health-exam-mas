# 文献库 | Literature Library

> PSP305 FYP — *Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres*
>
> 更新：2026-11-10。本文献库是**论文证据与阅读索引**，不是已经完成的实验、已校准参数集，也不是已确定的 Queue Scheduling Policy 清单。关键内容应在正式引用时再次检查原文具体页码、表格与方法定义。

## 1. 研究范围与使用规则

本项目研究的是**持续运行、患者陆续到达的日常体检中心**（daily health examination centre），不是普通综合医院门诊，也不是所有受检者同时到达的团体批量体检。邻近领域文献可以借鉴方法，但不可直接移植其流量、人数、服务时长或临床顺序。

- **RQ1 — 多智能体仿真与验证（约 50%）**：患者（Patient Agent）、检查站/资源（Station/Resource Agent）、离散事件仿真（DES）、多种体检项目组合、随机输入、模型验证。
- **RQ2 — 排队调度策略比较（约 40%）**：同一个检查站有患者等待时，决定**下一位由谁接受服务**（Queue Scheduling / Service Selection）。**FCFS** 是目前唯一明确的基线；其他规则须核对来源后选定。
- **RQ3 — 可选改进（约 10%）**：只有在前两部分发现可复现问题后，才考虑局部改进；不预设新算法。

**必须区分的决策：**
1. **Routing / Flow（流程或下一站选择）**：一个受检者下一步去哪个符合要求的检查站。
2. **Queue Scheduling（站点内排队调度）**：一个检查站空闲时，选择哪个已在其队列中等待的受检者先服务。
3. **Appointment / Batch Scheduling（预约或批量预排程）**：患者何时预约或整批患者怎样事先排好计划。

论文标题含有 *scheduling* 不代表它研究的是本项目的 RQ2。以下各论文均注明最接近哪种决策。

## 2. 一览表：已核对论文与 DOI

“直接链接”指公开可打开的论文记录页、期刊摘要页或全文；**打开页面不等于全文一定免费**。

| ID | 文献完整标题（作者，年份） | DOI / 可直接打开的页面 | 研究场景及用途 |
|---|---|---|---|
| P01 | **A heuristic algorithm for the hospital health examination scheduling problem** — Chern, Chien & Chen (2008) | [10.1016/j.ejor.2007.02.029](https://doi.org/10.1016/j.ejor.2007.02.029) | 体检套餐、人员/项目顺序、时间和资源限制；**体检排程** |
| P02 | **Fuzzy-based dynamic scheduling system for health examination** — Chiu & Yeh (2010) | [10.1109/ICMLC.2010.5580551](https://doi.org/10.1109/ICMLC.2010.5580551) | 体检项目动态安排；具体是否等同站点内 Queue Scheduling **待全文核查** |
| P03 | **Using the Integration of Discrete Event and Agent-Based Simulation to Enhance Outpatient Service Quality in an Orthopedic Department** — Kittipittayakorn & Ying (2016) | [10.1155/2016/4189206](https://doi.org/10.1155/2016/4189206) · [免费全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5058573/) | 普通骨科门诊，**DES + ABS 建模与验证的方法参考** |
| P04 | **Resource Allocation and Outpatient Appointment Scheduling Using Simulation Optimization** — Lin, Ling & Yeung (2017) | [10.1155/2017/9034737](https://doi.org/10.1155/2017/9034737) · [免费全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5635465/) | 多阶段、多类型患者、多资源；**结构和仿真优化方法参考** |
| P05 | **An intelligent real-time scheduler for out-patient clinics: A multi-agent system model** — Munavalli et al. (2020) | [10.1177/1460458220905380](https://doi.org/10.1177/1460458220905380) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/32081068/) | 门诊多智能体协调；**架构方法参考** |
| P06 | **Overbooking for physical examination considering late cancellation and set-resource relationship** — Ho et al. (2021) | [10.1186/s12913-021-07148-y](https://doi.org/10.1186/s12913-021-07148-y) · [免费全文](https://link.springer.com/article/10.1186/s12913-021-07148-y) | 体检套餐—资源关联、取消预约及超额预约；**不是站点内 Queue Scheduling** |
| P07 | **Improving patient satisfaction and outpatient diagnostic center efficiency using novel online real-time scheduling** — Jain et al. (2022) | [10.1016/j.orhc.2022.100338](https://doi.org/10.1016/j.orhc.2022.100338) · [期刊页](https://www.sciencedirect.com/science/article/pii/S2211692322000017) | 诊断中心 walk-in、检查约束和资源；具体调度决策**待全文核查** |
| P08 | **Applying Discrete Event Simulation to Reduce Patient Wait Times and Crowding: The Case of a Specialist Outpatient Clinic with Dual Practice System** — Fun et al. (2022) | [10.3390/healthcare10020189](https://doi.org/10.3390/healthcare10020189) · [免费全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC8871892/) | 真实数据输入、DES、候诊拥挤与情景实验；**方法参考** |
| P09 | **Outpatient scheduling problem in smart hospital with two-agent deep reinforcement learning algorithm** — Zuo, Jin & Liu (2024) | [10.1007/s10791-024-09474-1](https://doi.org/10.1007/s10791-024-09474-1) · [期刊页](https://link.springer.com/article/10.1007/s10791-024-09474-1) | 双智能体选择医疗活动/服务台；**须区别于站点内服务次序** |
| P10 | **When do people switch queues? An empirical study of discretionary queue switching at a physical examination center** — Li, Cui, Ji & Wei (2025) | [10.1111/deci.12646](https://doi.org/10.1111/deci.12646) · [期刊页](https://onlinelibrary.wiley.com/doi/abs/10.1111/deci.12646) | 体检中心实际排队切换行为；**行为动机，不直接给 B1/B2 参数** |
| P11 | **Optimization of Batch Centralized Health Examination Scheduling Considering Inter-Item Transition Time and Sex Differences: An Empirical Optimization Study** — Lv et al. (2026) | [10.1002/hsr2.72912](https://doi.org/10.1002/hsr2.72912) · [开放全文](https://onlinelibrary.wiley.com/doi/10.1002/hsr2.72912) | **集中批量体检**；检查站、移动时间、性别差异与约束，不能照搬日常到达模式 |

## 3. 按研究问题整理（中文阅读笔记）

### A. 体检中心与检查项目（首要关注）

**P01 — Chern et al. (2008)**

- **研究什么**：不同年龄、性别和需求的受检者选择不同体检套餐；研究检查顺序、时间与资源限制下的排程问题。
- **对 RQ1 有何帮助**：为“体检套餐 → 所需检查项目 → 资源需求”的建模提供背景。
- **注意**：其整体排程问题不能直接算作某检查站的下一位候选者选择规则；需阅读完整模型再确定能否提取策略。
- **下一步提取**：套餐与资源集合、时间先后约束、决策变量、优化目标。

**P02 — Chiu & Yeh (2010)**

- **研究什么**：按照检查资源可用状态，对体检者后续检查项目进行动态安排。
- **对 RQ1/RQ2 有何帮助**：关注检查项目选择及即时运行状态。
- **注意**：这主要看起来是**下一检查项目安排**，不能仅凭标题把“模糊动态调度”列为站点内部服务优先规则。
- **下一步提取**：全文算法的决策对象、可观察变量、时间尺度、是否涉及同一队列的服务次序；当前**需要原文核查**。

**P06 — Ho et al. (2021)**

- **研究什么**：体检套餐常需占用多种资源；取消预约及超额预约应联合考虑“套餐—资源关系”。
- **对 RQ1 有何帮助**：支持建模套餐异质性、多个检查站资源需求，提示不能仅把体检视为一次独立看诊。
- **对 RQ2 有何帮助**：提供预约层面运营权衡的背景，但不是站点内选择下一位患者的直接证据。
- **注意**：研究中的取消概率、资源结构和套餐比例属于特定机构，未经核实不能用作本项目默认数据。
- **下一步提取**：公开附录中的套餐与所需资源映射，并逐项记录原始项目、模型映射和简化。

**P10 — Li et al. (2025)**

- **研究什么**：基于体检中心观察，分析受检者为何请求改变系统分配的排队安排，以及这种行为与等待进程之间的联系。
- **对 RQ1 有何帮助**：证明受检者行为值得研究，并为以后区分 B0（完全遵从）与候选 B1/B2（有限自主选择）提供动机。
- **注意**：原文讨论的 queue switching **不应自动等同**“入队前改选下一站”。具体何时改选、是否已入队、使用什么信息，仍应以全文方法为准；不能把文中现象当作本项目行为规则的已验证参数。
- **下一步提取**：实测变量、行为发生的时机、识别方法、是否可用于参数校准。

**P11 — Lv et al. (2026)**

- **研究什么**：集中批量体检的检查项目排序，考虑检查站间移动时间、性别相关差异及部分项目先后约束。
- **对 RQ1 有何帮助**：候选检查项目、并行资源和站间移动数据；可作为后续 Model 1 配置的**待复核来源**。
- **注意**：批量预先排程与日常陆续到达不同；其案例数字不是日常中心到达率、服务时间概率分布或套餐比例的证据；原文平均时间也不能自动推导 Gamma 分布。
- **下一步提取**：原文 Table 11/12 的站点、容量、均值、方向性移动时间并核对单位与条件；所有使用数值注明原场景。

### B. DES + 多智能体环境与模型验证

**P03 — Kittipittayakorn & Ying (2016)**

- **研究什么**：结合离散事件仿真（DES）和基于智能体的仿真（ABS）描述门诊工作流程与人员交互，并以真实运营数据验证模型。
- **对 RQ1 有何帮助**：帮助区分“事件/队列/资源”和“智能体状态/行为/交互”，为软件验证与现实有效性验证提供范例。
- **注意**：研究对象是骨科门诊而非体检中心；不可以直接转录其医生配置、服务时长或到达规律。

**P04 — Lin et al. (2017)**

- **研究什么**：多阶段、多服务资源门诊；患者类别、路径和资源技能不同，使用仿真优化资源和预约。
- **对 RQ1 有何帮助**：多阶段流程、患者异质性及有限资源的模型结构参考。
- **注意**：预约和资源配置决策不能直接当作站点内 Queue Scheduling 策略。

**P05 — Munavalli et al. (2020)**

- **研究什么**：使用多智能体协调门诊服务和资源的实时状态。
- **对 RQ1 有何帮助**：理解患者、检查站/部门和调度机制的职责划分。
- **注意**：本项目 Patient / Station / Flow 的具体拆分是自己的设计选择，不能声称论文已经验证了相同的 Python/SimPy 架构。

**P08 — Fun et al. (2022)**

- **研究什么**：用医院信息系统、现场流程观察和服务时长数据构建 DES，再比较不同到达与诊疗开始情景。
- **对 RQ1 有何帮助**：为输入建模、数据来源登记、基线情景和验证设计提供范例。
- **注意**：原医院输入分布须核对场景适配性，不能作为体检中心的通用参数。

### C. 调度与优化方法（先核对决策对象）

**P07 — Jain et al. (2022)**

- **研究什么**：门诊诊断中心处理 walk-in 患者，在检查顺序、资源限制下做在线实时安排。
- **对 RQ2 有何帮助**：可探索动态需求和多检查项目场景下的算法比较方法。
- **注意**：是否包含站点内候诊者服务次序、具体约束和优先规则**需读全文确认**；不能直接列为已选 RQ2 baseline。

**P09 — Zuo et al. (2024)**

- **研究什么**：使用两智能体深度强化学习协调医疗活动选择与服务资源分配。
- **对 RQ2 有何帮助**：可参考状态信息和评价设计，后期再考虑更复杂方法。
- **注意**：活动/服务台分配通常更接近 routing 和 allocation，而不是已经确认的 station queue service selection。本项目**没有决定引入 RL**。

## 4. 文献证据如何转成模型设计

| 待建模对象/需求 | 参考文献 | 可支持的内容 | 仍不得直接推断的内容 |
|---|---|---|---|
| 检查套餐与资源映射 | P01, P06, P11 | 一名受检者可能需要多个检查项目，套餐与资源相关 | 本体检中心实际套餐比例、全部先后顺序 |
| 多站、多阶段流程 | P03, P04, P11 | 多种流程与有限容量的建模机制 | 本项目已通过医院验证的真实路径 |
| DES + Agent 架构 | P03, P05 | 流程、交互和动态状态的建模方法 | 本项目具体 Agent 拆分天然正确 |
| 数据校准与验证 | P03, P08 | 输入来源、基线比较、模型验证思路 | 未提供真实数据时宣称已实证验证 |
| 自主行为/改选请求 | P10 | 行为效应值得研究 | B1/B2 的概率、函数、触发规则已经被论文证实 |
| 队列服务顺序（RQ2） | **FCFS 为项目设计基线**；P02/P07/P09 待核查 | 可进一步寻找策略线索 | 把 Routing、预约排程或批量计划当作 Queue Scheduling |

## 5. 下一轮阅读与待办

1. **优先阅读 P06、P11 原文表格**：提取体检套餐/站点、有限资源、可能的项目次序；建立带页码、来源、原值、单位、适配说明的证据记录。对于 Model 1 候选数值，逐项核对后再引用。
2. **逐篇核对 P02、P07、P09 的决策对象**：只有明确控制“站点空闲时选择哪个已等待患者”的规则，才可能列入 RQ2 Queue Scheduling 候选库。
3. **精读 P10 的方法与定义**：区分入队前另选检查站与入队后换队，不混用术语。
4. **持续补录 Verification / Validation 文献**：应与 [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md) 的证据类别和 [VERIFICATION_PLAN.md](VERIFICATION_PLAN.md) 的设计状态对应。
5. **维护来源状态**：只有确实打开原论文全文、核对相关原始表格/算法/数据后，才能给该具体证据标注 `source-checked`；DOI/论文页已核对不等于所有方法和数值已经核验。

## 6. 文献记录模板

每增加一篇论文，请至少记录：

```text
ID:
Authors / Year:
Full Title:
Venue:
DOI:
Direct URL:
Scenario: daily examination / batch examination / outpatient / other
Decision object: routing / queue service selection / appointment / resource allocation / none
Evidence for RQ1:
Evidence for RQ2:
Data source and parameters (with table/page):
Verification / validation method:
Main limitations:
Applicability to this project:
Evidence status: identified / needs-primary-check / source-checked
Reading date / notes:
```

**学术诚信与研究状态：**本表只整理已经公开发表的研究及可核实页面，不表示已实施任何模型、已运行测试、已经获得医院数据或已确定优化算法。评估性代码、实验、论文分析与结论由学生独立完成。
