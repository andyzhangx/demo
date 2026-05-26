# KubeCon North America 2026 — CFP Submission

---

## Title

**Prefill Here, Decode There: Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d**

<details>
<summary>Alternate titles considered</summary>

- Scaling Disaggregated LLM Inference on Kubernetes: KAITO + llm-d + Gateway API
- One CRD, Two GPU Pools: Disaggregated LLM Inference with KAITO
- Split the GPU, Not the YAML: P/D Disaggregated Inference on Kubernetes
- Beyond Single-Pod Inference: Building a P/D Disaggregation Stack with Gateway API, llm-d, and KEDA
- Your LLM Prefill Is Starving Your Decode: Fixing It with KAITO and llm-d on Kubernetes
- KAITO + llm-d: Declarative Prefill/Decode Disaggregation on Kubernetes
- From 20 Lines of YAML to Disaggregated DeepSeek: A KAITO + llm-d Journey
</details>

---

## Session Type

Conference Session (35 min)

## Track

AI + ML + Intelligent Apps / Runtime

## Level

Intermediate

---

## Abstract (max 900 characters)

LLM inference has two phases with very different resource profiles: prefill is compute-bound and latency-sensitive, decode is memory-bandwidth-bound and throughput-sensitive. Running both on the same GPU pool forces a compromise — over-provisioning for prefill spikes wastes decode capacity, and vice versa.

P/D disaggregation fixes this, but existing approaches (NVIDIA Dynamo, llm-d standalone) require extensive manual wiring: topology-aware routing, KV cache transfer protocols, sidecar lifecycle management, and per-role autoscaling. KAITO introduces MultiRoleInference — a higher-level Kubernetes abstraction that composes llm-d's routing and Gateway API Inference Extension into a single declarative CRD.

We'll present the motivation for this layered approach vs. Dynamo/llm-d alone, share eval data comparing P/D vs. colocated serving (TTFT, throughput, GPU utilization), and demonstrate KEDA-driven autoscaling for each role independently.

---

## Description (max 1000 characters)

The problem: P/D disaggregation improves LLM serving efficiency by 30-60% on prefill-heavy workloads, but the infrastructure complexity is brutal — routing sidecars, NIXL KV transfer configuration, ZMQ discovery, port management, label-based scheduling profiles, and independent autoscaling all need correct orchestration.

Existing solutions: NVIDIA Dynamo provides a Python-native disaggregation runtime but is tightly coupled to NVIDIA's stack and not Kubernetes-native. llm-d offers Kubernetes-native P/D routing via Gateway API, but requires manual StatefulSet configuration, sidecar injection, and environment variable plumbing.

KAITO's MultiRoleInference CRD bridges this gap: it is an opinionated, declarative layer that orchestrates llm-d components automatically. One CRD generates prefill/decode StatefulSets with correct port assignments, NIXL side-channel env vars, sidecar injection (decode-only), InferencePool with proper targetPort, EPP plugin chain configuration, and KEDA ScaledObjects per role.

We'll show eval data: TTFT reduction, throughput gains, and autoscaling behavior under mixed workloads.

---

## Benefits to the Ecosystem

Attendees will learn:

1. **A layered abstraction for complex inference topologies** — How KAITO's MultiRoleInference CRD composes Gateway API InferencePool, llm-d EPP plugins, and vLLM NIXL into one declarative interface. Why this matters as topologies grow (E/P/D, speculative decoding, MoE).

2. **When to use P/D disaggregation (with data)** — Eval results: TTFT reduction (40-60% for long prompts), throughput gains (2-3x under prefill-heavy load), GPU utilization improvements, and break-even analysis by prompt length.

3. **How to autoscale P/D independently** — KEDA with role-specific metrics: prefill scales on queue depth, decode on KV-cache utilization. Live demo of asymmetric scaling under bursty traffic.

4. **KAITO vs Dynamo vs llm-d standalone** — Dynamo is Python-native/NVIDIA-coupled; llm-d is K8s-native but manual; KAITO adds a declarative CRD layer with built-in KEDA autoscaling, vendor-neutral GPU support, and single-CRD multi-model management.

5. **Production lessons** — NIXL side-channel pitfalls, sidecar placement constraints, port assignment rules, and startup ordering from running P/D on AKS.

All components are open source: KAITO (CNCF Sandbox), llm-d, Gateway API Inference Extension (K8s SIG), KEDA (CNCF Graduated).

---

## Talk Outline (35 min)

1. **The Problem** (5 min)
   - Why prefill and decode fight for the same GPU
   - Real production traces showing interference patterns
   - Cost of over-provisioning vs. latency degradation

2. **Landscape: How Others Solve It** (5 min)
   - NVIDIA Dynamo: Python-native, tightly coupled
   - llm-d standalone: K8s-native but manual
   - Why Kubernetes needs a higher-level abstraction

3. **KAITO MultiRoleInference Design** (8 min)
   - The CRD spec and what it generates
   - How it composes llm-d, Gateway API, and NIXL
   - Key design decisions: decode-only sidecar, port conventions, label contracts

4. **Live Demo** (10 min)
   - Deploy a model with P/D disaggregation (single YAML)
   - Show NIXL KV transfer in action (real-time metrics)
   - Trigger load spike → watch KEDA scale prefill independently
   - Compare latency: P/D vs. colocated baseline

5. **Eval Data & When to Use P/D** (5 min)
   - TTFT, throughput, utilization benchmarks
   - Break-even analysis by prompt length
   - Cost comparison (fewer total GPUs needed)

6. **What's Next** (2 min)
   - E/P/D (multimodal encode disaggregation)
   - Speculative decoding integration
   - Cross-node RDMA optimization

---

## Speaker Bio

**Andy Zhang** — Senior Software Engineer at Microsoft, AKS team. Maintainer of KAITO (CNCF Sandbox). Focused on Kubernetes-native AI infrastructure, GPU scheduling, and inference optimization. Previously spoke at KubeCon EU 2024 on KAITO.

**Linbo He** — [Bio TBD]

---

## Tags / Keywords

`kubernetes`, `llm-inference`, `gpu`, `prefill-decode-disaggregation`, `gateway-api`, `kaito`, `llm-d`, `vllm`, `kv-cache`, `autoscaling`, `keda`, `cncf`, `nixl`, `dynamo`

---

## References

- KAITO project: https://github.com/kaito-project/kaito
- MultiRoleInference design: https://github.com/kaito-project/kaito/pull/1991
- llm-d inference scheduler: https://github.com/llm-d/llm-d-inference-scheduler
- llm-d disaggregation docs: https://github.com/llm-d/llm-d-router/blob/main/docs/disaggregation.md
- Gateway API Inference Extension: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- KEDA KAITO scaler: https://github.com/kaito-project/keda-kaito-scaler
- NVIDIA Dynamo: https://github.com/ai-dynamo/dynamo
- NIXL (NVIDIA Inference Xfer Library): https://github.com/ai-dynamo/nixl
- P/D working config (our verified setup): https://github.com/andyzhangx/demo/blob/master/llm/pd-disaggregation/kaito/pd-working-config.md
