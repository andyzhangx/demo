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
