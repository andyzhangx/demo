# KAITO + llm-d Plugin Support TODO List

## Background

llm-d upstream already supports a fairly rich scheduling/plugin model across filters, scorers, pickers, profile handlers, and disaggregation deciders. KAITO currently integrates only a curated subset of these capabilities:

- **InferenceSet + GWIE default routing** focuses on:
  - `queue-scorer`
  - `kv-cache-utilization-scorer`
  - `prefix-cache-scorer`
- **MultiRoleInference (MRI) for P/D disaggregation** focuses on:
  - `disagg-profile-handler`
  - `prefix-based-pd-decider`
  - `by-label-selector` (`prefill-filter` / `decode-filter`)
  - `load-aware-scorer`
  - `kv-cache-utilization-scorer`
  - `max-score-picker`
  - plus helper plugins such as `approx-prefix-cache-producer` and `disagg-headers-handler`

This document tracks the gap between **llm-d upstream capability** and **KAITO first-class support**.

---

## Current State Summary

### Already wired in KAITO

#### InferenceSet / standard gateway routing
- `queue-scorer`
- `kv-cache-utilization-scorer`
- `prefix-cache-scorer`
- `metrics-data-source`
- `core-metrics-extractor`

#### MultiRoleInference / P/D routing
- `disagg-profile-handler`
- `prefix-based-pd-decider`
- `by-label-selector` as `prefill-filter` / `decode-filter`
- `load-aware-scorer`
- `kv-cache-utilization-scorer`
- `max-score-picker`
- `approx-prefix-cache-producer`
- `disagg-headers-handler`

### Not yet first-class in KAITO
- `precise-prefix-cache-producer`
- `precise-prefix-cache-scorer`
- `session-affinity-scorer`
- `session-affinity-filter`
- `lora-affinity-scorer`
- `latency-scorer`
- `slo-headroom-tier-filter`
- `weighted-random-picker`
- `random-picker`
- `token-load-scorer`
- `running-requests-size-scorer`
- `no-hit-lru-scorer`
- `active-request-scorer`
- `encode-filter`
- `always-disagg-pd-decider`
- `always-disagg-multimodal-decider`

### Important version note
KAITO currently pins the llm-d router chart / EPP image around the `v0.9.0` generation, so some newer upstream plugins or capabilities may exist in llm-d but are not automatically available in KAITO yet.

---

## Plugin Support Matrix

