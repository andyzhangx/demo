# KubeCon North America 2026 — CFP Submission

---

## Title

**Disaggregating LLM Inference on Kubernetes: Prefill/Decode Separation with KAITO and llm-d**

*(alternate: "From Monolith to Disaggregated: How We Split LLM Prefill and Decode on Kubernetes with Zero User Complexity")*

---

## Session Type

Conference Session (35 min)

## Track

AI + ML + Intelligent Apps / Runtime

## Level

Intermediate

---

## Abstract (max 900 characters)

Large language models like DeepSeek-V3 waste GPU resources when prefill (compute-bound) and decode (memory-bound) run on the same nodes. Prefill/Decode (P/D) disaggregation solves this by splitting these phases onto dedicated GPU pools — but the infrastructure complexity is brutal: custom routing, KV cache transfer, sidecar orchestration, and independent autoscaling.

We'll show how KAITO's new MultiRoleInference CRD turns this into a single 20-line YAML. Under the hood, it orchestrates llm-d routing sidecars, Gateway API InferencePools, NixlConnector KV cache transfer, and KEDA-based per-role autoscaling — all Kubernetes-native, no NATS, no etcd, no custom service mesh.

We'll demo live P/D disaggregation on a multi-node cluster, show real latency improvements, and explain the architecture decisions that made this work with zero changes to vLLM, zero user-facing sidecars, and zero platform lock-in.

---

## Description / Extended Abstract

### The Problem

LLM inference has two distinct phases:
- **Prefill**: processes the entire prompt in parallel (compute-bound, high GPU utilization)
- **Decode**: generates tokens one at a time (memory-bound, low GPU utilization)

Running both phases on the same GPU pool means prefill bursts starve decode latency, and decode idle time wastes expensive compute. Production deployments (DeepSeek, Meta, etc.) solve this with P/D disaggregation — but existing solutions require:
- Custom routing infrastructure (Dynamo uses NATS + etcd)
- Platform-specific GPU dependencies (NVIDIA-only)
- Manual sidecar configuration and KV cache plumbing
- Deep expertise in distributed inference internals

### Our Solution: MultiRoleInference CRD

KAITO (Kubernetes AI Toolchain Operator) introduces a `MultiRoleInference` CRD that abstracts all of this:

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

From this single resource, the controller automatically creates:
1. **Separate InferenceSets** for prefill and decode with `inference-role` labels
2. **Gateway API InferencePool** selecting all workspaces via Kubernetes-native CRDs
3. **llm-d EPP (Endpoint Picker Plugin)** with P/D-aware routing using `disagg-profile-handler` and `by-label-selector`
4. **Routing sidecars** injected into decode StatefulSets by the Workspace controller
5. **NixlConnector KV cache transfer** between prefill and decode pods (RDMA/TCP)
6. **KEDA autoscaling** with independent metrics per role

### Why llm-d over Dynamo?

We evaluated both NVIDIA Dynamo and llm-d for the routing layer. We chose llm-d because:
- **Kubernetes-native**: built on Gateway API / Inference Extension (K8s SIG direction)
- **Loosely coupled sidecar model**: no central coordinator, no NATS/etcd dependency
- **Hardware neutral**: works with NVIDIA GPU, Intel XPU, Google TPU
- **Pure Go**: consistent with the Kubernetes ecosystem
- **Extensible plugin system**: custom scorers, filters, and routing strategies

(Full comparison: https://github.com/kaito-project/kaito/pull/1995)

### Key Architecture Decisions

1. **Request always hits decode sidecar first** — EPP selects a decode pod, the sidecar decides whether to offload prefill based on cache hit rate and prompt length
2. **Sidecar injection via Workspace controller** — when `inference-role: decode` label is present, the controller includes the routing sidecar in the StatefulSet spec (no mutation webhooks, no extra infrastructure)
3. **Shared InferencePool for both roles** — `by-label-selector` plugin filters pods by role at routing time, avoiding duplicate pool management
4. **CEL validation** on the CRD ensures exactly one prefill + one decode role

### Live Demo Plan

1. Deploy a MultiRoleInference resource for a large model
2. Show the controller creating separate prefill/decode workspaces
3. Send concurrent requests and visualize P/D routing decisions in real-time
4. Compare latency: monolithic vs disaggregated (expect 30-50% TTFT improvement for long prompts)
5. Demonstrate independent autoscaling — scale prefill under load while decode stays stable

### Takeaways for Attendees

- How P/D disaggregation works and when it matters (not always!)
- How to extend Gateway API for AI-specific routing patterns
- Practical patterns for injecting infrastructure sidecars without webhooks
- How to evaluate Dynamo vs llm-d for your own stack
- The path from single-CRD UX to complex multi-resource orchestration in Kubernetes

---

## Benefits to the Ecosystem

This talk demonstrates:
- A real-world application of **Gateway API Inference Extension** (SIG-Network)
- How **KAITO** (CNCF Sandbox) enables advanced inference patterns without platform lock-in
- Patterns for building Kubernetes operators that manage complex distributed AI workloads
- Integration between **llm-d** (an open community project by Red Hat + IBM) and the K8s ecosystem
- How KEDA can be extended for AI-specific autoscaling metrics

---

## Speaker Bio

**Andy Zhang** — AKS Engineer at Microsoft, contributor to KAITO (Kubernetes AI Toolchain Operator, CNCF Sandbox), Kubernetes CSI drivers, and Azure Kubernetes Service. Focused on making GPU-accelerated AI workloads first-class citizens in Kubernetes. Co-designer of the MultiRoleInference CRD and the KAITO/llm-d integration for P/D disaggregated inference.

---

## Tags / Keywords

`kubernetes`, `llm-inference`, `gpu`, `prefill-decode-disaggregation`, `gateway-api`, `kaito`, `llm-d`, `vllm`, `kv-cache`, `autoscaling`, `cncf`

---

## Notes

- PR with full design: https://github.com/kaito-project/kaito/pull/1991
- Dynamo vs llm-d comparison: https://github.com/kaito-project/kaito/pull/1995
- KAITO project: https://github.com/kaito-project/kaito
- llm-d: https://github.com/llm-d/llm-d-inference-scheduler
- Gateway API Inference Extension: https://github.com/kubernetes-sigs/gateway-api-inference-extension
