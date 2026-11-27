# BBR 与 Inference Payload Processor（IPP）：演进关系与能力边界

## 结论与比较口径

**IPP 是 BBR 演进后的独立项目，不是把 BBR 推倒重写。**

BBR（Body-Based Routing）最初属于 Gateway API Inference Extension（GIE）。早期实现主要从请求 JSON 中提取 `model`，写入 `X-Gateway-Model-Name`，供网关选择 InferencePool。随着请求与响应插件框架的发展，BBR 的职责已经超出“按 body 路由”，因此迁移到 llm-d 组织，改名为 Inference Payload Processor。

[迁移提案][migration]明确把“重写或重新设计现有 BBR 框架”和“在迁移过程中新增 payload 插件”列为 **Non-Goals**。所以不能把当前 IPP 的每一项能力都说成“改名后新增”。

本文核对日期为 **2026-11-26**，采用以下范围：

- **早期 BBR 基线**：GIE [1964 插件化提案][bbr-proposal]对 **v1.2.1 初始实现**的描述，不代表迁移前最后一个 BBR 版本。
- **迁移前后关系**：以 llm-d 0.7 文档中的迁移提案为依据；迁移前 BBR 已经是请求与响应 payload 的可插拔处理框架。
- **当前 IPP 能力**：以核对时 `main` 的提交 [`373c6b25056a848be71792395ce4add108d9d682`][ipp-commit]及其文档为依据，**不保证全部已包含在某个发布镜像或 Helm chart 中**。
- GIE 提案引用固定在提交 [`f6274684049e1fdda587d8adfe6d7f07032c083e`][gie-commit]，便于复核。若要回答某次升级的精确增量，还需要旧 BBR tag 与目标 IPP 版本逐项比较。

## 能力对比

下表比较的是“早期单一用途实现”与“当前框架”，不是迁移提交的功能清单。

| 维度 | 早期 BBR（上述基线） | 当前 IPP（固定提交） |
| --- | --- | --- |
| 定位 | 从请求 body 提取模型名，辅助 pool 路由 | 可检查、修改推理请求和响应的 headers/body；路由是主要用途之一 |
| 项目归属与发布 | GIE 仓库内组件 | 独立的 llm-d 仓库、所有权与发布周期 |
| 请求处理 | `model` → `X-Gateway-Model-Name` | `body-field-to-header`、`base-model-to-header`、`model-selector` 等插件组合 |
| 响应处理 | 初始能力描述不包含响应插件框架 | profile 的完整 body / 流式 chunk 扩展点；全局 post-processing 支持响应 header / 完整 body，内置 `model-name-to-header` |
| 多模型与 LoRA | 依据提取的模型名匹配路由 | 根据 LoRA adapter 与 base model 的配置关系，通过 header 与 HTTPRoute 选择兼容的 pool；仍需保留 adapter 身份并确保后端可服务它 |
| 模型选择 | 使用客户端指定的模型名 | `Filter → Score → Pick`，选出具体模型后改写请求 `model` |
| 跨请求数据 | 初始实现不提供通用数据层 | Extractor、Collector、Datasource 维护模型配置、in-flight 等决策数据 |
| 配置与扩展 | 初始逻辑较固定 | YAML `PayloadProcessorConfig`、profiles、插件参数与引用；自定义 Go 插件需注册并构建 |
| 网关接入 | body 提取结果由网关路由消费 | 独立 ext-proc 服务；Helm 支持 Istio、GKE 接入，也可手工连接代理 |

**迁移前较晚期 BBR 已经具备请求/响应插件化框架。** 早期提案中的 DAG、guardrail、动态能力等设计讨论，也不能直接当成当前已交付功能；应以目标版本的实现、注册列表和配置为准。

## IPP 具体做什么

### 1. 保留 body-based routing，扩展 payload 处理

典型插件包括：

- `body-field-to-header`：把指定 JSON 字段复制到指定请求 header，例如 `model` → `X-Gateway-Model-Name`。
- `base-model-to-header`：通过带标签的模型映射 ConfigMap，把模型名或 LoRA adapter 名映射为 base model，设置 `X-Gateway-Base-Model-Name`。
- `model-selector`：执行模型选择，并将选中的具体模型写回请求 body。
- `model-name-to-header`：配置在全局 `postProcessing.plugins`，从请求周期状态读取选中的模型，在响应 header 中返回；需要请求所选 profile 执行过 `model-selector`，并非任意请求都会自动生成此响应头。它实现 `ResponseHeadersProcessor`，不能放入仅接受完整 body / chunk 接口的 profile `response` 列表。