| Plugin / Capability | llm-d upstream | KAITO InferenceSet default | KAITO MRI default | Custom via `eppPluginsConfig` | Notes |
|---|---|---:|---:|---:|---|
| `queue-scorer` | ✅ | ✅ | ❌ | ✅ | Default standard gateway scorer in KAITO |
| `kv-cache-utilization-scorer` | ✅ | ✅ | ✅ | ✅ | Already productized in both standard routing and MRI |
| `prefix-cache-scorer` | ✅ | ✅ | ❌ | ✅ | Standard InferenceSet path uses this; MRI currently stays on approximate producer + decider path |
| `approx-prefix-cache-producer` | ✅ | chart/default path only | ✅ | ✅ | Low-overhead default for MRI |
| `precise-prefix-cache-producer` | ✅ | ❌ | ❌ | ⚠️ partial | Requires tokenizer sidecar + KV-cache indexer wiring |
| `precise-prefix-cache-scorer` | ✅ (deprecated compatibility wrapper) | ❌ | ❌ | ⚠️ partial | Prefer producer + `prefix-cache-scorer`; not first-class in KAITO |
| `load-aware-scorer` | ✅ | ❌ | ✅ | ✅ | Primary MRI load signal today |
| `active-request-scorer` | ✅ | ❌ | ❌ | ✅ | Available upstream; not exposed by KAITO |
| `token-load-scorer` | ✅ | ❌ | ❌ | ✅ | Candidate for future experiments |
| `running-requests-size-scorer` | ✅ | ❌ | ❌ | ✅ | Upstream scorer, not integrated in KAITO |
| `latency-scorer` | ✅ | ❌ | ❌ | ⚠️ maybe | Depends on latency predictor path / extra plumbing |
| `lora-affinity-scorer` | ✅ | ❌ | ❌ | ⚠️ maybe | Needs LoRA-aware product design in KAITO |
| `session-affinity-scorer` | ✅ | ❌ | ❌ | ⚠️ version-dependent | Useful for chat/session stickiness, but not first-class today |
| `no-hit-lru-scorer` | ✅ | ❌ | ❌ | ✅ | Good candidate for cold-request spreading evaluation |
| `prefix-cache-affinity-filter` | ✅ | ❌ | ❌ | ⚠️ maybe | Often paired with latency/SLO aware routing |
| `slo-headroom-tier-filter` | ✅ | ❌ | ❌ | ⚠️ maybe | Needs SLO/latency predictor integration |
| `by-label-selector` / `label-selector-filter` | ✅ | ❌ | ✅ | ✅ | Used by MRI as `prefill-filter` / `decode-filter` |
| `prefill-filter` | ✅ | ❌ | ✅ | ✅ | MRI role-specific filter via by-label-selector |
| `decode-filter` | ✅ | ❌ | ✅ | ✅ | MRI role-specific filter via by-label-selector |
| `encode-filter` | ✅ | ❌ | ❌ | ⚠️ maybe | Needed for future E/P/D work |
| `session-affinity-filter` | ✅ | ❌ | ❌ | ⚠️ version-dependent | Stronger session pinning than scorer-only approach |
| `max-score-picker` | ✅ | implicit/default | ✅ | ✅ | Current MRI default picker |
| `weighted-random-picker` | ✅ | chart/default option | ❌ | ✅ | Interesting future option to reduce hot-spotting |
| `random-picker` | ✅ | chart/default option | ❌ | ✅ | Available upstream, not useful as KAITO default |
| `single-profile-handler` | ✅ | implicit single-profile flow | ❌ | ✅ | Standard non-disaggregated scheduling path |
| `disagg-profile-handler` | ✅ | ❌ | ✅ | ✅ | Core of KAITO MRI P/D support |
| `prefix-based-pd-decider` | ✅ | ❌ | ✅ | ✅ | Current KAITO MRI decider |
| `always-disagg-pd-decider` | ✅ | ❌ | ❌ | ✅ | Mostly useful for benchmarking / experiments |
| `always-disagg-multimodal-decider` | ✅ | ❌ | ❌ | ⚠️ maybe | Future E/P/D or multimodal direction |
| `disagg-headers-handler` | ✅ | ❌ | ✅ | ✅ | Required helper for MRI routing headers |
| `metrics-data-source` | ✅ | ✅ | indirect | ✅ | Standard gateway path already uses it |
| `core-metrics-extractor` | ✅ | ✅ | indirect | ✅ | Standard gateway path already uses it |
| Tokenizer/render sidecar for precise routing | N/A dependency | ❌ | ❌ | ⚠️ manual future work | Required for `precise-prefix-cache-*` path; see `kaito-project/kaito#2144` |
| KV-cache indexer / ZMQ event subscription | N/A dependency | ❌ | ❌ | ⚠️ manual future work | Required to make precise prefix-cache routing truly work |

### Matrix legend
- **✅** = supported / present
- **❌** = not supported / not wired by default
- **⚠️** = theoretically possible, but missing productization, version uplift, or required dependencies

---

## High-Priority TODOs

### 1. Upgrade KAITO's llm-d-router-gateway / EPP pinned version
**Why**
- KAITO currently lags behind llm-d upstream plugin evolution.
- Newer llm-d releases already contain useful additions such as improved session affinity support and more disaggregation options.

**To do**
- Bump the pinned chart version and EPP image version.
- Revalidate compatibility of Helm values, CRDs, plugin config schema, and log/metric names.
- Add upgrade notes for breaking changes in plugin names or parameters.

