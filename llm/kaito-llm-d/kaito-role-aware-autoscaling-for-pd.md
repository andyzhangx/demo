# KAITO Role-Aware Autoscaling for Prefill/Decode Disaggregation

## Goal

This document captures a concrete KAITO implementation plan for **role-aware autoscaling** in prefill/decode (P/D) disaggregated serving.

The target is not just to say that prefill and decode should scale independently, but to define **where the API lives, which controller owns it, which metrics should drive it, and how KV-related signals should be used**.

## Executive Summary

For P/D disaggregation in KAITO, the right scaling boundary is **per role**, not one global autoscaling knob for the whole service.

Two user-facing designs are viable:

1. **Recommended for the first implementation: role-aware annotations on `MultiRoleInference` (MRI).** A small MRI adapter projects each role's policy onto the corresponding child `InferenceSet.metadata.annotations`, reusing the existing `keda-kaito-scaler` provisioning and metrics machinery.
2. **Alternative: typed `spec.roles[].autoscaling` fields.** This offers better schema discoverability and field-level validation, at the cost of a CRD/API compatibility commitment. It remains an option if the policy contract later stabilizes or first-class schema tooling becomes a requirement.

The annotation recommendation is a scoped implementation choice, not a claim that annotations are universally a better API. It minimizes changes to KAITO's CRD and reuses its optional KEDA integration while P/D scaling policy is still evolving. The new annotation payload is still a public contract that needs validation and versioning.

In either design:

- MRI remains the single user-facing resource.
- Each role has one child `InferenceSet` and at most one authoritative autoscaling path.
- The scaler integration reconciles one role-specific `ScaledObject` per managed role; the MRI controller need not implement KEDA resource provisioning itself.
- Prefill and decode use different metrics and thresholds.
- Raw KV events remain routing/scoring inputs. Autoscaling consumes stable derived pressure metrics or desired-replica signals instead.

> **Implementation status:** The MRI annotation and typed API examples below are proposals, not currently deployable MRI autoscaling APIs. Existing InferenceSet annotations alone do not enable this design. The required MRI integration changes are listed explicitly below.

## Why Per-Role Autoscaling Is Needed

P/D disaggregation only pays off if prefill and decode can evolve capacity independently.

- **Prefill** is compute-heavy and TTFT-sensitive: scale it to protect prompt admission latency.
- **Decode** is memory/KV/cache-pressure-heavy and throughput-sensitive: scale it to protect steady-state generation throughput and KV headroom.

The scaling target for each loop is the role-specific `InferenceSet`, not the whole MRI and not an individual tensor-parallel pod.

## Existing Capabilities and Integration Gaps

