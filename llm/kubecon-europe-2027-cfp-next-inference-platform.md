# KubeCon + CloudNativeCon Europe 2027 — CFP Submission

---

## Title

**Beyond Prefill/Decode: Building the Next Kubernetes-Native Inference Platform with KAITO and llm-d**

<details>
<summary>Alternate titles considered</summary>

- After P/D: Prefix-Aware Routing and Tiered KV Cache for Kubernetes-Native LLM Inference
- From Prefill/Decode to Production Platform: Routing, Cache Tiers, and Scale with KAITO and llm-d
- Beyond One Inference Topology: Evolving Kubernetes-Native LLM Serving with KAITO and llm-d
- Kubernetes-Native Distributed Inference After P/D: Routing, Cache Tiers, and Platform Design
- What Comes After Prefill/Decode? Building Smarter LLM Platforms on Kubernetes
- From P/D to Platform: Prefix Routing, Tiered KV Cache, and Large-Scale Inference on Kubernetes
</details>

---

## Session Type

Conference Session (35 min)

## Track

AI + ML + Intelligent Apps / Platform Engineering / Runtime

## Level

Intermediate

---

## Abstract (max 900 characters)

Prefill/decode disaggregation proved that LLM inference on Kubernetes is not one uniform workload: prefill and decode want different resource shapes, scaling behavior, and scheduling decisions. But once P/D becomes practical, the harder question is what the platform needs next.

In this talk, we share the next step for **KAITO** and **llm-d** after the first successful P/D deployment. We will cover three concrete directions: **precise prefix-cache routing driven by KV events**, **tiered prefix cache across HBM, CPU RAM, and optional filesystem tiers**, and **larger-scale systems enabled by Wide Expert Parallelism and richer cross-node transport optimization**. The focus is not a vague roadmap, but a practical architecture story about what belongs in the runtime, what belongs in the routing layer, and what must be expressed as Kubernetes-native control-plane abstractions.

---

## Description (max 1000 characters)

P/D disaggregation solves an important performance problem, but it also exposes a platform design problem. Once inference is split across roles, better model serving is no longer just about kernels or faster GPUs. It becomes a Kubernetes problem: how should requests be placed based on real cache state, how should KV data span multiple memory tiers, and how should larger multi-node inference topologies remain operable?

This session starts from practical lessons learned running KAITO + llm-d with P/D on Kubernetes: routing sidecars, KV-transfer validation, role-specific autoscaling, and service/label/port contracts. From there, we show the next three areas that matter most: **KV-event-driven prefix-cache routing**, **tiered prefix cache across HBM/CPU/filesystem layers**, and **larger-scale platform evolution through Wide Expert Parallelism and transport-aware optimization**.

Attendees will leave with a concrete framework for treating distributed inference as a cloud-native platform problem, not just a model-server optimization problem.

---

## Benefits to the Ecosystem

Attendees will learn:

1. **Why P/D is only the beginning** — Prefill/decode disaggregation is the first useful distributed inference topology, but not the end state. It creates the foundation for more intelligent routing, cache hierarchy, and larger-scale serving patterns.

2. **How precise prefix-aware routing should evolve** — Why rough prefix heuristics are not enough, how KV events enable more accurate routing, and why this matters for TTFT, throughput, and cache locality.

3. **Why tiered prefix cache changes serving economics** — How HBM, CPU RAM, and optional filesystem tiers extend the effective cache working set and improve long-context and multi-turn workloads.

4. **What breaks at larger scale** — Why cross-node transport, KV movement cost, and expert-parallel coordination become first-order concerns as systems grow beyond a small local topology.

5. **Why Kubernetes needs a control-plane abstraction here** — What belongs in the model server, what belongs in llm-d's routing layer, and why KAITO should expose these capabilities as declarative platform APIs instead of hand-built runtime glue.

All components are open source: KAITO (CNCF Sandbox), llm-d, Gateway API Inference Extension (K8s SIG), and KEDA (CNCF Graduated).

---

## Talk Outline (35 min)

1. **Why P/D Was Only the First Step** (5 min)
   - What P/D solved: phase separation, utilization, TTFT/throughput tradeoffs
   - What it exposed: routing, cache, transport, and control-plane complexity
   - Why this is now a platform problem, not just a model-server problem

2. **Production Lessons from Running P/D on Kubernetes** (6 min)
   - Routing sidecars and decode-side placement rules
   - KV-transfer validation and side-channel pitfalls
   - Service, targetPort, env var, and label contracts
   - Why per-role autoscaling matters operationally

3. **Next Step #1: Precise Prefix-Cache Routing from KV Events** (8 min)
   - Limits of approximate prefix heuristics
   - How KV events improve cache-state visibility for routing
   - Why this matters for placement accuracy and latency
   - Where this belongs: model server signals vs router scoring vs control-plane API

4. **Next Step #2: Tiered Prefix Cache Across HBM / CPU / Filesystem** (7 min)
   - Why HBM-only cache is not enough for long-context and multi-turn serving
   - Extending working set size with tiered cache
   - Tradeoffs: locality, eviction, latency, and operational cost
   - How this changes cluster-level inference design

5. **Next Step #3: Scaling Beyond Small Topologies** (7 min)
   - Wide Expert Parallelism as a larger-scale systems direction
   - Why transport and cross-node optimization matter more as topologies grow
   - What Kubernetes platform teams need to verify before these become practical

6. **Closing: What the Kubernetes Abstraction Should Look Like** (2 min)
   - KAITO as the control-plane layer
   - llm-d as the routing/scheduling layer
   - A concrete roadmap from today’s P/D to tomorrow’s larger distributed inference platform

---

## Speaker Bio

**Andy Zhang**

**Linbo He**

---

## Tags / Keywords

`kubernetes`, `llm-inference`, `gpu`, `kaito`, `llm-d`, `gateway-api`, `kv-cache`, `prefix-cache`, `routing`, `distributed-inference`, `wide-expert-parallelism`, `autoscaling`, `cncf`

---

## References

- KAITO project: https://github.com/kaito-project/kaito
- llm-d project: https://github.com/llm-d/llm-d
- llm-d Router: https://github.com/llm-d/llm-d-router
- Gateway API Inference Extension: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- KEDA KAITO scaler: https://github.com/kaito-project/keda-kaito-scaler
- KubeCon NA 2026 P/D talk outline: https://github.com/andyzhangx/demo/blob/master/llm/kubecon-na-2026-pd-disaggregation.md
- KubeCon NA 2026 P/D CFP draft: https://github.com/andyzhangx/demo/blob/master/llm/kubecon-na-2026-cfp-pd-disaggregation.md
- Verified P/D config notes: https://github.com/andyzhangx/demo/blob/master/llm/pd-disaggregation/kaito/pd-working-config.md

---

## Notes

- This CFP intentionally does **not** center speculative decoding, because KAITO already supports it and it is no longer the most important differentiator for this talk.
- This CFP also avoids making E/P/D a primary storyline, to keep the session focused on the stronger platform arc: **routing precision, cache hierarchy, and larger-scale distributed inference systems**.
- Suggested visual for the end of the talk: a roadmap slide with **current / next / later** swimlanes:
  - current: P/D disaggregation
  - next: precise prefix-cache routing; tiered prefix cache
  - later: WEP and deeper cross-node transport optimization
