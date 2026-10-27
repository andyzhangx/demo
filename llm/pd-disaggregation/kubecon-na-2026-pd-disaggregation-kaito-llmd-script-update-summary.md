# 演讲稿修改总结：先介绍图表，再讲重点

- 日期：2026-10-27
- 文件：`kubecon-na-2026-pd-disaggregation-kaito-llmd.pptx`
- 基线：`4c5603b2bfefd3b73821a4d2c4724a616a4802f9`（包含最新手动上传及 slide 7 修改）
- 范围：52 页英文 notes，含 40 页主讲和 12 页隐藏备份。

## 修改原则

1. 有图表、架构图、流程图、时序图或对照布局时，先说明图的类型、阅读顺序和各区域含义，再解释重点。
2. 准确区分图表、表格、代码片段、流程和文字卡片；不把所有页面都称作“两张图”。
3. 保持英文口语化，可直接朗读；无图的封面、介绍、议程、资源和结束页不硬加图表介绍。
4. 保留技术限定：当前能力与提案、示意图与测量结果、KV 数据与控制路径、延迟目标与容量估算等。
5. 保留原始引用及技术参考段落；不修改可见页面、布局、图像、页码或隐藏状态。

## 逐页修改

| 页码 | 页面 | 图表/布局开场（英文） | 修改说明 |
|---|---|---|---|
| 1 | 00 / Introduction — Cloud Native AI + Inference Day |  | 保留简短开场，不为大会封面虚构图表说明。 |
| 2 | Prefill here, decode there Kubernetes-native LLM inference with KAITO and llm-d |  | 自然介绍完整主题及后续内容，不给标题页增加图表解说。 |
| 3 | Linbo He |  | 保留 Andy 自我介绍、维护项目及 Linbo 因签证无法到场的个性化说明，不添加额外履历。 |
| 4 | How KAITO + llm-d supports P/D |  | 按议程自然串联六部分，不把文字卡片称为图表。 |
| 5 | Prefill: process the prompt and select the first token | Start with the prompt across the top. Below it, the arrows run left to right: five prompt positions, causal prefill, and selection of the first output token. The teal strip underneath explains what we store in the KV cache. | 先说明上方提示词、下方从左到右流程及缓存横条，再解释因果注意力和首 token。 |
| 6 | Decode: consume a token, select the next, repeat | There are two views here. Read the table from top to bottom, one decode step per row. Its columns show the consumed token, the K/V we append, and the next token we select. The timeline below shows token arrivals at the client, from left to right. | 先定位上方逐步表格和下方客户端时间线，再解释缓存时机、TTFT 与 ITL。 |
| 7 | One request. Two latency targets. | The top row follows one request from left to right: prompt, prefill, KV cache, then decode. Below, the left card asks how quickly the answer starts; the right asks how smoothly it continues. | 先解释顶部请求流程和左右延迟目标，再说明指标及 goodput，避免将端到端延迟等同于计算时间。 |
| 8 | One shared pool ties two capacity decisions together | On the left, the shared GPU pool contains three example workers. Each has a teal prefill block and a purple decode block, because each worker handles both phases. The card on the right lists the trade-offs of that arrangement. | 先解释左侧共享池中每个工作单元的两个阶段，再说明右侧干扰与扩容取舍。 |
| 9 | Long prefills can interrupt token delivery | Read these schedules from left to right. The top row uses one shared GPU; the lower panel gives prefill and decode separate workers. Purple D blocks are decode steps, and the teal P block is a new request’s prefill. Block widths and gaps are conceptual, not measured timings. | 先说明上下调度对比、D/P 图例及非实测比例，再讲隔离收益、KV 交接和 chunked prefill。 |
| 10 | Prefill and decode batch different work | The left panel shows prefill: two prompt rows, each with several input positions. The right panel shows ordinary decode: three active requests, each combining its prior KV with one new input token. These are schematic examples, not benchmark batch sizes. | 先逐一定位左右面板中的提示词位置和活动请求，再解释批处理单位及并发限制。 |
| 11 | Separate pools let us tune each phase independently | These two cards separate the capacity decisions: prompt-heavy demand on the left, generation-heavy demand on the right. The three smaller cards below summarize what differs: latency targets, resource needs, and tuning knobs. | 以文字卡片方式说明左右容量决策和下方三类差异，保留拆分成本与工作负载依赖。 |
| 12 | The hard part is the Kubernetes wiring | The center box is one model service. Around it are four things that must agree: routing at the upper left, the KV-transfer contract below it, the decode-side proxy at the upper right, and lifecycle and scaling below that. The connections show coordination, not a step-by-step request trace. | 先从中心服务定位四周模块，明确连线代表协调关系，再讲配置与生命周期同步。 |
| 13 | Open-source P/D has several paths, not one winner | This table is a map of options, not a ranking. The left column names each approach, the middle shows its serving and routing path, and the right shows its Kubernetes packaging. The note below adds LWS DisaggregatedSet, which manages roles rather than supplying the engine or KV transport. | 先说明比较表三列及下方 LWS 注释，再介绍生态选择与 KAITO 定位，强调非排名。 |
| 14 | llm-d: a distributed inference stack | The central diagram runs from clients at the top, through routing, to model servers and GPU nodes below. Integrations enter from the left. Inside the diagram, workload APIs and autoscaling sit to the right; the far-right text explains why these pieces are composed. | 先解释中央架构图上下层级、左侧集成及右侧管理模块，再介绍组合架构和验证边界。 |
| 15 | llm-d: capabilities for distributed inference | On the left are ecosystem logos and, below them, a small community-history chart. That chart tracks GitHub stars over time, not serving performance. On the right are four capability areas; that’s the part we’ll focus on. | 先定位左侧生态与社区历史曲线、右侧四项能力，明确曲线不是性能结果。 |
| 16 | 03 / llm-d and KAITO — well-lit paths | These four cards are llm-d’s ‘well-lit paths’: tested deployment patterns, each framed as a practical question. The top row covers where requests should run and where reusable KV state should live. The bottom row covers expert parallelism and separating prefill from decode. | 以四张文字卡片介绍上下两行主题，不称为图表；保留 MoE 解释和本次重点。 |
| 17 | What is KAITO? | Read the architecture on the left from top to bottom: an InferenceSet manages WorkSpaces, which manage inference workloads, with node pools and GPU nodes underneath. The orange autoscaler follows workload metrics back up to adjust the InferenceSet. The card on the right summarizes what the user gets. | 先介绍左侧 InferenceSet 到工作负载、节点的层级及橙色指标反馈，再讲右侧用户能力。 |
| 18 | KAITO workload example | This is the declaration behind that architecture. At the top, the YAML identifies an InferenceSet. The green values highlight three choices: the replica count near the top, the GPU instance type farther down, and the model ID at the bottom. | 先定位 YAML 中上下位置及三个绿色字段，再解释声明式配置，保留副本数不等于 GPU 数的限制。 |
| 19 | KAITO works out the initial GPU node count | Read this formula block from top to bottom. First we calculate the usable memory on one GPU, then the minimum GPU count, and finally the node count. | 先说明公式自上而下的计算顺序，再解释显存预算、GPU 数和节点数，并保留这不是流量容量估算的限制。 |
| 20 | Why bring llm-d into KAITO? | Across the top are three building blocks: KAITO, llm-d, and vLLM with NIXL. The plus signs mean we combine them; this is not a request sequence. The cards below explain why we chose that combination. | 先定位上方三个组合组件和下方理由卡片，强调不是请求时序；保留 MRI alpha 与自动扩缩容尚待集成。 |
| 21 | 04 / KAITO + llm-d P/D — component boundaries | This responsibility map reads from applications at the top down to infrastructure at the bottom. The left column names each layer; the right explains its job. The highlighted orchestration row is where KAITO and llm-d fit. | 先解释职责表左右两列及上下层次，再逐层介绍组件边界，明确不是安装清单。 |
| 22 | 04 / KAITO + llm-d P/D — one service, two roles | The large card on the left describes what we declare: one model, one endpoint, and two roles. The four cards on the right show who makes that work, from KAITO at the top to vLLM and NIXL at the bottom. | 先介绍左侧声明意图和右侧四层职责卡片，再解释一个服务下两种角色独立配置。 |
| 23 | llm-d picks workers for each role | The upper diagram reads left to right: the gateway asks for a selection, the llm-d Router EPP makes the decision, and the box on the right represents the selected workers. The three points below explain how selection can be configured. | 先说明上方从网关到 EPP 再到选中 worker 的决策图，以及下方三个插件能力点，避免把选点误说为推理执行。 |
| 24 | One endpoint, three separate paths | There are three paths here. The purple band at the top is resource management, not traffic. Below it, blue arrows carry the request from the client on the left to decode on the right. The green path carries KV data directly between the two runtimes. | 先定位顶部资源管理、下方请求路径与绿色 KV 路径，再走请求流程，明确数据方向与读操作发起方不同。 |
| 25 | One MultiRoleInference declares both roles | On the left is the MultiRoleInference YAML. The arrow points to the topology it declares on the right: one logical service at the top, with prefill and decode underneath. The small cards represent role replicas, not individual GPUs. | 先介绍左侧 YAML 到右侧单服务双角色的映射，说明小卡片是副本而非 GPU，并保留示例未验证的声明。 |
| 26 | KAITO creates resources and keeps them aligned | This is a resource and responsibility map. MultiRoleInference sits at the top. The dashed branches lead to prefill resources on the left, decode resources in the middle, and routing resources on the right. They are not network paths or a claim that every object is a direct child. | 先解释顶部 MRI 与下方三组资源的虚线职责树，再讲各组运行时接线，避免误解成网络路径或严格直接子资源。 |
| 27 | The decode sidecar coordinates the P/D request | This sequence diagram reads downward in time. Across the top, from left to right, are the client, gateway, decode sidecar, prefill runtime, and decode runtime. Follow the numbered arrows; the green arrow is the KV payload, not another HTTP call. | 先讲时序图横向五个参与方、纵向时间和绿色 KV 箭头，再按请求、元数据、读 KV、响应的顺序解释。 |
| 28 | 04 / KAITO + llm-d P/D — KV transfer | The prefill worker is on the left and the decode worker is on the right. The arrow between them shows the direction of KV data. The notes underneath describe transport requirements, not extra request-routing steps. | 先定位左右 worker、KV 数据箭头和下方传输要求，再保留 RDMA 前提与实测成本的提醒。 |
| 29 | Scale the role that needs more capacity | These two cards separate the capacity problem by role. Prefill is on the left, decode is on the right, and the strip beneath each card names a starting signal. These are policy ideas, not benchmark charts. | 先说明左右两张角色卡片和下方信号条，再区分 prefill 等待队列与 decode 并发信号，保留提案状态。 |
| 30 | Today, KEDA scales an InferenceSet | This left-to-right flow shows the documented scaling mechanism: a trigger on the left, KEDA and HPA in the middle, and the target InferenceSet on the right. The box below gives a queue-metric example. | 先介绍触发器到 KEDA/HPA 再到 InferenceSet 的现有流程及下方指标示例，明确不等于完整 MRI 策略。 |
| 31 | KAITO autoscaling: keda-kaito-scaler | There is one architecture diagram on the left and a summary card on the right. In the diagram, inference pods sit at the lower left, the KAITO scaler at the lower right, KEDA above it, and the API server and native HPA across the top. | 明确左侧是一张架构图、右侧是摘要卡片，先定位各组件，再解释直读指标、KEDA/HPA 与 AND 的权衡。 |
| 32 | Let prefill and decode scale independently | We have two proposed control loops: prefill in teal on top, decode in purple below. Each row reads left to right from a signal, through a KEDA and HPA decision, to an InferenceSet. The dashed return arrows show feedback as capacity changes. | 先说明上方青色 prefill、下方紫色 decode 两条反馈回路与左右流程，再强调单一控制者和稳定扩缩容。 |
| 33 | One service can scale its two roles separately | Read this proposed policy flow from left to right. Service goals are on the left, policy reconciliation is in the middle, and the path splits into prefill at the upper right and decode at the lower right. | 先解释左侧服务目标经中间策略协调分为右上 prefill 和右下 decode，再说明独立目标仍需 MRI 集成。 |
| 34 | Observe each role. Act on its own capacity. | The top row gives the pattern: policies on the left, decisions in the middle, and serving capacity on the right. The teal and purple rows below apply that same pattern separately to prefill and decode. | 先定位顶部通用模式和下方两条角色流程，再强调有效指标、就绪容量以及路由与扩缩容的区别。 |
| 35 | Proposed policy: scale prefill and decode separately | The left panel proposes role policies in MRI annotations. The upper-right excerpt leaves role replicas unset; the example below shows independent decisions. This is not a deployable manifest: the MRI adapter and child opt-in still need integration. | 先定位左侧策略片段、右上角色副本片段与右下决策示例，再区分角色内 AND、原始公式与 HPA 实际调整节奏。 |
| 36 | Use two gauges to scale the two roles | The left card covers prefill waiting requests; the right covers decode running requests. Each has three decision boxes—scale down, hold, and scale up—with example replica bounds underneath. These are proposed policy thresholds, not measured results. | 先介绍左右角色卡片、三种决策区间和底部副本边界，再保留严格阈值比较及缺失指标不等于零、仍需实现验证的限制。 |
| 37 | Use derived signals to explain the load | This table has four examples. Read across from the native vLLM metric on the left, through the calculation in the middle, to its possible use on the right. | 先说明三列表格的阅读顺序，再解释四种派生信号及其限制，明确尚未集成到 MRI。 |
| 38 | Where KAITO + llm-d goes next | These three cards outline integration directions: cache-aware serving on the left, more inference roles in the middle, and larger-scale execution on the right. | 先定位三个路线图卡片，再说明缓存、E/P/D 和大规模执行方向，避免暗示发布日期。 |
| 39 | Resources | If you'd like to try this, here are the starting points. | 以自然收尾引出项目、扩缩容仓库及 P/D 指南，不生硬描述资源列表的位置。 |
| 40 | 06 / What’s next — Q&A | Thank you for joining us. | 简短致谢并进入问答。 |
| 41（备份） | Split the phases. Tune the pools independently. | There are two pools here: prefill on the left and decode on the right. The arrow between them shows KV cache data moving from prefill to decode. | 先介绍左右两个池和 KV 箭头，再说明独立调优收益及传输成本，保留由 decode 发起读取的说明。 |
| 42（备份） | Different roles need different scaling policies | This table compares two role policies. The left column names the setting, the middle shows prefill, and the right shows decode. The five rows cover signals, replica bounds, scaling thresholds, and shared guardrails. | 先解释策略表的列和行，再比较按副本信号、示例阈值及共同安全要求。 |
| 43（备份） | Three layers. Three clear responsibilities. | Read these three responsibility bands from top to bottom: KAITO, GWIE, and the llm-d Router. Each name is on the left, with its job on the right. | 先定位自上而下三层职责，再区分拓扑、API 合约和端点选择，强调 InferencePool 不是转发代理。 |
| 44（备份） | 03 / llm-d and KAITO — GPU node sizing | The three numbered cards walk left to right through the sizing estimate: memory budget, GPU count, then node count. | 先介绍从左到右三个估算步骤，再解释内存预算到节点数量的过程及版本、性能限制。 |
| 45（备份） | llm-d connects routing, prefill and decode | The bullets are on the left; the numbered flow runs across the right and bottom. Envoy and the scheduler are above, decode is below left, and prefill is below right. The broad NIXL arrow points from prefill to decode. | 先介绍右下方编号流程及反向 KV 箭头，再按调度、协调、prefill、读取 KV、decode 讲解，保留 SLO 非保证。 |
| 46（备份） | The decode sidecar coordinates the request | This diagram has four components. The gateway is on the left; the shaded decode pod contains the sidecar and local vLLM. Remote prefill sits below. Blue arrows carry requests, orange marks optional prefill, and green shows direct KV data transfer. | 先定位网关、pod 边界和三种颜色路径，再说明 sidecar 仅协调请求，KV 直达 decode。 |
| 47（备份） | When should you use P/D—and when not? | This is a two-by-two decision matrix. Left means costly or weak KV transfer; right means cheap, fast-enough transfer. The top row has different role bottlenecks or scaling needs; the bottom row has similar needs. | 先解释二维矩阵的行列含义，再逐象限说明何时拆分、何时优化拓扑或保持聚合。 |
| 48（备份） | Summary | Let me leave you with three takeaways for operating P/D on Kubernetes. | 自然总结三点：独立容量、明确职责、安全扩缩容，并保留 MRI 与公平对比限制。 |
| 49（备份） | 05 / Per-role autoscaling — configuration | These two cards separate today from the proposal: existing scaler settings are on the left, and proposed simplification is on the right. | 先明确左侧现状与右侧提案，再讲配置项和简化方向，不把自动调优或 MRI 集成说成已发布。 |
| 50（备份） | 03 / llm-d and KAITO — CNCF Sandbox project | There are three cards here, read left to right: operate the components, compose the serving stack, and deploy a tested path. | 先介绍三个卡片，再说明运行、组合和部署职责，保留非替代全部组件及非性能保证。 |
| 51（备份） | Safe autoscaling needs one writer and valid data | The three cards cover safety from left to right: replica ownership, metric availability, and lifecycle handoff. | 先定位三类安全卡片，再讲单写入者、真实指标及生命周期交接，强调缺失不是零。 |
| 52（备份） | 03 / llm-d and KAITO — capabilities | These four cards are building blocks, not benchmark results. Across the top are distributed execution and prefill/decode separation; across the bottom are state-aware scheduling and capacity control. | 先定位上下两排四个能力卡片，再区分执行、分离、调度与容量控制，保留验证和 MRI 限制。 |

## 验证结果

- PPT ZIP 部件集合不变；只有 52 个 `ppt/notesSlides/notesSlide*.xml` 部件变化。
- 所有可见 slide XML、图片、图表、布局、关系、主题和隐藏状态逐字节不变。
- Notes 中原有参考资料和非正文对象保持不变。
- 新增讲稿均为英文，直接从口语正文开始。
- 全部 52 页基线图像已渲染并用于图表方位核对；因为页面内容逐字节不变，讲稿修改不影响页面排版。
- 英文口述字数：3420 → 5178（增加图表导览说明）。
- 未在 PowerPoint 桌面版播放验证。
