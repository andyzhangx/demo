# KAITO 里 LoRA / RAG / Inference 三条能力线怎么对应 CRD

本文把一个常见问题讲清楚：**在 KAITO 里，普通推理、LoRA/QLoRA 微调、LoRA adapter 推理、以及 RAG 服务，分别落在哪些 CRD 上？**

结论先说：

- **Inference（普通模型推理）** 的核心入口是 `Workspace`
- **LoRA / QLoRA tuning** 也是用 `Workspace`，只是走 `tuning` 分支
- **LoRA adapter inference** 还是用 `Workspace`，只是走 `inference.adapters[]` 分支
- **Autoscaling / routing** 主要由 `InferenceSet` 和 `InferencePool` 补上
- **RAG** 则是单独的 `RAGEngine` CRD

也就是说，KAITO 的对象模型不是“LoRA 一个 CRD、RAG 一个 CRD、Inference 一个 CRD”这么一一平行，而是：

- `Workspace` 是基础工作负载入口
- `InferenceSet` / `InferencePool` 是规模化与路由层
- `RAGEngine` 是更高层的 RAG 组合应用层

---

## 1. 一张总表

| 能力线 | 主要 CRD / 对象 | 作用 |
|---|---|---|
| Inference | `Workspace` | 定义并部署一个模型推理实例 |
| Inference | `InferenceSet` | 管理同模型的多个副本，并与 KEDA 配合做 autoscaling |
| Inference | `InferencePool` | 对接 Gateway API Inference Extension，承接 inference-aware routing |
| LoRA tuning | `Workspace` | 跑 LoRA / QLoRA 微调任务，产出 adapter |
| LoRA inference | `Workspace` | 在推理工作负载里通过 `inference.adapters[]` 挂载一个或多个 adapter |
| RAG | `RAGEngine` | 定义 embedding、vector DB、RAG service，以及可选的 LLM endpoint |

---

## 2. Inference：普通模型推理对应哪些对象

### 2.1 `Workspace`：基础推理入口

`Workspace` 是 KAITO 的基础 CRD，也是最核心的对象。官方文档把它描述为：

> the basic building block for managing LLM inference/tuning workloads

对普通推理来说，你可以把 `Workspace` 理解为：

- 指定模型或 preset
- 指定 GPU 机型
- 让 KAITO 帮你推导资源、拉起 workload、配置 runtime

所以如果只是“把一个模型作为推理服务跑起来”，最直接的入口就是：

- `kind: Workspace`
- 使用 `inference` 相关配置

### 2.2 `InferenceSet`：多副本与 autoscaling

当你不只是想要“一个推理实例”，而是想要：

- 同模型多副本
- 随请求量扩缩容
- 配合 KEDA 指标做自动伸缩

这时就会上到 `InferenceSet`。

可以把它理解为：

> `InferenceSet` = 一组同模型推理实例的副本与伸缩管理层

它更偏规模管理，而不是定义单个 runtime。

### 2.3 `InferencePool`：路由入口

KAITO 会与 Gateway API Inference Extension 集成，并创建对应的 `InferencePool` 与 EPP（Endpoint Picker）。

所以在 inference 这条线上，可以用一句顺手的话来记：

- **`Workspace` = 跑起来**
- **`InferenceSet` = 扩起来**
- **`InferencePool` = 路起来**

---

## 3. LoRA：训练和推理都落在哪些对象上

LoRA 在 KAITO 里最容易让人误会的点是：**它不是一个独立平行的新 CRD。**

它主要是 `Workspace` 的两种不同使用方式：

1. `Workspace` 做 tuning，产出 adapter
2. `Workspace` 做 inference，挂载 adapter

### 3.1 LoRA / QLoRA 微调：`Workspace` + `tuning`

KAITO 官方文档明确支持：

- `tuning.method: lora`
- `tuning.method: qlora`

因此，LoRA/QLoRA 微调并不是一个单独的 `LoRAJob` 或类似 CRD，而是：

- `kind: Workspace`
- 使用 `tuning` 字段
- 指定输入数据、微调方法、输出位置

一个典型心智模型是：

- 输入：base model + dataset + tuning config
- 过程：KAITO 创建 Kubernetes Job 跑 tuning workflow
- 输出：adapter weights（可以保存成 image 或 volume 中的 artifact）

### 3.2 LoRA adapter 推理：`Workspace` + `inference.adapters[]`

LoRA adapter 训练完成后，推理阶段仍然是 `Workspace`，只是配置方式变了。

官方文档给出的方式是：

- 在 `Workspace` 的 `inference.adapters[]` 中声明一个或多个 adapter
- 推理时把这些 adapter 挂到 base model 上

所以 LoRA serving 的心智模型是：

- base model 仍由 `Workspace` 部署
- adapter 作为附加配置接入推理实例
- 若需要多副本、伸缩、智能路由，再叠加 `InferenceSet` / `InferencePool`

### 3.3 LoRA 这条线的最简映射

可以直接记成：

