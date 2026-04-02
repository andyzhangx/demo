# llm-d Inference Scheduler: Scorer 组合对比

## 概述

llm-d inference scheduler 基于 GIE（Gateway API Inference Extension）的 EPP 插件体系，通过 Filter → Score → Pick 流水线调度推理请求。P/D 分离与不分离场景下，scorer 组合和配置有显著差异。

## 不分离（标准模式，无 P/D disaggregation）

只需一个 scheduling profile：

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPickerConfig
plugins:
- type: precise-prefix-cache-scorer    # 基于 KV cache 命中打分
  parameters:
    tokenProcessorConfig:
      blockSize: 64                     # 必须匹配 vLLM block size
      hashSeed: "42"                    # 必须匹配 PYTHONHASHSEED
    indexerConfig:
      kvBlockIndexConfig:
        enableMetrics: true
      tokenizersPoolConfig:
        modelName: "your-model"
- type: decode-filter                   # 过滤非 decode 节点（标准模式下可省略）
- type: max-score-picker                # 选最高分的 pod
- type: single-profile-handler          # 单 profile，不做 P/D 拆分
schedulingProfiles:
- name: default
  plugins:
  - pluginRef: decode-filter
  - pluginRef: max-score-picker
  - pluginRef: precise-prefix-cache-scorer
    weight: 50
```

**核心组合：**

| 组件 | 类型 | 作用 |
|------|------|------|
| `precise-prefix-cache-scorer` 或 `prefix-cache-scorer` | Scorer | 按 KV cache 前缀匹配度打分 |
| `decode-filter`（或无 filter） | Filter | 标准模式下可省略 |
| `max-score-picker` | Picker | 选得分最高的 pod |
| `single-profile-handler` | ProfileHandler | 所有请求走同一个 profile |

## P/D 分离模式

需要 **两个 scheduling profile**（prefill + decode），加上 decider 和 header handler：

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPickerConfig
featureGates:
- prepareDataPlugins
plugins:
- type: prefill-filter                  # 过滤出 prefill pods
- type: decode-filter                   # 过滤出 decode pods
- type: prefix-cache-scorer             # KV cache 打分
  parameters:
    autoTune: false
    blockSizeTokens: 5
    maxPrefixBlocksToMatch: 256
    lruCapacityPerServer: 31250
- type: max-score-picker
- type: disagg-headers-handler          # 设置 x-prefiller-host-port header
- type: prefix-based-pd-decider         # 决定是否需要 P/D 拆分
  parameters:
    nonCachedTokens: 8                  # 未缓存 token > 8 才触发 P/D
- type: disagg-profile-handler          # 替代 single-profile-handler
  parameters:
    deciders:
      prefill: prefix-based-pd-decider
schedulingProfiles:
- name: prefill
  plugins:
  - pluginRef: prefill-filter
  - pluginRef: max-score-picker
  - pluginRef: prefix-cache-scorer
- name: decode
  plugins:
  - pluginRef: decode-filter
  - pluginRef: max-score-picker
  - pluginRef: prefix-cache-scorer
```

## E/P/D 全分离模式（多模态）

三个 scheduling profile（encode + prefill + decode）：

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPickerConfig
featureGates:
- prepareDataPlugins
plugins:
- type: by-label
  name: "encode-pods"
  parameters:
    label: "role"
    validValues: ["encode"]
- type: by-label
  name: "prefill-pods"
  parameters:
    label: "role"
    validValues: ["prefill"]
- type: by-label
  name: "decode-pods"
  parameters:
    label: "role"
    validValues: ["decode"]
- type: prefix-cache-scorer
  parameters:
    autoTune: false
    blockSizeTokens: 5
    maxPrefixBlocksToMatch: 256
    lruCapacityPerServer: 31250
- type: max-score-picker
- type: disagg-headers-handler
- type: always-disagg-multimodal-decider
- type: prefix-based-pd-decider
  parameters:
    nonCachedTokens: 8
- type: disagg-profile-handler
  parameters:
    profiles:
      encode: encode
      prefill: prefill
      decode: decode
    deciders:
      encode: always-disagg-multimodal-decider
      prefill: prefix-based-pd-decider
