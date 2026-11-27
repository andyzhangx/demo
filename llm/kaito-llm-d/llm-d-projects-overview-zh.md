# llm-d 项目全景介绍与 KAITO 关注点

> 整理日期：2026-11-27。本文基于 [llm-d GitHub 组织](https://github.com/llm-d) 当前仓库列表、主要 README 和归档状态，介绍各项目的职责与关系。
> 默认分支不等于已发布版本；部署或集成时，请按实际使用的 llm-d、GIE、vLLM 和 KAITO 版本核对 API、配置和组件边界。

## 1. llm-d 是什么？

**llm-d 是运行在 Kubernetes 上的分布式大模型推理基础设施。** vLLM、SGLang 负责在 GPU 等加速器上执行模型；llm-d 主要负责上层的请求路由、缓存利用、分离式推理、弹性伸缩和批处理。

它不是一个替代 vLLM 的新推理引擎，也不是单纯的 Kubernetes Operator，而是一组可以组合使用的组件、部署方案和工具。

核心目标包括：

- 根据后端负载和前缀缓存命中情况路由请求。
- 分离 Prefill 和 Decode，独立配置资源与伸缩策略。
- 利用分层 KV cache，减少重复计算。
- 支持大模型专家并行、多租户流控和异步批处理。
- 用可复现的测试与 benchmark 验证效果。

## 2. 整体架构

```text
在线请求
   │
   ▼
Gateway / Proxy
   ├── IPP：解析请求内容，辅助选择模型 / InferencePool
   │
   └── EPP：根据负载、缓存、优先级等选择具体后端
            │
            ├── 普通推理：单个模型服务处理完整请求
            │
            └── 分离式推理：Prefill → KV 数据传输 → Decode
                                             │
                                             ▼
                                         返回生成结果

离线任务 → Batch Gateway → 可选 Async Processor → 上述推理入口

配套：
  KEDA / Prometheus       弹性伸缩
  KV-cache 相关组件        缓存索引与分层卸载
  Simulator / Benchmark  测试与性能评估
  Prism                  性能结果分析
```

这是职责示意图，不表示所有部署都必须安装全部组件。IPP、EPP 通常通过代理的 **ext-proc 外部处理接口**参与请求处理，并不是简单串联的两个 HTTP 网关。

几个重要术语：

| 术语 | 含义 |
| --- | --- |
| Prefill | 处理输入 prompt、生成相应 KV cache 的阶段。 |
| Decode | 基于已有上下文逐步生成输出 token 的阶段。 |
| EPP | Endpoint Picker，选择具体推理后端的组件。 |
| IPP | Inference Payload Processor，处理请求/响应内容并辅助模型路由的组件。 |
| TTFT | Time To First Token，首个 token 的响应时间。 |
| KV cache | 推理时缓存的 Key/Value tensors，不是模型权重文件。 |

## 3. 核心推理与路由项目

### 3.1 llm-d：项目总入口

仓库：<https://github.com/llm-d/llm-d>

主仓库主要提供总体架构、设计文档、安装与运维指南，以及经测试的部署方案，即 **well-lit paths**。

重点场景包括：

- 负载与前缀缓存感知路由。
- Prefill/Decode 分离。
- 大模型专家并行。
- 分层 KV cache。
- 多租户流控、批处理和弹性伸缩。

**适合先从这里理解整体设计并选择部署方案。** 不建议直接拼接多个仓库默认分支上的最新组件，应该从兼容的发布组合和官方指南开始。

### 3.2 llm-d-router：智能请求路由核心

仓库：<https://github.com/llm-d/llm-d-router>

**旧名称是 `llm-d-inference-scheduler`，现在改名为 llm-d Router。**

最重要的组件是 **EPP（Endpoint Picker）**，它回答：

> 一个请求应该交给哪个推理 Pod？

EPP 可以结合以下信息进行决策：

- 后端当前负载与排队情况。
- 哪个后端已有可以复用的 prompt 前缀 KV cache。
- 请求优先级和服务目标。
- 流控与请求排队策略。

当前仓库还包含：

- `InferenceObjective`：定义请求优先级、性能目标等。
- `InferenceModelRewrite`：支持模型名称重写。
- **Disaggregation Sidecar**：协调 Prefill/Decode，或 Encode/Prefill/Decode 多阶段推理。
- 从其他仓库迁入的 KV-cache 索引代码。

Router 支持独立部署模式，也支持与 Kubernetes Gateway API 集成的 Gateway 模式。EPP 是路由决策组件，代理负责实际的数据面转发。

**这里的“调度”主要是请求选后端，不是 kube-scheduler 的 Pod 选节点。**

当前 README 明确说明，核心 EPP 代码以及 `InferenceObjective`、`InferenceModelRewrite` API 已从 Gateway API Inference Extension（GIE）迁入 Router；GIE 侧保留 `InferencePool` API 和 Endpoint Picker 协议等职责。阅读旧版本代码时需要注意组件边界的变化。

### 3.3 llm-d-inference-payload-processor：请求内容处理，IPP

仓库：<https://github.com/llm-d/llm-d-inference-payload-processor>

这是 **Body-Based Routing（BBR）** 相关能力的主要项目，但当前职责已经超出 BBR。这里的 BBR 指基于请求体的路由，不是 TCP BBR 拥塞控制。

IPP 是请求/响应处理插件框架，可以检查或修改：

- 请求和响应的 body。
- Headers、trailers。
- 路由所需的模型信息。

例如，客户端发送：

```json
{
  "model": "qwen-model",
  "messages": [
    {"role": "user", "content": "你好"}
  ]
}
```

IPP 可以从 body 提取 `model`，注入路由 header，让同一个入口服务多个模型或 LoRA adapter。

| 组件 | 主要回答的问题 |
| --- | --- |
| IPP | 请求的是哪个模型，应该进入哪个池？ |
| EPP | 池内具体选择哪个 Pod？ |

这些是典型职责划分，不代表 IPP 只能处理模型字段；它也支持更一般的请求/响应转换。

### 3.4 llm-d-kv-cache：KV 缓存相关库与工具

仓库：<https://github.com/llm-d/llm-d-kv-cache>

关注的是**推理过程中产生的 KV tensors**，不是模型权重文件。相关能力涉及：

- KV block 的位置与状态索引。
- 缓存感知路由。
- 将 KV cache 卸载到 CPU、磁盘或共享存储。
- PVC 缓存空间清理工具。

当前有两项重要迁移：

1. 用于路由的 **KV-Cache Indexer 已迁入 `llm-d-router`**，相关新开发应关注 Router。
2. `llmd-fs-backend` 已上游化到 **vLLM 的多层 offloading connector**；相关新功能在 vLLM 侧继续开发。

因此：

- 修改“缓存命中感知路由”，先看 Router。
- 修改“KV 数据如何落到文件系统”，需要同时看 vLLM 的 offloading 实现。

**与模型权重缓存的区别：**ModelMirror、模型文件流式加载和 Racer 权重缓存主要解决模型的存储、分发与加载；KV cache 主要解决推理运行时的上下文状态复用，两者不能混为一谈。

## 4. 弹性、批处理与异步任务

### 4.1 llm-d-autoscaling：推理服务弹性伸缩

仓库：<https://github.com/llm-d/llm-d-autoscaling>

**当前 `main` 的方向是 KEDA 配置方案和评估框架。**

```text
vLLM / EPP 指标
      ↓
  Prometheus
      ↓
     KEDA
      ↓
     HPA
      ↓
调整推理 Deployment 副本数
```

该仓库提供可参考的 KEDA 配置和实验环境，用于比较或调优：

- 请求队列深度相关指标。
- KV-cache 使用率相关指标。
- 其他推理负载信号。
- Prefill、Decode 不同角色的独立伸缩策略。
- 伸缩过程中的副本数、延迟与吞吐表现。

**旧的 Workload-Variant-Autoscaler（WVA）已在 `main` 上废弃。** 旧实现保留在 `release-0.9` 和冻结的 `legacy/` 中；`legacy/` 计划后续移除，不应作为新集成的基础。

### 4.2 llm-d-batch-gateway：面向用户的批处理 API

仓库：<https://github.com/llm-d/llm-d-batch-gateway>

提供 OpenAI 兼容的 `/v1/batches`、`/v1/files` 接口，负责：

- 上传批量请求文件。
- 创建、查询和取消批任务。
- 拆分和调度请求。
- 收集结果并更新任务状态。

典型用途包括批量生成 embedding、离线总结、数据处理和模型评测。

它包含 API Server、Batch Processor 和可插拔数据层，并内置自适应并发控制。**不强制依赖 `llm-d-async` 才能完成批处理。**

### 4.3 llm-d-async：队列消费与异步请求派发

仓库：<https://github.com/llm-d/llm-d-async>

它更像一个推理任务 worker/dispatcher：

```text
消息队列 → Async Processor → 推理网关 → 结果队列
```

重点是利用空闲算力处理延迟不敏感的请求，并根据容量和准入策略控制派发，减少对在线流量的影响。

| 项目 | 侧重点 |
| --- | --- |
| Batch Gateway | 管理用户看到的批任务、文件、状态和结果。 |
| Async Processor | 控制队列中的请求何时派发、允许多少并发。 |

两者可以组合使用，也可以将 Async Processor 接入已有的业务队列。

## 5. 测试、性能与诊断项目

| 项目 | 用途与边界 |
| --- | --- |
| [llm-d-inference-sim](https://github.com/llm-d/llm-d-inference-sim) | 不用真实 GPU 和大模型，模拟 vLLM 的接口及运行行为，适合路由、流控、伸缩和 CI 测试。不能替代真实 GPU 性能验证。 |
| [llm-d-benchmark](https://github.com/llm-d/llm-d-benchmark) | 部署测试环境、驱动负载、采集吞吐和延迟等数据，构建可复现的性能测试。 |
| [llm-d-prism](https://github.com/llm-d/llm-d-prism) | 汇总不同来源的 benchmark 数据，通过交互界面比较吞吐、延迟、成本和质量，可以理解为性能结果分析台。 |
| [llm-d-pd-utils](https://github.com/llm-d/llm-d-pd-utils) | P/D 部署诊断工具：GPU 拓扑、NVLink、RDMA、NCCL/RCCL、NIXL 传输测试，以及模型启动前的 preflight 检查。 |
| [llm-d-latency-predictor](https://github.com/llm-d/llm-d-latency-predictor) | 根据请求 trace 训练预测模型并提供延迟预测服务，供基于预测延迟的路由评分使用。当前 README 的架构和配置说明仍有 TODO，不能仅凭仓库名称推断成熟度或生产可用性。 |
| [llm-d-api-extensions](https://github.com/llm-d/llm-d-api-extensions) | 给推理服务添加自省 API，暴露启动配置、硬件和 KV-cache 信息，为路由决策提供数据。目前列出的实现是 vLLM endpoint plugin，不是 Kubernetes CRD 集合。 |

简记：**Benchmark 是“跑实验”，Prism 是“看结果”，Simulator 是“没有 GPU 时模拟后端”。**

## 6. 已归档的项目：新部署不要从这里开始

| 仓库 | 当前情况 |
| --- | --- |
| [llm-d-model-service](https://github.com/llm-d/llm-d-model-service) | 原先的 ModelService Operator，已废弃并归档。相关部署职责转向 Helm chart，README 指向 `llm-d-incubation/llm-d-modelservice`。 |
| [llm-d-deployer](https://github.com/llm-d/llm-d-deployer) | 旧的一体化部署 Helm charts，已废弃并归档，转向模块化部署。新部署优先遵循主仓库当前指南。 |
| [llm-d-routing-sidecar](https://github.com/llm-d/llm-d-routing-sidecar) | 独立 P/D sidecar 仓库已归档，代码迁入旧 Scheduler、也就是现在的 `llm-d-router`。 |

**名称混淆提醒：**`llm-d/llm-d-infra` 当前是组织 CI 和维护基础设施仓库；旧部署文档中的 `llm-d-incubation/llm-d-infra` 是另一个仓库，不能混为一谈。

旧仓库中的迁移链接反映历史迁移路径，并不保证其中所有安装命令适用于当前版本；实际部署应从 [llm-d 主仓库](https://github.com/llm-d/llm-d) 和[官方网站](https://llm-d.ai)的当前指南开始。

## 7. 社区维护类仓库

以下项目不是推理数据面的组件：

| 仓库 | 用途 |
| --- | --- |
| [llm-d.github.io](https://github.com/llm-d/llm-d.github.io) | 官方网站。 |
| [llm-d-infra](https://github.com/llm-d/llm-d-infra) | 组织的 CI 和维护基础设施。 |
| [llm-d-go-template](https://github.com/llm-d/llm-d-go-template) | Go 项目模板。 |
| [llm-d-python-template](https://github.com/llm-d/llm-d-python-template) | Python 项目模板。 |
| [.github](https://github.com/llm-d/.github) | 组织级 GitHub 配置和社区材料。 |
| [.project](https://github.com/llm-d/.project) | CNCF 项目元数据与自动化配置。 |

## 8. 从 KAITO 的角度，应该先看什么？

以下是集成研究建议，不代表 KAITO 已支持相应项目当前主线的全部能力。

| 优先级 | 项目 | 与 KAITO 相关的关注点 |
| --- | --- | --- |
| 1 | `llm-d-router` | EPP、请求队列、流控、后端选择和 P/D 协调。 |
| 2 | `llm-d-inference-payload-processor` | 单入口多模型、BBR、请求转换与模型路由。 |
| 3 | `llm-d-autoscaling` | EPP/vLLM 指标如何驱动 KEDA；与 KAITO scaler 的职责边界。 |
| 4 | `llm-d-inference-sim` + `llm-d-benchmark` | 无需 GPU 的功能验证，以及真实 GPU 性能回归。 |
| 5 | `llm-d-kv-cache` + vLLM offloading | 推理运行时缓存，应与权重流式加载分开评估。 |

集成前建议明确：

1. **版本组合：**KAITO 实际锁定的 llm-d、GIE、vLLM 版本是什么？
2. **资源所有权：**谁创建和管理 Gateway、InferencePool、EPP、模型 Deployment 等资源？
3. **伸缩所有权：**是否已有 scaler/HPA 在管理同一个 scale target，如何避免冲突？
4. **指标语义：**队列长度、KV 使用率等指标如何采集，是否区分 Prefill/Decode？
5. **验证层次：**模拟器验证接口与控制逻辑，真实 GPU/网络/存储环境验证性能和可靠性。

## 9. 资料入口

- [llm-d GitHub 组织](https://github.com/llm-d)
- [llm-d 主仓库](https://github.com/llm-d/llm-d)
- [llm-d 官方文档](https://llm-d.ai)
- [Well-lit paths](https://llm-d.ai/docs/well-lit-paths)
- [llm-d Router README](https://github.com/llm-d/llm-d-router#readme)
- [IPP README](https://github.com/llm-d/llm-d-inference-payload-processor#readme)
- [KV-cache README 与迁移说明](https://github.com/llm-d/llm-d-kv-cache#readme)
- [Autoscaling README 与 WVA 废弃说明](https://github.com/llm-d/llm-d-autoscaling#readme)
- [Gateway API Inference Extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension)

本文的项目链接均可继续追溯对应 README。仓库名称、代码位置与推荐部署方式会变化，后续维护应优先更新迁移说明和版本适用范围，而不是将历史文档中的组件边界当成永久事实。