模型映射 ConfigMap 可以被 watch 并更新，但这只说明映射数据可更新，**不等于任意插件代码或整个 pipeline 可以运行时热加载**。ConfigMap 映射也不会替你部署、下载或加载 LoRA adapter。

### 2. 模型选择，不只是提取模型名

模型选择管线为：

```text
候选模型 → Filter → Score → Pick → 改写请求 model → 提取路由 header
```

当前文档中的示例插件包括：

- `model-group-name-filter`：精确模型名保留同名候选；`auto` 保留全部候选；`auto/chat` 只保留配置为 `chat` 组的候选模型。
- `inflight-requests-scorer`：依据数据层记录的每模型 in-flight 数量评分，较低负载得分较高。
- `max-score-picker`、`random-picker`、`weighted-random-picker`：分别按最高分、均匀随机、按分数加权随机选择。
- `cost-scorer`：仓库内有参考实现，但**默认 runner 未注册**；不能只加一段 YAML 就假定官方默认二进制能使用它。默认 runner 已注册的 `costguard` 是另一个 scorer，不应混淆。

`auto` / `auto/chat` 是配置相应插件后的语义，不是网关看到字符串就会自动生效。模型组属性、候选模型和所需信号必须存在；它也不是自动理解 prompt 难度或保证回答质量的语义路由器。

### 3. 数据层与 profiles

- **请求内状态**：通过 cycle state 在同一请求的插件之间共享，例如选中模型供响应插件使用。
- **跨请求状态**：由数据层维护，供 filter、scorer、profile picker 等读取。
- **Extractor**：异步消费请求/响应事件；例如 `request-metadata-extractor` 更新每模型的 in-flight 计数。
- **Collector / Datasource**：分别适用于周期采集和 watch 等持续同步机制。
- **Profile**：每个请求选择一个 profile，再执行其 request/response 插件；只有一个 profile 且未显式配置 picker 时，自动使用 `single-profile-picker`。
- **全局处理阶段**：`preProcessing` 已在 profile 选择前执行；全局 body post-processors 在 profile 的完整响应 body 插件后执行，header post-processors 则在响应 headers 阶段执行。它们不是尚未接入的占位字段，详见下文的文档与代码差异。

这些计数是处理器观察到并异步更新的信号，不应无条件等同于模型服务器的精确实时队列或全局所有副本的负载。

`model-config-datasource` 从 JSON 文件同步候选模型，并支持显式配置 `groups` 和 `pricing`。**这里上游文档与代码存在差异**：插件文档仍写“默认 runner 未注册”，但固定提交的 [runner 注册代码][runner]已经注册它，[datasource 实现][modelconfig]也已处理模型组与价格。因此本文以该提交的代码为准；不要把过时的文档限制套用到所有版本。`chat` 分组仍需显式配置，不会自动产生。

## LoRA adapter 是什么，为什么要映射到 base model？

> 本节概念说明补充于 2026-11-27；不改变上文基于固定提交的 IPP 能力核对范围。以下模型名称和部署拓扑仅用于解释，不是可直接部署的完整配置。

### 1. LoRA adapter：基础模型上的一组微调参数

**LoRA（Low-Rank Adaptation，低秩适应）是一种参数高效微调方法。** 它通常冻结基础模型的原始参数，只训练一小组额外参数；这组参数通常称为 **LoRA adapter（适配器）**。

例如，针对同一个兼容的 Qwen 基础模型，可以训练不同的 adapter：

```text
Qwen + 客服 adapter → 适应客服问答任务
Qwen + SQL adapter  → 适应 SQL 生成任务
Qwen + 法律 adapter → 适应法律领域任务
```

Adapter **不是一个完整的模型，不能独立运行**，需要与兼容的基础模型一起使用。它也不是 system prompt 或知识库文件，而是训练得到的参数；并不是任何 adapter 都能与任意 Qwen/Llama 模型混用。

对于应用 LoRA 的权重矩阵，可简化理解为：

```text
有效权重 = 基础权重 W + adapter 增量 ΔW
ΔW = 缩放因子 × B × A
```

`A`、`B` 是低秩矩阵，其参数量通常远小于原始权重矩阵。相比全参数微调，这样可以降低需要训练、保存的参数量和相应的训练资源开销。具体效果仍取决于模型、训练方法和任务。

### 2. 多个 adapter 可以共用一份基础模型

如果推理引擎支持并启用了 multi-LoRA，一个模型服务可以加载一份基础模型，再服务多个 adapter：

