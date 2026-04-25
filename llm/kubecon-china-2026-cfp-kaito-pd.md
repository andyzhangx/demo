# KubeCon + CloudNativeCon China 2026 (Shanghai) — CFP Submission

---

## Title

**From Model Name to Disaggregated Inference: KAITO's Journey to Production LLM Serving on Kubernetes**

<details>
<summary>Alternate titles considered</summary>

- One CRD to Serve Them All: Auto-Scaling and Disaggregated LLM Inference with KAITO
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

## Description

Deploying LLMs on Kubernetes still demands deep expertise across GPU provisioning, runtime tuning, autoscaling, and distributed serving. What if a single YAML could take any Hugging Face model from zero to a production-ready, auto-scaling — and even disaggregated — inference service?

This session walks through KAITO (Kubernetes AI Toolchain Operator, CNCF Sandbox) end-to-end, from its foundational model-to-service automation to the latest advancement: prefill/decode (P/D) disaggregated inference.

**Part 1: Model-Aware Inference Automation.** Specify a Hugging Face model ID, and KAITO handles GPU node provisioning via Karpenter, automated GPU memory estimation (model weights + KV-cache + activation memory) to determine optimal parallelism (single-GPU, tensor-parallel, or multi-node pipeline-parallel), runtime configuration, and inference endpoint exposure. We cover how any-model support turns thousands of weekly Hugging Face releases into deployable Kubernetes workloads without per-model engineering.

**Part 2: Production Autoscaling with KEDA.** KAITO integrates with KEDA through a custom kaito-scaler that monitors vLLM serving metrics — pending queue depth, running requests, KV-cache utilization — to auto-scale inference replicas. We show how GPU-aware scaling policies handle the unique challenges of slow node provisioning and expensive cold starts.

**Part 3: Prefill/Decode Disaggregated Inference (New).** Large models like DeepSeek-V3 benefit significantly from separating compute-bound prefill and memory-bound decode onto dedicated GPU pools. KAITO's new MultiRoleInference CRD, built on llm-d inference scheduler and Gateway API Inference Extension, makes this declarative:

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

Under the hood, the controller orchestrates: separate InferenceSets per role, llm-d EPP plugin chain for P/D-aware routing (disagg-profile-handler + by-label-selector + precise-prefix-cache-scorer), NixlConnector for zero-copy KV cache transfer between prefill and decode pods, routing sidecars injected into decode StatefulSets, and independent KEDA autoscaling per role with different scaling signals for prefill vs decode.

We conclude with a live demo: deploying a model, watching KAITO provision GPUs and configure everything, then enabling P/D disaggregation and showing real-time routing decisions and per-role autoscaling under load.

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
