# Dynamo vs llm-d: 分布式 LLM 推理编排框架对比

两者都是 LLM 推理的**编排层（orchestration layer）**，位于推理引擎（vLLM/SGLang/TRT-LLM）之上，解决多 GPU/多节点分布式服务问题。核心能力高度重叠，但设计哲学和实现路径不同。

- **Dynamo**: https://github.com/ai-dynamo/dynamo
- **llm-d**: https://github.com/llm-d/llm-d

## 整体对比

### 相同点

| 能力 | Dynamo | llm-d |
|---|---|---|
| Prefill/Decode 分离（disaggregated serving） | ✅ | ✅ |
| KV-cache 感知路由 | ✅ | ✅（prefix-cache aware） |
| 多层 KV 卸载（GPU→CPU→SSD→远端） | ✅ (KVBM) | ✅（vLLM KVConnector + 文件系统后端） |
| SLA/SLO 驱动的自动扩缩 | ✅ (Planner) | ✅ (Workload Variant Autoscaler) |
| 支持 vLLM / SGLang 后端 | ✅ 两者均支持 | vLLM 为主，SGLang 支持中 |
| NIXL 用于 KV 传输 | ✅ | ✅ |
| OpenAI 兼容 API | ✅ | ✅ |

### 关键差异

| 维度 | **Dynamo**（NVIDIA） | **llm-d**（Red Hat / 社区） |
|---|---|---|
| **主导方** | NVIDIA | Red Hat + 开源社区（IBM 等） |
| **核心语言** | **Rust** + Python | **Go**（调度器）+ Python（vLLM 贡献） |
| **控制面** | 自有服务发现 + etcd/NATS；K8s 通过 Grove operator 可选 | **Kubernetes 原生**——直接构建在 K8s Gateway API / Inference Gateway (IGW) 之上 |
| **部署模型** | 可裸机、可容器、可 K8s（灵活但需额外配置） | **K8s-first**，Helm chart + 标准 K8s API 即控制面 |
| **推理引擎耦合** | 同时深度支持 SGLang、TRT-LLM、vLLM | 深度绑定 **vLLM**，调度器通过 sidecar 编排 P/D |
| **硬件倾向** | 强 NVIDIA 优化（NVLink/NVSwitch/GB200 NVL72） | 硬件中立——显式支持 **NVIDIA GPU、Intel XPU、Google TPU** |
| **路由实现** | 自建 Router 组件，内置 KV overlap 计算 | 复用 **K8s Gateway API 扩展点**（EPP），调度器作为 filter/scorer 插件 |
| **P/D 协调** | 内置于框架的 prefill-decode 调度管道 | Decode 端 **sidecar** 模式，松耦合 |
| **模型启动优化** | **ModelExpress**：GPU-to-GPU 权重流式传输（7× 冷启动加速） | 无等价组件，依赖标准模型加载 |
| **配置调优** | **AIConfigurator**：离线模拟 10K+ 配置找最优 | 无等价组件，靠 benchmark guide 手动调 |
| **多模态/视频** | 原生支持多模态 E/P/D + FastVideo 视频生成 | 聚焦 LLM 文本推理 |

---

## Router 深度对比

### 一、架构定位

| | **Dynamo Router** | **llm-d Inference Scheduler** |
|---|---|---|
| **本质** | 自建的独立路由组件，嵌入 Dynamo Frontend 或独立部署 | K8s Gateway API 的 **EPP（Endpoint Picker）扩展**，嵌入 Envoy ext-proc 回调链 |
| **语言** | **Rust**（核心）+ Python bindings | **Go** |
| **数据面** | Dynamo 自有 HTTP Frontend 直接转发 | **Envoy** 代理 → ext-proc 回调 → EPP 做决策 → Envoy 执行转发 |
| **控制面** | etcd/NATS 服务发现，Router 自维护全局状态 | **K8s API**（InferencePool / InferenceModel CRD）+ GIE 框架 |
| **服务发现** | 动态注册（`register_model()`），通过 etcd 广播 | K8s Pod endpoint 自动发现 |

**核心区别**：Dynamo Router 是个**全自建的有状态路由器**；llm-d 是在标准 K8s Gateway 基础上做**插件式增强**。

### 二、KV Cache 感知路由

这是两者最核心的功能，实现路径完全不同：

#### Dynamo：事件驱动的全局 Radix Tree

```
Worker → KVPublisher → (KV stored/removed events) → KVIndexer (全局 Radix Tree) → Router 查询
```

- 每个 Worker 内嵌 **KVPublisher**，在 block 分配/淘汰时发出事件
- **KVIndexer** 维护全局前缀树（RadixTree），每个节点存储 worker ID + block 信息
- 支持**并发 RadixTree**（多线程，sticky worker routing 保证 per-worker 串行化）或单线程版本
- Block 通过 token hash 标识（含 LoRA adapter name），跨 worker 做精确 overlap 匹配
- Router 调用 `find_matches_for_request(tokens)` → 返回每个 worker 的匹配 block 数