**Acceptance criteria**
- KAITO can deploy a newer llm-d router chart successfully.
- Existing InferenceSet and MRI flows remain backward compatible.

---

### 2. Productize `precise-prefix-cache` routing in KAITO
**Why**
- Current KAITO MRI uses `approx-prefix-cache-producer`, which is lighter but heuristic.
- Precise prefix-cache routing is one of the most meaningful upgrades for higher cache-hit accuracy, especially under memory pressure and in P/D disaggregation.

**Important dependency: tokenizer sidecar is required**
This is the main caveat.

As described in **kaito-project/kaito#2144**, the precise path requires more than just swapping plugin names:

- `precise-prefix-cache-producer` depends on a **token-producer** path that sends prompts to a **vLLM render endpoint**
- that render endpoint is typically provided by a **tokenizer sidecar** / `vllm launch render` sidecar in the EPP pod
- it also depends on **KV-cache indexer** wiring and ZMQ event subscription to vLLM KV cache events

The approximate pipeline does **not** require that extra sidecar.

**Reference**
- PR: <https://github.com/kaito-project/kaito/pull/2144>

**To do**
- Add an optional tokenizer/render sidecar to the EPP deployment.
- Gate it behind a feature flag or MRI spec field.
- Wire `token-producer` + `precise-prefix-cache-producer` + `prefix-cache-scorer` with `prefixMatchInfoProducerName`.
- Configure the KV-cache indexer to subscribe to vLLM KV events.
- Add e2e coverage for accurate prefix-cache-aware routing.

**Open questions**
- Should tokenizer sidecar be global, per-InferencePool, or per-MRI?
- What is the acceptable default CPU/memory overhead for production clusters?
- Should precise mode be opt-in only?

**Acceptance criteria**
- KAITO can enable precise prefix-cache routing without manual Helm chart patching.
- Router correctly uses exact tokenization and real-time KV cache state.
- Docs clearly explain cost/benefit vs approximate mode.

---

### 3. Expose plugin configuration as a stable KAITO API surface
**Why**
- Today, many advanced llm-d capabilities are only reachable through raw `eppPluginsConfig` customization.
- That is flexible, but not yet a good productized UX.

**To do**
- Decide which plugins deserve first-class API fields vs raw pass-through config.
- Keep `eppPluginsConfig` for escape hatches, but add opinionated spec fields for common strategies.
- Define validation rules for incompatible combinations.

**Candidate first-class knobs**
- precise vs approximate prefix-cache routing
- session affinity mode
- picker strategy (`max-score` vs `weighted-random`)
- latency/SLO aware scheduling
- always-disagg behavior for testing / benchmarking

**Acceptance criteria**
- Common routing strategies can be enabled via CRD fields rather than hand-written EPP YAML.
- Advanced users can still override with custom config.

---

## Medium-Priority TODOs

### 4. Add first-class session affinity support
**Why**
- Upstream llm-d already supports `session-affinity-scorer`, and newer versions also support `session-affinity-filter`.
- This is useful for multi-turn chat, cache stickiness, and lowering repeated prefill cost.

**To do**
- Evaluate which session-affinity strategy should be exposed first.
- Add KAITO spec support for session header / session-id based routing.
- Document tradeoffs vs pure cache-aware routing.

**Acceptance criteria**
- Users can opt into session-aware routing without editing raw EPP config.

---

### 5. Add first-class latency/SLO-aware scheduling support
**Why**
- Upstream llm-d has `latency-scorer` and `slo-headroom-tier-filter`.
- This is important for production environments where routing must honor latency objectives, not just queue depth or cache affinity.

**To do**
- Evaluate whether KAITO should also expose latency predictor dependencies.
- Decide how SLO targets should be configured: per service, per model, or per request class.
- Add example configs and benchmark methodology.

**Acceptance criteria**
- KAITO can deploy an SLO-aware llm-d routing profile in a supported way.