```text
一个支持 multi-LoRA 的 vLLM 服务
├── 一份兼容的 Qwen 基础模型权重
├── 客服 adapter，对外模型名 qwen-customer-service
├── SQL adapter，对外模型名 qwen-sql
└── 法律 adapter，对外模型名 qwen-legal
```

每个请求指定要使用哪个 adapter，从而减少不同微调版本之间基础模型权重的重复加载。Adapter 自身仍然占用资源，具体并发、加载和容量限制由引擎及配置决定。

**部署 IPP 不会自动启用 multi-LoRA，也不会自动训练、下载或加载 adapter。** 这些属于模型服务的配置与生命周期管理职责。

### 3. “映射到 base model”是查路由关系，不是转换模型

假设平台有两组后端：

```text
qwen-pool
└── 运行 Qwen，能够服务 qwen-customer-service、qwen-sql

llama-pool
└── 运行 Llama，能够服务 llama-legal
```

客户端发送：

```json
{
  "model": "qwen-sql",
  "messages": [
    {"role": "user", "content": "查询最近一个月销售额最高的十个商品"}
  ]
}
```

`qwen-sql` 是对外暴露的 adapter 模型名称。IPP 根据显式配置的映射关系知道它依赖 Qwen：

```text
请求模型 qwen-sql → 基础模型 qwen → 由 HTTPRoute 选择 qwen-pool
```

这里不是把 adapter 转换成基础模型，也不是 IPP 根据名称猜测模型兼容性，而是使用平台提供的映射数据辅助路由。

### 4. 为什么需要 header 和 HTTPRoute？

模型名在 JSON body 中，而标准 Gateway API `HTTPRoute` 的匹配条件不会直接解析 JSON body 中的 `model` 字段。因此，IPP 将模型信息转换成网关可以匹配的 header。

在本文固定提交所描述的 `base-model-to-header` 插件配置下，典型流程是：

```text
① 客户端：body.model = qwen-sql
          │
          ▼
② IPP：查配置映射，qwen-sql → qwen
          │
          ▼
③ base-model-to-header 设置路由 header
   X-Gateway-Base-Model-Name: qwen
          │
          ▼
④ HTTPRoute 匹配 header，选择 qwen-pool
          │
          ▼
⑤ EPP 在该 pool 中选择能够服务此请求的 endpoint/Pod
          │
          ▼
⑥ 模型服务器使用 Qwen + SQL adapter 完成推理
```

IPP 通过代理的 ext-proc 接口参与处理；上图是职责与决策顺序示意，并不意味着 IPP 是所有推理流量都直接穿过的独立 HTTP 反向代理。具体代理配置还需要保证路由决策能够消费修改后的 header。

### 5. 关键边界：保留 adapter 身份，选中的后端必须支持它

**用于选择 pool 的基础模型信息，与后端执行时需要的 adapter 信息，是两件事。**

```text
路由 header：X-Gateway-Base-Model-Name: qwen
请求 body：  model = qwen-sql
```

对于这种显式指定 adapter 的请求，典型做法是保留 body 中的 `qwen-sql`，额外设置基础模型路由 header。模型服务器依靠原始 adapter 名选择对应的微调参数。

如果直接把 body 中的 `model` 改成 `qwen`，又没有通过其他受支持的机制保留 adapter 身份，后端可能只执行基础模型，而不是 SQL adapter。不要将 `base-model-to-header` 的路由映射与 `model-selector` 的主动选模、body 改写混为一谈。

此外，选对基础模型池并不代表请求必然成功：

- 最终后端必须已经加载该 adapter，或者具备经过配置和验证的加载机制。
- 不能假设同一个 pool 的所有 Pod 都自动拥有所有 adapter。
- 如果不同 Pod 的 adapter 可用性不同，需要相应的后端筛选/路由能力，或将 pool 组织为具有一致服务能力的后端集合；仅增加 ConfigMap 映射不能解决这个问题。
- 未知 adapter、映射缺失、加载失败等情况，需要按目标版本验证错误处理，不能默认静默退回基础模型。

简言之：**基础模型决定兼容的后端集合，adapter 决定使用哪个微调版本；IPP 提供模型到 pool 的路由依据，但不负责保证 adapter 已在后端可用。**

## 两个请求示例

以下是流程说明，不是完整的可直接部署配置。模型名为示意值，实际必须与模型服务器、候选数据、映射和 HTTPRoute 一致。

### 示例 A：明确指定 `qwen`

```json
{"model":"qwen","messages":[{"role":"user","content":"你好"}]}
```

早期 BBR：

