# KAITO + P/D Disaggregation Deck Outline

## Goal

Build a **new KAITO + P/D disaggregation deck** quickly by reusing the strongest pages from `From_Model_Serving_to_Distributed_Inference.pptx`, trimming the llm-d-only parts, and adding the missing KAITO-specific architecture / implementation / ops story.

Primary message:

> KAITO turns llm-d-style P/D disaggregated inference from a manual stack into a Kubernetes-native, declarative workflow.

---

## Fast Copy Strategy

### A. Directly copy from source deck
- P41 — What is KAITO?
- P42 — Workload Lifecycle
- P43 — How the GPU Node Count Is Computed
- P44 — Autoscaling: keda-kaito-scaler
- P34 — Why P/D? Prefill and Decode Two Phases
- P35 — Why P/D? Prefill and Decode Scale Differently
- P38 — Aggregated vs Disaggregated Pareto Frontier
- P37 — Efficient KV Transfer in vLLM via NIXL *(optional if deck is too long)*

### B. Keep but tweak
- P10 — Challenges of Real Production Inference
- P12 — Production Distributed Inference Architecture
- P15 — What is LLM-D?
- P19 — KV Cache Reuses “conversation”
- P20 — Where Standard Load-Balancing Fails
- P21 — Intelligent Inference Scheduling
- P45 — Autoscaling: Composite Metrics
- P47 — Production-Stack
- P48 — GPU Node Mocker
- P49 — Testing=Confidence

### C. Write new pages
- Why KAITO on top of llm-d / Dynamo / manual stack
- What is MultiRoleInference?
- What resources one MRI CR generates
- decode-only sidecar / port / label / env contracts
- benchmark / break-even analysis
- AKS / production lessons learned

---

## Proposed New Deck Structure

Target length: **16–18 slides** for a 25–35 minute talk.

---

### Slide 1 — Title *(NEW)*
**Suggested title**

**KAITO Meets llm-d: From One-Click Serving to Prefill/Decode Disaggregated Inference on Kubernetes**

**Subtitle options**
- From model name to distributed inference with one CRD
- Declarative P/D disaggregation on Kubernetes

**Speaker line**
- Andy Zhang
- Linbo He

**Speaker note**
Set expectation early: this is not only about P/D theory; it is about making the full stack operational on Kubernetes.

---

### Slide 2 — Why production inference is hard *(TWEAK from P10)*
**Keep**
- Production needs sustained token capacity
- SLOs, cost, lifecycle, validation, governance

**Tweak**
- Remove generic wording that does not connect to KAITO / P/D
- End the slide with one takeaway:

> Running a model is easy. Operating a production inference system is the hard part.

**Speaker note**
This slide is the setup for why a higher-level abstraction is needed.

---

### Slide 3 — Where this fits in the stack *(TWEAK from P12)*
**Keep**
- Big architecture view
- Gateway / orchestration / runtime / KV / storage layers

**Tweak**
Highlight only these layers:
- KAITO = workload lifecycle + GPU operations + Kubernetes abstraction
- llm-d = inference routing / scheduling / distributed inference primitives
- vLLM = runtime
- NIXL = KV transport

**Takeaway**
> KAITO and llm-d solve different layers of the problem and compose naturally.

---

### Slide 4 — What is KAITO? *(DIRECT from P41)*
**Why keep**
- Clean value proposition
- Good transition from general problem to KAITO

**Message**
KAITO abstracts model deployment, node provisioning, scaling, and lifecycle into Kubernetes-native APIs.

---

### Slide 5 — Why KAITO on top of llm-d / Dynamo / manual stack *(NEW)*
**Core comparison to show**

| Option | What it gives you | What still hurts |
|---|---|---|
| Manual llm-d stack | Routing + scheduling primitives | Too much wiring: InferencePool, EPP, sidecar, labels, ports, configs |
| Dynamo | Full-stack disaggregation framework | Heavier integration, more runtime coupling, less natural K8s fit |
| **KAITO + llm-d** | K8s-native declarative abstraction on top of strong routing primitives | Best fit for platform teams already operating Kubernetes |