The source baseline for this proposal is KAITO [`3c831cad`](https://github.com/kaito-project/kaito/tree/3c831cadcae38b9b66cd615d865739d3b9ef771b) and keda-kaito-scaler [`ba1f2340`](https://github.com/kaito-project/keda-kaito-scaler/tree/ba1f234098a0f02d2e52ebc90eddf717a31a3318). These are source snapshots, not a guarantee that every released chart has the same capabilities. Pin and test compatible versions before implementation or deployment.

### What Can Be Reused

- MRI already creates one child `InferenceSet` per role and sets role labels such as `kaito.sh/inference-role: prefill` and `decode` on selectors/templates.
- A nil role `replicas` already causes the MRI controller to stop enforcing that role's replica count.
- The scaler auto-provision controller consumes top-level **`InferenceSet.metadata.annotations`** and creates a `ScaledObject` targeting that InferenceSet.
- Current scaler source supports a `scaledobject.kaito.sh/metrics` YAML/JSON list, per-metric up/down thresholds, model-pod and EPP metric sources, readiness gating, and stabilization/cooldown controls. It is **not limited to one metric**.
- Multi-metric combination currently supports a conservative **AND** policy. This is not equivalent to the usual maximum-of-replica-recommendations behavior of multiple HPA metrics.

The [website's metric-based scaler example](https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference#metric-based-keda-scaler) demonstrates the annotation integration pattern. Its single-metric configuration and the current source's `metrics` list must not be assumed to be interchangeable across versions.

### What Must Change for MRI

1. **Annotation placement:** MRI currently copies its annotations into child `InferenceSet.spec.template.annotations`, not child `metadata.annotations`. Simply putting existing `scaledobject.kaito.sh/*` annotations on MRI does not configure child auto-provisioning.
2. **Explicit child exclusion:** The existing auto-provision create/update predicates reject MRI-owned InferenceSets via `isMultiRoleInferenceChild`. Copying annotations to child metadata is therefore insufficient; the scaler needs an intentional, opt-in MRI integration path.
3. **Role-specific policy:** One flat MRI annotation map cannot give prefill and decode different thresholds and bounds. The adapter must map policies by role type, not list position, and must not copy one global policy onto both roles.
4. **Metric attribution:** Existing EPP scraping is reusable infrastructure, but its InferenceSet-oriented discovery does not automatically support MRI's shared router/EPP topology or per-role attribution. Model-pod metrics are the initial scope; EPP integration requires separate verification.

## Recommended API Design

### Option A: Role-Aware MRI Annotations — Recommended

Introduce one proposed MRI annotation, **`autoscaling.kaito.sh/roles`**, containing a versioned YAML object. Each role policy uses the existing scaler annotation suffixes (`min-replicas`, `max-replicas`, `combinepolicy`, `metrics`, and supported behavior settings), rather than inventing a second set of scaling algorithms.

The new annotation name, envelope, and translation rules below require implementation. They are not existing KAITO features.

```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v3
  annotations:
    autoscaling.kaito.sh/roles: |
      version: v1alpha1
      roles:
        prefill:
          min-replicas: "1"
          max-replicas: "8"
          combinepolicy: AND
          metrics:
          - name: vllm:num_requests_waiting
            type: gauge
            upthreshold: 8
            downthreshold: 1
        decode:
          min-replicas: "2"
          max-replicas: "16"
          combinepolicy: AND
          metrics:
          - name: vllm:num_requests_running
            type: gauge
            upthreshold: 24
            downthreshold: 4
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
  - type: decode
    instanceType: Standard_ND96isr_H100_v5
    replicas: null
```

The model/SKUs and thresholds are illustrative, not validated deployment or capacity recommendations. Verify exact metric names and semantics against the deployed runtime; do not assume every engine exports vLLM's metric names. Initial policies use per-replica model-pod gauge aggregation supported by the selected scaler version.

#### Annotation Contract and Projection

- `version` is required. Reject unsupported versions, malformed YAML, duplicate keys, unknown fields, and role names not present in `spec.roles`.
- A role entry enables KAITO-managed autoscaling for that role. An omitted entry means this adapter does not manage an autoscaler for that role.
- Require explicit `min-replicas` and `max-replicas` in the MRI policy. For the first release, require `1 <= min <= max`; do not rely on node-count-derived bounds or enable scale-to-zero for P/D before activation/routing semantics are designed.
- `metrics` is a non-empty structured list; scalar settings use the string representation expected by scaler annotations. Validate thresholds, metric types/sources, combinations, and behavior settings against the supported scaler contract before reconciliation.
- The adapter serializes `metrics` to `scaledobject.kaito.sh/metrics`, prefixes supported scalar keys with `scaledobject.kaito.sh/`, and sets `scaledobject.kaito.sh/auto-provision: "true"` on the matching child **metadata**.
- Only an explicit allowlist of scaler settings is accepted. Do not expose internal ownership annotations or arbitrary KEDA fields through this payload. The first implementation supports model-pod metrics; EPP and arbitrary Prometheus queries are not implied by this example.
- Reject a policy for a role with non-nil `replicas`. Reject ambiguous global `scaledobject.kaito.sh/*` configuration on the same MRI rather than guessing precedence.
- Treat generated child scaler annotations as adapter-owned output. Preserve unrelated child metadata, remove stale adapter-owned keys when a policy changes, and never require users to edit generated children.
- Do not propagate the MRI policy blob into child templates, Workspaces, or pods. Keep it separate from the existing propagation of workload annotations.
- Bound payload size and keep the annotation within Kubernetes metadata limits. Changes must trigger reconciliation even when MRI `metadata.generation` does not change; a generation-only watch predicate is insufficient.

For the prefill role, the projection produces the equivalent of these annotations on `<mri-name>-prefill` (generated output, not a second user-authored object):

```yaml
metadata:
  annotations:
    scaledobject.kaito.sh/auto-provision: "true"
    scaledobject.kaito.sh/min-replicas: "1"
    scaledobject.kaito.sh/max-replicas: "8"
    scaledobject.kaito.sh/combinepolicy: AND
    scaledobject.kaito.sh/metrics: |
      - name: vllm:num_requests_waiting
        type: gauge
        upthreshold: 8
        downthreshold: 1
```

This output only becomes effective after the MRI-child exclusion is deliberately adapted. Existing standalone InferenceSet behavior must remain unchanged.

### Option B: Typed `spec.roles[].autoscaling` — Alternative

The same intent can be represented as typed fields, for example this proposed `spec.roles` excerpt:

```yaml
roles:
- type: prefill
  instanceType: Standard_ND96isr_H100_v5
  replicas: null
  autoscaling:
    minReplicas: 1
    maxReplicas: 8
    combinePolicy: AND
    metrics:
    - name: vllm:num_requests_waiting
      type: gauge
      upThreshold: 8
      downThreshold: 1
- type: decode
  instanceType: Standard_ND96isr_H100_v5
  replicas: null
  autoscaling:
    minReplicas: 2
    maxReplicas: 16
    combinePolicy: AND
    metrics:
    - name: vllm:num_requests_running
      type: gauge
      upThreshold: 24
      downThreshold: 4
```

Advantages include schema discovery through `kubectl explain`, IDE completion, schema/admission validation, and more granular declarative field management when the CRD list/map schemas are designed correctly. It also puts replica mode and scaling intent together in the role spec.

Costs include CRD/generated-client changes, defaulting and conversion decisions, and a longer-lived compatibility commitment while the P/D policy model evolves. Typed fields do not automatically create status or correct lifecycle handling; those still need implementation.

A typed API should not blindly embed every KEDA trigger field. If arbitrary Prometheus queries or backend-specific triggers are later needed, define a deliberate extension contract, including authentication and metric-combination semantics. Do not imply that the current annotation adapter already supports them.

### Comparison and Decision

| Dimension | Role-aware annotations | Typed role fields |
| --- | --- | --- |
| Initial integration | Reuses scaler annotation contract; needs MRI adapter and validation | Needs CRD/API work as well as controller integration |
| Role-specific policies | Explicit role map in annotation payload | Natural placement under each role |
| Validation/discovery | Custom parsing/admission; embedded YAML is opaque to CRD schema | Better schema tooling and earlier field-level validation |
| GitOps/field ownership | Whole policy blob is one annotation value | Finer-grained with correctly designed structural schemas |
| Fast policy iteration | Avoids CRD churn, but payload compatibility still matters | Stable contract must be considered for each schema change |
| Status and handoff | Must be implemented explicitly | Must also be implemented explicitly |
| Backend coupling | Intentionally reuses supported scaler vocabulary | Can be abstract, but only if designed that way |

**Decision: recommend Option A for the initial implementation.** KAITO already has an annotation-driven optional scaler with multi-metric and behavior support. A thin, validated role-aware adapter is a smaller integration than introducing a new typed policy surface now. Keep Option B documented as a future alternative, not a second simultaneously authoritative configuration source.

This recommendation has a boundary: if policies become large, require extensive composition, or need strong schema tooling for broad production use, reevaluate typed fields or a separate policy resource. Annotation-based does not mean unversioned or unvalidated.

## API Semantics and Replica Ownership

These semantics apply regardless of which public representation is chosen:

| Role replicas | Role policy | Mode |
| --- | --- | --- |
| Non-nil | Absent | Fixed replicas; MRI enforces the value |
| Nil | Present | KAITO-managed autoscaling; MRI does not write replicas |
| Nil | Absent | Externally managed replicas; no guarantee that any scaler exists |
| Non-nil | Present | Invalid; reject at admission |

For Option A, "role policy" means an entry under `autoscaling.kaito.sh/roles`; for Option B it means `roles[].autoscaling`. Preserve the nil/nil state for existing user-managed HPA/KEDA setups.

Mode changes require an ordered handoff, not merely changing fields:

- **Fixed to managed autoscaling:** stop MRI replica enforcement before enabling the managed scaler. Define bootstrap behavior so initial replicas converge to the configured minimum without MRI becoming a second steady-state writer.
- **Managed autoscaling to fixed:** disable/remove the managed ScaledObject and its HPA, confirm replica control is released, then enforce the fixed value. Cleanup must gate fixed-replica reconciliation, including the case where the scaler component is unavailable.
- **Policy removal with nil replicas:** clean up only the managed scaler/HPA, then leave replicas externally managed. Do not reset the last replica count or silently install a default policy.
- **Manual scaler conflicts:** report a conflict rather than silently adopting/deleting user-owned ScaledObjects or running two controllers against one target. Check both HPA and ScaledObject targets.
- **Potential future migration:** reject simultaneous typed and annotation policies for a role, or define a coordinated one-way migration. Do not run both provisioning paths concurrently.

Annotation admission must validate the decoded payload and cross-check `spec.roles`. Invalid updates should be rejected instead of silently disabling a working policy. Controller validation remains necessary for existing objects, version skew, and dynamic failures.

## Recommended Controller Behavior and Ownership

Keep policy ownership separate from KEDA implementation ownership:

1. **MRI controller / MRI adapter:** reconcile child InferenceSets and project each role's validated policy to child metadata. Watch annotation changes, policy removal, and child drift. Do not manage all child metadata indiscriminately.
2. **Scaler integration:** explicitly admit opted-in, adapter-managed MRI children through the current exclusion boundary; validate projected configuration, build and reconcile ScaledObjects using the existing implementation, and handle cleanup. An owner-aware gate/feature flag must distinguish this supported path from arbitrary annotations on MRI children, including removal events that must still reach cleanup.
3. **KEDA/HPA:** update the child InferenceSet's scale subresource. MRI leaves role replicas alone in autoscaling mode.
4. **MRI status aggregation:** expose role policy acceptance, managed ScaledObject reference, scaler readiness, and conflicts separately from workload readiness. Surface missing/incompatible KEDA installation and invalid metric wiring rather than claiming successful scaling. These status additions are implementation work, not existing behavior supplied by annotations.

For the annotation-first integration, preserve the existing lifecycle chain:

```text
MRI --owns--> role InferenceSet --owns--> role ScaledObject --owns--> HPA
```

The scaler controller reconciles ScaledObjects; the MRI controller does not need to duplicate their construction logic. Kubernetes owner references define lifecycle ownership, not which controller binary must reconcile a resource. A future typed API can reuse this same integration boundary.

Track applied policy identity with a digest/version as appropriate: annotation-only updates do not necessarily advance MRI generation. Assign a clear writer for MRI status conditions; do not have the MRI and scaler controllers overwrite each other's status.

Required failure and transition tests include role-specific projection, role reorder, annotation-only updates, policy key removal, bounds/threshold rejection, fixed/autoscaling handoff, child recreation, missing KEDA, manual scaler conflicts, cleanup, and non-regression of standalone InferenceSet provisioning. Independent P/D scaling also needs end-to-end verification against the deployed runtime and routing topology.

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

### v1: Annotation-First Role-Aware Integration

This is the recommended first implementation, not an already available MRI feature.

- Implement and validate the versioned MRI role-policy annotation and metadata projection.
- Add an explicit MRI-child opt-in path to the scaler; retain standalone InferenceSet behavior and existing ScaledObject construction logic.
- Use `vllm:num_requests_waiting` for prefill and `vllm:num_requests_running` (or a verified equivalent) for decode, initially one model-pod metric per role.
- Require positive minimum replicas and explicit bounds; keep raw KV events in routing only.
- Implement ownership handoff, cleanup, conflict detection, and per-role status before presenting the feature as supported.
- Pin compatible KAITO, scaler, KEDA, Kubernetes, and model-runtime versions; verify emitted HPA behavior against the cluster's feature gates.

Why this is the preferred first step: it reuses mature scaler mechanisms, avoids an immediate typed autoscaling CRD surface, and keeps routing and scaling responsibilities separate. It is smaller in scope, not a zero-code annotation change.

### v2: Add Decode KV Pressure with Explicit Combination Semantics

Add an aggregated KV pressure metric only after defining its meaning and collection path. For example, decode concurrency and KV pressure may be:

- independent scale-up reasons (either is sufficient), or
- a load signal plus a scale-down safety guard, or
- intentionally combined with conservative AND semantics.

The current annotation provisioner supports AND only. It must not be presented as equivalent to independent KEDA triggers whose desired replica recommendations are combined by taking the maximum. If the selected policy requires OR, separate up/down combinations, or arbitrary Prometheus queries, extend and test the scaler contract explicitly rather than merely adding another metric to the list.

Verify MRI role attribution and shared EPP discovery before using EPP metrics. Ensure KV occupancy is a useful pressure signal rather than only retained cache state, and make scale-down conservative enough for in-flight decode work.

### v3: Desired-Replica Computation and API Reassessment

Move from metric thresholding to explicit desired-replica computation if measurements justify the added complexity:

- `kaito_prefill_desired_replicas = f(queue depth, prompt tokens, TTFT budget)`
- `kaito_decode_desired_replicas = f(running requests, KV pressure, throughput budget)`

KEDA can act as the actuator while an aggregator or KAITO-native component computes demand. This is conceptually closer to llm-d's WVA-style direction, but is not the first implementation.

Revisit typed `roles[].autoscaling` or a policy resource when the contract stabilizes or annotation ergonomics become a limitation. Preserve a single authoritative policy source and an explicit migration path; do not require a rewrite of the scaler execution layer.

## Recommendation for KAITO Product UX

The preferred initial UX is:

- users author one `MultiRoleInference` with role-aware autoscaling annotations;
- KAITO projects independent prefill/decode policies onto generated child InferenceSets;
- the scaler integration manages role-specific ScaledObjects;
- MRI reports policy/scaler state without requiring users to inspect generated children for every failure;
- routing stays llm-d-aware and scaling stays role-aware.

Users should not need to discover generated child names, patch their annotations, or hand-wire multiple ScaledObjects for the managed path. Existing manual scaling remains possible through the explicit externally managed mode.

## Practical Recommendation

> Prefer a versioned, role-aware annotation on `MultiRoleInference` for the initial P/D autoscaling API, adapt it to existing InferenceSet scaler annotations, and reuse `keda-kaito-scaler` for one ScaledObject per managed role. Keep typed `roles[].autoscaling` as an alternative; scale prefill on queue pressure, decode on running load and later well-defined KV pressure, and keep raw KV events in the routing plane.

## References

- [KAITO metric-based KEDA scaler documentation](https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference#metric-based-keda-scaler)
- [KAITO P/D documentation source](https://github.com/kaito-project/kaito/blob/3c831cadcae38b9b66cd615d865739d3b9ef771b/website/docs/prefill-decode-disaggregation.md)
- [MRI replica and annotation reconciliation](https://github.com/kaito-project/kaito/blob/3c831cadcae38b9b66cd615d865739d3b9ef771b/pkg/controllers/multiroleinference/controller.go#L431-L476)
- [Scaler metrics and annotation contract](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/README.md)
- [Auto-provision predicates and MRI-child exclusion](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/pkg/controllers/autoprovision/auto_provision_controller.go#L378-L427)
- [ScaledObject builder and lifecycle ownership](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/pkg/scaledobject/provisioner.go)
- [EPP metric source](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/pkg/metricsource/epp_source.go)
- `llm-d/docs/well-lit-paths/foundations/workload-autoscaling.md`
- `llm-d/docs/architecture/core/router/epp/scheduling.md`
- `llm-d/docs/architecture/advanced/kv-management/prefix-cache-aware-routing.md`
