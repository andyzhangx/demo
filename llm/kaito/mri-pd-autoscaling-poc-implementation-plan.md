# MRI Role-Aware P/D Autoscaling: POC Implementation Plan

**Status:** implementation plan only; no POC implementation, GPU deployment, or performance validation has been completed.

This plan translates [KAITO proposal #2503](https://github.com/kaito-project/kaito/pull/2503) into an incremental proof of concept for independently scaling the prefill and decode roles of a `MultiRoleInference` (MRI).

Analysis date: **2026-11-03**. Source snapshots inspected:

- [Proposal at `ae8de325`](https://github.com/kaito-project/kaito/blob/ae8de3257d393dfb3db389aa2a5dd29c2b3e8c27/docs/proposals/20261103-role-aware-pd-autoscaling.md).
- [KAITO implementation baseline `4c450c32`](https://github.com/kaito-project/kaito/tree/4c450c328a21047f7fa576780a086cc1a393cc95).
- [keda-kaito-scaler baseline `3964e100`](https://github.com/kaito-project/keda-kaito-scaler/tree/3964e100f0093ec609b663704e726f2bb3fe8fd9).

These are reproducible analysis baselines, not a promise that upstream has not changed. Recheck them when implementation starts. This work should use dedicated branches and must not be mixed into CPU inference PR #2431.

## 0. Fastest Path: Minimal, Manually Operated Scale-Up Demo

**Choose this section if the immediate goal is a basically working experiment, not the complete managed-mode implementation in proposal #2503.** Sections 1–9 retain the full plan. This shortcut deliberately replaces policy projection and automated ownership handoff with an operator-run procedure; it is **not proposal-compliant managed mode**, a supported production configuration, or evidence that the POC already works. The checklist below must pass on a real cluster before making that claim.

### 0.1 Scope and minimum changes

Use an **isolated disposable test cluster**, dedicated pinned KAITO/scaler builds, one explicitly opted-in MRI, exactly one prefill and one decode role, and fixed per-Workspace GPU/node/TP topology. Record the MRI namespace/name/UID and both child names/UIDs in a lab allowlist; names or role labels alone are not authorization. Start with spare suitable GPU capacity so the first experiment tests serving scale-out rather than node provisioning. Test provisioning separately afterward.

| Component | Minimum experiment work | Deliberately deferred |
|---|---|---|
| KAITO install | Remove the unconditional MRI role-replica default from the dedicated chart/installed CRD; prove nil survives admission, readback and reconciliation | General mode-aware mutator and compatibility migration |
| KAITO controller | Reuse the existing nil guard **only if** live tests establish ownership; test child metadata preservation | Full parent policy projection/status/lifecycle automation; add a small projection change if metadata does not survive |
| Scaler | Add an explicitly authorized MRI-child path, strict role-local collection, positive bounds and enforced scale-up-only behavior | General managed-policy schema, broad refactoring, automatic drain/downscale |
| Operator | Bootstrap positive replicas, configure existing child annotations, activate only after gates pass, and perform verified shutdown | Unattended activation, restart recovery and ownership transitions |

**Stock KAITO installation plus a scaler-only change is not a reliable shortcut.** The installed replica default can make the parent overwrite the HPA. Merely removing the scaler's MRI predicate exclusion also leaves unsafe metric aggregation and ownership gaps. The minimum deliverable is the install adjustment **plus** the focused scaler changes and the runbook below; a controller Go change may be unnecessary, but that is a testable conditional, not a guarantee.

### 0.2 Establish replica ownership before enabling KEDA

The pinned source makes the narrower path plausible:

- [`reconcileInferenceSet`](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/pkg/controllers/multiroleinference/controller.go) assigns child `spec.replicas` only when `role.Replicas != nil`. The [Go API](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/api/v1alpha1/multiroleinference_types.go) explicitly describes nil as allowing external autoscalers.
- The [Helm MRI CRD](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/charts/kaito/workspace/templates/kaito.sh_multiroleinferences.yaml) has `default: 1` for role replicas, while the [base CRD](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/config/crd/bases/kaito.sh_multiroleinferences.yaml) does not. Inspect the **rendered and installed** CRD, not just the base YAML.
- [`SetDefaults`](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/api/v1alpha1/multiroleinference_default.go) also fills nil replicas with one. However, the pinned [MRI webhook registration](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/pkg/workspace/webhooks/webhooks.go) is validating-only. The [pinned Knative validation path](https://github.com/knative/pkg/blob/c9015f8bfdea/webhook/resourcesemantics/validation/validation_admit.go) decodes and calls `Validate`, not `SetDefaults`, and returns an allow response without a mutation patch. No direct MRI reconciler call to `SetDefaults` was found in this baseline. Thus the method's existence alone does **not** prove it persists a default, nor does source inspection prove a particular deployed admission stack leaves nil intact.

Lab procedure:

1. Pin the controller, chart, scaler, KEDA, vLLM and routing-sidecar versions/images. In this **test installation only**, remove the unconditional `roles[].replicas` default from the chart/CRD installation path. Verify every served version and any conversion/mutating admission path actually installed. Do not blanket-patch a shared/production CRD. Fixed workloads in this test installation must specify replicas explicitly; do not rely on the removed default. An explicit YAML `null` is **not** a bypass for Kubernetes defaulting.
2. With autoscaling disabled, create the MRI with explicit safe positive counts (for example one Workspace per role). Wait for both child InferenceSets, Workspaces, model pods and the working P/D route. This lets KAITO bootstrap the counts; the scaler must never directly write replicas. Avoid creating a nil-parent child at zero and expecting KEDA to recover it.
3. Remove each role's parent replica field using an identity/type-checked edit. Read the stored MRI back through the API and prove **both roles remain absent/nil**, rather than one. Repeat after metadata updates, repeated MRI reconciles and a controller restart. Retain the positive child counts. If a live defaulter/controller restores a parent value, stop: adjust that active lab defaulting path or implement the required KAITO change before activation.
4. Check the installed child InferenceSet `/scale` endpoint and HPA RBAC. The [baseline CRD](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/config/crd/bases/kaito.sh_inferencesets.yaml) declares `spec.replicas`, `status.replicas` and `status.selector`, but the live API must expose and populate them correctly. Before KEDA activation, test an operator-controlled positive scale increase, confirm repeated MRI reconciles do not revert it, and wait for serving readiness. Do not overlap that test writer with an HPA.

The result is a manually established external-writer arrangement using the existing nil guard, **not** the proposal's implemented `managed` mode. If nil cannot be preserved, stay observation-only; there is no annotation that fixes two competing replica writers.

### 0.3 Configure existing child annotations, not invented parent APIs

For this lab only, manually configure the **top-level `metadata.annotations` of each child InferenceSet**, not its Workspace template. The pinned [annotation constants](https://github.com/kaito-project/keda-kaito-scaler/blob/3964e100f0093ec609b663704e726f2bb3fe8fd9/pkg/constants/constants.go) and [metric parser](https://github.com/kaito-project/keda-kaito-scaler/blob/3964e100f0093ec609b663704e726f2bb3fe8fd9/pkg/scaledobject/provisioner.go) already support the following keys. The example is an annotation fragment, **not a complete object or a runnable unmodified-install recipe**:

```yaml
metadata:
  annotations:
    scaledobject.kaito.sh/auto-provision: "false" # change only after activation gates pass
    scaledobject.kaito.sh/min-replicas: "1"
    scaledobject.kaito.sh/max-replicas: "3" # illustrative: MUST be >= the live child count
    scaledobject.kaito.sh/metrics: |
      - name: vllm:num_requests_waiting
        type: gauge
        source: modelpod
        upthreshold: 2
        downthreshold: 1
```

This is the **prefill** fragment. For the **decode** child, use `name: vllm:num_requests_running` instead, with separately calibrated thresholds. The example numbers only exercise the parser; they are not recommended capacity targets. For `source: modelpod`, `type: gauge` defaults to `service-avg` in the current parser; the supported explicit equivalent is `aggregation: service-avg`. Keep this aggregation fixed for the narrow demo. Both thresholds are required by the existing positive-minimum parser; their presence does **not** authorize downscale in this demo. Validate `0 <= downthreshold < upthreshold`, positive bounds and a maximum no smaller than the current count before enabling either role.

The baseline MRI `CreateOrUpdate` updates selected child metadata entries and the template, rather than replacing the child's top-level annotation map, which suggests these scaler annotations can survive. **Verify it** across repeated parent reconciles and restarts, including unchanged Workspace template hashes and no model rollout caused by autoscaling-only edits. If the deployed path removes/replaces these annotations or rolls models, a small KAITO projection/preservation change is required; do not paper over this with a script that continually fights the controller.

Keep `auto-provision: "false"` until the custom scaler gates below pass. Then enable the two roles deliberately, one at a time. The existing annotations configure scaling; a separate lab feature gate/UID allowlist authorizes this experiment. Do not claim the proposal's parent role-policy annotation is already supported, or introduce a new public policy spelling for this shortcut.

### 0.4 Focused scaler changes that cannot be skipped

1. **Explicit MRI authorization, not only a predicate edit.** The current auto-provision predicates exclude MRI children. Add an opt-in path without changing standalone behavior. At reconciliation **and metric serving**, verify the controller-owner API group/kind/name/UID, live same-namespace nonterminating parent UID, persisted nil parent replicas, exact P/D role membership and intended child UID. A matching name suffix/label is insufficient. Revalidate on resync and before activation; parent replacement, role changes or missing authorization block decisions. A ScaledObject watch can enqueue reconciliation without the child predicate, so the checks must live inside the handler too. Add the needed MRI read/watch permission, and ensure the lab gate blocks recreation during shutdown.
2. **One SO/HPA pair per role, no competing writers.** Reject activation if any other ScaledObject/HPA targets the child; never adopt or delete a foreign one. Keep parent/child/SO/HPA UIDs and owner chains for later cleanup. The scaler supplies metrics/configuration only; HPA alone performs recurring child `/scale` writes after bootstrap.
3. **Strict complete role-local metrics.** Replace the legacy partial-success averaging for opted-in children only. Snapshot the verified role's child/Workspace/endpoint membership, require desired-count and readiness agreement, and hold decisions on pending/terminating/rollout/membership changes rather than choosing a partial ready subset. Require each expected endpoint to return the correct nonnegative finite **gauge**, with known engine/rank cardinality and no duplicate global series. Missing series, timeout, malformed response, NaN/Inf, stale samples or incomplete coverage mean unavailable/error, **not zero** or an average of survivors. Keep prefill waiting and decode running entirely separate. Scope caches by object UIDs, role, configuration and membership epoch; invalidate known failures and old in-flight refreshes. Bound every sample's age (at most two collection intervals) and cross-endpoint skew. A present numeric zero is valid only after all these checks.
4. **Verify the actual decode metrics route.** The [Workspace Service](https://github.com/kaito-project/kaito/blob/4c450c328a21047f7fa576780a086cc1a393cc95/pkg/workspace/manifests/manifests.go) is `80 -> 5000`; decode's routing sidecar listens on `5000` and the engine on `5001`. The MRI controller explicitly intends `/metrics` proxying through that sidecar. From the scaler's network context compare the real Service/sidecar response with the engine response for the pinned runtime, including names, TYPE, cardinality and failure propagation. **Do not blindly scrape Service port 5001**: the engine container port does not imply a Service port exists. If proxying is broken, fix it or add a controlled role-aware metrics Service/targetPort, then repeat validation.
5. **Enforce scale-up-only beyond one YAML field.** Generate `advanced.horizontalPodAutoscalerConfig.behavior.scaleDown.selectPolicy: Disabled` on each SO, verify it reaches the live HPA, and include `SelectPolicy` in drift comparison/repair (the baseline comparison omits it). Use bounded scale-up increments. HPA can clamp an above-max replica count **before** scale-down behavior normalization, so activation and every bounds update must reject `maxReplicas < current replicas`; retain a safe last-applied bound on rejection. Protect the child/SO/HPA from out-of-band writers with lab RBAC/admission and recheck live counts before applying bounds. A preflight check alone is not protection against concurrent writers. If safe writer/bounds enforcement cannot be established, remain observation-only.
6. **Exclude bypasses.** No scale-to-zero, fallback, idle replicas, restore-to-original-replica-count, replica-setting pause annotations or automatic drain/downscale. Reject or remove these fields only on positively identified demo-owned objects, and detect drift. Keep replicas positive throughout activation. Metric failures must reach KEDA as unavailable; they must not invoke a fallback or synthetic low signal.

### 0.5 Bring-up and acceptance: what “basically working” must mean

Implement and unit-test the narrow changes first, then run in this order: install/defaulting check → positive fixed P/D serving baseline → nil-parent ownership check → annotation preservation → strict observation-only metrics → one-role activation → two-role scale-up → failure injection → manual shutdown. Do not enable the HPA while still debugging replica ownership or scrape coverage.

Record the following acceptance evidence, not just created Kubernetes objects:

- [ ] Both parent role replicas are persisted absent/nil across API readback, unrelated updates, repeated MRI reconciles and controller restart; positive child counts are preserved.
- [ ] Supported child annotations survive reconciliation, and autoscaling-only edits cause no Workspace template change/model rollout. The live `/scale` contract and permissions work.
- [ ] Each role has exactly one authorized SO/HPA pair. An HPA-driven child increase survives repeated MRI reconciles; the scaler never writes replicas directly.
- [ ] Separate long-input/short-output and short-input/long-output load profiles, with cold/unique prefixes as needed, demonstrate the intended **distinct** prefill-waiting and decode-running signals. Record both roles' metric samples and decisions; do not infer independence just from two HPAs existing.
- [ ] Newly added Workspaces become Ready **and actually receive routed inference work / participate in P/D KV transfer**. Capture routing/engine logs or equivalent request evidence and successful responses, not only pod readiness.
- [ ] Failed endpoints, missing series, partial coverage, stale caches and readiness/membership changes freeze the affected role's decision and surface unavailable, never a synthetic zero or reduced-denominator average. No stale sample crosses child recreation or role boundaries.
- [ ] Low load does not decrease either child count; live HPA `scaleDown` remains Disabled after drift reconciliation. A requested maximum below the live count is rejected without modifying the safe live bound. Unsupported replica-changing KEDA settings are rejected.
- [ ] Manual shutdown below proves SO **and** HPA absence before any fixed parent replica value is restored. Repeat with KEDA unavailable: handoff must remain blocked, not optimistically succeed.

### 0.6 Manual safe exit and deliberately deferred work

For this disposable lab, the operator replaces the full lifecycle/status state machine:

1. Stop load and **disable new activation/recreation first** using the lab gate; set child auto-provision annotations false and verify the scaler cannot recreate the demo SOs. Do not write parent replicas yet. Preserve recorded UIDs/owner chains and cleanup access even when activation is disabled.
2. Remove only the positively identified demo-owned ScaledObjects (UID-preconditioned deletion). Confirm each SO is absent **and its KEDA-owned HPA is absent**, and check no other writer targets the child. A successful Delete call, a deletion timestamp, or an unavailable KEDA operator is not proof of release. If KEDA is unavailable or cleanup stalls, stop here; do not hand off replicas.
3. Only after both pairs are absent, restore explicit positive parent role counts, normally equal to the current child counts so handoff itself does not downscale. Verify MRI now maintains those fixed counts. Any later lab teardown is a separate operator action, not an autoscaling/drain demonstration.

Mode-aware admission, full parent policy validation/projection, durable accepted-policy/status reporting, automatic disable/delete/restart handoff, compatibility migration and drain-aware downscale remain in the full plan below. This manual shortcut deliberately does not implement those guarantees. **This document is still a plan, not a tested implementation: basic functionality cannot be guaranteed until the real-cluster acceptance checklist passes.**

## 1. Recommendation

Implement the POC in three stages:

1. **Observation-only:** validate policy, resolve ownership and collect strict role-local metrics, without changing replicas.
2. **Guarded scale-up-only:** enable independent prefill/decode expansion after proving admission, ownership and metric correctness.
3. **Drain-aware bidirectional scaling:** a later milestone, blocked on a verified request/KV-transfer drain protocol.

The first usable POC should demonstrate:

> Each role can scale out independently with an explainable decision; incomplete or stale metrics do not become a low-load signal; the system can relinquish replica ownership safely.

Do not label the scale-up preview as production-ready bidirectional autoscaling.

## 2. Initial Scope

| Area | POC decision |
|---|---|
| Topology | One MRI with exactly one prefill role and one decode role |
| Scaling unit | Number of Workspaces in each role's InferenceSet |
| Per-replica topology | Initially one GPU node per Workspace, with a fixed supported tensor-parallel configuration |
| Prefill signal | Native `vllm:num_requests_waiting` gauge |
| Decode signal | Native `vllm:num_requests_running` gauge |
| Aggregation | Independent, complete-coverage `service-avg` for each role |
| Bounds | Explicit positive minimum and maximum; no scale-to-zero |
| Controller path | One ScaledObject and one HPA per managed role |
| Monitoring dependency | Direct metrics collection through the KAITO scaler; Prometheus is not required |
| First automated action | Scale up only, with bounded increments |

Explicitly defer:

- Automatic scale-down until drain is proven.
- Changing tensor parallelism or per-Workspace hardware while scaling.
- TTFT/ITL histograms, tail-latency targets, KV-cache utilization and EPP metrics as scaling inputs.
- Arbitrary user-supplied HPA templates, fallback replicas and scale-to-zero.
- A generalized policy engine or broad controller refactoring.

For the full managed-mode implementation in sections 1–9, use the versioned annotation policy and validation rules defined in the proposal. The separately scoped manual lab in section 0 uses existing child annotations instead; it does not introduce a second policy schema or treat proposed annotation/status fields as already implemented APIs.

## 3. Ownership and Control Flow

```text
MRI role policy
    |
    v
KAITO validates and projects accepted role policy
    |
    +--> prefill InferenceSet metadata --> ScaledObject --> HPA --> /scale
    |
    +--> decode InferenceSet metadata  --> ScaledObject --> HPA --> /scale
                                                               |
                                                               v
                                                  existing InferenceSet controller
                                                               |
                                                               v
                                                  Workspaces / nodes / model pods
```

KEDA means **Kubernetes Event-driven Autoscaling**. Here KEDA manages the HPA objects; the HPA is the recurring writer of a managed child InferenceSet's desired replicas. The scaler supplies metrics and provisions autoscaling configuration; it should not become an additional direct replica writer.

### Replica ownership modes

| Mode | Parent role replicas | Recurring replica owner |
|---|---|---|
| `fixed` | Explicit positive number | MRI controller |
| `managed` | Persisted nil, with an accepted managed policy | HPA provisioned by this integration |
| `external` | Persisted nil, with explicit external ownership intent | External controller/operator, not this integration |

An omitted role policy entry should preserve fixed-mode behavior. Existing objects with nil replicas must not be silently reinterpreted as managed. Bootstrap a new child to a safe positive replica floor before activating the ownership handoff; specify and test how this interacts with current replicas and configured bounds.

## 4. KAITO Implementation

### 4.1 Persist mode-aware admission and align CRDs first

Relevant areas:

- `api/v1alpha1/multiroleinference_types.go`
- `api/v1alpha1/multiroleinference_default.go`
- `api/v1alpha1/multiroleinference_validation.go`
- `pkg/workspace/webhooks/webhooks.go`
- `config/crd/bases/kaito.sh_multiroleinferences.yaml`
- `charts/kaito/workspace/templates/kaito.sh_multiroleinferences.yaml`
- Helm webhook/RBAC/certificate configuration and `Makefile` generation targets

The inspected Helm CRD unconditionally defaults role replicas to `1`, while the generated base CRD does not. This makes nil an unreliable ownership signal. The existing validating webhook and an in-memory call to `Default` are not sufficient to establish persisted mode-aware defaults.

Required changes:

1. Add strict parsing, semantic validation and canonicalization of the proposal's versioned role policy.
2. Remove the unconditional role-replica schema default and keep generated/base/Helm schemas aligned.
3. Register a real mutating admission path that persists fixed defaults while retaining nil for valid managed/external roles.
4. Extend webhook RBAC and certificate/CA-bundle handling for the new configuration.
5. Update the manifest-generation process: it currently does not copy the MRI CRD alongside the other generated CRDs.
6. Define migration handling for existing objects before managed activation; do not infer intended ownership solely from a legacy nil value.

Test with the **rendered Helm CRD**, not only the base YAML. A schema test that ignores the install artifact can miss this exact failure.

### 4.2 Project policy without rolling model pods

In `pkg/controllers/multiroleinference/controller.go`, `reconcileInferenceSet()` already avoids continuously overriding child replicas when role replicas is nil. Replace reliance on that isolated nil check with explicit accepted ownership-mode decisions.

The existing path copies MRI annotations into the child workload template. Autoscaling policy and internal lifecycle markers must not flow there indiscriminately.

- Put allowlisted scaler configuration on the child **InferenceSet metadata**.
- Filter management annotations out of the workload template.
- Persist an accepted policy digest and lifecycle identity for consistency checks.
- Ensure changing thresholds or polling settings does not cause a model rollout.
- Verify watch predicates enqueue metadata-only policy changes and cleanup transitions.

A digest is not authentication. The scaler must separately verify the real owner relationship and live parent policy.

### 4.3 Implement an acknowledged ownership transition

For managed to fixed/external transitions:

```text
Revoke managed activation
    -> retain ownership identity needed for cleanup
    -> request removal of owned ScaledObject
    -> confirm both owned ScaledObject and HPA are absent
    -> allow the new owner to control replicas
```

Issuing a delete request is not proof that the old replica writer is gone. Preserve enough identity to clean up after restarts, policy removal or feature-gate disablement. A disabled feature gate must not strand managed autoscaling resources.

If KEDA is unavailable or cleanup stalls, expose a pending/error condition instead of activating a second writer. If KEDA CRDs are absent, ordinary fixed MRI operation must still start successfully; avoid unconditionally registering informers for missing optional APIs.

### 4.4 Keep status ownership narrow

The MRI controller should remain the sole writer of MRI status. The scaler can publish narrowly scoped child observations, which MRI aggregates.

Expose enough information to diagnose:

- Accepted policy and current ownership mode.
- Current versus desired/ready replicas per role.
- Metric coverage/freshness and why a decision is unavailable.
- Missing dependencies, conflicting autoscalers and pending transitions.

Serving readiness and autoscaling readiness are different conditions. A serving role can be healthy while scaling is paused because metrics are incomplete.

## 5. keda-kaito-scaler Implementation

### 5.1 Add an authorized managed-MRI path

Relevant areas:

- `pkg/controllers/autoprovision/auto_provision_controller.go`
- `pkg/scaledobject/provisioner.go`

Do not implement support by merely removing the predicate that excludes MRI children. Reconciliation itself must validate:

- The child controller owner reference, including API group, name and UID.
- The live parent's role membership and accepted policy.
- The persisted mode and nil-replicas ownership contract.
- Lifecycle/accepted-policy identity matching the projected child configuration.
- Absence of foreign HPA or ScaledObject owners targeting the same child.

Leave the existing standalone InferenceSet path unchanged. Only clean up resources that positively match this integration's ownership identity; do not delete foreign autoscalers.

### 5.2 Build a strict metric path, not permissive partial averaging

Relevant areas:

- `pkg/metricsource/modelpod_source.go`
- `pkg/aggregator/service_avg_aggregator.go`
- `pkg/scaler/metric_cache.go`

The inspected legacy aggregation path can skip failed Service scrapes or reduce missing data to zero. That behavior is not a suitable contract for managed P/D decisions.

For each role, require:

1. An owner-verified expected Workspace/Service membership set.
2. Desired/ready/member state consistent enough to permit a decision.
3. A valid sample from every eligible member; no partial average.
4. Presence of the requested gauge, with defined series/cardinality rules.
5. Finite, nonnegative values and the expected metric type.
6. Per-sample freshness, initially bounded by twice the configured polling interval.
7. A coherent collection epoch, invalidated when policy or membership changes.

Preserve metric type and label information before parsing discards it. Keep independent role caches and key them by object UID, role, accepted policy and membership identity. Invalidate known failed refreshes and discard late updates from an older identity/epoch.

Missing, stale, NaN, wrong-type or failed data should produce **unavailable**, not zero or an average of surviving members. Propagating a metric error is necessary, but it does not by itself prevent HPA's independent min/max corrections.

### 5.3 Verify the actual metrics endpoint

The inspected Workspace Service exposes port `80` targeting `5000`. KAITO's decode configuration documents a routing sidecar on `5000` that proxies `/metrics` to the vLLM engine on `5001`.

Validate this with the pinned runtime and sidecar images before changing scraping:

- Prefill Service returns the expected prefill runtime gauges.
- Decode Service returns the actual decode engine gauges through the proxy.
- Values and metric identity agree with a direct engine observation.
- The contract remains correct after scaling and membership changes.

Do not simply point Service scraping at `5001`: the current Service does not expose that port. Add a dedicated metrics Service only if actual endpoint verification establishes that it is needed.

### 5.4 Make scale-up-only genuinely constrained

Reuse the existing conservative multi-metric formula and per-period replica-increase limit where suitable. In the preview, low metrics mean hold rather than a scale-down multiplier.

The generated HPA behavior should include:

```yaml
scaleDown:
  selectPolicy: Disabled
```

Also update drift detection: the inspected comparison logic does not include `SelectPolicy`, so changing only the builder may fail to repair an existing object.

**Important:** HPA may clamp `currentReplicas > maxReplicas` before applying normal scale-down behavior. `Disabled` alone is not a complete no-downscale guarantee.

Therefore:

- Reject preview activation or bound changes that put max below current replicas.
- Keep an accepted safe configuration when a new one is invalid.
- Reject fallback, idle replicas, restore-original-replicas and pause settings that write a replica count.
- Detect conflicting external writers and preserve the single-writer assumption.
- Verify KEDA/HPA behavior on the chosen Kubernetes version in a real test cluster.
- Stay observation-only whenever these preconditions cannot be established.

## 6. Implementation Milestones

### A. Admission, policy and schema consistency

Deliver parser/defaulting/validation tests, generated CRD alignment, mutating admission plumbing and compatibility/migration cases. Prove persisted read-back behavior for fixed, managed and external modes.

### B. Policy projection and ownership lifecycle

Deliver metadata projection/filtering, status aggregation, conflict handling and restart-safe transitions. Prove policy-only updates do not roll workloads and that new replica ownership is not granted before old writers disappear.

### C. Strict metrics and observation-only integration

Use fake HTTP endpoints and synthetic membership to exercise role isolation, metric typing, cardinality, completeness, freshness and cache invalidation. Render the intended autoscaling objects without activating replica writes in observation-only mode.

### D. Guarded scale-up-only GPU POC

Activate one HPA per role after all prerequisites pass. Start with spare node capacity so infrastructure provisioning delay does not obscure scaling correctness. Test node auto-provisioning separately afterward.

Use two load profiles:

- Long prompts with short responses to emphasize prefill demand.
- Short prompts with long responses to emphasize decode demand.

These are experimental controls, not a promise that the two pipeline stages are physically independent. Record both roles' actual signals, bottlenecks and decisions.

### E. Later drain-aware scale-down

Do not enable bidirectional operation until a candidate replica can:

1. Stop receiving new request assignments and new KV-transfer placements.
2. Continue existing requests and transfers.
3. Report verifiable completion or a defined timeout/failure outcome.
4. Pass a final ownership/readiness check before deletion.

Low average queue depth, SIGTERM handling or a Pod termination grace period alone does not establish this protocol. The existing direct Workspace deletion path must be integrated with a real drain acknowledgment.

## 7. Validation and Acceptance Matrix

| Test | Required outcome |
|---|---|
| Rendered Helm CRD plus admission | Managed/external nil survives persisted read-back; fixed defaults remain explicit |
| Threshold-only policy edit | No StatefulSet/model rollout |
| Prefill versus decode load | Role-local metrics and decisions are independently observable |
| One or all endpoint failures | No partial average or synthetic zero; scaling decision unavailable |
| Missing/wrong-type/NaN/stale metric | Rejected as invalid input, with an actionable reason |
| Parent recreation or membership change | Old cache samples and late responses cannot be reused |
| Controller/scaler restart | Accepted ownership and pending cleanup recover without a second writer |
| Foreign HPA or ScaledObject | Conflict reported; foreign resource is not adopted or deleted |
| KEDA absent | Fixed MRI still works; managed activation remains blocked |
| Managed policy removal/disable | Owned ScaledObject and HPA are gone before replica ownership transfers |
| Preview max below current replicas | Rejected without introducing an implicit shrink |
| Low-load preview | No automatic downscale, including independent HPA/KEDA paths |
| Provisioning delay | No runaway expansion while expected replicas are not ready |

Use unit tests and envtest for parsing, admission and controller object behavior. Envtest does not provide a real HPA controller, KEDA reconciliation or Kubernetes garbage collection, so it cannot prove the full cleanup/no-downscale contract. Those checks require a disposable integration cluster.

For the GPU experiment, record policy digests, child desired/ready counts, ScaledObject/HPA state, metric coverage/age, generation/token latency and request errors. Treat performance claims as unproven until measured.

## 8. Suggested Patch Series

1. **KAITO:** policy types/parser, persisted admission and CRD-generation consistency.
2. **KAITO:** policy projection, ownership state machine, status and focused tests.
3. **Scaler:** verified managed-child path, strict metrics and cache identity.
4. **Scaler:** preview builder/drift fixes, safe lifecycle cleanup and integration harness.
5. **Examples/docs:** pinned manifests, load profiles, failure injection and measured results.

Before implementation, select the supported Kubernetes/KEDA/runtime versions, initial bounds and thresholds, and a disposable GPU test environment. Keep unknown endpoint or drain behavior visible as a blocker rather than hiding it behind optimistic defaults.

## 9. Rollback and Downgrade

To roll back the integration, transition roles to fixed ownership using the new compatible controllers and wait for managed ScaledObjects and HPAs to disappear. Persist explicit fixed replicas before downgrading KAITO.

External mode is only a rollback option while retaining a KAITO version that understands and preserves that ownership contract. Do not downgrade to an older controller that may restore replicas to `1` or overwrite externally managed values.

A safe rollback is an observed ownership transition, not just removal of annotations or uninstalling the scaler.