- **LoRA training** → `Workspace(tuning.method = lora / qlora)`
- **LoRA inference** → `Workspace(inference.adapters[])`
- **LoRA inference at scale** → 再叠加 `InferenceSet` / `InferencePool`

---

## 4. RAG：单独的 `RAGEngine`

RAG 在 KAITO 里不是在 `Workspace` 上多加几行配置这么简单，而是有一条单独的 operator/CRD 线：

- `kind: RAGEngine`

官方文档对 `RAGEngine` 的定义大意是：

- 定义一个完整 RAG 服务需要的组件
- 包括 embedding service、vector DB、RAG service
- 也可以包含可选的 LLM endpoint

### 4.1 `RAGEngine` 负责编排什么

从官方说明看，`RAGEngine` 一般会管理：

- embedding 服务
- vector database
  - 默认可用内置 FAISS
  - 也支持 Qdrant / Milvus 等持久化向量库
- RAG service
  - 基于 LlamaIndex 编排
  - 可提供 indexing、retrieve、chat-completion 类接口
- 可选接入一个 LLM endpoint

因此，`RAGEngine` 更像：

> 一个“组合式 AI 应用 CRD”，而不是单纯的模型运行 CRD

---

## 5. 三条能力线之间怎么组合

最常见的几种组合方式如下。

### 5.1 纯 inference

适合只跑一个普通推理服务：

- `Workspace`
- 可选：`InferenceSet`
- 可选：`InferencePool`

### 5.2 LoRA tuning + LoRA inference

适合产出 adapter 再挂载到推理：

1. `Workspace(tuning)` 跑 LoRA / QLoRA 微调
2. 输出 adapter image 或 volume artifact
3. 另一个 `Workspace(inference.adapters[])` 部署 base model + adapter
4. 如需规模化，再加 `InferenceSet` / `InferencePool`

### 5.3 RAG + inference

适合企业知识库问答：

1. `Workspace` 提供 LLM 推理 endpoint（也可以是外部 LLM endpoint）
2. `RAGEngine` 负责 embedding、vector DB、retrieval、RAG service
3. `RAGEngine` 在请求链路里把检索出来的上下文送给 LLM

### 5.4 LoRA + RAG + inference

适合既要任务适配、又要知识增强的场景：

1. `Workspace(tuning)` 产出 LoRA adapter
2. `Workspace(inference.adapters[])` 部署带 adapter 的推理实例
3. `RAGEngine` 提供知识检索增强
4. 如需副本伸缩和路由，再叠加 `InferenceSet` / `InferencePool`

这个组合对应的职责边界很清晰：

- **LoRA**：让模型更擅长特定任务/风格/领域
- **RAG**：给模型补充最新或私有知识
- **Inference CRD**：把模型服务本身跑起来、扩起来、路起来

---

## 6. 一个简单脑图

可以把 KAITO 的对象模型理解成下面三层：

### 6.1 基础工作负载层

- `Workspace`

负责：

- 普通 inference
- LoRA/QLoRA tuning
- 带 adapter 的 inference

### 6.2 规模化与路由层

- `InferenceSet`
- `InferencePool`

负责：

- replicas
- autoscaling
- inference-aware routing

### 6.3 组合应用层

- `RAGEngine`

负责：

- embedding
- vector DB
- retrieval orchestration
- RAG service
- 与 LLM endpoint 的衔接

因此，LoRA 不是一条完全独立的对象线，而是横跨 `Workspace` 的两种模式：

- `Workspace` for tuning
- `Workspace` for inference with adapters

---

## 7. 最实用的记忆法

### Inference

- `Workspace` = 单实例推理
- `InferenceSet` = 多副本与扩缩
- `InferencePool` = 智能路由

### LoRA

- `Workspace(tuning)` = 训练并产出 adapter
- `Workspace(inference.adapters[])` = 在推理服务里挂 adapter

### RAG

- `RAGEngine` = 编排 embedding + vector DB + retrieval + RAG service

---

## 8. 这和 “LoRA / RAG / inference 是不是同一回事” 的关系

顺手也把一个常见误区说清楚：

- **Inference**：把模型服务跑起来
- **LoRA**：让模型通过参数高效微调更适合某任务/领域
- **RAG**：在推理时给模型补外部知识

它们不是一回事，但在 KAITO 里可以很自然地组合：

- 先用 `Workspace(tuning)` 产出 LoRA adapter
- 再用 `Workspace(inference.adapters[])` 部署带 adapter 的推理服务
- 最后用 `RAGEngine` 给它接上企业知识库

---

## 9. 参考结论

如果只想记一句话，可以记下面这个版本：

> **KAITO 里，`Workspace` 是 inference 与 LoRA/tuning 的基础入口，`InferenceSet` / `InferencePool` 负责规模化与路由，`RAGEngine` 负责 RAG 组合服务。**

---

## References

- KAITO introduction: <https://kaito-project.github.io/kaito/docs/>
- KAITO tuning guide: <https://kaito-project.github.io/kaito/docs/next/tuning/>
- KAITO LoRA adapters guide: <https://kaito-project.github.io/kaito/docs/lora-adapters/>