**代价函数**：
```
cost = overlap_score_weight × prefill_blocks + decode_blocks
```
选 cost 最低的 worker。可配 `router_temperature` 做 softmax 采样避免热点。

#### llm-d：Scraper 拉取 + Filter/Scorer 插件链

```
Scraper → 定期拉取 Pod metrics → Datastore → Filter chain → Scorer chain → Pod 选择
```

- **Scraper** 定期从 vLLM Pod 抓取指标（KV cache 命中率、队列深度、负载等）
- **precise-prefix-cache-scorer**：维护自己的 block index，对候选 Pod 做前缀匹配打分
  - 配置 `blockSize`、`maxPrefixBlocksToMatch` 等参数
- 通过 **SchedulingProfile** YAML 编排 filter → scorer → picker 链
- 分数加权后选最高分 Pod

| 维度 | Dynamo | llm-d |
|---|---|---|
| KV 信息获取 | Worker **推送**事件（实时） | Scraper **拉取**指标（周期性） |
| 全局索引 | 自建并发 RadixTree + per-worker 节点 | prefix-cache-scorer 内置 block index |
| 精度 | Block 级精确 overlap（含 LoRA hash） | Block 级匹配，但受拉取延迟影响 |
| 多引擎支持 | SGLang / TRT-LLM / vLLM 均有 KVPublisher | 主要针对 vLLM |

### 三、P/D 分离路由

| | Dynamo | llm-d |
|---|---|---|
| 路由决策 | Router 内置 prefill/decode pool 概念，统一代价函数分配 | **disagg-profile-handler** 插件：为 prefill 和 decode 配置独立 SchedulingProfile |
| 触发条件 | 自动（基于 Planner 决策） | **prefix-based-pd-decider**：当 uncached tokens > 阈值时触发 P/D 分离 |
| KV 传输协调 | 框架内置 | **Decode 端 Sidecar** 协调 vLLM 通过 NIXL 做 P2P KV 传输 |
| E/P/D 三阶段 | 支持多模态 Encode/Prefill/Decode | 实验性支持（`always-disagg-multimodal-decider`） |

### 四、可扩展性与插件化

| | Dynamo | llm-d |
|---|---|---|
| 扩展方式 | 代码级：修改 Router 的 Rust 逻辑或 Python bindings | **YAML 声明式**：配置 filter/scorer/picker 插件组合 |
| 自定义路由 | 需要编写 Rust/Python 代码 | 实现 Go interface → 注册插件 → YAML 引用 |
| Profile 机制 | 无（单一代价函数） | **SchedulingProfile**：可为不同请求类型定义不同 filter/scorer 链 |
| Label 过滤 | 无对等功能 | **by-label-selector**：直接用 K8s label selector 过滤 Pod（如 `hardware-type: H100`） |

llm-d 的插件化显著更强——可以纯 YAML 组装路由策略，不改代码。

### 五、多 Router 协同

**Dynamo**：支持**多 Router 实例**间通过 Inter-Router Communication 同步状态：
- `AddRequest` / `RemoveRequest` / `OverlapUpdate` 三种事件
- 保证分布式环境下路由一致性

**llm-d**：EPP 本身无状态（或低状态），依赖 K8s API + Envoy 的负载均衡机制天然支持水平扩展。不需要显式的 router 间同步。

### 六、额外路由能力

| 能力 | Dynamo | llm-d |
|---|---|---|
| 优先级调度 | `nvext.agent_hints.latency_sensitivity` + 队列策略（FCFS / WSPT） | 多租户公平性 + 优先级（通过 scorer 权重） |
| 背压控制 | `router_queue_threshold` | Envoy 层面流控 + EPP 层面 filter |
| Session affinity | 通过 KV cache overlap 隐式实现 | 显式支持 |
| LoRA 路由 | Block hash 含 adapter name，自动路由 | cache-aware LoRA routing（v0.5） |
| 多模型 | 单 Router 服务单模型 | **InferencePool CRD** 原生支持多模型共享集群 |

---

## 总结

- **Dynamo** = NVIDIA 的全栈推理操作系统。Rust 性能 + 深度 NVIDIA 硬件集成 + 自有控制面，功能最全但生态绑定更强。Router 是**高性能有状态路由器**，实时事件驱动、全局 RadixTree、精确 block overlap 计算，性能天花板更高。

- **llm-d** = Kubernetes 原生的推理编排。复用标准 K8s Gateway API，硬件中立，组件松耦合，更适合已有 K8s 平台的多云/多硬件场景。Scheduler 是**K8s 原生的声明式调度框架**，插件化 filter/scorer 链、YAML 编排、Envoy ext-proc 集成，灵活性和可扩展性更好。

**工程选型建议**：纯 NVIDIA GPU 集群追求极致性能 → Dynamo；K8s 平台上需要多硬件、多模型、可定制路由策略 → llm-d。
