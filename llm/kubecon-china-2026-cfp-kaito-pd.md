# KubeCon + CloudNativeCon China 2026 (Shanghai) — CFP Submission

---

## Title

**KAITO Meets llm-d: From One-Click Model Serving to Prefill/Decode Disaggregated Inference on Kubernetes**

<details>
<summary>Alternate titles considered</summary>

- One CRD to Serve Them All: Auto-Scaling and Disaggregated LLM Inference with KAITO
- From Model Name to Disaggregated Inference: KAITO's Journey to Production LLM Serving on Kubernetes
- KAITO: From Hugging Face Model to Prefill/Decode Disaggregated Inference on Kubernetes
- The Full Stack of Kubernetes-Native LLM Inference: GPU Provisioning, Autoscaling, and P/D Disaggregation
</details>

---

## Session Format

Session Presentation (30 minutes)

## Track

AI + ML

## Level

Any

---

## Description (max 1000 characters)

Deploying LLMs on Kubernetes demands expertise across GPU provisioning, runtime tuning, autoscaling, and distributed serving. KAITO (CNCF Sandbox) turns this into a single YAML.

This session covers KAITO end-to-end in three parts. First, model-aware automation: specify a Hugging Face model ID, and KAITO provisions GPU nodes via Karpenter, estimates GPU memory to choose optimal parallelism (tensor-parallel or multi-node pipeline-parallel), and exposes an inference endpoint. Second, production autoscaling: KEDA-based kaito-scaler monitors vLLM metrics (queue depth, KV-cache usage) to auto-scale replicas with GPU-aware policies. Third, the new frontier — prefill/decode disaggregated inference: KAITO's MultiRoleInference CRD separates compute-bound prefill and memory-bound decode onto dedicated GPU pools, using llm-d for P/D-aware routing via Gateway API Inference Extension, NixlConnector for zero-copy KV cache transfer, and per-role KEDA autoscaling.

---

## Benefits to the Ecosystem

KAITO demonstrates that Kubernetes-native abstractions — CRDs, controllers, and CNCF projects like KEDA and Karpenter — compose naturally for AI infrastructure, scaling from simple single-model serving to advanced disaggregated inference without leaving the Kubernetes ecosystem.

**For the AI/ML community**: Automated GPU memory estimation (model weights + KV-cache overhead + activation memory) drives parallelism decisions before scheduling, preventing costly OOM restarts. Any-model support means the thousands of models published weekly on Hugging Face deploy on Kubernetes with autoscaling via a single CR — no per-model tuning required.

**For platform teams**: This session delivers a blueprint for production AI on Kubernetes at two levels. Level 1: model-aware resource allocation + KEDA-driven autoscaling on vLLM metrics for standard inference. Level 2: P/D disaggregated inference using Gateway API Inference Extension and llm-d for workloads that need maximum GPU efficiency — all configured declaratively.

**For the cloud-native ecosystem**: The P/D disaggregation architecture showcases real-world adoption of Gateway API Inference Extension (K8s SIG direction for AI routing), llm-d as a Kubernetes-native routing layer, and KEDA for heterogeneous GPU autoscaling. Multi-node distributed inference and disaggregated serving extend Kubernetes to workloads previously confined to specialized ML platforms — democratizing AI infrastructure for any organization running Kubernetes.

---

## Case Study?

Yes

## Presented This Talk Before?

A related talk covering KAITO's foundational features (model-to-service automation, autoscaling) was submitted to KubeCon Japan 2026. This submission extends it significantly with the P/D disaggregated inference architecture (MultiRoleInference CRD, llm-d integration, Gateway API routing, per-role autoscaling) — new work that represents KAITO's evolution from single-model serving to distributed inference orchestration.

## CNCF-Hosted Software

https://github.com/kaito-project/kaito

## Open Source Projects

- https://github.com/kaito-project/kaito
- https://github.com/llm-d/llm-d-inference-scheduler
- https://github.com/kubernetes-sigs/gateway-api-inference-extension
- https://github.com/kaito-project/keda-kaito-scaler
