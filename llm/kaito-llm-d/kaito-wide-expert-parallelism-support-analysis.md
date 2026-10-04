# KAITO Support Analysis for llm-d Wide Expert Parallelism

## Background

This note analyzes how KAITO relates to the deployment pattern described in llm-d's
[Multi-Node Wide Expert Parallelism](https://github.com/llm-d/llm-d/blob/main/docs/well-lit-paths/foundations/wide-expert-parallelism.md).

The short version:

> **KAITO already provides some of the routing and P/D-disaggregation building blocks needed by llm-d WideEP, but it does not yet expose Wide Expert Parallelism as a first-class deployment pattern.**

In particular, KAITO can already integrate with llm-d Router / EPP, provision separate prefill and decode roles, and enable NIXL-based KV transfer between them. However, the full llm-d WideEP deployment also depends on additional capabilities that KAITO does not yet productize today, such as multi-rank DP-aware target port exposure, WideEP-specific multi-node topology management, and DeepEP/RDMA-focused deployment plumbing.

---

## What llm-d WideEP Actually Requires

According to llm-d's architecture and deployment guide:

- llm-d WideEP is designed for very large **MoE** models such as DeepSeek-R1.
- The model server uses a **DP/EP** deployment shape:
  - **attention layers** run with **data parallelism (DP)**
  - **expert / MLP layers** run with **expert parallelism (EP)**
- The deployment is typically combined with **prefill/decode disaggregation**.
- The NVIDIA path depends on **DeepEP**, **NVSHMEM**, and **GPU-initiated RDMA**.
- llm-d's router / EPP is configured with a WideEP-specific plugin stack for role-aware scheduling.
- The llm-d guide exposes **multiple DP rank ports** (for example 8 ports for rank0-rank7), so the router can schedule across ranks rather than treating the pod as a single opaque endpoint.
- The llm-d deployment uses **DisaggregatedSet** and **LeaderWorkerSet**-style pod-group management to keep prefill and decode revisions aligned.

Useful references:

- llm-d WideEP concept doc: <https://github.com/llm-d/llm-d/blob/main/docs/well-lit-paths/foundations/wide-expert-parallelism.md>
- llm-d WideEP guide: <https://github.com/llm-d/llm-d/blob/main/guides/wide-ep/README.md>
- llm-d WideEP router values: <https://github.com/llm-d/llm-d/blob/main/guides/wide-ep/router/wide-ep.values.yaml>

---

## What KAITO Already Supports Today

### 1. llm-d Router / EPP integration

KAITO already integrates with the llm-d router gateway Helm chart for inference-aware routing.

Relevant code / docs:

- `website/docs/gateway-api-inference-extension.md`
- `pkg/utils/consts/consts.go`
- `pkg/workspace/manifests/manifests.go`

This means KAITO already has the basic control-plane path to create an InferencePool with an llm-d EPP deployment.

### 2. Prefill/decode disaggregation via MultiRoleInference

KAITO already supports **prefill/decode disaggregation** through `MultiRoleInference`.

Relevant docs / code:

- `website/docs/prefill-decode-disaggregation.md`
- `api/v1alpha1/multiroleinference_types.go`
- `pkg/controllers/multiroleinference/controller.go`
- `pkg/workspace/inference/preset_inferences.go`

When a `MultiRoleInference` is created, KAITO can already:

- create separate child workloads for **prefill** and **decode**
- inject the `llm-d-routing-sidecar` into decode pods
- set `VLLM_NIXL_SIDE_CHANNEL_HOST` to the pod IP
- create a single InferencePool / EPP deployment for role-aware scheduling

This is an important subset of the llm-d WideEP story, because llm-d WideEP is typically deployed together with P/D disaggregation.

### 3. Default P/D plugin pipeline with llm-d EPP

KAITO already auto-generates a default llm-d EndpointPickerConfig for MRI-based P/D serving.

Current default plugin path includes:

- `disagg-headers-handler`
- `approx-prefix-cache-producer`
- `prefix-based-pd-decider`
- `disagg-profile-handler`
- `by-label-selector` as prefill/decode filters
- `load-aware-scorer`
- `kv-cache-utilization-scorer`
- `max-score-picker`

This is useful because WideEP needs role-aware routing, and KAITO already has the basic EPP plumbing for that.

### 4. Custom EPP plugin override surface

KAITO already exposes `spec.eppPluginsConfig` on `MultiRoleInference`, allowing users to provide a custom ConfigMap with a raw llm-d EndpointPickerConfig.

This is the main escape hatch today for experimenting with plugin stacks closer to llm-d upstream guides.

---

## Where KAITO Still Falls Short for WideEP

### 1. KAITO's multi-node inference path is TP/PP-oriented, not WideEP-oriented

KAITO's current multi-node inference documentation describes a topology based on:

- **tensor parallelism (TP)** within a node
- **pipeline parallelism (PP)** across nodes
- **StatefulSet + Ray** as the distributed deployment mechanism

Reference:

- `website/docs/multi-node-inference.md`

This is a different model from llm-d WideEP, which is specifically about **DP/EP for MoE serving**.

So while KAITO supports multi-node vLLM inference in general, its current first-class multi-node path is **not** the same as llm-d WideEP.

### 2. MultiRoleInference only models two roles: prefill and decode

The current `MultiRoleInferenceSpec` is intentionally simple:

- one `prefill` role
- one `decode` role

That is sufficient for P/D disaggregation, but it does not natively model the additional topology assumptions that WideEP brings, such as:

- multi-node pod groups per role
- multi-rank DP-aware endpoint layout
- revision-consistent pairing semantics similar to `DisaggregatedSet`

In other words, MRI can express **role separation**, but not the full **WideEP deployment shape**.

### 3. KAITO does not currently expose multi-rank target ports the way llm-d WideEP does

This is one of the biggest functional gaps.

llm-d's WideEP router guide configures multiple `targetPorts` (for example rank0-rank7) so the EPP can route across DP ranks.

KAITO currently programs the InferencePool with **a single target port**, and its CRD/docs indicate that the current shape only supports one port definition.

That means KAITO does **not** yet have a first-class equivalent of llm-d's **DP-aware multi-port model-server exposure**.

This is a major blocker for clean WideEP parity.

### 4. KAITO does not currently productize DisaggregatedSet / LeaderWorkerSet-style topology management for this path

llm-d WideEP relies on a pod-group deployment model with stronger coordination semantics.

By contrast, KAITO's current docs still describe `LeaderWorkerSet` as a **future enhancement** for multi-node inference.

Reference:

- `website/docs/multi-node-inference.md`

This is another signal that KAITO is not yet at the same topology-management maturity as llm-d's WideEP deployment path.

### 5. KAITO does not yet expose WideEP-specific RDMA / DeepEP deployment plumbing as a productized API surface

llm-d's WideEP overlays include environment- and provider-specific settings such as:

- privileged container enablement
- RDMA/GPU resource claim plumbing
- GPU-to-NIC mapping (`DEEP_EP_DEVICE_TO_HCA_MAPPING`)
- UCX / NVSHMEM / RoCE tuning
- topology affinity tuned for accelerator + NIC locality

KAITO's current MRI surface exposes useful knobs such as:

- `instanceType`
- `runtimeConfig`
- `eppPluginsConfig`

But that is not the same thing as a complete, supported WideEP deployment API.

At best, users could manually approximate pieces of the configuration today; KAITO does not yet productize the full stack.

---

## Practical Conclusion

### What KAITO supports today

KAITO already supports the following **building blocks** that are relevant to llm-d WideEP:

- llm-d Router / EPP integration
- prefill/decode disaggregation
- NIXL-based KV transfer between prefill and decode
- custom EPP plugin configuration through `eppPluginsConfig`

### What KAITO does not yet support as a first-class feature

KAITO does **not** yet provide a clean, first-class implementation of llm-d's Wide Expert Parallelism deployment pattern, because it is still missing key pieces such as:

- DP/EP-oriented deployment semantics
- multi-rank DP-aware `targetPorts`
- `DisaggregatedSet` / `LeaderWorkerSet`-style topology management for this path
- WideEP-specific rollout and revision-gating behavior
- productized DeepEP / RDMA / GPU-NIC mapping configuration

### Best current characterization

A concise way to describe the current state is:

> **KAITO supports the llm-d routing and P/D-disaggregation foundations that WideEP builds on, but it does not yet support llm-d WideEP itself as a first-class deployment mode.**

---

## Recommended Next Steps for KAITO

If KAITO wants to support llm-d WideEP more directly, the roadmap likely needs to include the following items.

### 1. Support multi-port `targetPorts` in the InferencePool path

This is needed so EPP can route to per-rank endpoints instead of treating each pod as a single opaque model-server target.

### 2. Introduce a WideEP-aware multi-node topology abstraction

Either by adopting upstream constructs such as `LeaderWorkerSet` / `DisaggregatedSet`, or by providing an equivalent KAITO-native abstraction that captures:

- multi-node role groups
- rank-aware endpoint exposure
- revision consistency across roles

### 3. Extend MRI or add a new CRD mode for WideEP-specific role topology

Current MRI is focused on simple prefill/decode role separation. WideEP likely needs either:

- richer role topology under MRI, or
- a separate first-class API surface for WideEP

### 4. Productize DeepEP / RDMA deployment knobs

This includes provider-aware support for:

- privileged mode when required
- RDMA / DRA resource claims
- UCX / NVSHMEM env configuration
- GPU/NIC locality alignment

### 5. Add WideEP-specific llm-d EPP profile support

KAITO should eventually support a WideEP-oriented EPP configuration that can mirror llm-d upstream more closely, including:

- role-aware scheduling profiles
- revision gating / rollout safety
- rank-aware endpoint selection

---

## Bottom Line

If the question is **"Can KAITO already express the full llm-d WideEP design from `wide-expert-parallelism.md`?"**, the answer today is:

> **Not yet.**

If the question is **"Does KAITO already have some of the required pieces?"**, the answer is:

> **Yes — especially llm-d EPP integration, P/D disaggregation, and NIXL/KV-transfer-related plumbing.**

That makes WideEP support in KAITO a realistic future extension, but not something that is already fully productized today.
