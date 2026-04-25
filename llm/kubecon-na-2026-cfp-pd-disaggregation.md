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

LLM inference has two phases with very different resource profiles: prefill is compute-bound, decode is memory-bound. Running both on the same GPU pool wastes resources and hurts latency. Prefill/Decode (P/D) disaggregation splits them onto dedicated pools — but wiring up intelligent routing, KV cache transfer, sidecar orchestration, and per-role autoscaling is complex.

We'll show how KAITO's MultiRoleInference CRD and llm-d inference scheduler make this a single 20-line YAML on Kubernetes. Built entirely on Gateway API Inference Extension, the system uses llm-d's EPP plugin chain for P/D-aware routing, NixlConnector for zero-copy KV cache transfer, and KEDA for independent prefill/decode autoscaling — all Kubernetes-native, all open source.

---

## Description (max 1000 characters)

LLM inference has two phases with opposite resource profiles: prefill is compute-bound, decode is memory-bound. Running both on the same GPU pool wastes resources and hurts latency. P/D disaggregation fixes this — but the infrastructure complexity is brutal.

KAITO's new MultiRoleInference CRD makes it declarative: specify a model and two roles (prefill + decode), and the controller orchestrates everything. Built on llm-d and Gateway API Inference Extension, it uses llm-d's EPP plugin chain for intelligent P/D routing, NixlConnector for zero-copy KV cache transfer between pods, routing sidecars auto-included in decode StatefulSets, and KEDA per-role autoscaling — prefill scales on queue depth, decode on KV-cache utilization. All Kubernetes-native, all open source.

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
