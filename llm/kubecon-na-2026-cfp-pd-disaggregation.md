# KubeCon North America 2026 — CFP Submission

---

## Title

**Scaling Disaggregated LLM Inference on Kubernetes: KAITO + llm-d + Gateway API**

*(alternate: "One CRD to Rule Them All: Prefill/Decode Disaggregated Inference with KAITO and llm-d")*

---

## Session Type

Conference Session (35 min)

## Track

AI + ML + Intelligent Apps / Runtime

## Level

Intermediate

---

## Abstract (max 900 characters)

LLM inference has two phases with very different resource profiles: prefill is compute-bound, decode is memory-bound. Running both on the same GPU pool wastes resources and hurts latency. Prefill/Decode (P/D) disaggregation splits them onto dedicated pools — but wiring up intelligent routing, KV cache transfer, sidecar orchestration, and per-role autoscaling is complex.

We'll show how KAITO's MultiRoleInference CRD and llm-d inference scheduler make this a single 20-line YAML on Kubernetes. Built entirely on Gateway API Inference Extension, the system uses llm-d's EPP plugin chain for P/D-aware routing, NixlConnector for zero-copy KV cache transfer, and KEDA for independent prefill/decode autoscaling.

Live demo: deploy disaggregated inference for a large model, visualize routing decisions in real-time, and show per-role autoscaling responding to load — all Kubernetes-native, all open source.

---

## Description / Extended Abstract

### The Problem

LLM inference has two distinct phases:
- **Prefill**: processes the entire prompt in parallel (compute-bound, benefits from high GPU parallelism)
- **Decode**: generates tokens autoregressively (memory-bound, benefits from optimized KV cache)

Co-locating both phases leads to resource contention: prefill bursts starve decode latency, and decode idle cycles waste GPU compute. P/D disaggregation addresses this by running each phase on dedicated GPU pools — but the infrastructure is hard to get right.

### KAITO + llm-d: Kubernetes-Native P/D Disaggregation

KAITO (Kubernetes AI Toolchain Operator, CNCF Sandbox) introduces a `MultiRoleInference` CRD that abstracts the full P/D stack:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v32
spec:
  model:
    name: deepseek-ai/DeepSeek-V3.2
  roles:
    - type: prefill
      replicas: 2
      instanceType: Standard_NC24ads_A100_v4
    - type: decode
      replicas: 3
      instanceType: Standard_NC24ads_A100_v4
```

From this single resource, the controller orchestrates:

**1. llm-d Routing via Gateway API Inference Extension**
- A shared InferencePool selects all prefill + decode workspaces
- llm-d's EPP (Endpoint Picker Plugin) runs a plugin chain:
  - `disagg-profile-handler`: decides whether prefill offloading is needed based on cache hit rate and prompt length
  - `by-label-selector`: filters pods by `inference-role` label (prefill vs decode)
  - `precise-prefix-cache-scorer` + `load-aware-scorer`: ranks candidates
  - `disagg-headers-handler`: sets `x-prefiller-host-port` header for decode sidecar coordination
- All routing runs as an Envoy ext-proc filter — no custom proxy, no service mesh changes

**2. KV Cache Transfer via NixlConnector**
- Prefill pods produce KV cache; decode pods consume it
- NixlConnector enables zero-copy transfer over RDMA or TCP
- Both roles run with `kv_role: kv_both` for bidirectional capability
- The decode sidecar coordinates the transfer: receives the prefill endpoint from EPP, triggers KV transfer, then starts decoding

**3. Sidecar Orchestration**
- The Workspace controller detects `inference-role: decode` on an InferenceSet and includes the llm-d routing sidecar directly in the decode StatefulSet spec
- No mutation webhooks, no injection controllers — the sidecar is a first-class container
- Sidecar receives requests on port 8080, orchestrates prefill if needed, then forwards to local vLLM

**4. Per-Role Autoscaling with KEDA**
- The MultiRoleInference controller propagates KEDA annotations to child InferenceSets
- Prefill and decode scale independently based on role-specific metrics:
  - Prefill: scale on queue depth / prompt processing latency
  - Decode: scale on KV cache utilization / concurrent generation sessions
- Each InferenceSet exposes a `/scale` subresource — standard KEDA ScaledObject integration
- Users configure scaling once at the MRI level; the controller handles per-role propagation

### Live Demo Plan

1. Deploy a MultiRoleInference resource for DeepSeek-V3.2
2. Watch the controller create separate prefill/decode InferenceSets, workspaces, InferencePool, and EPP
3. Send concurrent requests with varying prompt lengths
4. Visualize llm-d routing decisions: which requests get offloaded to prefill vs handled locally
5. Ramp up load → show KEDA scaling prefill replicas independently while decode stays stable
6. Compare TTFT (Time to First Token): monolithic vs disaggregated

### Takeaways for Attendees

- How P/D disaggregation works and when it provides real benefit (long prompts, high concurrency)
- How llm-d's plugin-based routing integrates with Gateway API Inference Extension
- Patterns for building Kubernetes operators that manage complex multi-resource AI workloads
- How to wire KEDA autoscaling for heterogeneous GPU workloads with different scaling signals
- The path from a single CRD user experience to a multi-component distributed system

---

## Benefits to the Ecosystem

- Real-world application of **Gateway API Inference Extension** (K8s SIG direction for AI routing)
- Demonstrates **KAITO** (CNCF Sandbox) enabling advanced inference patterns declaratively
- Shows **llm-d** (open community project) as a production-ready P/D routing layer on Kubernetes
- Patterns for **KEDA** integration with AI-specific autoscaling metrics
- All components are open source and vendor-neutral

---

## Speaker Bio

**Andy Zhang** — AKS Engineer at Microsoft, contributor to KAITO (Kubernetes AI Toolchain Operator, CNCF Sandbox), Kubernetes CSI drivers, and Azure Kubernetes Service. Focused on making GPU-accelerated AI workloads first-class citizens in Kubernetes. Co-designer of the MultiRoleInference CRD and the KAITO/llm-d integration for P/D disaggregated inference.

---

## Tags / Keywords

`kubernetes`, `llm-inference`, `gpu`, `prefill-decode-disaggregation`, `gateway-api`, `kaito`, `llm-d`, `vllm`, `kv-cache`, `autoscaling`, `keda`, `cncf`

---

## References

- KAITO project: https://github.com/kaito-project/kaito
- MultiRoleInference design: https://github.com/kaito-project/kaito/pull/1991
- llm-d inference scheduler: https://github.com/llm-d/llm-d-inference-scheduler
- Gateway API Inference Extension: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- KEDA KAITO scaler: https://github.com/kaito-project/keda-kaito-scaler