```text
model=qwen → X-Gateway-Model-Name: qwen
           → HTTPRoute 匹配 → qwen 的 InferencePool → EPP 选 Pod
```

当前 IPP 可配置成相同的简单行为：

```text
body-field-to-header → X-Gateway-Model-Name: qwen
                     → HTTPRoute 匹配 → qwen 的 InferencePool → EPP 选 Pod
```

也可配置 `base-model-to-header`，用 `X-Gateway-Base-Model-Name` 进行路由。例如请求 `qwen-lora-a`，映射指向 `qwen` 时，网关仍选择 qwen pool，而 body 中的 adapter 名可保留给支持该 adapter 的模型服务器。无需为了显式模型请求强行启用自动模型选择。

### 示例 B：请求 `auto/chat`

```json
{"model":"auto/chat","messages":[{"role":"user","content":"解释 Kubernetes Deployment"}]}
```

假设已经配置候选模型及其 `chat` 组属性、in-flight 数据采集，以及以下插件：

```text
model-selector
  ├─ model-group-name-filter：只留下 chat 组候选
  ├─ inflight-requests-scorer：按观察到的 in-flight 负载评分
  └─ max-score-picker：选择最高分模型，例如 qwen
→ 请求 body 改为 model=qwen
→ body-field-to-header / base-model-to-header
→ HTTPRoute 选择 pool
→ EPP 选择该 pool 中的 Pod
```

在相同配置下，`auto` 则不按 `chat` 组缩小候选。若配置 `model-name-to-header` 响应插件，可把实际选中的模型名返回给客户端。没有候选、没有正确的数据来源或只开启字段提取插件时，都不能把 `auto/chat` 当成已经可用的自动路由能力。

## 配置与部署：不要把“可插拔”理解成“自动可用”

下面是仅复制模型名到请求 header 的最小配置示意；它不包括 Gateway、HTTPRoute、InferencePool、代理连接或模型部署：

```yaml
apiVersion: llm-d.ai/v1alpha1
kind: PayloadProcessorConfig
plugins:
  - type: body-field-to-header
    parameters:
      fieldName: model
      headerName: X-Gateway-Model-Name
profiles:
  - name: explicit-model
    plugins:
      request:
        - pluginRef: body-field-to-header
```

- `PayloadProcessorConfig` 是进程读取的 YAML 配置，**不是可直接创建的 Kubernetes CRD**；通常由 Helm 放入 ConfigMap 并挂载，启动时由 loader 校验。
- 自定义插件需要实现相应 Go 接口、注册 factory，并构建包含该插件的 runner；YAML 负责选择和组合已注册插件，而不是下载执行任意插件代码。
- 数据层插件放在顶层 `datalayer` 的相应列表，不能把 Extractor / Datasource 当成普通 request 插件串入 profile。
- Helm 的 `provider.name=istio` 生成 `EnvoyFilter` 等接入资源；`gke` 生成 `GCPRoutingExtension`；`none` 只创建 IPP 核心资源，代理接入需自行配置。
- 上游架构按每 Gateway 一个 IPP 部署描述；IPP 与 EPP 独立配置和部署。需要核实代理对 ext-proc `FULL_DUPLEX_STREAMED` 等模式的支持及事件开关。

## 与 EPP、KAITO、Racer 的分工

```text
客户端 → Gateway/Proxy → IPP：payload 处理、模型选择、路由 header
                      → HTTPRoute：根据 header 选择 InferencePool
                      → EPP：在 pool 内选择 endpoint/Pod
                      → 模型服务器：执行推理
响应   ← Gateway/Proxy ← IPP：按配置处理响应 ← 模型服务器
```

| 组件 | 主要回答的问题 | 不能替代的职责 |
| --- | --- | --- |
| IPP | 请求用哪个模型、如何处理 payload、如何提供 pool 路由依据？ | 不管理模型工作负载，不替 EPP 选择具体 Pod |
| EPP（Endpoint Picker Extension） | 已选 pool 中，哪个 endpoint/Pod 更适合？ | 不是 IPP 的通用请求/响应处理框架 |
| KAITO | 如何声明、部署和管理模型服务工作负载及相关资源？ | 上游 IPP 有插件不代表 KAITO 已自动暴露对应 API 或完成集成 |
| Racer | 模型文件/权重的数据分发、缓存与加载加速如何实现？ | 不负责 HTTP payload 的模型选择，也不替代 EPP 调度；不同于推理 KV-cache 路由信号 |

因此，IPP 的 data layer 是**决策元数据层**，不能与 Racer 的模型数据缓存混为一谈。它们可以在一个服务系统中协作，但不会因为都使用“数据/缓存”就承担相同职责。

