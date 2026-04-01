# vLLM Router Load Balancing: `consistent_hash` vs `cache_aware`

两者都是为了提高 KV Cache 命中率，但机制完全不同。

## `consistent_hash` — 基于身份的固定映射

**原理：** 对 session/user ID 做一致性哈希，**同一个用户/会话永远路由到同一个 worker**。

- 不看请求内容，只看"你是谁"（通过 `X-Session-ID`、`X-User-ID` 等 header 或 body 字段）
- 160 个虚拟节点保证分布均匀
- **不感知负载**，目标 worker 挂了才 fallback

**适用场景：** 多轮对话 — 用户第 1 轮的 KV Cache 在 worker A 上，第 2、3 轮自然也路由到 A，复用整段对话历史。

## `cache_aware` — 基于内容的前缀匹配

**原理：** 维护一个 **per-worker 的 radix tree**，记录每个 worker 缓存了哪些 prompt 前缀。路由时：

1. **负载均衡时**（worker 负载相当）：找前缀匹配率最高的 worker
   - 匹配率 > `cache_threshold`（默认 0.5）→ 路由过去（cache hit）
   - 匹配率太低 → 路由到 tree 最小的 worker（最有空间缓存新前缀）
2. **负载不均时**（超过 `balance_abs_threshold` 或 `balance_rel_threshold`）→ 直接路由到最空闲的 worker

**适用场景：** 大量请求共享相同 system prompt / few-shot examples，但来自不同用户。

## 核心区别

| | `consistent_hash` | `cache_aware` |
|---|---|---|
| **路由依据** | 用户/会话 ID（身份） | 请求 prompt 内容（前缀） |
| **感知负载** | ❌ 不感知 | ✅ 有负载均衡兜底 |
| **缓存命中逻辑** | 隐式 — 同用户去同节点，自然命中 | 显式 — 维护 radix tree 追踪前缀 |
| **最佳场景** | 多轮对话（同一用户连续请求） | 共享前缀（不同用户，相同 system prompt） |
| **开销** | 低（只算哈希） | 较高（维护 radix tree，定期 eviction） |

## 一句话总结

- **consistent_hash**：同一个人 → 同一台机器（靠身份绑定）
- **cache_aware**：相似的 prompt → 同一台机器（靠内容匹配）

如果是多租户场景，每个租户有自己的 system prompt，`cache_aware` 会自动把同租户的请求聚到同一 worker，而不需要客户端传 session ID。

## 参考

- [vllm-router load balancing docs](https://github.com/vllm-project/router/tree/main/docs/load_balancing)

---

## `power_of_two` — Power of Two Choices 算法

**Power of Two Choices** 是一个经典的负载均衡算法，源自论文 *"The Power of Two Choices in Randomized Load Balancing"* (1996, Mitzenmacher)。

### 原理

每次路由时：
1. **随机挑 2 个** healthy worker
2. 查询这两个的当前负载（pending requests）
3. **选负载低的那个**

### 为什么不直接选全局最空闲的？

| 策略 | 问题 |
|---|---|
| Round Robin | 完全不看负载，请求处理时间不均时会堆积 |
| 最短队列（全局） | 需要实时查所有 worker 状态，高并发下有 **thundering herd** 问题 — 大量请求同时涌向同一个"最空闲"节点 |
| **Power of Two** | 只查 2 个，开销极低，但数学上已经能 **指数级降低最大负载** |

### 数学直觉

- 纯随机：最繁忙 worker 的负载是 O(log n / log log n)
- 随机选 2 个取较优：最繁忙 worker 的负载降到 O(log log n)

仅仅多看一个选择，效果就从 log n 级别降到了 log log n 级别 — 这就是 "two choices" 的威力。选 3 个、4 个的边际收益则很小。

### 适用场景

- 请求处理时间差异大（比如短 prompt 和长 prompt 混合）
- 想要负载感知但不想维护全局状态
- Worker 数量较多时效果尤其好
