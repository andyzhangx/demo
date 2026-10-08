# KubeCon + CloudNativeCon Europe 2027 — CFP Submission

---

## Title

**Beyond Prefill/Decode: Intelligent Scheduling and Autoscaling for LLM Inference on Kubernetes**

<details>
<summary>Alternate titles considered</summary>

- Beyond Prefill/Decode: Intelligent Inference Scheduling on Kubernetes
- After P/D: Intelligent Scheduling, Autoscaling, and Tiered KV Cache for LLM Inference on Kubernetes
- From Prefill/Decode to Production Platform: Scheduling, Autoscaling, and Scale with KAITO and llm-d
- Beyond One Inference Topology: Evolving Kubernetes-Native LLM Serving with KAITO and llm-d
- Kubernetes-Native Distributed Inference After P/D: Intelligent Scheduling, Cache Tiers, and Platform Design
- What Comes After Prefill/Decode? Building Smarter LLM Platforms on Kubernetes
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

Prefill/decode disaggregation showed that LLM inference on Kubernetes is not one workload. Prefill and decode have different bottlenecks, different scaling signals, and different placement needs. Once that split works, the next challenge is no longer just model serving performance. It is platform design.

In this talk, we share what comes next for **KAITO** and **llm-d** after a working P/D deployment: **how we moved from the earlier Gateway API Inference Extension (GWIE)-based path to `llm-d-router`**, **why KAITO built on a Kubernetes-native routing and scheduling layer instead of a more vertically integrated runtime path such as Dynamo**, **how to support separate autoscaling for prefill and decode roles**, **how live cache signals can improve request placement**, and **how cache tiers can extend beyond GPU memory**. We focus on practical platform lessons from the current system, which still uses sidecar-heavy integration for P/D today.

---

## Description (max 1000 characters)

P/D disaggregation improves LLM serving, but it also makes the platform harder to operate. Once requests are split across prefill and decode, teams need better answers for scaling, routing, cache management, and day-2 operations.

This session shares practical lessons from running **KAITO** with **llm-d** on Kubernetes. We show how the design moved from the earlier Gateway API Inference Extension (GWIE)-based path to `llm-d-router`, why KAITO built on a Kubernetes-native routing and scheduling layer instead of a more vertically integrated runtime path such as Dynamo, why prefill and decode need different autoscaling policies, how the current sidecar-heavy P/D integration shapes lifecycle and operability tradeoffs, how live cache state can improve request placement, and why extending cache beyond GPU memory changes both cost and performance.

The goal is not to present a distant roadmap. It is to give platform engineers a clear design framework for the next stage of Kubernetes-native inference: what belongs in the model server, what belongs in the router, and what should become a first-class Kubernetes control-plane concept.

---

## Benefits to the Ecosystem

Attendees will learn:

1. **Why P/D is only the beginning** — Prefill/decode disaggregation is the first useful distributed inference topology, but not the end state. It creates the foundation for more intelligent routing, autoscaling, cache hierarchy, and larger-scale serving patterns.

2. **Why autoscaling must become role-aware** — Prefill and decode experience different bottlenecks and queue dynamics, so they cannot be scaled well by a single generic policy. We will show the concrete support model discussed after the move from the earlier GWIE-based path to `llm-d-router`.

3. **Why KAITO built on llm-d’s routing layer** — Why KAITO favored a Kubernetes-native routing and scheduling layer over a more vertically integrated runtime path, and how that choice affects extensibility, control-plane boundaries, and ecosystem fit.

4. **What changed in the routing architecture** — Why the integration moved from the earlier GWIE-based path to `llm-d-router`, what the current sidecar-heavy P/D design gets right, and where it still creates operational friction today.

5. **How precise prefix-aware routing should evolve** — Why rough prefix heuristics are not enough, how KV events enable more accurate routing, and why this matters for TTFT, throughput, and cache locality.

6. **Why tiered prefix cache changes serving economics** — How HBM, CPU RAM, and optional filesystem tiers extend the effective cache working set and improve long-context and multi-turn workloads.

7. **Why Kubernetes needs a control-plane abstraction here** — What belongs in the model server, what belongs in llm-d's routing layer, and why KAITO should expose these capabilities as declarative platform APIs instead of hand-built runtime glue over time.

All components are open source: KAITO (CNCF Sandbox), llm-d, Gateway API Inference Extension (K8s SIG), and KEDA (CNCF Graduated).

---

## Talk Outline (35 min)

1. **Why P/D Was Only the First Step** (5 min)
   - What P/D solved: phase separation, utilization, TTFT/throughput tradeoffs
   - What it exposed: routing, autoscaling, cache, transport, and control-plane complexity
   - Why this is now a platform problem, not just a model-server problem

2. **Production Lessons from Running P/D on Kubernetes** (6 min)
   - The move from the earlier GWIE-based path to `llm-d-router`
   - Routing sidecars and decode-side placement rules in the current design
   - KV-transfer validation and side-channel pitfalls
   - Service, targetPort, env var, and label contracts

3. **Why KAITO Built on llm-d’s Routing Layer** (5 min)
   - NVIDIA Dynamo is a powerful runtime-level disaggregation path, but more tightly coupled to the NVIDIA stack
   - llm-d provides a Kubernetes-native routing and scheduling layer that fits KAITO’s control-plane model better
   - What that choice preserves at the control-plane boundary and enables for ecosystem integration

4. **Next Step #1: Autoscaling for Prefill / Decode** (5 min)
   - Why prefill and decode have different queueing and saturation signals
   - Why a single autoscaler policy is not enough
   - How the current `llm-d-router`-based design supports separate autoscaling for the two roles

5. **Next Step #2: Routing Architecture Tradeoffs** (4 min)
   - What the current sidecar-heavy integration gets right
   - Where it creates lifecycle and operability challenges today
   - Which parts should stay in the current design and which parts should move as router capabilities mature

6. **Next Step #3: Precise Prefix-Cache Routing from KV Events** (5 min)
   - Limits of approximate prefix heuristics
   - How KV events improve cache-state visibility for routing
   - Why this matters for placement accuracy and latency

7. **Next Step #4: Tiered Prefix Cache Across HBM / CPU / Filesystem** (4 min)
   - Why HBM-only cache is not enough for long-context and multi-turn serving
   - Extending working set size with tiered cache
   - Tradeoffs: locality, eviction, latency, and operational cost

8. **Closing: What the Kubernetes Abstraction Should Look Like** (3 min)
   - KAITO as the control-plane layer
   - llm-d as the routing/scheduling layer
   - A concrete roadmap from the earlier GWIE-based path, to today’s `llm-d-router` integration, to the next platform improvements around autoscaling, routing precision, and cache tiers

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
- This CFP also avoids making E/P/D a primary storyline, to keep the session focused on the stronger platform arc: **platform architecture choice, autoscaling, routing precision, and cache hierarchy**.
- Suggested visual for the end of the talk: a roadmap slide with **past / current / next** swimlanes:
  - past: earlier GWIE-based path
  - current: `llm-d-router` with sidecar-heavy P/D integration
  - next: role-aware autoscaling, more precise prefix-cache routing, and tiered prefix cache
- Consistent session framing: the talk should present `llm-d-router` plus sidecar-heavy P/D integration as the **current** design, not as a fully completed future-state architecture.