---

### 6. Add support for richer picker strategies
**Why**
- KAITO MRI currently defaults to `max-score-picker`.
- Some workloads may benefit from `weighted-random-picker` to reduce hot-spotting.

**To do**
- Benchmark `max-score` vs `weighted-random` under bursty and heterogeneous workloads.
- Decide whether picker strategy belongs in CRD or stays in custom config.

**Acceptance criteria**
- Users can choose the picker policy without forking generated plugin YAML.

---

### 7. Evaluate `no-hit-lru-scorer` and cold-request spreading
**Why**
- For cold prompts, `no-hit-lru-scorer` can help distribute prefill-heavy misses more evenly.
- This may complement existing load-aware routing in large clusters.

**To do**
- Benchmark against current `load-aware-scorer + kv-cache-utilization-scorer` setup.
- Determine whether it is especially useful for prefill pools.

---

### 8. Evaluate `lora-affinity-scorer` support
**Why**
- If KAITO wants to support richer LoRA-heavy multi-tenant serving, affinity to already-loaded LoRA adapters becomes important.

**To do**
- Assess prerequisites in KAITO model/runtime management.
- Define API for LoRA-aware routing.
- Test with realistic multi-adapter workloads.

---

## Longer-Term TODOs

### 9. Extend MRI beyond P/D to E/P/D
**Why**
- llm-d upstream already has `always-disagg-multimodal-decider` and `encode-filter` related patterns.
- KAITO today is centered on P/D, not multimodal encode-prefill-decode orchestration.

**To do**
- Define whether KAITO should introduce an encode role into MRI.
- Extend role model, pod templates, routing sidecar assumptions, and docs.
- Validate gateway and scheduler interactions for multimodal requests.

**Acceptance criteria**
- KAITO can represent E/P/D topologies natively, not just P/D.

---

### 10. Support alternate decider strategies for benchmarking and experimentation
**Why**
- `always-disagg-pd-decider` is useful for testing and controlled experiments.
- It may also simplify debugging when trying to isolate routing effects.

**To do**
- Add an opt-in mode for always-disaggregate behavior.
- Ensure it is clearly marked as experimental / benchmarking-oriented.

---

## Suggested Implementation Order

### Phase 1
- Upgrade pinned llm-d router version
- Stabilize plugin compatibility matrix
- Keep current default behavior unchanged

### Phase 2
- Add tokenizer sidecar support
- Add KV-cache indexer wiring
- Enable precise prefix-cache as opt-in

### Phase 3
- Productize session affinity and picker selection
- Add latency/SLO-aware routing support

### Phase 4
- Expand MRI to E/P/D and multimodal scheduling
- Evaluate LoRA-aware routing and experimental deciders

---

## Notes from PR #2144

`kaito-project/kaito#2144` is the key reference for why KAITO currently stays on the approximate prefix-cache path:

1. **No tokenizer sidecar today** — precise mode needs a token-producer that calls a vLLM render endpoint.
2. **KV-cache indexer not configured yet** — even though KV cache events may already be enabled on vLLM pods, the EPP/indexer side still needs full subscription and indexing wiring.
3. **`kv-cache-utilization-scorer` was chosen as the low-cost next step** — it reuses existing `/metrics` scraping and adds no tokenizer sidecar overhead.
4. **Approximate routing is already good enough for an initial production path** — especially before the additional complexity of precise mode is justified.

This means the KAITO roadmap should treat **precise prefix-cache routing as a deliberate feature project**, not as a small config tweak.

---

## Practical Recommendation

Near term, KAITO should continue to:
- keep `kv-cache-utilization-scorer` in the default path
- keep approximate prefix awareness as the default low-overhead option
- make precise prefix-cache routing opt-in first

The next meaningful product step is:

> **Add tokenizer sidecar + KV-cache indexer plumbing, then productize `precise-prefix-cache-producer` as an opt-in routing mode.**
