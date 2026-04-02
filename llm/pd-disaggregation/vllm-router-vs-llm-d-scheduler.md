# vLLM Router vs llm-d Inference Scheduler: A Comparison

## Overview

Both components solve the same core problem — **routing inference requests to the right vLLM backend** — but take fundamentally different architectural approaches.

| | vLLM Router | llm-d Inference Scheduler |
|---|---|---|
| **Project** | [vllm-project/production-stack](https://github.com/vllm-project/production-stack) | [llm-d/llm-d-inference-scheduler](https://github.com/llm-d/llm-d-inference-scheduler) |
| **Language** | Python | Go |
| **Architecture** | Standalone reverse proxy | K8s Gateway API EPP (ext-proc callback) |
| **K8s Integration** | Helm chart, runs as a Deployment | Native Gateway API Inference Extension (GIE) |
| **Gateway Dependency** | None (self-contained HTTP proxy) | Requires Envoy-based Gateway API impl (e.g., kgateway) with ext-proc support |
| **CRD Usage** | None | `InferencePool`, `InferenceModel` (GIE CRDs) |
| **Plugin System** | Fixed routing algorithms | Extensible Filter → Scorer → Picker pipeline |
| **P/D Disaggregation** | Not supported | First-class support via routing sidecar + `disagg-profile-handler` |
| **Maturity** | Production-ready, simpler setup | More advanced features, heavier infrastructure |

## Architecture

### vLLM Router

```
Client → vLLM Router (Python) → vLLM Instance A
                               → vLLM Instance B
                               → vLLM Instance C
```

The router is a **standalone Python HTTP proxy** that sits between the client and vLLM instances. It discovers backends via the Kubernetes API and forwards requests based on its routing algorithm.

- **Self-contained**: no external gateway dependency
- **Service discovery**: watches K8s pods directly
- **Metrics**: exports QPS, TTFT, pending/running requests per instance
- **Observability**: integrates with Prometheus + Grafana via the production-stack Helm chart

### llm-d Inference Scheduler

```
Client → Envoy Gateway (ext-proc) ←→ EPP (Go) → picks backend
              ↓
         vLLM Instance A / B / C
```

The EPP (Endpoint Picker Plugin) runs as a **sidecar/service alongside an Envoy-based Gateway**. It doesn't proxy traffic itself — instead, Envoy calls the EPP via the [ext-proc](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_proc_filter) filter to decide which backend to route to. Envoy then routes the actual request.

- **Gateway API native**: uses `InferencePool` and `InferenceModel` CRDs
- **ext-proc callback**: EPP makes routing decisions, Envoy handles traffic
- **UDS Tokenizer**: separate sidecar for tokenization (no Python in EPP)
- **Extensible pipeline**: Filter → Scorer → Picker plugins, configurable via YAML

## Routing Algorithms

### vLLM Router

| Algorithm | Description |
|---|---|
| **Round-robin** | Simple rotation across healthy instances |
| **Session-ID** | Sticky routing — same session always hits the same instance |
| **Prefix-aware** | Routes based on prompt prefix to maximize KV cache reuse (WIP) |

Configuration is via Helm `values.yaml` — pick one algorithm, apply globally.

### llm-d Inference Scheduler

The EPP uses a **plugin pipeline** that runs for every request:

```
Request → Filters (eliminate) → Scorers (rank) → Picker (select)
```

**Filters** (eliminate unfit backends):

| Filter | Description |
|---|---|
| `health-check-filter` | Remove unhealthy pods |
| `least-queue-filter` | Remove overloaded pods (queue > threshold) |
| `least-kv-cache-filter` | Remove pods with insufficient KV cache headroom |
| `loaded-lora-filter` | Only keep pods with the required LoRA adapter loaded |
| `prefix-aware-filter` | Only keep pods likely to have prefix cache hits |

**Scorers** (rank remaining backends):

| Scorer | Description |
|---|---|
| `queue-score-scorer` | Prefer lower queue depth |
| `kv-cache-score-scorer` | Prefer more available KV cache |
| `prefix-cache-scorer` | Prefer higher prefix cache hit rate (lightweight, hash-based) |
| `precise-prefix-cache-scorer` | Prefer higher prefix cache hit rate (token-level, needs tokenizer) |
| `session-affinity-scorer` | Prefer the same pod for the same session |
| `load-aware-scorer` | Composite load signal |

**Pickers:**

| Picker | Description |
|---|---|
| `max-score-picker` | Pick the highest-scoring backend |
| `random-weighted-picker` | Weighted random based on scores |

**Profile Handlers** (mode selection):

| Handler | Description |
|---|---|
| `single-profile-handler` | Standard mode — all pods are equal |
| `disagg-profile-handler` | P/D mode — routes to prefill or decode pools based on `prefix-based-pd-decider` |

All configured via a single YAML:

```yaml
filters:
  - name: health-check-filter
  - name: least-queue-filter
    args:
      queueThreshold: 200
scorers:
  - name: queue-score-scorer
    weight: 80
  - name: prefix-cache-scorer
    weight: 20
picker:
  name: max-score-picker
profileHandler:
  name: single-profile-handler
```

## P/D Disaggregation Support

### vLLM Router
**Not supported.** The router treats all vLLM instances as equivalent and has no concept of prefill vs decode roles.

### llm-d Inference Scheduler
**First-class support.** The `disagg-profile-handler` separates pods into prefill and decode pools. Combined with:

- **`prefix-based-pd-decider`**: decides per-request whether to disaggregate based on prefix cache hit rate
- **[llm-d-routing-sidecar](https://github.com/llm-d/llm-d-routing-sidecar)**: deployed alongside decode pods, handles request forwarding to prefill workers and KV cache transfer via NIXL/LMCache

## Installation Complexity

### vLLM Router (Production Stack)

```bash
helm repo add vllm https://vllm-project.github.io/production-stack
helm install vllm vllm/vllm-stack -f values.yaml
```

That's it. The Helm chart bundles router + vLLM + Prometheus + Grafana. No CRDs, no external gateway, no extra operators.

### llm-d Inference Scheduler

Requires:
1. Gateway API CRDs (`kubectl apply -f ...`)
2. GIE CRDs (`kubectl apply -f ...`)
3. kgateway Helm install (Envoy-based gateway with ext-proc)
4. EPP Deployment + UDS Tokenizer sidecar
5. `InferencePool` + `InferenceModel` CR definitions
6. (Optional) P/D sidecar for disaggregated mode

For local dev: `make env-dev-kind` handles everything in one command.

## When to Use Which

### Choose vLLM Router when:
- You want a **simple, self-contained** routing solution
- You don't need P/D disaggregation
- You prefer a **Python-native** stack that's easy to customize
- You want minimal K8s infrastructure overhead
- Prefix-aware + session-sticky routing is sufficient

### Choose llm-d Inference Scheduler when:
- You need **P/D disaggregation** (prefill/decode separation)
- You want **K8s Gateway API** native integration
- You need **fine-grained, pluggable routing logic** (custom filters/scorers)
- You're running at scale and want **Envoy-grade traffic handling**
- You need **LoRA-aware routing** or advanced KV cache-aware scheduling
- You want to align with the emerging **Gateway API Inference Extension** standard

### Use both concepts together:
The vLLM Semantic Router (proposed, not yet implemented) could sit in front of either solution, adding request classification and parameter injection before routing decisions are made.

## Summary

The **vLLM Router** is the pragmatic choice — simple, works out of the box, good enough for most deployments. The **llm-d Inference Scheduler** is the advanced choice — more powerful, more extensible, but requires heavier infrastructure. If you're doing P/D disaggregation or need fine-grained scheduling control, llm-d is the way to go. If you just need to load-balance across vLLM instances with KV cache affinity, the vLLM Router gets you there faster.