**One-line takeaway**
> llm-d gives the routing building blocks; KAITO turns them into an operator workflow.

**Source material**
- `llm/dynamo-vs-llm-d.md`
- `llm/kubecon-na-2026-cfp-pd-disaggregation.md`

---

### Slide 6 — Why P/D? Two phases, two resource profiles *(DIRECT from P34)*
**Keep as-is**
- Prefill = compute-bound / latency-sensitive
- Decode = memory-bandwidth-bound / throughput-sensitive

**Takeaway**
> One GPU pool is forced to compromise between two very different jobs.

---

### Slide 7 — Why P/D? They scale differently *(DIRECT from P35)*
**Keep as-is**

**Talk track**
- Prefill spikes are bursty
- Decode is steady-state throughput pressure
- Independent scaling becomes valuable fast

---

### Slide 8 — Aggregated vs disaggregated serving *(DIRECT from P38)*
**Keep as-is**

**Takeaway**
> Disaggregation expands the operating envelope, but only if the system can coordinate routing and KV transfer correctly.

---

### Slide 9 — KV cache reuse and why routing matters *(TWEAK from P19 + P20 + P21)*
**Recommended merge**
Instead of keeping 3 separate legacy slides, compress them into 1 slide if time is tight.

**Narrative**
1. KV cache reuse lowers TTFT and cost
2. Naive load balancing destroys cache locality
3. Intelligent routing is mandatory for production efficiency

**If more time is available**
Keep them as separate slides:
- Slide 9: P19
- Slide 10: P20
- Slide 11: P21

---

### Slide 10 — What is llm-d in this architecture? *(TWEAK from P15)*
**Keep**
- Kubernetes-native distributed inference framing
- Scheduling / routing / disaggregation building blocks

**Tweak**
Avoid turning this into an llm-d project overview.
Focus on 3 functions only:
- request routing
- scheduling policy
- disaggregated inference coordination

**Takeaway**
> We use llm-d as the routing and scheduling substrate, not as the whole user experience.

---

### Slide 11 — MultiRoleInference: one CRD for P/D disaggregation *(NEW)*
**Content**
Use the user-facing CR from:
- `llm/kaito-llm-d/multi-role-inference-pd-disaggregation.md`

Show a trimmed MRI example:
```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v32
spec:
  inference:
    preset:
      name: deepseek-ai/DeepSeek-V3.2
  roles:
    - type: prefill
      replicas: 2
      instanceType: Standard_NC24ads_A100_v4
    - type: decode
      replicas: 3
      instanceType: Standard_NC24ads_A100_v4
```

**Takeaway**
> The user describes topology and intent once; KAITO expands that into runnable infrastructure.

---

### Slide 12 — What one MRI CR generates *(NEW)*
**Visual**
Show this expansion flow:
- MultiRoleInference
  - prefill InferenceSet
  - decode InferenceSet
  - shared InferencePool
  - EPP plugin config
  - HelmRelease / OCIRepository
  - DestinationRule
  - KEDA ScaledObjects / annotations

**Best source**
Reuse and simplify the architecture diagram from:
- `llm/kaito-llm-d/multi-role-inference-pd-disaggregation.md`

**Takeaway**
> KAITO is not replacing llm-d. It is generating and owning the llm-d-facing resources for you.

---

### Slide 13 — Request flow: Gateway → EPP → Decode → Prefill → KV transfer *(NEW)*
**Flow to show**
- Client request
- Gateway / HTTPRoute / DestinationRule
- llm-d EPP selects decode + prefill
- Decode sidecar receives request first
- Prefill vLLM produces KV cache
- Decode vLLM pulls KV via NIXL and generates output

**Best source**
- Request flow section from `llm/kaito-llm-d/multi-role-inference-pd-disaggregation.md`

**Takeaway**
> The control-plane abstraction is simple, but the runtime flow is not — that is exactly why the abstraction matters.

---

### Slide 14 — decode-only sidecar / ports / labels / env contracts *(NEW)*
**Must-cover implementation contracts**

