# 文献库 | Literature Library

> PSP305 FYP — *Multi-Agent Simulation and Comparative Evaluation of Queue Scheduling Policies for Daily Health Examination Centres*
>
> 更新：2026-11-24。本文是论文证据与阅读索引，不是已校准参数集、最终算法清单或实验结果。保留 P01–P11，补齐 P12–P18；本轮阅读报告中的 C24、M-ODD、M-STRESS、M-VV、B24 分别对应 P14、P15、P16、P17、P18。

## 1. 研究范围与证据边界

本项目研究持续运行、患者陆续到达的**日常体检中心**，不是一般综合门诊或所有患者同时到达的批量体检。邻近场景可提供方法参考，输入不能直接移植。

- **RQ1（约 50%）**：Python + SimPy DES 支撑的 Multi-Agent Simulation；说明 Patient Agent 的状态、异质性、可观察信息、决策与交互，并开展 verification / validation。
- **RQ2（约 40%）**：比较站点的 Queue Scheduling Policies。**FCFS 是唯一已确认基准**，其他算法、指标和实验参数尚未确定。
- **RQ3（可选约 10%）**：前两部分发现可复现问题后，再考虑针对性改进，不要求新算法。

| 决策对象 | 问题 | 不能混同的内容 |
| --- | --- | --- |
| Queue Scheduling / Service Selection | 资源可用时，哪个已排队患者先服务？ | 患者下一站选择 |
| Routing / Flow | 患者下一步去哪个合法检查站？ | 本站候诊者的服务优先级 |
| Appointment / Batch Scheduling | 如何分配预约名额、时段或整批检查计划？ | 单纯站点队列规则 |
| Resource Allocation | 怎样配置或指派服务资源？ | 不改变资源的队列规则比较 |

论文标题含 *scheduling* 并不能确定其决策对象。联合优化的整体收益也不能全部归因于 Queue Scheduling。

证据使用时区分：**原文事实（场景和位置）→ 项目适配（改动与理由）→ 合成验证或敏感性设置（目的与限制）**。方法文献能解释为什么描述或检验某项设计，不能使 Model 0 的数值、六阶段顺序或 B1/B2 行为变成医院事实。证据类别和状态见 [MODEL_ASSUMPTIONS](MODEL_ASSUMPTIONS.md)。

## 2. 统一编号与原文链接

DOI 链接可用于定位出版物，不保证免费全文；“正文已读”不代表附件齐全、算法复现或全部证明核验完成。

