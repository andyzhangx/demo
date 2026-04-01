# llm-d Scorers vs vLLM Router Policies Comparison

Both projects solve the same problem (LLM inference request routing), but at completely different architectural levels.

## Architecture Differences

| | **vLLM Router** | **llm-d Inference Scheduler** |
|---|---|---|
| **Positioning** | Standalone lightweight HTTP router | Kubernetes-native, built on Gateway API + Envoy EPP |
| **Architecture** | Single policy selection | Filter → Score → Pick pipeline, composable plugins |
| **Extensibility** | 5 fixed policies, not composable | Plugin-based, scorers can be weighted and stacked |
| **Deployment** | Process-level, CLI startup | K8s CRD (EndpointPickerConfig), integrated with Envoy |

## Feature Mapping

| vLLM Router Policy | llm-d Counterpart | Difference |
|---|---|---|
| **`round_robin`** | No direct equivalent (max-score-picker selects randomly on tied scores) | llm-d has no pure round-robin, assumes there's always a better signal |
| **`random`** | No direct equivalent | Same as above |
| **`consistent_hash`** | **`session-affinity-scorer`** | vLLM uses a consistent hash ring (160 virtual nodes); llm-d uses a scorer with weighted mixing alongside other scorers |
| **`power_of_two`** | **`load-aware-scorer`** + **`active-request-scorer`** | vLLM implements classic "power of two choices"; llm-d splits into two fine-grained scorers — load-aware checks queue depth, active-request tracks per-request TTL |
| **`cache_aware`** | **`precise-prefix-cache-scorer`** | This is where the biggest difference lies 👇 |

## Prefix Cache Routing: Core Differences

| | vLLM Router `cache_aware` | llm-d `precise-prefix-cache-scorer` |
|---|---|---|
| **Cache state source** | Router's own **approximate radix tree** (inferred from routing history) | Subscribes to **real-time KV Cache state** from vLLM engines via **KV Events** (ZMQ) |
| **Accuracy** | Approximate — unaware of actual evictions | Precise — tracks real block existence |
| **Load balancing** | Built-in (abs/rel threshold switches to shortest queue) | Achieved through weighted combination with `load-aware-scorer` |
| **Cold request handling** | Routes to worker with smallest tree | **`no-hit-lru-scorer`** — LRU ordering to evenly distribute new cache growth |
| **Tokenizer** | Not required (matches by character/byte prefix) | Required — uses HuggingFace tokenizer for true token-level block matching |
| **Configuration complexity** | 3 parameters | Requires blockSize, hashSeed (must match vLLM), tokenizer, KV Events config, etc. |

## llm-d Exclusive Capabilities

llm-d has several capabilities that vLLM Router lacks entirely:

1. **Disaggregated P/D/E scheduling** — prefill and decode use different scheduling profiles, supporting Encode/Prefill/Decode three-stage separation
2. **Label-based filters** (`by-label`, `by-label-selector`, `decode-filter`, `prefill-filter`) — filter pods by K8s label roles
3. **`no-hit-lru-scorer`** — specifically optimizes cold request distribution, preventing all new cache from concentrating on a few pods
4. **Context-length scorer** — routes requests to different hardware specs based on token count
5. **Multi-scorer weighted composition** — can simultaneously use prefix-cache(weight=2) + no-hit-lru(weight=1) + load-aware(weight=1)

## Summary

- **vLLM Router** = Simple and practical, 5 mutually exclusive policies, works out of the box, suitable for single-strategy scenarios
- **llm-d** = Kubernetes-native composable scheduling framework, multi-scorer weighted stacking + real-time KV Cache state tracking, suitable for production-grade heterogeneous clusters and P/D disaggregated deployments

## References

- [vllm-router load balancing docs](https://github.com/vllm-project/router/tree/main/docs/load_balancing)
- [llm-d inference scheduler architecture](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/architecture.md)
