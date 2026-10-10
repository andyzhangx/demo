# KAITO Role-Aware Autoscaling for Prefill/Decode Disaggregation

## Goal

This document captures a concrete KAITO implementation plan for **role-aware autoscaling** in prefill/decode (P/D) disaggregated serving.

The target is not just to say that prefill and decode should scale independently, but to define **where the API lives, which controller owns it, which metrics should drive it, and how KV-related signals should be used**.

## Executive Summary

For P/D disaggregation in KAITO, the right scaling boundary is **per role**, not one global autoscaling knob for the whole service.

The recommended design is:

1. `MultiRoleInference` remains the top-level user API.
2. The MRI controller creates one child `InferenceSet` for `prefill` and one for `decode`.
3. The MRI controller also creates one role-specific `ScaledObject` per child `InferenceSet`.
4. `prefill` and `decode` use **different metrics and thresholds**.
5. **KV events should primarily drive routing/scoring**, not raw autoscaling decisions.
6. If KV information is used for autoscaling, it should first be aggregated into a **stable pressure metric** or **desired replicas signal**, then consumed by KEDA.

## Why Per-Role Autoscaling Is Needed

P/D disaggregation only pays off if prefill and decode can evolve capacity independently.

- **Prefill** is compute-heavy and TTFT-sensitive.
- **Decode** is memory/KV/cache-pressure-heavy and throughput-sensitive.

Those are different bottlenecks, so they should not share one autoscaling signal.

A practical way to say it:

- scale **prefill** to protect prompt admission latency
- scale **decode** to protect steady-state generation throughput and KV headroom

## What KAITO Already Has Today

Current KAITO building blocks already line up well with this design:

- `InferenceSet` is the autoscaling/scaled-replica boundary.
- `MultiRoleInference` creates child `InferenceSet`s for `prefill` and `decode`.
- The MRI controller labels child `InferenceSet`s and pod templates with role labels such as:
  - `kaito.sh/inference-role: prefill`
  - `kaito.sh/inference-role: decode`
- KEDA integration already exists for `InferenceSet` via `keda-kaito-scaler`.

This means KAITO already has the right **reconciliation boundary** for independent scaling: each role-specific child `InferenceSet`.

## Important Current Limitation

KAITO's current KEDA auto-provision flow is **InferenceSet-centric**, not MRI-centric.

Today, `keda-kaito-scaler`'s auto-provision controller watches top-level `InferenceSet.metadata.annotations`, for example:

- `scaledobject.kaito.sh/auto-provision`
- `scaledobject.kaito.sh/max-replicas`
- `scaledobject.kaito.sh/threshold`

However, the current MRI controller propagates MRI annotations into **child `InferenceSet.spec.template.annotations`**, not into child `InferenceSet.metadata.annotations`.

That means the existing annotation-based auto-provision path is **not enough by itself** to express MRI role-aware autoscaling cleanly.

There is a second limitation: the default auto-provision controller is optimized for a **simple single-metric InferenceSet case**, while MRI needs:

- one policy for prefill
- another policy for decode
- possibly multiple triggers for decode
- role-specific defaults and status reporting

So the recommended product direction is **not** "tell users to hand-wire multiple `ScaledObject`s" and also **not** "stretch the old annotation-only model too far".

## Recommended API Design

Add autoscaling configuration directly to each MRI role.

Example:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v3
spec:
  labelSelector:
    matchLabels:
      apps: deepseek-v3
  model:
    name: deepseek-ai/DeepSeek-V3
  roles:
  - type: prefill
    instanceType: Standard_ND96isr_H100_v5
    replicas: null
    autoscaling:
      minReplicas: 1
      maxReplicas: 8
      triggers:
      - type: kaito-external
        metricName: vllm:num_requests_waiting
        threshold: "8"
        metricProtocol: http
        metricPort: "80"
        metricPath: /metrics
        scrapeTimeout: 5s

  - type: decode
    instanceType: Standard_ND96isr_H100_v5
    replicas: null
    autoscaling:
      minReplicas: 2
      maxReplicas: 16
      triggers:
      - type: kaito-external
        metricName: vllm:num_running_requests
        threshold: "24"
        metricProtocol: http
        metricPort: "80"
        metricPath: /metrics
        scrapeTimeout: 5s
      - type: prometheus
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: kaito_decode_kv_cache_pressure
        threshold: "0.8"
        query: |
          avg(kaito_decode_kv_cache_pressure{multiroleinference="deepseek-v3"})
