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

The problem: P/D disaggregation improves LLM serving efficiency by 30-60% on prefill-heavy workloads, but infrastructure complexity is brutal — routing sidecars, NIXL KV transfer, ZMQ discovery, port management, scheduling profiles, and independent autoscaling all need correct orchestration.

Existing solutions: NVIDIA Dynamo provides disaggregation but is tightly coupled to NVIDIA's stack, not Kubernetes-native. llm-d offers Kubernetes-native P/D routing via Gateway API but requires manual StatefulSet config, sidecar injection, and env var plumbing.

KAITO's MultiRoleInference CRD bridges this gap: a declarative layer orchestrating llm-d components automatically. One CRD generates prefill/decode StatefulSets with correct port assignments, NIXL env vars, decode-only sidecar injection, InferencePool with proper targetPort, EPP plugin chain, and KEDA ScaledObjects per role.

We'll show eval data: TTFT reduction, throughput gains, and autoscaling behavior under mixed workloads.

---

## Benefits to the Ecosystem

Attendees will learn:

1. **A layered abstraction for complex inference topologies** — How KAITO's MultiRoleInference CRD composes Gateway API InferencePool, llm-d EPP plugins, and vLLM NIXL into one declarative interface. Why this matters as topologies grow (E/P/D, speculative decoding, MoE).

2. **When to use P/D disaggregation** — Eval data showing TTFT reduction, throughput gains, GPU utilization improvements under different workload profiles, and break-even analysis by prompt length.

3. **How to autoscale P/D independently** — KEDA with role-specific metrics: prefill scales on queue depth, decode on KV-cache utilization. Example of asymmetric scaling under bursty traffic.

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

**Andy Zhang**

**Linbo He**

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

---

## Travel / Logistics

**Event:** KubeCon + CloudNativeCon North America 2026
**Dates:** November 9–12, 2026
**Venue:** [Salt Palace Convention Center](https://www.visitsaltlake.com/salt-palace-convention-center/attend/), 90 South West Temple, Salt Lake City, UT 84101

### Official Room Block Hotels

All hotels below are part of the official KubeCon NA 2026 room block (discounted rates) and are within walking distance of the Salt Palace Convention Center. Taxes ~17.52% unless noted. Book early — room blocks close mid-to-late October 2026.

| Hotel | Stars | Rate/night | Distance | Walk | Notes |
|---|---|---|---|---|---|
| [Hyatt Regency Salt Lake City](https://www.hyatt.com/hyatt-regency/en-US/slcrs-hyatt-regency-salt-lake-city) | ★★★★ | $265+ | 0.0 mi | 2 min | Adjacent to venue — most convenient |
| [Hilton Salt Lake City Center](https://www.hilton.com/en/hotels/slccchh-hilton-salt-lake-city-center/) | ★★★★ | $259+ | 0.1 mi | 3 min | Right next door |
| [Salt Lake Marriott Downtown at City Creek](https://www.marriott.com/en-us/hotels/slcut-salt-lake-marriott-downtown-at-city-creek/overview) | ★★★★ | $259+ | 0.2 mi | 2 min | Very close, flexible cancellation |
| [Kimpton Hotel Monaco](https://www.monaco-saltlakecity.com/) | ★★★★ | $224+ | 0.3 mi | 3 min | Boutique; 24h cancellation policy |
| [Hyatt Place Salt Lake City/Downtown/The Gateway](https://www.hyatt.com/hyatt-place/en-US/slczd-hyatt-place-salt-lake-city-downtown-the-gateway) | ★★★ | $215+ | 0.3 mi | 8 min | **Includes breakfast** |
| [Salt Lake Marriott City Center](https://www.marriott.com/en-us/hotels/slccc-salt-lake-city-marriott-city-center/overview) | ★★★★ | $249+ | 0.4 mi | 9 min | Solid four-star option |
| [Element Salt Lake City Downtown](https://www.marriott.com/en-us/hotels/slcel-element-salt-lake-city-downtown/overview) | ★★★ | $209+ | ~0.4 mi | ~10 min | **Includes breakfast**; extended-stay style |
| [The Little America Hotel](https://saltlake.littleamerica.com/) | ★★★★ | $219+ | 0.7 mi | 16 min | Classic SLC property, large rooms |
| [DoubleTree by Hilton Downtown](https://www.hilton.com/en/hotels/slcwsdt-doubletree-suites-salt-lake-city-downtown/) | ★★★ | $234+ | 0.7 mi | 16 min | 15.52% tax (lower) |

### Recommendations

- 🏃 **Closest to venue:** Hyatt Regency (2 min) or Hilton City Center (3 min)
- 💰 **Best value:** Hyatt Place ($215, breakfast included) or Element ($209, breakfast included)
- ✨ **Most flexible cancellation:** Kimpton Hotel Monaco (24h) or Salt Lake Marriott Downtown at City Creek (24h)

Official venue + travel page (booking links, room block cutoffs): <https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/attend/venue-travel/>