1. **Decode pod has sidecar; prefill pod does not**
2. **InferencePool targetPort must match the prefill vLLM port**
3. **decode sidecar sits in front of local vLLM**
4. **`kaito.sh/inference-role=prefill|decode` labels are required**
5. **`VLLM_NIXL_SIDE_CHANNEL_HOST=status.podIP` is required on both sides**

**Recommended concrete table**

| Contract | Prefill | Decode |
|---|---|---|
| Sidecar | No | Yes |
| vLLM port | 5000 | 5001 |
| Sidecar port | N/A | 5000 |
| Role label | `prefill` | `decode` |
| NIXL side-channel host | Pod IP | Pod IP |

**Best source**
- `llm/pd-disaggregation/kaito/pd-working-config.md`
- `llm/pd-disaggregation/kaito/README.md`

**Takeaway**
> Most real-world P/D failures are contract bugs, not model bugs.

---

### Slide 15 — KV transfer via NIXL *(DIRECT or LIGHT TWEAK from P37)*
**Keep**
- Conceptual NIXL / KV transfer explanation

**Add one verified number if you want concreteness**
From `pd-working-config.md`:
- 4 MB transfer in 15.8 ms
- ~252.9 MB/s observed in verified run

**Takeaway**
> P/D becomes worthwhile only when KV movement is cheap enough relative to saved prefill work.

---

### Slide 16 — Independent autoscaling for prefill and decode *(DIRECT P44 + TWEAK P45)*
**Structure**
- First half: reuse P44 to explain KAITO autoscaling baseline
- Second half: show P/D-specific asymmetry
  - Prefill scales on queue depth / prompt pressure
  - Decode scales on KV / generation pressure

**Source**
- `llm/kaito-llm-d/multi-role-inference-pd-disaggregation.md`
- `llm/kubecon-na-2026-cfp-pd-disaggregation.md`

**Takeaway**
> P/D is not just a routing change; it unlocks role-specific scaling policy.

---

### Slide 17 — Production integration and testability *(TWEAK from P47 + P48 + P49)*
**Recommended story**
- production-stack integration
- GPU node mocker for CPU-only E2E
- two test paths: mocked GPU + real GPU

**Takeaway**
> If you cannot test NodeClaim → Node → Pod → InferencePool → EPP → KV transfer end-to-end, you do not really have a production feature.

---

### Slide 18 — Benchmark / break-even analysis *(NEW)*
**Recommended slide title**

**When Does P/D Disaggregation Pay Off?**

**Recommended subtitle**

P/D wins once prefill pressure dominates and KV transfer overhead is smaller than the saved prefill compute.

**Recommended layout: one chart + one summary table**

#### Left chart
**Chart title:** P95 TTFT vs. Prompt Length

- **X-axis:** prompt length (input tokens)
- **Y-axis:** P95 TTFT (seconds)
- **Series 1:** Colocated serving
- **Series 2:** P/D disaggregation
- **Optional vertical marker:** break-even point at **~[X] input tokens**

**Chart annotation copy**
- **Short prompts:** colocated is competitive because routing + KV-transfer overhead is not yet amortized
- **Break-even zone:** around **[X] input tokens** / **[Y]% cache miss rate**, P/D starts to reduce TTFT consistently
- **Long prompts:** P/D separates prefill pressure from decode throughput, so TTFT grows more slowly

#### Right-side summary table

| Workload region | Winner | Why |
|---|---|---|
| Short prompts / high cache hit | Colocated or near-tie | Little prefill to offload; extra coordination can dominate |
| Medium prompts / mixed cache hit | Break-even zone | Routing quality and KV-transfer efficiency decide the outcome |
| Long prompts / prefill-heavy | **P/D disaggregation** | Prefill no longer steals decode capacity |

**Recommended metric row below the chart**
- **Primary metric:** P95 TTFT
- **Secondary metrics:** throughput, TPOT / ITL, GPU utilization, GPUs needed for the same SLO

**Recommended speaker line**
> P/D is not a universal win. It becomes compelling when prompt length, cache-miss rate, or prefill concurrency is high enough that separating prefill from decode recovers more GPU efficiency than the extra coordination costs.

**Ready-to-paste takeaway box**
> **Break-even rule of thumb:** below the break-even point, keep it simple; above it, P/D buys lower TTFT and better decode stability.