## 当前限制与落地检查

1. **全局 pre/post 已接入，旧文档说明滞后**：固定提交的 architecture/configuration 文档仍写“预留、尚未调用”，但 [loader][loader] 已加载这些插件，[runner][runner] 已传给服务端，[请求 handler][request-handler] 在 profile 选择前调用 `preProcessors`，[响应 handler][response-handler] 在 profile body 插件后调用 `postProcessors`，并在响应 headers 阶段调用 header post-processors。因此不能继续沿用“pre/post 未接入”的结论；本文以该提交代码为准，不推定较旧发布版本也具有相同行为。
2. **响应插件有流式边界**：完整 body 的 `ResponseProcessor` 会强制缓冲；`ResponseChunkProcessor` 按流式 chunk 工作，两者不能在同一 profile 混用。全局 body post-processors 会令所有 profiles 需要缓冲，并与 profile chunk processors 冲突；loader 会拒绝该组合。全局 header post-processors 不强制完整 body 缓冲。
3. **仓库里有代码，不等于默认可用**：`cost-scorer` 未出现在该提交的默认注册列表，需额外注册；`model-config-datasource` 则已注册，尽管插件文档尚未更新。还要区分“已注册”“已配置”“对应事件已启用”。
4. **Guardrail、语义选模是扩展方向，不是默认保证**：迁移提案提到待贡献的 guardrail 示例，不等于默认发行版已包含完整安全审查或语义路由能力。
5. **没有自动性能提升承诺**：ext-proc 事件带来代理与 IPP 之间的额外交互；解析、插件处理、响应缓冲都可能增加延迟与资源使用。纯路由场景可关闭不需要的响应事件，但依赖响应事件维护 in-flight 的方案需保留相应事件并验证计数行为。
6. **按目标版本验证端到端行为**：固定镜像/chart、查看注册列表，验证候选数据与 LoRA 映射、路由 header、HTTPRoute、EPP 接入、流式响应及故障处理，再测试实际吞吐和延迟。本文不代表已完成 KAITO 集成或性能测试。

简言之：**早期 BBR 是“提取模型名以帮助路由”；当前 IPP 是“保留该能力的可插拔推理 payload 处理框架”。但插件化在 BBR 阶段已发展，独立迁移本身不是一次功能重写。**

## 参考资料

- [IPP 仓库][ipp-repo]
- [llm-d 0.7：IPP 迁移提案（含 Non-Goals）][migration]
- [GIE：1964 Pluggable BBR Framework 提案（固定提交）][bbr-proposal]
- [IPP Architecture（固定提交）][architecture]
- [IPP Plugins Reference（固定提交）][plugins]
- [IPP Configuration（固定提交）][configuration]
- [IPP Creating a Plugin（固定提交）][create-plugin]
- [IPP runner：默认插件注册（固定提交）][runner]
- [IPP model-config-datasource：模型、分组与价格配置实现（固定提交）][modelconfig]
- [IPP 配置 loader：插件接口分类、pre/post 装配及缓冲约束（固定提交）][loader]
- [IPP 请求 handler：全局 pre-processing 调用（固定提交）][request-handler]
- [IPP 响应 handler：全局 post-processing 调用（固定提交）][response-handler]

[ipp-repo]: https://github.com/llm-d/llm-d-inference-payload-processor
[migration]: https://llm-d.ai/docs/0.7/proposals/llm-d-inference-payload-processor
[ipp-commit]: https://github.com/llm-d/llm-d-inference-payload-processor/commit/373c6b25056a848be71792395ce4add108d9d682
[gie-commit]: https://github.com/kubernetes-sigs/gateway-api-inference-extension/commit/f6274684049e1fdda587d8adfe6d7f07032c083e
[bbr-proposal]: https://github.com/kubernetes-sigs/gateway-api-inference-extension/blob/f6274684049e1fdda587d8adfe6d7f07032c083e/docs/proposals/1964-pluggable-bbr-framework/README.md
[architecture]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/docs/architecture.md
[plugins]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/docs/plugins.md
[configuration]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/docs/configuration.md
[create-plugin]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/docs/create_new_plugin.md
[runner]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/cmd/runner/runner.go
[modelconfig]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/pkg/framework/plugins/datalayer/modelconfigcollector/plugin.go
[loader]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/pkg/config/loader/configloader.go
[request-handler]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/pkg/handlers/request.go
[response-handler]: https://github.com/llm-d/llm-d-inference-payload-processor/blob/373c6b25056a848be71792395ce4add108d9d682/pkg/handlers/response.go