schedulingProfiles:
- name: encode
  plugins:
  - pluginRef: "encode-pods"
- name: prefill
  plugins:
  - pluginRef: "prefill-pods"
  - pluginRef: "max-score-picker"
  - pluginRef: "prefix-cache-scorer"
- name: decode
  plugins:
  - pluginRef: "decode-pods"
  - pluginRef: "max-score-picker"
  - pluginRef: "prefix-cache-scorer"
```

## 关键差异总结

| | 不分离（标准） | P/D 分离 | E/P/D 全分离 |
|---|---|---|---|
| **ProfileHandler** | `single-profile-handler` | `disagg-profile-handler` | `disagg-profile-handler` |
| **Scheduling Profiles** | 1 个 (default) | 2 个 (prefill + decode) | 3 个 (encode + prefill + decode) |
| **Filters** | 可选 | **必须**（prefill-filter + decode-filter） | **必须**（by-label × 3） |
| **Scorer** | prefix-cache-scorer | 同上，两个 profile 各配一份 | 同上，prefill + decode 各配一份 |
| **Picker** | max-score-picker | 同上 | 同上 |
| **额外插件** | 无 | disagg-headers-handler + prefix-based-pd-decider | + always-disagg-multimodal-decider |
| **Feature Gate** | 无 | `prepareDataPlugins` | `prepareDataPlugins` |
| **Pod 标签** | 不需要 | `llm-d.ai/role: prefill/decode` | `llm-d.ai/role: encode/prefill/decode` |
| **Sidecar** | 不需要 | decode pod 需要 routing sidecar | decode pod 需要 routing sidecar |

## Scorer 选择

两种 prefix cache scorer 可选：

| Scorer | 特点 | 适用场景 |
|--------|------|----------|
| `prefix-cache-scorer` | 轻量级，基于调度历史估算 KV cache 命中 | 快速部署、低资源开销 |
| `precise-prefix-cache-scorer` | 精确版，通过 KV Events 实时追踪 vLLM 实例的 KV cache 状态 | 生产环境推荐，需配置 tokenizer、blockSize、hashSeed |

### `precise-prefix-cache-scorer` 关键配置

```yaml
- type: precise-prefix-cache-scorer
  parameters:
    tokenProcessorConfig:
      blockSize: 64         # 必须匹配 vLLM block size
      hashSeed: "42"        # 必须匹配 vLLM PYTHONHASHSEED
    indexerConfig:
      kvBlockIndexConfig:
        enableMetrics: true
      tokenizersPoolConfig:
        modelName: "hf-repo/model-name"
        hf:
          huggingFaceToken: "xxx"  # 或通过 HF_TOKEN 环境变量设置
```

## P/D 分离的智能决策

`prefix-based-pd-decider` 的逻辑：
- **跳过 prefill 分离**（在 decode pod 本地执行）：当 KV cache 命中率高 或 prompt 很短时
- **触发 prefill 分离**：当未缓存的 token 数 > `nonCachedTokens` 阈值时

这意味着 P/D 分离不是全量的——scheduler 会逐请求决定是否值得分离，兼顾延迟和吞吐。

## 自定义 Filter（集成外部系统）

如果外部系统使用不同的 Pod 标签（非 `llm-d.ai/role`），可以用 `by-label` filter 替代内置的 `prefill-filter`/`decode-filter`：

```yaml
- type: by-label
  name: "decode-pods"
  parameters:
    label: "inference-role"           # 自定义标签 key
    validValues: ["decode", "both"]   # 允许的标签值
    allowsNoLabel: false              # 没有该标签的 pod 是否保留
```

也支持 `by-label-selector` 进行多标签 AND 匹配：

```yaml
- type: by-label-selector
  parameters:
    matchLabels:
      inference-role: decode
      hardware-type: H100
```

## References

- [llm-d Architecture](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/architecture.md)
- [Disaggregation Doc](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/disaggregation.md)
- [Routing Sidecar](https://github.com/llm-d/llm-d-routing-sidecar) (已合并到 inference-scheduler repo)
- [Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/)
- [Create New Filter Guide](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/create_new_filter.md)
