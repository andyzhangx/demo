# llm-d-autoscaling 与 keda-kaito-scaler 对比

## 结论

**`llm-d-autoscaling` 提供基于 Prometheus + KEDA 的扩缩容配置蓝图和评测框架；`keda-kaito-scaler` 是直接采集指标、专门对接 KAITO 的 KEDA external scaler。** 两者都使用 KEDA，但并不是相同定位的两个 scaler 实现。

- 常规 KAITO 推理、不希望维护 Prometheus：优先评估 `keda-kaito-scaler`，前提是使用 KAITO `InferenceSet`。
- 已有 Prometheus，需要复杂指标、Prefill/Decode（PD）分离或系统化策略评测：参考 `llm-d-autoscaling` 的配置和 benchmark 框架。

本文基于以下源码快照，不将 `main` 的能力等同于所有已发布版本：

| 项目 | 审阅版本 |
| --- | --- |
| `llm-d/llm-d-autoscaling` | [`b3313cd5cdf7a4a526a6e682254387102cb4dbdc`](https://github.com/llm-d/llm-d-autoscaling/tree/b3313cd5cdf7a4a526a6e682254387102cb4dbdc) |
| `kaito-project/keda-kaito-scaler` | [`932ef75afa563e1160b425b10b761122122b21e1`](https://github.com/kaito-project/keda-kaito-scaler/tree/932ef75afa563e1160b425b10b761122122b21e1) |

## 1. 项目定位及架构

### llm-d-autoscaling

在上述快照中，原来的 **Workload-Variant-Autoscaler（WVA）自定义 controller 已弃用**：旧实现位于 `release-0.9`，`main` 中的 `legacy/` 是冻结且计划移除的代码，不能将旧 WVA 架构当作当前推荐路线。

现在的主线是：

```text
vLLM / llm-d EPP 暴露指标
          │ Prometheus 采集
          ▼
      Prometheus
          │ KEDA 内置 Prometheus scaler 执行 PromQL
          ▼
         KEDA
          ▼
         HPA
          ▼
模型服务 Deployment 的副本数
```

仓库主要提供：

1. **KEDA 配置蓝图**：结合 serving topology 配置 `ScaledObject`、阈值、min/max replicas 和 HPA behavior，包括独立的 prefill/decode 策略。
2. **评测平台**：部署场景、驱动负载并收集副本数、延迟、吞吐及 trigger 数值，用实验比较扩缩容策略。

### keda-kaito-scaler

它是实际部署运行的服务，提供 KEDA external scaler 接口，并可自动创建和维护 `ScaledObject`：

```text
模型 Pod / EPP 的 /metrics
          │ 后台直接采集
          ▼
   keda-kaito-scaler
   内存缓存、窗口聚合
          │ gRPC external scaler API
          ▼
         KEDA
          │ HPA（1↔N）及 KEDA 缩零/激活机制（0↔1）
          ▼
   KAITO InferenceSet
          ▼
KAITO controller 管理推理实例
```

这里的“直接采集”不代表每次 KEDA 请求都临时抓取 Pod。后台 poller 维护每个 scaler 副本的本地缓存，KEDA 查询从缓存返回。缓存尚未准备好或过期时返回指标不可用，避免将缺失指标误当成零负载。

## 2. 依赖区别：Prometheus 格式不等于 Prometheus Server

**llm-d 推荐蓝图依赖 Prometheus 指标查询能力；KAITO scaler 不需要 Prometheus Server。**

| 组件或能力 | llm-d 推荐方案 | keda-kaito-scaler |
| --- | --- | --- |
| KEDA | 需要 | 需要 |
| Prometheus Server／兼容查询服务 | 推荐蓝图需要 | 不需要 |
| 模型/EPP 暴露 Prometheus 格式指标 | 用于采集 | scaler 直接解析 |
| 自定义 external scaler 服务 | 当前推荐链路无需 WVA controller | 需要部署 `keda-kaito-scaler` |
| KAITO InferenceSet controller | llm-d Deployment 蓝图不依赖 | KAITO 推理扩缩容需要 |
| Grafana | 不是扩缩容必需组件 | 不是扩缩容必需组件 |
| 新建专用 `kube-prometheus-stack` | 不必，可复用既有服务 | 不需要 |

llm-d 的部署文档明确写着 **“Install Prometheus (required for autoscaler metrics)”**。推荐 PD 配置使用 `type: prometheus`，例如：

```promql
max(vllm:num_requests_waiting{model_name="...",role="prefill"})
max(vllm:kv_cache_usage_perc{model_name="...",role="prefill"})
```

可以复用现有 Prometheus 或兼容 PromQL 的托管服务，但必须处理指标采集、查询地址、网络连通性和鉴权。仅暴露 vLLM `/metrics`，不能原样满足这些 Prometheus trigger 的要求。

KAITO scaler 的“无 Prometheus 依赖”也不等于“零依赖”：仍需 KEDA、KAITO controller、相应 CRD 和可达的模型/EPP 指标端点。其启动流程等待 `InferenceSet`、`ScaledObject`、`ClusterTriggerAuthentication` CRD；部署文档还要求它与 KEDA 位于同一 namespace，以便正确解析认证 Secret。

## 3. 功能和策略对比

| 维度 | llm-d-autoscaling | keda-kaito-scaler |
| --- | --- | --- |
| 核心定位 | 策略蓝图、实验和 benchmark | external scaler、KAITO 自动集成 |
| 主要扩缩容对象 | 模型服务 Deployment | KAITO `InferenceSet`，不是直接扩缩已有单个 Workspace |
| 指标来源 | Prometheus 查询 | 模型 Pod 或 EPP 直接采集 |
| 策略配置 | PromQL、KEDA triggers、HPA behavior | InferenceSet annotations、自动生成的 ScaledObject；也可手工配置 |
| 多指标组合 | 普通多 trigger/HPA 通常选择较大的副本建议；可另配组合逻辑 | 自动配置目前只支持 AND |
| GPU 保护策略 | 由具体 blueprint 决定 | 强调保守决策、扩容前新实例 Ready 检查、策略周期内最多增减一个副本 |
| 指标历史 | 可使用持久化时序和 PromQL 时间窗口 | 本地滚动内存缓存，不是完整时序数据库 |
| PD 分离 | 有 prefill/decode 分别配置的推荐蓝图 | 自动配置跳过由 `MultiRoleInference` 控制的 InferenceSet |
| 策略评测 | 提供系统化负载、报告和对比框架 | 重点是 KAITO 集成，不是同等规模的 benchmark 平台 |

### AND 策略的含义

KAITO 自动配置支持一个或多个指标：

- 全部指标高于各自扩容阈值，且新实例已 Ready，才发出扩容信号。
- 全部指标低于各自缩容阈值，才发出缩容信号。
- 其他情况保持。
- 自动生成的策略限制增减步长；实际执行仍受 KEDA/HPA 的容差、稳定窗口、冷却及可用指标影响。

单指标也可使用。AND 策略有利于保守控制昂贵 GPU 资源，但可能比“任一指标超标就扩容”响应更慢，阈值仍需负载验证。这是默认集成策略取舍，不意味着 KEDA 或 Prometheus 不能实现相同策略。

### 聚合方式不等同于任意 PromQL

KAITO scaler 支持 gauge、histogram 及指定的聚合方式。histogram 默认使用滚动窗口中的平均观测值：

```text
ΔSum / ΔCount
```

**它不是 P95/P99。** 模型 Pod gauge 默认按实例进行平均；部分来源/配置可使用 sum 等方式，但不能因此认为能直接执行任意 PromQL。

若要使用 P95/P99 延迟、复杂跨指标计算或长时序规则，Prometheus 路线提供更直接的表达能力。KAITO 本地缓存更轻量，但不替代完整监控和长期历史分析。

## 4. Scale-to-zero（0↔1）

KAITO scaler 文档标明 **v0.7.0+ 支持缩零和唤醒**，但需要专门配置：

- `min-replicas: "0"`。
- 激活信号使用 `source: epp`，因为模型 Pod 缩到零后不能再提供唤醒指标。
- 配置匹配的 activation/deactivation 阈值和冷却时间。
- 保证 EPP 在模型实例为零时仍运行并暴露所需信号，同时验证请求入口、等待和超时行为。

因此，不能只将最小副本数改成 0，就认定完整请求唤醒链路已成立。

llm-d 的 KEDA 路线是否安全支持缩零、用什么信号唤醒，取决于具体配置和推理入口。使用 KEDA 本身不等于每个推荐场景都已验证端到端 scale-to-zero。

另外，**推理实例缩为零不等于 GPU VM 一定被删除或停止计费**；节点释放取决于 KAITO/基础设施供应与回收策略，需要独立验证。

## 5. KAITO 场景下如何选择

### 优先选 keda-kaito-scaler

适合：

- 已使用或准备使用 KAITO InferenceSet。
- 常规模型服务，以等待队列、平均排队延迟等直接指标为主要信号。
- 希望降低对 Prometheus 的运维依赖。
- 接受保守的 AND 策略和受控扩缩容步长。

需要先确认 InferenceSet controller、版本及 CRD 支持；不能简单认为给已有普通 Workspace 加上 annotation 就能扩缩容。

### 优先参考 llm-d 的蓝图及评测框架

适合：

- 已有 Prometheus，或需要复杂 PromQL 和历史指标。
- 使用 prefill/decode 分离，需按角色独立制定扩缩容策略。
- 希望在模拟环境和真实 GPU 上系统比较阈值、队列策略及成本/延迟表现。

这不等于把 llm-d 的 Deployment blueprint 原样应用到 KAITO MultiRoleInference 就能生效；资源模型、控制权和副本语义需要单独适配。尤其不能让两个 controller 同时争用同一资源的 replicas。

## 参考资料

以下链接固定到审阅 commit，方便核对实现和版本差异：

1. [llm-d README：WVA 弃用、KEDA 主线和仓库定位](https://github.com/llm-d/llm-d-autoscaling/blob/b3313cd5cdf7a4a526a6e682254387102cb4dbdc/README.md)
2. [llm-d benchmark：Prometheus/KEDA 部署前提](https://github.com/llm-d/llm-d-autoscaling/blob/b3313cd5cdf7a4a526a6e682254387102cb4dbdc/benchmark/README.md#L164-L181)
3. [llm-d PD 分离推荐配置](https://github.com/llm-d/llm-d-autoscaling/blob/b3313cd5cdf7a4a526a6e682254387102cb4dbdc/benchmark/config/scenarios/guides/pd-disaggregation.yaml)
4. [KAITO scaler README：配置、依赖、AND 策略及 scale-to-zero](https://github.com/kaito-project/keda-kaito-scaler/blob/932ef75afa563e1160b425b10b761122122b21e1/README.md)
5. [KAITO 模型 Pod 指标采集](https://github.com/kaito-project/keda-kaito-scaler/blob/932ef75afa563e1160b425b10b761122122b21e1/pkg/metricsource/modelpod_source.go)
6. [KAITO EPP 指标来源](https://github.com/kaito-project/keda-kaito-scaler/blob/932ef75afa563e1160b425b10b761122122b21e1/pkg/metricsource/epp_source.go)
7. [KAITO external scaler：缓存及指标不可用处理](https://github.com/kaito-project/keda-kaito-scaler/blob/932ef75afa563e1160b425b10b761122122b21e1/pkg/scaler/scaler.go)
