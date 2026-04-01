# llm-d Scorers vs vLLM Router Policies 对比

两个项目解决同一个问题（LLM 推理请求路由），但架构层次完全不同。

## 架构差异

| | **vLLM Router** | **llm-d Inference Scheduler** |
|---|---|---|
| **定位** | 独立的轻量 HTTP 路由器 | Kubernetes-native，基于 Gateway API + Envoy EPP |
| **架构** | 单一 policy 选择 | Filter → Score → Pick 流水线，多插件可组合 |
| **扩展性** | 5 个固定 policy，不可组合 | 插件化，scorer 可加权叠加 |
| **部署** | 进程级，CLI 启动 | K8s CRD（EndpointPickerConfig），与 Envoy 集成 |

## 功能映射

| vLLM Router Policy | llm-d 对应组件 | 差异 |
|---|---|---|
| **`round_robin`** | 无直接对应（默认 max-score-picker 在等分时随机选） | llm-d 没有纯 round-robin，认为总有更好的信号 |
| **`random`** | 无直接对应 | 同上 |
| **`consistent_hash`** | **`session-affinity-scorer`** | vLLM 用一致性哈希环（160 虚拟节点），llm-d 用 scorer 打分，可与其他 scorer 加权混合 |
| **`power_of_two`** | **`load-aware-scorer`** + **`active-request-scorer`** | vLLM 是经典 "power of two choices"；llm-d 拆成两个细粒度 scorer — load-aware 看队列深度，active-request 追踪每个请求的 TTL |
| **`cache_aware`** | **`precise-prefix-cache-scorer`** | 这是差异最大的地方 👇 |

## 前缀缓存路由：核心区别

| | vLLM Router `cache_aware` | llm-d `precise-prefix-cache-scorer` |
|---|---|---|
| **缓存状态来源** | 路由器自己维护的 **近似 radix tree**（基于路由历史推测） | 通过 **KV Events**（ZMQ）订阅 vLLM 引擎的 **实时 KV Cache 状态** |
| **准确性** | 近似 — 不知道实际是否被 evict | 精确 — 追踪真实的 block 存在 |
| **负载均衡** | 内建（abs/rel threshold 切换到 shortest queue） | 通过 `load-aware-scorer` 加权组合实现 |
| **冷请求处理** | 路由到 tree 最小的 worker | **`no-hit-lru-scorer`** — LRU 排序，均匀分散新缓存增长 |
| **tokenizer** | 不需要（按字符/字节前缀匹配） | 需要 — 用 HuggingFace tokenizer 做真正的 token-level block 匹配 |
| **配置复杂度** | 3 个参数 | 需配置 blockSize、hashSeed（必须与 vLLM 一致）、tokenizer、KV Events 等 |

## llm-d 独有能力

llm-d 有几个 vLLM Router 完全没有的能力：

1. **Disaggregated P/D/E 调度** — prefill 和 decode 用不同的 scheduling profile，支持 Encode/Prefill/Decode 三阶段分离
2. **Label-based filter**（`by-label`、`by-label-selector`、`decode-filter`、`prefill-filter`）— 按 K8s label 过滤 Pod 角色
3. **`no-hit-lru-scorer`** — 专门优化冷请求的分布，避免所有新缓存集中在少数 Pod
4. **Context-length scorer** — 按请求 token 长度路由到不同硬件规格的 Pod
5. **多 scorer 加权组合** — 可以同时用 prefix-cache(weight=2) + no-hit-lru(weight=1) + load-aware(weight=1)

## 一句话总结

- **vLLM Router** = 简单实用，5 个互斥 policy，开箱即用，适合单一策略场景
- **llm-d** = Kubernetes-native 的可组合调度框架，多 scorer 加权叠加 + 真实 KV Cache 状态追踪，适合生产级异构集群和 P/D 分离部署

## 参考

- [vllm-router load balancing docs](https://github.com/vllm-project/router/tree/main/docs/load_balancing)
- [llm-d inference scheduler architecture](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/architecture.md)
