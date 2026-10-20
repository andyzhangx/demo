# KAITO Role-Aware Autoscaling for Prefill/Decode Disaggregation

## Goal

This document captures a concrete KAITO implementation plan for **role-aware autoscaling** in prefill/decode (P/D) disaggregated serving.

The target is not just to say that prefill and decode should scale independently, but to define **where the API lives, which controller owns it, and which vLLM-native metrics drive scaling or observation**. Every scaling signal must either be emitted by vLLM itself or have an explicit derivation from verified vLLM-native metrics. The first implementation uses native metrics only; derived metrics are a next-phase goal, not a prerequisite or an existing capability.

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
- Raw KV events remain routing/scoring inputs. Initial scaling uses native vLLM request-count gauges. A subsequent phase may aggregate native KV utilization, latency, or token counters into clearly defined derived signals; it must not invent unavailable inputs.

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
- Current scaler source supports a `scaledobject.kaito.sh/metrics` YAML/JSON list, per-metric up/down thresholds, readiness gating, and stabilization/cooldown controls. It is **not limited to one metric**. This design uses only its model-pod source to read metrics directly from vLLM; other source types are outside scope.
- Multi-metric combination currently supports a conservative **AND** policy. This is not equivalent to the usual maximum-of-replica-recommendations behavior of multiple HPA metrics.