```

## API Semantics

Suggested semantics:

- `roles[].replicas != nil` means **fixed replica mode**.
- `roles[].autoscaling != nil` means **external autoscaling mode**.
- These two should be treated as mutually exclusive for a given role.
- If `autoscaling` is set, the MRI controller should leave the role's replica count under scaler control.

This aligns well with the current KAITO behavior where `nil` replicas already imply the controller should not actively force a fixed count.

## Recommended Controller Behavior

For each MRI role, the controller should reconcile two things:

1. the child `InferenceSet`
2. the role-specific `ScaledObject` (if autoscaling is configured)

### Reconcile Flow

For each role in `spec.roles`:

1. Reconcile child `InferenceSet`:
   - `<mri-name>-prefill`
   - `<mri-name>-decode`
2. If `role.autoscaling == nil`:
   - do not create a `ScaledObject`
   - respect fixed replica semantics if `role.replicas` is set
3. If `role.autoscaling != nil`:
   - validate `role.replicas == nil`
   - create or update one `ScaledObject` targeting the child `InferenceSet`
4. Aggregate child readiness and autoscaling readiness back into MRI status

### Ownership Model

The MRI controller should own the role-specific `ScaledObject`s directly.

That gives KAITO a clean UX:

- users declare scaling intent once at MRI level
- child `InferenceSet`s remain implementation details
- KEDA stays the execution engine
- MRI status can summarize both routing and scaling health

## Recommended Scaling Signals

## Prefill Metrics

Prefill should scale on **prompt pressure** and **queueing pressure**.

Recommended signals, in priority order:

1. `vllm:num_requests_waiting`
2. prefill queue depth
3. prompt-tokens backlog (if/when available)

Why:

- prefill is short-lived but expensive
- TTFT degrades before GPU utilization becomes useful
- queue depth is a better early signal than CPU/GPU utilization

In practice, the best v1 behavior is:

- scale prefill up when waiting requests stay above threshold
- keep scale-down conservative to avoid oscillation during bursty prompt traffic

## Decode Metrics

Decode should scale on **sustained generation pressure**, not just prompt arrival.

Recommended signals, in priority order:

1. running / in-flight decode requests
2. decode queue depth
3. KV cache pressure or utilization
4. token-throughput saturation metrics

Why:

- decode is the long-lived stage
- decode pressure is often better reflected in concurrency and KV occupancy than in waiting queue alone
- GPU utilization is too lagging and often too noisy for LLM serving

## What To Do With KV Events

The important design choice is:

> **Do not feed raw KV events directly into KEDA.**

Raw KV events are better suited for:

- routing decisions
- cache affinity
- endpoint scoring
- avoiding hot or fragmented decode pods

This matches the llm-d style architecture well: KV-aware signals are first-class inputs for the routing plane.

## Why Raw KV Events Are a Poor Direct Autoscaling Signal

Raw KV events are often:

- high-frequency
- bursty
- topology-specific
- noisy relative to actual replica need
- hard to translate 1:1 into desired replicas

KEDA and HPA work best when they consume:

- stable gauges
- queue depth
- concurrency counts
- pressure metrics
- explicit desired replica outputs

So the right pattern is to **aggregate first, scale second**.

## Recommended KV-Autoscaling Pattern

If KAITO wants KV-aware autoscaling, it should consume **derived** metrics such as:

- `kaito_decode_kv_cache_pressure`
- `kaito_decode_effective_kv_headroom`
- `kaito_decode_kv_transfer_backlog`
- `kaito_decode_kv_transfer_fail_rate`
- `kaito_decode_desired_replicas`

Those metrics can be produced by:

- a small KV event aggregator/exporter
- an EPP-adjacent metrics component
- a future KAITO-native autoscaling controller

Then KEDA can scale from those metrics in a stable way.

## Recommended Release Plan

### v1: Simple and Immediately Implementable

This is the recommended first shipping version.

- `prefill` scales on `vllm:num_requests_waiting`
- `decode` scales on `vllm:num_running_requests` or equivalent running-load metric
- KV-aware plugins remain in the routing plane only
- MRI controller owns role-specific `ScaledObject`s

Why this is the best first step:

- minimal implementation risk
- clean separation between routing and scaling
- easy to explain in docs and talks
- maps well to current KAITO + KEDA architecture

### v2: Add Decode KV Pressure

Add a second decode trigger using an aggregated KV pressure metric.

Example:

- trigger A: running decode requests
- trigger B: decode KV cache pressure

That lets decode scaling reflect both request concurrency and memory pressure.

### v3: Desired-Replica Computation

Move from "metric thresholding" to "desired replica computation".

For example:

- `kaito_prefill_desired_replicas = f(queue depth, prompt tokens, TTFT budget)`
- `kaito_decode_desired_replicas = f(running requests, KV pressure, throughput budget)`

At that point, KEDA becomes mostly an actuator while the scaling intelligence lives in a KAITO-native controller or aggregator.

This is conceptually closer to llm-d's WVA-style direction, but it is more complex and should not be the first step.

## Recommendation for KAITO Product UX

The preferred KAITO UX is:

- users author one `MultiRoleInference`
- MRI expresses per-role scaling intent declaratively
- KAITO generates the child `InferenceSet`s and child `ScaledObject`s
- routing stays llm-d-aware
- scaling stays role-aware

This is better than asking users to:

- discover generated child object names
- create multiple `ScaledObject`s manually
- understand which metrics belong to which role without guidance

In short:

> **`MultiRoleInference` should be the user-facing autoscaling API for P/D serving, while `InferenceSet` remains the controller-facing scaling target.**

## Practical Recommendation

If a single sentence is needed for a design review or conference talk, use this:

> In KAITO, role-aware autoscaling for prefill/decode should be implemented by letting `MultiRoleInference` generate one child `InferenceSet` and one role-specific `ScaledObject` per role; prefill scales on queue/waiting-request style signals, decode scales on running-request and later KV-pressure style signals, and raw KV events remain routing inputs rather than direct KEDA triggers.

## References

- `kaito/website/docs/keda-autoscaler-inference.md`
- `kaito/website/docs/prefill-decode-disaggregation.md`
- `kaito/pkg/controllers/multiroleinference/controller.go`
- `keda-kaito-scaler/pkg/controllers/autoprovision/auto_provision_controller.go`
- `keda-kaito-scaler/pkg/scaler/scaler.go`
- `llm-d/docs/well-lit-paths/foundations/workload-autoscaling.md`
- `llm-d/docs/architecture/core/router/epp/scheduling.md`
- `llm-d/docs/architecture/advanced/kv-management/prefix-cache-aware-routing.md`