**Figure caption template**
Benchmark setup: same model, same total GPU budget, same request distribution; only serving topology changes (colocated vs. P/D).

**If the real benchmark is not ready yet**
Use the exact structure above with placeholders like **[X]**, **[Y]**, and **[model / GPU SKU]**. Do **not** invent numbers.

---

### Slide 19 — AKS / production lessons learned *(NEW)*
**Recommended slide title**

**AKS Lessons Learned: The Hard Part Is the Contracts**

**Final bullet wording**
- **Use a decode-only sidecar.** Putting the routing sidecar on prefill pods added instability and unnecessary memory pressure; the stable pattern is sidecar on decode, no sidecar on prefill.
- **Treat ports as API contracts.** `InferencePool.targetPort`, decode sidecar port, and prefill vLLM port must line up exactly, or routing fails in ways that look like runtime bugs.
- **Treat labels as routing inputs.** `kaito.sh/inference-role=prefill|decode` is not cosmetic metadata — the EPP depends on it to select the right workers.
- **Automate NIXL endpoint wiring in the controller.** `VLLM_NIXL_SIDE_CHANNEL_HOST=status.podIP` must be correct on both prefill and decode pods, otherwise KV handshakes fail across pods.
- **Observe the stack at three layers.** You need EPP routing signals, vLLM inference metrics, and KV-transfer / KV-event visibility together; none of them alone is enough to debug P/D.
- **Invest in CPU-only E2E before scaling out GPU tests.** GPU node mocker and mocked NodeClaim → Node → Pod flows are what make fast iteration and safe regression testing practical on AKS.

**Optional closing line at bottom of slide**
> P/D disaggregation is easy to explain on a whiteboard. Making the contracts reliable in a real AKS deployment is the real engineering work.

**Best source**
- `llm/pd-disaggregation/kaito/README.md`
- `llm/pd-disaggregation/kaito/pd-working-config.md`

**Takeaway**
> The hard part is not the idea of P/D. The hard part is making the contracts operationally reliable.

---

### Slide 20 — Summary / Q&A *(NEW)*
**Summary line**
- llm-d gives the routing substrate
- KAITO gives the declarative Kubernetes abstraction
- MultiRoleInference is the bridge from model serving to distributed inference

---

## Recommended Cut Order (if time is short)

### Keep no matter what
- 1 Title
- 2 Production problem
- 4 What is KAITO
- 6 P/D phase difference
- 7 Scale difference
- 11 MRI CRD
- 12 MRI-generated resources
- 13 Request flow
- 14 Sidecar / port / label / env contracts
- 16 Independent autoscaling
- 19 Lessons learned

### Cut first
- P37 / KV transfer deep dive
- standalone KV reuse slide(s)
- production-stack details
- GPU node mocker details

---

## Copy / Edit Checklist

### Direct copy checklist
- [ ] P41 copied
- [ ] P42 copied
- [ ] P43 copied
- [ ] P44 copied
- [ ] P34 copied
- [ ] P35 copied
- [ ] P38 copied
- [ ] P37 copied *(optional)*

### Tweak checklist
- [ ] P10 retitled around production gap
- [ ] P12 highlighted KAITO + llm-d + vLLM + NIXL only
- [ ] P15 narrowed to llm-d's role in the story
- [ ] P19/P20/P21 compressed or refreshed
- [ ] P45 rewritten as role-specific autoscaling policy
- [ ] P47/P48/P49 compressed to 1–2 slides

### New slide checklist
- [ ] Why KAITO on top of llm-d / Dynamo / manual stack
- [ ] MultiRoleInference CRD
- [ ] MRI-generated resources
- [ ] Request flow
- [ ] decode-only sidecar / ports / labels / env
- [ ] benchmark / break-even analysis
- [ ] AKS / production lessons learned

---

## Author Notes

Do **not** let the deck drift into a generic llm-d overview.

The strongest version of this talk is:
1. explain why P/D matters,
2. show why raw llm-d/manual wiring is not enough for most users,
3. show how KAITO turns that into a clean Kubernetes abstraction,
4. prove that the operational details were actually worked through.