The [website's metric-based scaler example](https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference#metric-based-keda-scaler) demonstrates the annotation integration pattern. Its single-metric configuration and the current source's `metrics` list must not be assumed to be interchangeable across versions.

### What Must Change for MRI

1. **Annotation placement:** MRI currently copies its annotations into child `InferenceSet.spec.template.annotations`, not child `metadata.annotations`. Simply putting existing `scaledobject.kaito.sh/*` annotations on MRI does not configure child auto-provisioning.
2. **Explicit child exclusion:** The existing auto-provision create/update predicates reject MRI-owned InferenceSets via `isMultiRoleInferenceChild`. Copying annotations to child metadata is therefore insufficient; the scaler needs an intentional, opt-in MRI integration path.
3. **Role-specific policy:** One flat MRI annotation map cannot give prefill and decode different thresholds and bounds. The adapter must map policies by role type, not list position, and must not copy one global policy onto both roles.
4. **Metric attribution and availability:** Scrape only the vLLM endpoints belonging to the target MRI role. A model-pod metric does not include requests still queued in the router/EPP. Verify the actual runtime image and `/metrics` output; support in upstream source does not guarantee availability in the deployed image.

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

The model/SKUs and thresholds are illustrative, not validated deployment or capacity recommendations. These examples require vLLM and the two request-count gauges listed below. Check the deployed image's `/metrics` output before enabling the policy; upstream availability is not a deployment check. Initial policies use per-replica model-pod gauge aggregation supported by the selected scaler version.

#### Annotation Contract and Projection

- `version` is required. Reject unsupported versions, malformed YAML, duplicate keys, unknown fields, and role names not present in `spec.roles`.
- A role entry enables KAITO-managed autoscaling for that role. An omitted entry means this adapter does not manage an autoscaler for that role.
- Require explicit `min-replicas` and `max-replicas` in the MRI policy. For the first release, require `1 <= min <= max`; do not rely on node-count-derived bounds or enable scale-to-zero for P/D before activation/routing semantics are designed.
- `metrics` is a non-empty structured list; scalar settings use the string representation expected by scaler annotations. Validate thresholds, metric types/sources, combinations, and behavior settings against the supported scaler contract before reconciliation. The first release accepts only `vllm:num_requests_waiting` for prefill and `vllm:num_requests_running` for decode, both gauges from the model-pod source. Histograms in the observation inventory below are not automatically admitted as autoscaling triggers.
- The adapter serializes `metrics` to `scaledobject.kaito.sh/metrics`, prefixes supported scalar keys with `scaledobject.kaito.sh/`, and sets `scaledobject.kaito.sh/auto-provision: "true"` on the matching child **metadata**.
- Only an explicit allowlist of scaler settings is accepted. Do not expose internal ownership annotations or arbitrary KEDA fields through this payload. EPP-exported metrics, derived metrics, and arbitrary Prometheus query triggers are outside v1. The optional KV gauge and explicitly defined vLLM-derived signals may enter a later scaling allowlist only after their collection adapter and control policy are implemented and tested.
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

A typed API should not blindly embed every KEDA trigger field. It must retain the same native-metric allowlist in v1 and the same verified derivation contract in later phases, including availability checks and combination semantics. Switching representation does not justify adding unsupported inputs.

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
4. **MRI status aggregation:** expose role policy acceptance, managed ScaledObject reference, scaler readiness, metric availability, and conflicts separately from workload readiness. Surface missing/incompatible KEDA installation and invalid metric wiring rather than claiming successful scaling. These status additions are implementation work, not existing behavior supplied by annotations.

For the annotation-first integration, preserve the existing lifecycle chain:

```text
MRI --owns--> role InferenceSet --owns--> role ScaledObject --owns--> HPA
```

The scaler controller reconciles ScaledObjects; the MRI controller does not need to duplicate their construction logic. Kubernetes owner references define lifecycle ownership, not which controller binary must reconcile a resource. A future typed API can reuse this same integration boundary.

Track applied policy identity with a digest/version as appropriate: annotation-only updates do not necessarily advance MRI generation. Assign a clear writer for MRI status conditions; do not have the MRI and scaler controllers overwrite each other's status.

Required failure and transition tests include role-specific projection, role reorder, annotation-only updates, policy key removal, bounds/threshold rejection, fixed/autoscaling handoff, child recreation, missing KEDA, missing/stale/invalid metric samples, role attribution, manual scaler conflicts, cleanup, and non-regression of standalone InferenceSet provisioning. Independent P/D scaling also needs end-to-end verification against the deployed vLLM image and routing topology.

## vLLM-Native Metrics and Corresponding Actions

The inventory below is verified against the [vLLM production metrics documentation](https://docs.vllm.ai/en/stable/usage/metrics/) and [metric registrations at source commit `8407bc0b`](https://github.com/vllm-project/vllm/blob/8407bc0bb6b0061dacb731ae3cc54b6035f112b3/vllm/v1/metrics/loggers.py). It is an upstream availability inventory, **not a claim that an uninspected deployed image exports every metric**. Each enabled metric must also pass the runtime verification gate below.

### Native Gauges for Scaling and KV Safety

| Native vLLM metric | Type and unit | Role and meaning | Corresponding action |
| --- | --- | --- | --- |
| `vllm:num_requests_waiting` | Gauge, requests | Prefill: requests waiting inside that vLLM engine | Primary v1 prefill trigger. Above the configured up-threshold, request scale-up; below the down-threshold, allow scale-down, subject to readiness, bounds, stabilization, and cooldown. Otherwise hold. |
| `vllm:num_requests_running` | Gauge, requests | Decode: requests in model execution batches; not all router-level in-flight requests | Primary v1 decode trigger. Apply the same bounded up/down/hold behavior using decode-specific thresholds. |
| `vllm:kv_cache_usage_perc` | Gauge, fraction from 0 to 1 | Decode: engine KV-cache utilization; `0.8` means 80%, not 0.8% | Observe and alert initially. In a separately implemented v2 policy, use sustained high utilization as a scale-down guard and investigate capacity pressure. High utilization alone must not automatically cause expansion. |

For the first two rows, the current scaler's single-metric formula adjusts one replica per permitted step, rather than promising an arbitrary immediate jump to an optimal replica count. Apply thresholds to the scaler's documented per-replica aggregation, not an unqualified sum across the whole MRI.

The same native waiting-request gauge may be observed on decode instances to diagnose decode-side queueing. That does not introduce a new queue-depth metric or automatically make it a second v1 trigger.

KV occupancy is not a direct measurement of remaining safe request capacity. Its relationship to active work, cache reuse, and reclaimability depends on runtime semantics and workload. Validate that relationship before using it to gate scaling; no synthetic pressure/headroom metric is assumed.

### Native Histograms and Counter for Observation and Policy Tuning

These metrics are native vLLM outputs, but are **observational in v1**, not additional v1 KEDA triggers. They also provide the inputs for explicitly defined next-phase derivations.

| Native vLLM metric family | Type and unit | Corresponding action |
| --- | --- | --- |
| `vllm:time_to_first_token_seconds` | Histogram, seconds | Observe prefill-side first-token latency. If queue growth and latency rise together, review the prefill threshold and minimum replicas. Engine-local TTFT is not necessarily client-visible end-to-end P/D TTFT. |
| `vllm:request_queue_time_seconds` | Histogram, seconds | Observe time spent waiting in each role's engine. Sustained queueing supports capacity diagnosis; do not mistake it for instantaneous queue depth. |
| `vllm:request_prefill_time_seconds` | Histogram, seconds | Diagnose prefill compute latency and benchmark runtime/SKU choices before changing scaling bounds. |
| `vllm:request_decode_time_seconds` | Histogram, seconds | Diagnose decode service duration; interpret with output length because a longer generation naturally takes longer. |
| `vllm:inter_token_latency_seconds` | Histogram, seconds | Observe decode token-delivery latency and investigate regressions alongside the running-request gauge. |
| `vllm:generation_tokens_total` | Counter, tokens | Count generated tokens; a reset-aware rate over a window yields decode output throughput for observation and the v2 derived signal below. |

The generation counter is registered as `vllm:generation_tokens`; Prometheus exposition adds the `_total` suffix. Histogram families expose bucket/count/sum series rather than one instantaneous scalar with the family name. A dashboard may compute windowed averages or quantiles from those native series; v1 does not require publishing their results as a new exported metric or using them as scaling inputs. Publishing the defined recording rules below is a v2 goal. Do not treat the raw sum, missing observations, or a no-traffic interval as a valid low-latency sample. Existing scaler histogram support does not by itself establish the desired P/D control policy.

### Next-Phase Derived Metrics — Only from Existing vLLM Inputs

The following are **proposed recording-rule names, not metrics already emitted by vLLM or KAITO**. Each has a concrete native source and formula. They can be implemented with Prometheus recording rules or a narrowly scoped aggregation adapter; v1 does not depend on either.

In the formulas, `role_series(...)` selects only the intended MRI/role, deduplicates scrapes, and retains the appropriate engine/replica scope. Kubernetes discovery labels may supply identity, but no non-vLLM load metric supplies the signal. Group by cluster/namespace/MRI/role so unrelated workloads are never merged. The formulas specify semantics rather than ready-to-paste PromQL with assumed label names.

| Proposed derived metric | Existing native vLLM input | Derivation and unit | Intended action in the next phase |
| --- | --- | --- | --- |
| `kaito:decode_kv_cache_usage_max` | `vllm:kv_cache_usage_perc` | Maximum of valid decode engine samples in the role; fraction `[0, 1]` | Observe/alert on the most occupied engine; evaluate a scale-down guard, not unconditional scale-up. A role average must not conceal a hot engine; a role-wide maximum alone does not identify which replica is safe to remove. |
| `kaito:decode_kv_cache_free_fraction_min` | `vllm:kv_cache_usage_perc` | `1 - max(role_series(kv_cache_usage_perc))`; fraction `[0, 1]` | Equivalent conservative free-cache-fraction view for the guard. This is **not** effective request capacity, free bytes, or headroom adjusted for pending work; do not treat it as independent evidence from KV utilization. |
| `kaito:prefill_ttft_p95_seconds` | `vllm:time_to_first_token_seconds_bucket` and the native histogram count | Apply `histogram_quantile(0.95, ...)` to the sum of per-series bucket rates over 5m, retaining workload/role labels and the `le` bucket boundary; seconds | Observe the prefill latency tail and tune queue thresholds/minimum replicas. First require enough observations; do not average per-pod P95 values or equate engine-local TTFT with client P/D latency. Not a direct scaling trigger until a policy is tested. |
| `kaito:decode_generation_tokens_per_second` | `vllm:generation_tokens_total` | Sum of per-series reset-aware `rate(...[5m])` for decode engines; tokens/s | Observe actual output throughput and benchmark capacity. Throughput alone is not saturation or unsatisfied demand; neither high nor low throughput alone requests scale-up or scale-down. |

A derived metric is allowed only if all required source series exist on the deployed vLLM version, have the expected units/topology, and are fresh. Handle counter resets before aggregation, require adequate histogram observations, and propagate missing/invalid inputs rather than converting them to zero. For a role-wide safety guard, a partial scrape must not silently present the surviving engines as complete coverage.

Prometheus recording-rule outputs are **not available from the vLLM model-pod `/metrics` endpoint**. To use them for future automated decisions, implement a dedicated, validated collection path (for example, an adapter reading the approved recording rules) and define its authentication, time-window, freshness, coverage, and failure semantics. Merely putting these names in the current model-pod `metrics` annotation will not work. Observation can precede that scaling integration.

### Runtime Verification Gate — Required Before Enabling Actions

1. **Pin versions:** record the actual vLLM image tag/digest, KAITO, scaler, KEDA, and Kubernetes versions. Do not infer metric availability from current upstream documentation alone.
2. **Scrape real endpoints:** inspect `/metrics` on representative prefill and decode vLLM serving endpoints with representative traffic. Verify required metric names, `TYPE`, units, labels, and finite values; include newly created replicas in readiness checks. Do not assume a particular service port from the examples.
3. **Match role scope:** discover endpoints through MRI/role ownership and labels. Do not assume vLLM automatically exposes Kubernetes role labels. Avoid scraping the router instead of vLLM or double-counting engine/worker series in multi-process or tensor-parallel deployments.
4. **Check basic semantics:** waiting/running counts must be non-negative; KV utilization must be a fraction in `[0, 1]`. Verify the scaler's per-replica aggregation matches the observed engine topology and that native histograms produce samples under representative traffic.
5. **Fail closed on missing data:** if required metrics are absent, stale, non-finite, or unreachable, do not activate a new autoscaling policy. For an active policy, hold scaling decisions, especially scale-down, and surface a metric-unavailable condition/event. **Missing is not zero.** A valid observed zero request count is different from a failed scrape.
6. **Implement the guard across the execution path:** the missing-data contract requires scaler/HPA error-handling and fallback behavior to be verified or hardened. It is not guaranteed by adding an MRI annotation. Do not emit synthetic zero values or leave a fallback path that scales down on unavailable data. If an optional observation metric is missing, disable that observation feature and report it; do not silently substitute a custom metric.

No cluster or deployed runtime was inspected while writing this document. A release must not claim support for an enabled metric until this gate passes on the actual runtime image. If a name differs in another vLLM version, explicitly verify and document that version's native equivalent before accepting it; do not silently alias an unknown name.

## KV Events and Out-of-Scope Signals

Raw KV events can continue to support routing, cache affinity, and endpoint scoring, but they are not KEDA metrics in this proposal. The v1 scaling/observation inventory is limited to the native gauges, histograms, and counter above; v2 derivations must trace back to those verified sources.

Do not require an undefined pressure/headroom exporter, a token-backlog metric, EPP-exported load, or an unexplained desired-replica signal. Native cumulative token counters cannot reconstruct queued prompt-token work. A replica recommendation calculated internally by the scaler is an action, not evidence that vLLM exports a desired-replica metric. Defined transformations of existing native signals, such as the v2 rules above, are allowed.

Connector-specific transfer instrumentation is not part of the initial inventory. Adding it would require a separately verified vLLM version and connector configuration; do not make an optional connector metric a prerequisite for basic P/D autoscaling.

## Recommended Release Plan

### v1: Annotation-First Scaling from Two Native Request Gauges

This is the recommended first implementation, not an already available MRI feature.

- Implement and validate the versioned MRI role-policy annotation and metadata projection.
- Add an explicit MRI-child opt-in path to the scaler; retain standalone InferenceSet behavior and existing ScaledObject construction logic.
- Scale prefill only on `vllm:num_requests_waiting` and decode only on `vllm:num_requests_running`, one native model-pod gauge per role.
- Use separate role thresholds with positive minimum replicas, explicit upper bounds, readiness checks, stabilization, and cooldown. Tune the example values using measured workloads rather than treating them as production defaults.
- Complete the runtime metric verification gate and missing-data safeguards before enabling the policy.
- Implement ownership handoff, cleanup, manual-scaler conflict detection, and per-role status.
- Observe the native latency histograms and KV utilization where verified available; these do not become automatic triggers merely because they appear on a dashboard.
- Verify emitted HPA behavior against the cluster's supported APIs and feature gates.

This first step reuses existing scaler mechanisms without introducing a typed autoscaling CRD surface or requiring any custom metric exporter.

### v2: Derived Signals from Native Inputs and Optional KV Safety Guard

Implement the recording rules defined above, with source-to-output tests for reset handling, histogram quantiles, role isolation, complete coverage, and missing data. Begin with observation/alerts; keep v1 scaling operational without a dependency on the new rules. Any promotion to an automated scaling input requires the explicit collection adapter and validated policy, not just a new metric name in annotations.

Use `vllm:kv_cache_usage_perc`, or its verified maximum/minimum-free-fraction derivations, for the optional KV signal. Prefer a clearly specified scale-down guard to treating occupancy alone as demand for new replicas.

An example policy to evaluate is:

- high running-request count can request scale-up independently of KV utilization;
- low running-request count permits scale-down only when KV utilization is also below a validated safe threshold;
- high KV utilization with low running-request count blocks scale-down and triggers investigation rather than unconditional expansion;
- unavailable required KV samples hold decisions under the missing-data contract.

**This asymmetric policy is not implemented by simply appending the KV gauge to the existing AND metric list.** The current provisioner applies conservative AND combination; it could suppress needed scale-up when concurrency is high but KV occupancy is low. A separate, tested scaler-policy extension is required. Until that exists, retain the single-metric v1 policy and use KV utilization only for observation/alerts. Define per-replica aggregation conservatively enough that a fleet average does not hide a hot replica before removal.

### v3: Production Hardening Using the Same Native Inputs

- Validate bursts, steady state, cold starts, long generations, partial scrape failures, and scale-down with in-flight requests.
- Tune thresholds, minimum replicas, stabilization, and cooldown against the native queue/running gauges and latency histograms.
- Test runtime upgrades for metric-name/type changes, new engine topology, and changed KV-utilization semantics.
- Revisit typed `roles[].autoscaling` or a policy resource only if schema/tooling needs justify migration; keep native-source traceability for every direct or derived signal and a single authoritative policy source.

Later phases may publish the defined vLLM-derived metrics, but must not depend on an input that vLLM cannot actually provide. Custom desired-replica signals remain outside this plan.

## Recommendation for KAITO Product UX

The preferred initial UX is:

- users author one `MultiRoleInference` with role-aware autoscaling annotations;
- KAITO projects independent prefill/decode policies onto generated child InferenceSets;
- the scaler integration manages role-specific ScaledObjects;
- MRI reports policy/scaler state without requiring users to inspect generated children for every failure;
- routing stays llm-d-aware and scaling stays role-aware, using verified native vLLM inputs directly in v1 and explicit, tested derivations in later phases.

Users should not need to discover generated child names, patch their annotations, or hand-wire multiple ScaledObjects for the managed path. Existing manual scaling remains possible through the explicit externally managed mode.

## Practical Recommendation

> Prefer a versioned, role-aware annotation on `MultiRoleInference`, adapt it to existing InferenceSet scaler annotations, and reuse `keda-kaito-scaler`. Scale prefill on native `vllm:num_requests_waiting` and decode on native `vllm:num_requests_running`; observe native latency histograms and `vllm:kv_cache_usage_perc`, and add a KV safety guard only after explicit implementation and runtime verification. Keep typed fields as an alternative and raw KV events in routing. Add the documented vLLM-derived recording rules in the next phase; do not invent unavailable source metrics.

## References

- [KAITO metric-based KEDA scaler documentation](https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference#metric-based-keda-scaler)
- [KAITO P/D documentation source](https://github.com/kaito-project/kaito/blob/3c831cadcae38b9b66cd615d865739d3b9ef771b/website/docs/prefill-decode-disaggregation.md)
- [MRI replica and annotation reconciliation](https://github.com/kaito-project/kaito/blob/3c831cadcae38b9b66cd615d865739d3b9ef771b/pkg/controllers/multiroleinference/controller.go#L431-L476)
- [Scaler metrics and annotation contract](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/README.md)
- [Auto-provision predicates and MRI-child exclusion](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/pkg/controllers/autoprovision/auto_provision_controller.go#L378-L427)
- [ScaledObject builder and lifecycle ownership](https://github.com/kaito-project/keda-kaito-scaler/blob/ba1f234098a0f02d2e52ebc90eddf717a31a3318/pkg/scaledobject/provisioner.go)
- [vLLM production metrics](https://docs.vllm.ai/en/stable/usage/metrics/)
- [vLLM native metric definitions, source snapshot `8407bc0b`](https://github.com/vllm-project/vllm/blob/8407bc0bb6b0061dacb731ae3cc54b6035f112b3/vllm/v1/metrics/loggers.py)
- `llm-d/docs/well-lit-paths/foundations/workload-autoscaling.md`
- `llm-d/docs/architecture/core/router/epp/scheduling.md`
- `llm-d/docs/architecture/advanced/kv-management/prefix-cache-aware-routing.md`
