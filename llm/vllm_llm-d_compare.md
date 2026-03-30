现在我对两个系统都有了全面了解。下面是详细对比：

---

## vllm-router `kv_aware` vs llm-d `precise-prefix-cache-scorer` 对比

### 1. 架构层面

| 维度 | vllm-router `kv_aware` (PR #130) | llm-d `precise-prefix-cache-scorer` |
|------|------|------|
| **语言** | Rust | Go |
| **部署形态** | 独立进程（vllm-router 二进制） | Envoy ext-proc sidecar（EPP），基于 K8s Gateway API Inference Extension (GIE) |
| **数据面** | vllm-router 自身做 HTTP 反向代理 | Envoy 做数据面，EPP 只做调度决策 |
| **与 K8s 集成** | 弱 — 通过 vLLM 服务发现或静态配置获取 worker 列表 | 强 — 原生使用 InferencePool CRD、Pod label、K8s RBAC |
| **配置方式** | CLI 参数 | YAML 插件配置（EndpointPickerConfig） |

### 2. 调度架构

| 维度 | vllm-router | llm-d |
|------|------|------|
| **调度模型** | 单一 Policy — `kv_aware` 一个策略完成所有决策（评分 + 选择 + P/D bypass） | **插件化 Filter → Scorer → Picker 管线** — 多个 scorer 可以加权组合 |
| **可组合性** | ❌ 不支持多个 scorer 加权组合 | ✅ 支持，如 `precise-prefix-cache-scorer` (weight: 2) + `load-aware-scorer` (weight: 1) + `no-hit-lru-scorer` (weight: 1) |
| **Filter 机制** | 无独立 filter 层，只有 prefill/decode 的静态 worker 列表 | 丰富 — `decode-filter`、`prefill-filter`、`by-label-selector`、`context-length-aware` 等 |
| **Scheduling Profile** | 单一 policy 或 prefill-policy + decode-policy | 多 profile 系统 — 每个 profile 可以有不同的 filter + scorer 组合 |

**简言之：llm-d 是插件化的调度框架，kv_aware 是单体策略。**

### 3. KV Events 处理

| 维度 | vllm-router | llm-d |
|------|------|------|
| **ZMQ 订阅** | 自建 `KVEventPool` — 每个 worker 一个 ZMQ SUB 线程 | `kvevents.Pool` — 支持多并发 worker（`concurrency` 可配） |
| **Worker 发现** | 从 vLLM 服务发现 HTTP 地址推导 ZMQ 端口 | ✅ **K8s Pod 自动发现** — Pod reconciler 监听 Pod 生命周期，自动添加/移除订阅 |
| **Msgpack 解码** | 用 `rmpv` crate 手写解码逻辑 | 用 Go msgspec 适配器解码 |
| **引擎支持** | 仅 vLLM | vLLM + **SGLang**（`engineType: "sglang"`） |

**关键差异：llm-d 有 K8s Pod reconciler 自动管理 ZMQ 订阅生命周期，vllm-router 需要从服务发现手动推导。**

### 4. KV Block Index

| 维度 | vllm-router | llm-d |
|------|------|------|
| **存储后端** | 仅 `DashMap`（进程内内存） | **多后端** — InMemory / CostAwareMemory (Ristretto) / **Redis** / **Valkey**（支持 RDMA） |
| **多副本 HA** | ❌ 不支持 — 每个 router 实例维护独立 index | ✅ 支持 — Redis/Valkey 后端 + `discoverPods: true` 实现 active-active 多副本 |
| **容量管理** | `max_entries` 仅为 advisory，不做硬淘汰 | InMemory 有 size 上限 + podCacheSize，CostAwareMemory 有内存上限（如 `"2GiB"`） |
| **多设备感知** | ❌ 无 | ✅ `kvCacheBackendConfigs` 支持 GPU/CPU 不同权重（如 GPU=1.0, CPU=0.8） |
| **Metrics** | ❌ 无 | ✅ `enableMetrics` — admissions/evictions/hits/misses + 可配日志间隔 |

**关键差异：llm-d 支持分布式 index（Redis/Valkey），适合多副本部署；vllm-router 只有进程内 DashMap。**

### 5. Tokenization

| 维度 | vllm-router | llm-d |
|------|------|------|
| **Tokenizer** | HuggingFace tokenizers（Rust 原生绑定） | HuggingFace tokenizers（Go 绑定）+ **本地文件自动发现** |
| **Worker 池** | 未提及并行 tokenization | `workersCount` 可配多个 goroutine 并行 |
| **离线支持** | 需要下载 tokenizer | ✅ `local.autoDiscoveryDir` 支持离线/air-gapped 环境 |

### 6. Prefix Scoring

| 维度 | vllm-router | llm-d |
|------|------|------|
| **算法** | 最长连续前缀匹配（contiguous prefix match） | 最长连续前缀匹配 + **prefixStore** 缓存 |
| **Prefix Cache** | ❌ 无 prefix store | ✅ `prefixStoreConfig` — 缓存 tokenization + block key 结果，避免重复计算 |
| **Block hash 兼容性** | ⚠️ 用 Rust `DefaultHasher`（SipHash），注释承认与 Python `hash()` 不完全兼容，依赖 vLLM 事件中的 hash | ✅ Go 侧实现兼容 Python hash |

### 7. P/D Disaggregation

| 维度 | vllm-router | llm-d |
|------|------|------|
| **P/D bypass** | ✅ `--pd-uncached-token-threshold` | ✅ `prefix-based-pd-decider` + `nonCachedTokens` |
| **E/P/D 三阶段** | ❌ 不支持 | ✅ 实验性支持 Encode/Prefill/Decode |
| **Decider 插件** | 内置在 kv_aware policy 中 | 独立 decider 插件，可替换 |

### 8. Speculative Indexing

| 维度 | vllm-router | llm-d |
|------|------|------|
| **支持** | ✅ 默认开启 | ✅ 默认关闭，需显式开启 |
| **TTL** | `--kv-speculative-ttl-ms` (默认 2000ms) | `speculativeTTL` (默认 "2s") |
| **实现** | 直接写入 DashMap，带 `is_speculative` 标记 | 类似，带 TTL 的临时条目 |

### 9. 额外能力（llm-d 有而 vllm-router 没有）

| 能力 | 说明 |
|------|------|
| **`load-aware-scorer`** | 基于 Pod 负载的评分，可与 KV 评分加权组合 |
| **`session-affinity-scorer`** | 会话亲和性 |
| **`no-hit-lru-scorer`** | 冷请求 LRU 分散，避免缓存堆积在少数 Pod |
| **`context-length-aware`** | 按 context length 路由到不同硬件配置的 Pod |
| **`by-label-selector` / `by-label`** | K8s label 级别的 Pod 过滤 |
| **多模型支持** | 多个 InferencePool 支持不同模型 |
| **Lifecycle hooks** | Pre-call / Scoring / Post-choice / After-response 完整生命周期 |

---

## 总结

```
                    vllm-router kv_aware          llm-d precise-prefix-cache-scorer
                    ─────────────────────         ──────────────────────────────────
定位                轻量级独立 router               K8s 原生推理调度框架
架构                单体 policy                    插件化 filter + scorer + picker
KV Index 后端       DashMap（进程内）               InMemory / Redis / Valkey
多副本 HA           ❌                             ✅ (Redis/Valkey)
Pod 自动发现        ❌ (需服务发现推导)             ✅ (K8s Pod reconciler)
Scorer 组合         ❌ 单一                        ✅ 多 scorer 加权
E/P/D 三阶段        ❌                             ✅ (实验性)
多引擎              仅 vLLM                        vLLM + SGLang
多设备权重          ❌                             ✅ (GPU/CPU 不同权重)
复杂度              低 — 适合快速集成               高 — 适合生产级 K8s 部署
```

**一句话总结：** vllm-router 的 `kv_aware` 是 llm-d `precise-prefix-cache-scorer` 的 **Rust 轻量化简化版**——核心算法（KV events → block index → prefix scoring → P/D bypass → speculative indexing）基本相同，但缺少 llm-d 的插件化框架、分布式 index、K8s 原生集成、多 scorer 组合等生产级能力。