| ID | 文献完整标题（作者，年份） | DOI / 原文链接 | 主要定位 |
| --- | --- | --- | --- |
| P01 | **A heuristic algorithm for the hospital health examination scheduling problem** — Chern, Chien & Chen (2008) | [10.1016/j.ejor.2007.02.029](https://doi.org/10.1016/j.ejor.2007.02.029) | 体检整体排程；缺全文 |
| P02 | **Fuzzy-based dynamic scheduling system for health examination** — Chiu & Yeh (2010) | [10.1109/ICMLC.2010.5580551](https://doi.org/10.1109/ICMLC.2010.5580551) | 下一检查室选择：Routing |
| P03 | **Using the Integration of Discrete Event and Agent-Based Simulation to Enhance Outpatient Service Quality in an Orthopedic Department** — Kittipittayakorn & Ying (2016) | [10.1155/2016/4189206](https://doi.org/10.1155/2016/4189206) · [全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5058573/) | 骨科门诊 DES + ABS 与验证方法 |
| P04 | **Resource Allocation and Outpatient Appointment Scheduling Using Simulation Optimization** — Lin, Ling & Yeung (2017) | [10.1155/2017/9034737](https://doi.org/10.1155/2017/9034737) · [全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5635465/) | 含明确的站点 Queue Scheduling；另联合资源与预约优化 |
| P05 | **An intelligent real-time scheduler for out-patient clinics: A multi-agent system model** — Munavalli et al. (2020) | [10.1177/1460458220905380](https://doi.org/10.1177/1460458220905380) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/32081068/) | 门诊 MAS、流程与资源协调 |
| P06 | **Overbooking for physical examination considering late cancellation and set-resource relationship** — Ho et al. (2021) | [10.1186/s12913-021-07148-y](https://doi.org/10.1186/s12913-021-07148-y) · [全文](https://link.springer.com/article/10.1186/s12913-021-07148-y) | 套餐—资源关联及预约名额 |
| P07 | **Improving patient satisfaction and outpatient diagnostic center efficiency using novel online real-time scheduling** — Jain et al. (2022) | [10.1016/j.orhc.2022.100338](https://doi.org/10.1016/j.orhc.2022.100338) · [原文页](https://www.sciencedirect.com/science/article/pii/S2211692322000017) | 在线联合服务顺序、检查顺序与资源指派 |
| P08 | **Applying Discrete Event Simulation to Reduce Patient Wait Times and Crowding: The Case of a Specialist Outpatient Clinic with Dual Practice System** — Fun et al. (2022) | [10.3390/healthcare10020189](https://doi.org/10.3390/healthcare10020189) · [全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC8871892/) | DES 数据输入、验证与情景分析 |
| P09 | **Outpatient scheduling problem in smart hospital with two-agent deep reinforcement learning algorithm** — Zuo, Jin & Liu (2024) | [10.1007/s10791-024-09474-1](https://doi.org/10.1007/s10791-024-09474-1) · [原文页](https://link.springer.com/article/10.1007/s10791-024-09474-1) | 两名优化 Agent 的联合调度 |
| P10 | **When do people switch queues? An empirical study of discretionary queue switching at a physical examination center** — Li, Cui, Ji & Wei (2025; online 2024) | [10.1111/deci.12646](https://doi.org/10.1111/deci.12646) · [原文页](https://onlinelibrary.wiley.com/doi/abs/10.1111/deci.12646) | 自动入队后的 switching 行为 |
| P11 | **Optimization of Batch Centralized Health Examination Scheduling Considering Inter-Item Transition Time and Sex Differences: An Empirical Optimization Study** — Lv et al. (2026) | [10.1002/hsr2.72912](https://doi.org/10.1002/hsr2.72912) · [全文](https://onlinelibrary.wiley.com/doi/10.1002/hsr2.72912) | 集中批量体检、资源与移动时间候选输入 |
| P12 | **Combining discrete event and agent-based simulation for reducing draftees waiting time in physical examination centers** — Ying & Kittipittayakorn (2018) | [10.23055/ijietap.2018.25.2.3458](https://doi.org/10.23055/ijietap.2018.25.2.3458) | 征兵体检 DES + ABS；缺全文 |
| P13 | **Data analysis of ambient intelligence in a healthcare simulation system: a pilot study in high-end health screening process improvement** — Chen et al. (2021) | [10.1186/s12913-021-06949-5](https://doi.org/10.1186/s12913-021-06949-5) · [全文](https://link.springer.com/article/10.1186/s12913-021-06949-5) | 高端体检 FIFO、输入建模及验证 |
| P14 | **Frontiers in Operations: Waiting Experience in Open-Shop Service Networks: Improvements via Flow Analytics and Automation** — Chen et al. (2024) | [10.1287/msom.2022.0590](https://doi.org/10.1287/msom.2022.0590) | Priority 与 Routing 分离；LST / SERPT 候选依据 |
| P15 | **The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism** — Grimm et al. (2020) | [10.18564/jasss.4259](https://doi.org/10.18564/jasss.4259) · [全文](https://www.jasss.org/23/2/7.html) | 模型描述、设计理由与用途 |
| P16 | **Strengthening the reporting of empirical simulation studies: Introducing the STRESS guidelines** — Monks et al. (2019; online 2018) | [10.1080/17477778.2018.1442155](https://doi.org/10.1080/17477778.2018.1442155) | DES / ABS 报告透明性与复现 |
| P17 | **Methods That Support the Validation of Agent-Based Models: An Overview and Discussion** — Collins, Koehler & Lynch (2024) | [10.18564/jasss.5258](https://doi.org/10.18564/jasss.5258) · [全文](https://www.jasss.org/27/1/11.html) | 用途导向的验证方法与局限 |
| P18 | **Frontiers in Operations: The Confidence Trap in Operations Management Practices: Anatomy of Man-Made Disasters** — Bhardwaj & Akkermans (2024) | [10.1287/msom.2023.0034](https://doi.org/10.1287/msom.2023.0034) | 外围 System Dynamics 参考 |

## 3. 贡献、适用范围与阅读边界

以下记录依据截至 2026-11-24 的正文审阅及所列位置。全库 18 篇中，16 篇可获取正文已审阅；P01、P12 缺全文。此状态不表示本项目已复现文献结果或完成医院验证。

### A. 体检流程、输入与行为

**P01 — Chern et al. (2008)**

- **贡献／用途**：摘要、引言及可见片段涉及套餐、检查顺序、时间和资源约束，可作体检整体排程背景。
- **边界／状态**：缺完整模型、例题和算法；不能从片段中的 Round Robin 推导出可用的站点队列规则。全文获取按用户决定暂缓，不承担关键参数或算法证据。

**P02 — Chiu & Yeh (2010)**

- **贡献／用途**：§3、图 1、§4.2 明确输出某受检者下一检查室的优先级，属于 Routing。Mamdani + centroid 使用候选检查时间、预计等待、距离和医生优先级，可供 RQ1 动态流程参考。
- **边界／状态**：六页正文及关键图表已读。专家定义的模糊范围不是随机时长分布；完整规则库省略，图示存在不一致，不能声称精确复现。吞吐改善与耗时节省不是同一指标，也没有患者服从概率证据。

**P06 — Ho et al. (2021)**

- **贡献／用途**：决策为各套餐预约名额，文内表 2、11、13 提供特定套餐—关键资源关系和数据处理范例，支持 RQ1 的需求异质性。
- **边界／状态**：正文和文内附录已读。关键资源清单不等于完整 RequiredTests；每日容量 K 不等于并行服务器数。取消率、套餐比例和成本含特定案例／估计成分，数据不公开，不直接校准 daily walk-in。

**P10 — Li et al. (2025)**

- **贡献／用途**：§4.1 明确患者完成前一项后由系统自动分配下一队列，早于实际移动；已入队者可经工作人员请求 switching，进入目标队末，以后仍需完成跳过项目。支持研究真实行为与队列安排的交互。
- **边界／状态**：作者公开主文及稳健性讨论已读，Appendix DOCX 未取得。该中心有提前预约；观察关联与 GEE 结果不是因果决策函数。曾换队的人群比例、队列记录中的请求比例不能当作 B1 的独立接受概率，也不能直接支持入队前 override。

**P11 — Lv et al. (2026)**

- **贡献／用途**：§6.2、表 10–12 提供集中批量体检的站点、容量、均值与方向性移动时间，是 Model 1 六站候选配置的输入来源。
- **边界／状态**：17 页正文、表 11 和公式 (6)/(7) 已审阅。其批量、有限时长样本不支持日常到达率、套餐比例、Gamma/CV 或临床通用先后关系。表 11 有 12 列但仅 11 个出发站数值行，缺妇科出发行；不可补零、推造或强制对称。印刷公式 (6)/(7) 对同设备双向排序有疑点，不能据此断言作者程序错误。确定性模拟与优化结果比较也不是医院经验验证。

**P12 — Ying & Kittipittayakorn (2018)**

- **贡献／用途**：期刊元数据和摘要表明是征兵体检 DES + ABS 研究，可作邻近方法线索。
- **边界／状态**：缺全文，暂缓获取，不承担具体算法或数值证据。相关会议文章是另一出版物，不能替代本篇并标注“全文已读”。

**P13 — Chen et al. (2021)**

- **贡献／用途**：Methods、表 2–5 描述台湾高端体检 FIFO 流程、多种服务输入和模拟—实际对照，可供 RQ1 输入溯源与验证设计参考。
- **边界／状态**：主文、关键表格与限制已读。部分时长由专家估计，RFID 房间停留不等于纯操作时间；清洗可能影响尾部。约 21 人／日是历史量，30 人／日是扩容情景。验证并非每项完全吻合；结尾 BEWR 是未来建议，不是已给出完整规则并比较的算法。原始数据受限。

### B. 混合建模、站点队列与联合优化

**P03 — Kittipittayakorn & Ying (2016)**

- **贡献／用途**：AnyLogic 骨科门诊 DES + ABS，使用 6 月资料建模、7 月资料验证，适合 RQ1 的方法及资料分离参考。
- **边界／状态**：正文与表 1–3 已读。§2.3 称患者 static objects，§2.4 又称 active agents，不宜据此主张已校准患者自主改选。预约／现场到达及优先规则属于原门诊场景，不能直接证明本项目架构或输入。

**P04 — Lin et al. (2017)**

- **贡献／用途**：§2.3 的 D3 明确为资源可用时选择下一候诊患者；§3.3–3.4 比较 FCFS、SPT、LNS、CP、SQNO、LR，§3.2.2 给出组合规则。是 RQ2 的直接候选来源，修正此前仅列为资源／预约参考的定位。
- **边界／状态**：主文及相关规则、结果已读。SQNO 在此是选择患者所用的下游拥堵信息，不应仅凭名称归为 Routing。整体优化同时改变资源与预约，收益不能全部归于队列；其门诊输入并非体检中心校准数据。

**P05 — Munavalli et al. (2020)**

- **贡献／用途**：Types of agents、Algorithms 1–3、Simulation runs 展示 Patient / Resource / Coordination 的 MAS 及流程协调，配对随机输入的做法可供实验设计参考。
- **边界／状态**：主文已读。Patient Agents 被描述为 passive，重点含路径和资源协调，不能支持已验证的自主 switching、LLM 或本项目完全相同的 Python/SimPy 分工。输入仍含模型设定。

**P07 — Jain et al. (2022)**

- **贡献／用途**：正文变量 X、Z、Y 分别涉及站点服务顺序、患者检查顺序和并行资源指派；在线更新冻结已开始／已完成操作。可供多检查、动态需求及联合决策比较方法参考。
- **边界／状态**：17 页主文已读，Supplementary Document S1 缺失。它不是单纯 Queue Scheduling 插件；案例 time unit 不同，表 4/7 的 Hours 与表 9/11 的 mins 标注冲突，式 16 的分母也需保留原口径。只显示部分到达拟合，不能声称所有输入均经拟合或精确复现。

**P08 — Fun et al. (2022)**

- **贡献／用途**：Methods、表 1–4、Limitations 区分系统到达、现场 TMS 和专家估计，采用 face validation、实际总停留时间对比及 STRESS-DES，供 RQ1 的输入、验证和局限报告参考。
- **边界／状态**：主文已读，详细输入／输出独立附件未完整取得。研究为妇产科 DES；FIFO 是模型假设，总停留时间不等于纯排队等待。清洗与原场景不能忽略，不直接提供 ABM 自治证据。

**P09 — Zuo et al. (2024)**

- **贡献／用途**：§3–5 的两个优化 Agent 联合选择患者操作和服务台，§5.2 包含 SPT、MWKR、MOPNR 与 GA 对比；可供状态与算法评估线索。
- **边界／状态**：主文、表 6–9 数值结果已读，图形表 5 伪代码未逐行核验。不是每名患者拥有一个学习模型；实验含合成配置、忽略移动等假设，不能称医院校准，也不构成本项目必须引入 RL 的理由。数据／实现尚未核实为公开可运行包。

**P14 — Chen et al. (2024)**

- **贡献／用途**：§2.2–2.3、§5.1 区分 Priority（选下一患者）与 Routing（选下一站），比较 FCFS、ACP-LST、ACP-SERPT；Appendix B 为条件明确的独立解析小算例提供线索，是 RQ2 的核心候选依据。
- **边界／状态**：正文与 Online Appendix A–F 已读，未运行复现或全面独立验证证明。§3 的两站确定性理论有适用条件；§4 真实中心有预约和早到安排。Buffer 改变 Flow，不能将整套 ACP 效果归于队列排序。OA.1 的平均服务器数不能直接作整数容量；Appendix D / E 的拥堵计数口径不同。到达参数、时间起点及并列／种子信息仍有复现缺口；部分指标可能方向相反，不能预设所有指标改善或公平性保证。

### C. 模型描述、报告与验证方法

**P15 — Grimm et al. (2020), ODD**

- **贡献／用途**：§1.4、§2.3 明确实体、状态、谁在何时按何顺序行动及更新；§3.6–3.8 和表 2 支持设计理由、输入及用途评估。可完善 RQ1 的 Patient 状态—信息—决策—交互，以及事件读写边界。
- **边界／状态**：20 页主文及图 1–3／表 1–2 已读。S1 仅读 1–28/62 页，S7 仅读 1–4/17 页，其余附件未完整阅读。Sensing 是 Agent 可获信息，Observation 是研究者输出记录。采用 ODD 不证明自治或现实有效性，不强制学习／心理规则，也不规定六阶段或数值参数。

**P16 — Monks et al. (2019), STRESS**

- **贡献／用途**：表 3–4、§5.4–5.6 要求报告模型逻辑、队列规则、输入来源、样本／处理、初值、运行长度、抽样、独立重复、随机流／seed 和软件版本。可支持 RQ1 透明报告与 RQ2 配对输入、输出和不确定性说明。
- **边界／状态**：13 页主文（印刷页 55–67）及表 1–7 已读，原始独立补充清单未完整核验。六类报告内容不是六阶段执行机制；示例 Gamma 不是体检参数。没有固定 30 次、统一 warm-up 或指定 keyed streams 的要求。可复现性不等于 validation；把混合仿真报告原则用于本项目 DES + ABS 是说明清楚的适配。

**P17 — Collins, Koehler & Lynch (2024)**

- **贡献／用途**：§2.3 区分符合规格的 verification 与按用途评估代表性的 validation；§3.13–3.19 讨论 docking，§3.29–3.32 讨论敏感性，§3.53–3.65、§4.29–4.31 支持追踪、互补证据和变更后的迭代检查。
- **边界／状态**：32 页主文、关键图表已读，未另读全部被引文献。跨实现一致可能共享错误，差异须先核对假设；它不裁决原生／协调版的事件顺序。日志、可视化、模拟重复或单个观测落入置信区间都不能独立证明现实有效性。九种方法不是 FYP 必做清单；§3.52 印刷的 family-wise error 公式有数学疑点，不能直接采用。

**P18 — Bhardwaj & Akkermans (2024)**

- **贡献／用途**：§3–4 以 System Dynamics 反馈回路研究运营者、监管者与风险认知，可作动态假设及敏感性报告的外围参考。
- **边界／状态**：主文已读，独立 S1 未读。history-friendly 假想情形参数不是体检数据；不支持本站时长、队列优先级或患者行为，不作为核心输入依据。

## 4. RQ2 候选规则登记：尚未选定的比较方案

| 规则 | 排序依据及来源 | 状态／信息限制 |
| --- | --- | --- |
| FCFS | 本站入队较早者先服务；Model 0 已定义稳定并列规则 | **唯一已确认基准**；不把入中心时间等同本站入队时间 |
| SPT | 本站处理时间较短者先；P04 §3.4 | **候选**；后续明确可用的预期时长估计，不能偷看未来随机实现值 |
| LST | 在整个系统中停留较久者先；P14 的 ACP-LST | **候选**；不等于本站 FCFS，需有入中心时间信息 |
| SERPT | 全部剩余检查的预期处理总时长较短者先；P14 的 ACP-SERPT | **候选**；不同于本站 SPT，需定义未完成项目与预期时长；P14 的处理口径含 call + service |

P04 的 LNS、CP、SQNO、LR，以及 P09 的 MWKR、MOPNR 等仅保留为进一步线索，不承诺全部比较。若只提取 ACP 的排序规则，应标为适配，不声称完整复现 ACP。P02 Fuzzy Routing、P07／P09 联合调度和 P13 的未来 BEWR 不应直接充当已确定的队列基准。

选定前逐项记录决策时机、可用信息、排序与并列规则、非抢占性及资源机制；再确定少量可比策略。共同 Flow / B0 和配对外生输入可用于初始比较，Model 2 不是前提。指标、公平性定义、阈值、重复数及统计方案仍待决定；P14 的 20 分钟阈值不是行业标准。

## 5. 证据到模型的映射与后续核查

| 对象 | 可用参考 | 仍需区分或完成 |
| --- | --- | --- |
| Patient 状态、信息与交互 | P03、P05、P15、P16 | 中心安排与患者自主决策；不能以类名或 ODD 描述证明自治 |
| 套餐、资源和日常输入 | P06、P07、P11、P13 | 原场景、样本、单位、统计口径、映射与简化；组合来源应称 literature-informed scenario，不能称某医院重建 |
| 患者行为 | P10、P15 | 入队后 switching 与入队前 override 分开；B1/B2 仍为未校准假设 |
| 站点服务选择 | P04、P14 | 规则可复现性、信息可用性、共同 Flow 及资源控制 |
| 软件正确性 | P14 简化算例；P15–P17 方法指导 | Model 0、T01–T10 与具体事件契约仍是项目设计；须独立预期与实际执行证据 |
| 医院现实有效性 | P03、P08、P13、P17 | 合适的现实样本、专家判断与用途；不能由 synthetic tests 或 sensitivity 反推参数真实 |
| 复现与随机比较 | P05、P16 | seed 本身不足以配对输入；说明 streams 或预生成输入，保存版本、命令与输出 |

优先事项：

1. 在现有规则登记表逐项补原值、原文位置、适配和证据状态，保留 Model 0 数值及 T01–T10。
2. 确定一个连贯的 Model 1 数据路线；医院公开套餐不能单独证明流量、比例、服务分布或临床先后。
3. 按需要补 P07 S1、P08 独立附件、P10 Appendix 及 P09 图形伪代码。P01／P12 暂缓，P18 S1 可后置；ODD／STRESS 的部分附件边界继续保留。
4. 每项具体主张核查后才标 `source-checked`；`verified-in-code` 与 `validated-empirically` 需要各自执行证据。阅读完成不等于模型验收。
5. 本轮未确认这些论文有一套公开、可直接运行且配齐原始数据的 Python + SimPy 实现；这不证明作者从未发布代码。

## 6. 后续记录要求

每项新增记录保留：ID、作者／年份、完整标题、出版信息、DOI／原文 URL、场景与决策对象、RQ1／RQ2 用途、关键页／表、输入来源与适配、阅读范围、未完成材料及证据状态。更新具体规则时与 [MODEL_SPEC](MODEL_SPEC.md)、[MODEL_ASSUMPTIONS](MODEL_ASSUMPTIONS.md) 和 [VERIFICATION_PLAN](VERIFICATION_PLAN.md) 对齐。

**研究状态：**本次是文献与方法证据更新，没有新增仿真实现、算法复现、研究实验或医院验证。评估性代码、实验、分析与结论按课程要求由学生独立完成；开发和验收记录见 [PROJECT_PROGRESS](../PROJECT_PROGRESS.md)。
