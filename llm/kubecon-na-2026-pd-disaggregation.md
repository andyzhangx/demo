# KubeCon North America 2026 — 20-Minute Talk Outline

## Session

**Title:** Prefill Here, Decode There: Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d

**Event:** KubeCon + CloudNativeCon North America 2026  
**Format:** CNCF-hosted Co-located talk (20 min target)  
**Track:** Cloud Native AI + Inference Day  
**Audience:** Any Level

---

## Goal

Turn the original 35-minute CFP idea into a sharper 20-minute story for a broad KubeCon co-located audience.

The talk should answer three practical questions:

1. **Why separate prefill and decode at all?**
2. **Why is this still hard on Kubernetes today?**
3. **Why does KAITO + llm-d make P/D disaggregation more usable in production?**

---

## Core Message

LLM inference has two very different phases:

- **Prefill** is compute-bound and latency-sensitive.
- **Decode** is memory-bandwidth-bound and throughput-sensitive.

Running both on the same GPU pool forces a compromise in latency, throughput, and utilization.

**Prefill/decode disaggregation** fixes this by placing the two phases on separate GPU pools. The challenge is not the idea itself — the challenge is the orchestration complexity: topology-aware routing, KV cache transfer protocols and data paths, decode-side sidecars, per-role autoscaling, targetPorts, env vars, label contracts, and startup ordering.

The main value of **KAITO MultiRoleInference** is that it turns this complexity into a **Kubernetes-native declarative abstraction** built on top of the llm-d Router, Gateway API Inference Extension, and KEDA.

### What KAITO is

For this talk, KAITO should be introduced as a **progression from basic model serving to distributed inference on Kubernetes**.

A plain way to say it is:

> **KAITO is a Kubernetes-native AI operator that starts with simple model serving and scales up to more advanced inference topologies through higher-level APIs.**

In this story, the important thing is that KAITO gives you an object model for that progression:

- **`Workspace`** is the basic building block for running one model-serving or tuning workload.
- **`InferenceSet`** is the scale-out layer for multiple inference replicas and autoscaling.
- **`InferencePool`** is the routing-facing layer that integrates with Gateway API Inference Extension.
- **`MultiRoleInference`** is the higher-level abstraction for advanced topologies such as prefill/decode separation.

That lets you explain KAITO as more than “an operator”:

- it starts with ordinary model serving
- it adds scale, routing, and autoscaling as first-class Kubernetes objects
- it then extends naturally into distributed inference patterns like P/D

Its value is that it **packages increasingly complex inference topology into a declarative Kubernetes UX**:

- users begin with higher-level APIs instead of hand-built runtime objects
- child resources are synthesized automatically
- routing and autoscaling become part of the platform model
- advanced topologies like P/D still look like Kubernetes operations, not bespoke glue code

Another good way to explain KAITO is by capability layers:

- **Serving layer** — `Workspace` gets a model workload running on Kubernetes
- **Scaling layer** — `InferenceSet` turns one serving workload into a scalable replica set
- **Routing layer** — `InferencePool` integrates the workload with inference-aware request routing
- **Topology layer** — `MultiRoleInference` lets one logical service expand into role-specific backends such as prefill and decode

That gives you a more concrete speaker message:

> **KAITO is not just a deployment helper. It is an inference platform API that adds serving, scaling, routing, and topology as first-class Kubernetes concepts.**

A good short phrasing for the talk is:

> **The llm-d Router provides the EPP-based routing and scheduling layer; KAITO provides the Kubernetes-native abstraction and orchestration layer on top.**

If time allows, also mention that KAITO is trying to make the path from **single-model serving** to **distributed inference** feel continuous:

- start with a serving workload
- scale it with inference-native objects
- route it with inference-aware infrastructure
- evolve it into richer topologies without throwing away the API model

That framing matters for the audience, because otherwise people may confuse KAITO with the runtime or with llm-d itself.

### KAITO: the version that sounds good on stage

A more natural way to explain KAITO in the talk is:

> **KAITO is the Kubernetes control-plane layer that takes you from model serving to distributed inference without changing mental models.**

If you want one extra sentence after that, use this:

> **llm-d is the smart routing and scheduling layer underneath; KAITO is the layer that turns those capabilities into a normal Kubernetes workflow.**

Then break it down in the order the audience can follow:

- **Start with `Workspace`** when you just want to run a model workload.
- **Move to `InferenceSet`** when you need multiple replicas and autoscaling.
- **Add `InferencePool`** when you need inference-aware routing through GWIE.
- **Use `MultiRoleInference`** when one logical service becomes a richer topology, like prefill/decode separation.

That progression is the real story:

- same platform
- richer objects as the serving problem gets harder
- no need to manually re-assemble the stack every time the topology evolves

Speaker note:
- Don’t over-explain KAITO.
- The audience mostly needs to understand that **KAITO is the abstraction**, not the model server and not the scheduler.
- The punchline is: **KAITO gives you a clean path from simple serving to distributed inference.**

### P/D disaggregation scenarios worth explaining explicitly

This section should sound practical, not theoretical. A simple way to say it is:

- If prompts are long, or the traffic is **retrieval-heavy**, **prefill gets expensive fast**.
- If generations are long, or concurrency is high, **decode becomes the bottleneck**.
- If you want **different scaling behavior** for prompt processing and token generation, P/D starts to make sense.
- If the model or topology wants **different parallelism choices** for prefill and decode, that is another strong reason to split them.
- If the workload is small and simple, **P/D may not be worth the extra moving parts**.

You can summarize the value in one line:

> **P/D helps when prefill and decode need different resource shapes, different scaling behavior, or different parallelism choices.**

Then connect it back to infrastructure:

- prefill can scale for **compute and latency**
- decode can scale for **memory bandwidth, active KV memory, and steady throughput**
- the real win is **independent capacity shaping**, not just a benchmark number
- but you only get that win if the **KV-transfer path is fast enough**

A good caution line, adapted from the NVIDIA Dynamo guidance, is:

> **P/D is not automatically better. For small models, short prompts, low concurrency, or clusters without a fast KV-transfer fabric, an aggregated deployment is often simpler and sometimes faster.**

Speaker note:
- This is a good place to sound opinionated.
- Say clearly that P/D is **not** the right answer for every workload.
- If useful, give the audience a concrete mental model: single-node multi-GPU with fast GPU-to-GPU transfer is the easiest place to win; cross-node P/D raises the bar because the KV path matters much more.

### Autoscaling story for P/D: what exists today and what the talk should recommend

This should be explained in a very direct way:

- **Today, KEDA already works well with KAITO `InferenceSet`.**
- KAITO docs already show both **cron-based scaling** and **metric-based scaling**.
- The useful metric example today is `vllm:num_requests_waiting`.

For the P/D story, the key point is simple:

> **Once MRI creates separate prefill and decode child `InferenceSet`s, the natural autoscaling boundary is per role, not one global knob for the whole service.**

Then make the scaling split concrete:

- **Prefill** should scale on prompt pressure, for example waiting requests, because that is what protects TTFT.
- **Decode** should scale on longer-lived saturation signals, like KV/cache pressure or steady decode load, because that is what protects throughput.

The recommendation for the talk should be blunt:

> **The right UX is not asking users to hand-author multiple ScaledObjects. The right UX is letting one MRI express per-role scaling intent and having KAITO push that down into the generated child InferenceSets.**

Speaker note:
- Keep the message operational.
- “Independent scaling” by itself is not the whole story.
- The real point is **metric-appropriate independent scaling with a clean Kubernetes UX**.

---

## What to Emphasize in the 20-Minute Version

Compared with the original 35-minute conference-session structure, this shorter version should:

- spend **less time on ecosystem history**
- spend **more time on the problem/solution tradeoff**
- keep implementation details only when they directly explain the user value
- end with a clear answer to **when to use P/D and when not to**

This should feel less like a deep internals talk and more like a crisp architecture + production lessons talk.

---

## Audience Takeaways

By the end of the talk, attendees should remember:

1. **Prefill and decode are fundamentally different workloads.**
2. **P/D disaggregation can improve TTFT, throughput, and GPU efficiency for the right workloads.**
3. **The hard part is orchestration, and KAITO provides a higher-level Kubernetes abstraction for it.**
4. **Per-role autoscaling is part of the value proposition, not an afterthought.**
5. **Not every workload needs P/D; there is a clear break-even point.**

---

## Slide-Friendly Agenda

For the deck itself, keep the agenda short, architectural, and easy to scan. A good opening agenda slide should tell the audience that the talk moves from the **problem**, to the **Kubernetes orchestration gap**, to the **KAITO + llm-d solution**, and ends with **practical production tradeoffs**.

**Suggested agenda slide content:**

1. **Why separate prefill and decode?**
2. **Why is P/D still hard on Kubernetes?**
3. **KAITO + llm-d architecture**
4. **How MultiRoleInference makes P/D declarative**
5. **Per-role autoscaling**
6. **Evaluation and tradeoffs**
7. **Production lessons**
8. **What comes next**

---

## Recommended 20-Minute Agenda

### 1) Opening + problem framing (0:00 - 0:30)
- Introduce the talk with one practical question:
  - Why does colocating prefill and decode on the same GPU pool make LLM serving inefficient?
- Set expectation:
  - this is not just about performance tuning
  - this is about choosing the right abstraction for modern inference topologies on Kubernetes

### 2) Why prefill and decode should not fight for the same GPU (0:30 - 4:00)
- Explain the two phases simply:
  - prefill = compute-heavy, TTFT-sensitive
  - decode = memory/KV-cache/bandwidth-heavy, throughput-sensitive
- Show the operational consequence:
  - if you scale for prefill spikes, decode capacity is wasted
  - if you optimize for decode efficiency, TTFT suffers during prompt bursts
- Key message:
  - **one request, two bottlenecks, one unhappy GPU pool**

### 3) Why existing P/D solutions are still hard to use on Kubernetes (4:00 - 7:00)
- Brief landscape:
  - NVIDIA Dynamo: powerful runtime-level disaggregation, but more tightly coupled to the NVIDIA stack
  - llm-d standalone: Kubernetes-native routing and scheduling, but still operationally manual
- Emphasize the real source of complexity:
  - topology-aware routing and endpoint selection
  - KV cache transfer protocol and data path validation
  - decode-side sidecar lifecycle
  - per-role targetPort / env / label contracts
  - role-specific autoscaling and startup ordering
- Key message:
  - P/D is valuable, but the setup complexity blocks mainstream adoption

### 4) KAITO MultiRoleInference: the abstraction layer (7:00 - 12:30)
- First explain **what KAITO is**:
  - a Kubernetes-native abstraction layer for AI model serving and orchestration
  - not just another model server, but the layer that turns complex inference topologies into declarative APIs
- Introduce **Gateway API Inference Extension + llm-d Router** plainly:
  - InferencePool represents model-serving backends
  - the llm-d Router supplies the EPP that performs model-aware endpoint selection
  - its plugin chain adds KV-cache-aware routing and P/D-aware scheduling on top of the base Gateway pattern
- Show a simple architecture diagram:
  - client / gateway
  - InferencePool / llm-d Router EPP
  - prefill pool
  - KV cache handoff
  - decode pool
- Explain the concrete user experience of a single MultiRoleInference resource:
  - users create one MRI object with prefill and decode roles
  - KAITO creates child InferenceSets for each role
  - decode pods get an injected llm-d routing sidecar
  - KAITO creates one InferencePool + EPP for the overall service
- Highlight the design value:
  - users declare the topology they want
  - KAITO wires the plumbing automatically
- Mention a few implementation details only as proof points:
  - decode-only sidecar placement
  - targetPort and port conventions
  - label contracts and NIXL env wiring

### 5) Results: when P/D helps and when it does not (12:30 - 16:30)
- Show only the most convincing evaluation outputs:
  - TTFT comparison
  - throughput comparison under mixed load
  - GPU utilization / capacity efficiency under asymmetric traffic
- Interpret the data rather than dumping charts
- Make the talk more credible by saying explicitly:
  - P/D is not automatically better for every workload
  - the break-even point depends on prompt length, concurrency, and workload shape
- Good fit:
  - long prompts
  - prefill-heavy or bursty traffic
  - TTFT-sensitive interactive workloads
  - environments where GPU efficiency or fewer total GPUs matters
- Not always worth it:
  - small PoCs
  - short-prompt low-concurrency workloads
  - teams not ready to operate a more advanced inference topology

### 6) Production lessons + closing (16:30 - 20:00)
- Share a short list of practical lessons:
  - startup ordering matters
  - decode-side sidecar placement rules matter
  - KV transfer path and side-channel setup must be validated early
  - autoscaling metrics must be role-specific
  - service / targetPort / label contracts are easy to get wrong
- Explain the current KAITO autoscaling support path and the better P/D UX direction:
  - today, KEDA integrates naturally with InferenceSet
  - for P/D, the clean UX is for MRI to propagate per-role autoscaling annotations to child InferenceSets
  - that allows prefill and decode to keep different metrics and thresholds without asking users to hand-author per-role ScaledObjects
- Add a short **future integration roadmap** for KAITO + llm-d:
  - **near term:** precise prefix-cache routing based on KV events; productized tiered prefix cache across HBM, CPU RAM, and optional filesystem tiers
  - **next topology:** E/P/D
  - **larger-scale systems:** Wide Expert Parallelism and deeper transport / cross-node optimization
- Final takeaway:
  - the challenge is no longer whether P/D works
  - the challenge is how to make advanced inference topologies feel native on Kubernetes
- Close with next steps:
  - deeper KAITO integration with llm-d scheduling capabilities
  - richer inference topologies without hand-wired plumbing

---

## Suggested Slide-by-Slide Story

For a 20-minute co-located talk, the slide count should be **flexible**. If slides are light and visual, a longer deck can work; if the diagrams are dense, a shorter deck is better. In practice, something like **18-30 slides** is a reasonable range, and adjacent ideas can be merged freely. Below is a **reference slide structure**, not a hard page-count target: each slide includes the core message, a suggested visual, and the intended speaker emphasis.

### Slide 1 — Title
**Prefill Here, Decode There**  
Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d

**Suggested visual:** clean title slide with one simple split-GPU illustration: left = prefill, right = decode.

**Speaker note:**
- Start with the operational problem, not the project names.
- The title should make people expect an architecture story, not a vendor pitch.

### Slide 2 — The core question
- Why does one LLM request behave like two different systems problems?

**Suggested visual:** one large user request arrow splitting into two colored branches.

**Speaker note:**
- Set up curiosity immediately.
- Tell the audience the whole talk is basically answering this one question.

### Slide 3 — One request, two phases

**Actual PPTX slide 5 — One request. Two different performance targets.** (The outline numbering predates the two foundation slides.)

- **Prefill → TTFT (time to first token):** mainly affects the wait for the first output; lower is better. Also track prefill latency and input-token processing throughput (**input tok/s**). Often compute-bound, not universally.
- **Decode → ITL (inter-token latency) / TPOT (average time per output token after the first):** mainly affects ongoing token delivery; lower is better. Also track aggregate **output tok/s**. Often memory-bandwidth-bound, depending on workload and hardware.
- **Both → total response latency and system capacity / SLO goodput:** requests/s meeting the TTFT and token-delivery targets, not simply raw token throughput.

**Visual:** editable Prompt → Prefill → KV cache → Decode diagram above two color-matched metric cards.

**Speaker notes and measurement boundaries:**
- TTFT is not just prefill compute: queueing, routing, input processing/tokenization, scheduling and delivery contribute. In P/D, KV transfer and coordination can also be on the first-token critical path; this does not prescribe a worker protocol or delivery order.
- ITL/TPOT are not pure decode-kernel time. Scheduling, preemption, contention, detokenization, transport and stream buffering can change observed latency. Colocated prefill can stall decode; chunked prefill can mitigate interference.
- At matching client boundaries and with more than one output token, latency **to the last token ≈ TTFT + (Nout − 1) × TPOT**. This is not HTTP request-close time. Client timing differs from vLLM frontend/engine timing and additionally includes network/delivery overhead.
- vLLM's ITL histogram samples consecutive streamed **output events**, potentially multi-token; TPOT is one sample per request, `(e2e − TTFT)/(Nout − 1)`. Their means/percentiles need not match because of event grouping and weighting. The server records zero TPOT for requests with at most one output token; the benchmark excludes them from TPOT statistics.
- Aggregate output tok/s across concurrent requests is not per-request speed. At matching boundaries, a request's post-first-token speed is approximately `1/TPOT`; larger batches may increase aggregate throughput while hurting ITL/TPOT. Input tok/s and output tok/s represent different work, not equivalent productivity. State aggregation scope, time window, sequence lengths and prefix-cache accounting.
- Prefill populates KV; longer prompts also affect decode attention and KV cost. KV occupancy is a capacity-pressure indicator, not memory bandwidth or a primary latency metric.

Sources: [vLLM metrics definitions](https://docs.vllm.ai/en/latest/design/metrics/), [vLLM benchmark latency definitions](https://docs.vllm.ai/en/latest/benchmarking/cli/#understanding-the-latency-metrics), and [NVIDIA Dynamo P/D overview](https://docs.nvidia.com/dynamo/kubernetes/disaggregated-serving/overview). Conceptual mapping, not benchmark results.

### Slide 4 — Prefill profile
- compute-bound
- latency-sensitive
- prompt-heavy bursts hurt

**Suggested visual:** icon row or radar chart showing compute-heavy / latency-sensitive.

**Speaker note:**
- Make it feel operational, not academic.
- Prefill is where prompt length hurts first.

### Slide 5 — Decode profile
- memory-bandwidth-bound
- KV-cache-sensitive
- throughput-oriented

**Suggested visual:** mirror of Slide 4 so the contrast is obvious.

**Speaker note:**
- Contrast directly with prefill.
- This makes clear why a single optimization strategy is awkward.

### Slide 6 — Why shared GPU pools are a compromise
- one pool, two conflicting optimization goals

**Suggested visual:** one shared GPU pool being pulled in two directions.

**Speaker note:**
- This is the first “pain” slide.
- Land the message: one workload, two resource profiles, one unhappy pool.

### Slide 7 — What goes wrong in practice
- overprovisioning
- unstable TTFT
- poor utilization under mixed traffic

**Suggested visual:** 3-callout layout with TTFT spike, low utilization, wasted headroom.

**Speaker note:**
- Make the problem concrete for platform teams.
- Use examples they would recognize from dashboards.

### Slide 8 — What P/D disaggregation changes
- separate prefill and decode pools
- independent scaling
- KV handoff becomes required

**Suggested visual:** before/after architecture mini-diagram.

**Speaker note:**
- Introduce both the benefit and the cost.
- Do not oversell; mention the KV handoff complexity immediately.

### Slide 9 — Why P/D is still hard on Kubernetes
- topology-aware routing and endpoint selection
- KV transfer protocol and data path validation
- decode-side sidecar lifecycle
- targetPort / env / label contracts
- role-specific autoscaling and startup ordering

**Suggested visual:** checklist or layered stack with many moving parts.

**Speaker note:**
- Emphasize orchestration complexity.
- Make this sound concrete, not abstract: this is where manual wiring starts to hurt.
- This sets up why an abstraction layer matters.

### Slide 10A — Open-source P/D: several paths, different abstractions

> Rendered as slide 9 in the 38-slide PowerPoint, followed by the integration rationale on slide 10. Outline numbering below is retained for existing references; the generator controls final presentation order.

| Approach | Serving / routing path | Kubernetes packaging |
| --- | --- | --- |
| NVIDIA Dynamo | Integrated inference stack | Operator + DynamoGraphDeployment |
| llm-d | P/D-aware EPP + routing sidecar | Gateway API / InferencePool |
| AIBrix | P/D-aware gateway + engines | StormService / RoleSet |
| KServe + llm-d | llm-d serving integration | LLMInferenceService |
| Ray Serve + KubeRay | P/D application + vLLM KV connectors | RayService + Serve configuration |
| vLLM Production Stack | vLLM + LMCache / NIXL + router | Helm-managed P/D deployment |

Also relevant: **LWS DisaggregatedSet** declaratively orchestrates roles as child LeaderWorkerSets; engines and KV transport remain separate.

**Takeaway:** Declarative APIs already exist. The opportunity is simpler integration—not the first CRD.

**Visual:** editable three-column landscape table, with a separate workload-controller callout.

**Speaker notes:**
- Representative capabilities, not an adoption, maturity, or performance ranking. Projects overlap and can be composed.
- KServe wraps llm-d rather than providing a competing underlying P/D engine. Dynamo and AIBrix also have declarative Kubernetes orchestration.
- SGLang/vLLM/TensorRT-LLM are engines; NIXL/LMCache/Mooncake are transport or cache building blocks, not standalone Kubernetes serving platforms.
- Check actual releases: latest documentation can include alpha/new capabilities. This comparison does not establish production readiness.

### Slide 10B — Why llm-d is the best fit for KAITO’s P/D integration

**Scope:** for teams choosing KAITO’s Kubernetes operating model—not a universal best-platform claim.

**Composition diagram:** KAITO (MRI → child InferenceSets) + llm-d (EPP + decode routing sidecar) + vLLM/NIXL (execution + KV movement). This is not a request-flow sequence.

- **Reuse the API model:** retain Workspace/InferenceSet and extend to role-specific replicas, GPU instance types and runtime settings.
- **Integrate, do not rebuild:** reuse llm-d’s P/D endpoint selection and request orchestration; KAITO supplies sidecar, port and InferencePool wiring.
- **Clear ownership:** use Gateway API/InferencePool boundaries, retain upstream routing plugins, and avoid adding a second serving platform API alongside KAITO.

**Takeaway:** KAITO owns deployment intent and lifecycle; llm-d supplies reusable inference routing.

**Speaker notes:**
- This is a best-fit architectural judgment for extending KAITO, not a measured latency/throughput/cost comparison.
- KServe and AIBrix remain valid orchestration alternatives; Dynamo is an integrated stack; Ray Serve suits Ray-centric applications. Their existing users need not migrate solely for P/D.
- KAITO’s documented implementation already creates child InferenceSets, an InferencePool and EPP; it injects a decode routing sidecar and configures the vLLM NIXL side channel.
- Current documented scope is alpha MRI, vLLM and Istio, with suitable GPU connectivity for KV transfer. Gateway/HTTPRoute, TLS, capacity and fabric preparation remain platform responsibilities.
- Independent role replica settings are not an automatic MRI-level scaling policy. Keep current KEDA/InferenceSet support separate from the proposed MRI scaling-policy UX.

**Official references for both slides (checked 2026-10-20):**
- [KAITO P/D implementation and limitations](https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation/)
- [llm-d architecture](https://llm-d.ai/docs/architecture)
- [Dynamo Kubernetes deployment](https://docs.nvidia.com/dynamo/v1.1.0/getting-started/kubernetes-deployment)
- [AIBrix P/D routing](https://aibrix.readthedocs.io/latest/features/gateway-routing/pd-disaggregation.html) and [StormService](https://aibrix.readthedocs.io/latest/designs/aibrix-stormservice.html)
- [KServe LLMInferenceService](https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview)
- [Ray Serve P/D](https://docs.ray.io/en/latest/serve/llm/user-guides/prefill-decode.html)
- [vLLM Production Stack P/D](https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/disaggregated-prefill.html)
- [LWS DisaggregatedSet](https://lws.sigs.k8s.io/docs/concepts/disaggregatedset/)

### Slide 11 — What KAITO is
- Kubernetes-native AI operator
- control-plane abstraction from model serving to distributed inference
- API-first workflow built around `Workspace`, `InferenceSet`, `InferencePool`, and `MultiRoleInference`

**Suggested visual:** a simple object ladder: `Workspace` -> `InferenceSet` -> `InferencePool` -> `MultiRoleInference`.

**Speaker note:**
- This is the first real KAITO definition slide.
- Say clearly that KAITO is the Kubernetes-facing abstraction layer.
- A nice line here is: “KAITO is not just for serving one model; it gives you an upgrade path from basic serving to richer inference topologies.”

### Slide 12 — KAITO’s object model in one view
- `Workspace` = run a model workload
- `InferenceSet` = scale replicas and attach autoscaling
- `InferencePool` = connect serving backends to inference-aware routing
- `MultiRoleInference` = express richer topologies like P/D as one logical service

**Suggested visual:** a 4-layer ladder or staircase: serving -> scaling -> routing -> topology.

**Speaker note:**
- This page should make KAITO feel concrete.
- Show how its API surface grows with the problem instead of just calling it “an operator.”
- A good line here is: “KAITO adds higher-level Kubernetes objects as the serving topology gets more sophisticated.”

### Slide 13 — KAITO starts with serving: `Workspace`
- the basic workload entrypoint for model serving and tuning
- good mental model: one model workload, one Kubernetes object
- the place where KAITO begins before scaling and routing enter the picture

**Suggested visual:** one `Workspace` object mapping to one serving workload.

**Speaker note:**
- Keep this simple.
- The audience should understand that KAITO does not start with P/D; it starts with ordinary model serving.
- That makes the later distributed-inference story feel like an extension, not a different product.

### Slide 14 — KAITO scales serving: `InferenceSet` + `InferencePool`
- `InferenceSet` adds replicas and autoscaling
- `InferencePool` adds inference-aware routing through GWIE
- together, they move KAITO from “run a model” to “operate a serving system”

**Suggested visual:** one `Workspace` expanding into an `InferenceSet`, then attaching to an `InferencePool`.

**Speaker note:**
- This is where KAITO starts to look like a serving platform, not just a deployment helper.
- Emphasize that routing and scaling are first-class objects, not afterthought YAML.

### Slide 15 — KAITO extends naturally to distributed inference
- `MultiRoleInference` is the object for richer topologies
- one logical service can expand into prefill and decode backends
- the same Kubernetes object model continues even when the topology becomes distributed

**Suggested visual:** `Workspace` -> `InferenceSet` / `InferencePool` -> `MultiRoleInference` with prefill/decode branches.

**Speaker note:**
- This is the transition slide from “what KAITO is” to “why KAITO matters for P/D.”
- The key idea is continuity: same platform, richer topology.

### Slide 16 — Why KAITO matters here
- turns topology into declarative APIs
- gives users a continuous path from `Workspace` to `InferenceSet` to `InferencePool` to `MultiRoleInference`
- synthesizes lower-level objects automatically
- keeps the same platform model even as the topology becomes distributed

**Suggested visual:** CRD progression or pipeline: `Workspace` -> `InferenceSet` -> `InferencePool` -> `MultiRoleInference` -> generated child objects.

**Speaker note:**
- Explain the operator value.
- This is where you shift from problem framing to product value.
- The important framing is not just “KAITO hides complexity”; it is “KAITO gives you a clean Kubernetes path as the inference topology gets more advanced.”
- That continuity is what makes P/D feel like an extension of serving, not a completely separate system.

### Slide 17 — What the llm-d Router brings to the stack
- EPP implementation for the GWIE flow
- model-aware and role-aware endpoint selection
- KV-cache-aware and P/D-aware plugin chain
- the routing intelligence KAITO builds on

**Suggested visual:** llm-d Router EPP box with plugin labels around it.

**Speaker note:**
- This slide should answer one question only: **what new capability does llm-d add?**
- Explain that KAITO is not inventing its own routing algorithm here; it is building on llm-d Router as the EPP implementation and scheduling substrate.
- Mention that this gives KAITO room to grow into richer inference topologies later.

### Slide 18 — Why all three: KAITO + GWIE + llm-d Router
- KAITO = declarative abstraction and orchestration
- GWIE = Kubernetes-native contract between gateway and inference backends
- llm-d Router = routing intelligence and P/D-aware scheduling
- InferencePool = the contract surface that binds them together

**Suggested visual:** layered diagram with explicit separation of concerns.

**Speaker note:**
- This slide should answer “why all three?” very clearly.
- Use a simple progression: **llm-d gives the routing brain, GWIE gives the Kubernetes routing contract, and KAITO turns the whole thing into a usable platform workflow.**
- Be precise here: KAITO still uses GWIE objects and integration patterns, but it does **not** rely on GWIE’s reference routing implementation for P/D behavior.
- Keep this slide conceptual; save the concrete topology for the next page.

### Slide 19 — End-to-end architecture diagram
- client request enters through the gateway
- gateway targets an InferencePool (GWIE contract surface)
- llm-d Router EPP selects decode and, when needed, prefill
- KAITO-managed child InferenceSets provide the actual prefill/decode backends
- KV data moves directly between prefill and decode
- one user endpoint, multiple coordinated runtime paths

**Suggested visual:** full architecture diagram; this is one of the anchor slides.

**Speaker note:**
- This is the concrete payoff slide for 17 and 18.
- Show the audience where each piece from the previous slides lands in the real architecture.
- Make the child InferenceSets visible so the audience sees the real KAITO object model.
- Keep returning to this diagram when later slides discuss request flow or autoscaling.

### Slide 20 — What MultiRoleInference declares
- one logical inference service
- two roles
- role-specific scaling and runtime behavior
- a single user-facing object for the whole P/D topology

**Suggested visual:** small YAML snippet or CRD field summary.

**Speaker note:**
- Show the API intent before the generated objects.
- Focus on user intent, not every field.
- This is a good place to say the user experience starts with one object, not a pile of hand-wired components.

### Slide 21 — What MultiRoleInference generates
- child InferenceSet for prefill
- child InferenceSet for decode
- decode-side llm-d routing sidecar injection
- one InferencePool with correct targetPort wiring
- llm-d Router EPP deployment and plugin chain
- per-role autoscaling hooks via child InferenceSets

**Suggested visual:** generated-object tree or exploded diagram from the CRD.

**Speaker note:**
- Show what KAITO creates for the user.
- This is where “one CRD generates the stack” should feel real.
- If possible, visually distinguish “user creates one MRI” from “KAITO synthesizes multiple child objects.”
- This is one of the strongest “abstraction value” slides in the deck.

### Slide 22 — Why the decode-side sidecar exists
- stable client-facing entrypoint on port 5000
- internal prefill coordination
- local decode remains stream owner on vLLM port 5001

**Suggested visual:** decode pod diagram with sidecar and local vLLM ports.

**Speaker note:**
- This is a good concrete implementation slide.
- Explain why the sidecar placement is deliberate, not accidental.
- Say that this is one of those details that is easy to hand-wire incorrectly and valuable to standardize.

### Slide 23 — Request flow, part 1
- request enters gateway
- gateway targets the InferencePool
- llm-d Router EPP decides whether prefill work is needed
- decode endpoint is selected

**Suggested visual:** sequence diagram, phase 1 only.

**Speaker note:**
- Animate this if possible.
- Keep this slide narrowly focused on entry, decision, and endpoint choice.
- Mention the P/D-aware scheduling profile and decider only briefly, as proof that the routing logic is specialized.

### Slide 24 — Request flow, part 2
- decode-side sidecar coordinates prefill
- prefill builds KV cache
- KV moves pod-to-pod via NIXL
- local decode streams output

**Suggested visual:** sequence diagram, phase 2 continuation.

**Speaker note:**
- Keep it stepwise, not all at once.
- This is where the audience should see why the topology is helpful but nontrivial.
- Make clear that the gateway is not shuttling KV cache; the data path is directly between pods.

### Slide 25 — Why KV transfer matters
- P/D is only useful if KV movement is fast and reliable
- validate the transfer path and side-channel setup early in production

**Suggested visual:** KV transfer path callout, maybe with “critical path” highlighted.

**Speaker note:**
- This is a good operational-truth slide.
- Explicitly say this is one of the first things to validate in real deployments.
- If this path is wrong, the theoretical benefit of P/D disappears quickly.

### Slide 26 — Why CPU-era autoscaling breaks for LLM inference
- traditional Kubernetes autoscaling often assumes CPU or memory are the main pressure signals
- LLM serving is usually bottlenecked by queue depth, token generation pressure, active KV memory, and prompt/generation mix
- you can have low CPU and still have terrible TTFT or blocked requests
- scaling on CPU alone misses the actual user-facing bottleneck

**Suggested visual:** side-by-side: classic web-service HPA signals vs LLM inference signals.

**Speaker note:**
- This is the key motivation slide for the autoscaler section.
- Be direct: CPU-era autoscaling logic came from web workloads, not GPU-bound inference systems.
- A useful line is: “LLM serving fails in ways CPU graphs often do not show.”

### Slide 27 — Why KEDA fits modern inference workloads
- KEDA is event-driven and works with external metrics and triggers
- that makes it a much better fit for inference queues and model-serving signals than CPU-only scaling
- it can support both metric-based scaling and time-based scaling
- this is the reason KAITO leans on KEDA for inference autoscaling

**Suggested visual:** KEDA in the middle with external metrics / cron triggers feeding scaling decisions.

**Speaker note:**
- Don’t get too deep into KEDA internals.
- The audience mainly needs the conceptual shift: from generic resource proxies to workload-aware scaling signals.

### Slide 28 — KEDA autoscales a KAITO InferenceSet

**Takeaway:** KEDA and the KAITO external scaler provide direct-metric autoscaling for one InferenceSet; independent prefill/decode scaling is the next step.

**On-slide copy:**

- The KAITO external scaler reads vLLM metrics directly—no Prometheus required.
- InferenceSet annotations enable autoscaling and select the metric + target.
- The KAITO scaler creates a ScaledObject and scrapes vLLM inference pods.
- KEDA manages an HPA; HPA sets replicas through the InferenceSet `/scale` API.
- KAITO reconciles the desired number of inference replicas.
- Guide example: average `vllm:num_requests_waiting`, target **10**, maximum **5** replicas.
- Scheduled scaling is separate: built-in KEDA cron + manually configured ScaledObject; no dedicated KAITO scaler needed.

**Visual:** Left-to-right control flow: annotated InferenceSet → KAITO external scaler → KEDA + HPA → KAITO operator. Below it, show the guide’s waiting-request metric example and a separate cron option.

**Speaker notes:**

KAITO supports annotation-driven, metric-based autoscaling of an InferenceSet with KEDA and the dedicated KEDA KAITO external scaler. The external scaler reads scaledobject.kaito.sh/* annotations, automatically provisions the ScaledObject, and scrapes vLLM metrics directly from the associated inference pods. No separate Prometheus deployment is required for this integration. KEDA creates/manages the HPA; the Kubernetes HPA controller updates the InferenceSet /scale subresource, and KAITO reconciles the desired inference replicas.

The guide’s example aggregates vllm:num_requests_waiting using average, with threshold/target 10 and maxReplicaCount 5. These are illustrative settings, not universal defaults or a fixed scaling-time guarantee. HPA stabilization, scaling policies, and workload readiness also affect observed scaling. Configure annotation keys and API versions for the deployed KAITO/scaler release; the guide and scaler repository can differ.

Scheduled scaling is a separate option: a manually authored ScaledObject can use KEDA’s built-in cron trigger against the InferenceSet. It does not require the dedicated KAITO scaler. Do not describe the direct-metrics integration as a Prometheus-query path.

Scaling here changes one InferenceSet replica count. Independent prefill/decode replica control is the proposed next step, not an existing capability demonstrated by this example.

**Speaker script:**

Let’s look at how KAITO integrates with KEDA today. For metric-based scaling, we enable autoscaling on an InferenceSet through annotations. The dedicated KEDA KAITO external scaler uses those annotations to create a ScaledObject automatically.

The scaler reads vLLM metrics directly from the inference pods, so this path does not require a separate Prometheus deployment. KEDA manages an HPA, which updates the InferenceSet’s desired replica count through its scale API. KAITO then reconciles the inference replicas.

The guide’s example uses the average number of waiting requests as the scaling signal, with a target of ten and a maximum of five replicas. That is a queue-pressure signal, not GPU utilization and not request rate.

For predictable traffic, KEDA’s built-in cron trigger is another option. That uses a manually configured ScaledObject and does not need the dedicated KAITO scaler.

The important boundary is that this scales one InferenceSet as a unit. It does not yet give us independent prefill and decode scaling. That is the next step we will look at.

**Sources:**

- https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference/
- https://github.com/kaito-project/keda-kaito-scaler
- https://keda.sh/docs/2.18/concepts/scaling-deployments/#scaling-custom-resources

---

### Slide 29 — Independent autoscaling by role in P/D
- in P/D, prefill and decode should not share one scaling signal
- prefill example metric: `vllm:num_requests_waiting`
- decode example signals: KV/cache pressure or sustained decode saturation
- the clean UX is for MRI to express per-role intent and map it to child `InferenceSet`s

**Suggested visual:** two side-by-side scaling graphs, plus a small “MRI -> child InferenceSets -> ScaledObjects” flow.

**Speaker note:**
- Keep this very practical.
- Say: “once prefill and decode are separate backends, they should scale like separate backends.”
- Then add the UX point: users should express that once at the MRI layer, not by hand-authoring multiple ScaledObjects.

### Slide 30 — Why this abstraction helps operators
- fewer manually coordinated objects
- fewer implicit contracts around ports / labels / env / targetPort wiring
- one user-facing MRI object instead of hand-wired child resources
- easier to reason about desired topology

**Suggested visual:** “manual plumbing” vs “declarative abstraction” comparison.

**Speaker note:**
- Bring the value back to the platform team audience.
- Mention that abstraction is not about hiding power; it is about making the topology operable.
- This is a good place to say the user should reason about topology and policy, not every plumbing detail.

### Slide 31 — Evaluation results: TTFT
- colocated vs disaggregated
- explain which workloads gain most

**Suggested visual:** one clean TTFT chart with 1-2 highlighted takeaways.

**Speaker note:**
- One chart, one interpretation.
- Highlight prompt-length-sensitive gain rather than narrating every series.
- Resist the urge to explain every line.

**Public evidence used in the PPTX (actual slide 40):** the [vLLM MORI-IO study](https://vllm.ai/blog/2026-04-07-moriio-kv-connector) supplies exact per-request TTFT arrays. These show a TTFT penalty, not a gain, with P/D at fixed 2K/1K and 8 req/s; no prompt-length sweep was published. The slide preserves this trade-off.

### Slide 32 — Evaluation results: throughput
- compare throughput under mixed load

**Suggested visual:** throughput chart with one highlighted region where separation helps.

**Speaker note:**
- Keep narration high signal.
- Tie the result back to earlier “two workloads, one pool” framing.
- Mixed-load behavior matters more here than peak synthetic throughput.

**Public evidence used in the PPTX (actual slide 41):** the same report provides a SLO-attainment-versus-offered-rate curve. The slide highlights 8 req/s without relabeling attainment as measured tokens/s. This is concurrent P/D activity at fixed lengths, not a heterogeneous mixed-traffic result.

### Slide 33 — Evaluation results: utilization / efficiency
- show GPU utilization or capacity efficiency under asymmetric traffic

**Suggested visual:** utilization bars, efficiency table, or stacked pool usage chart.

**Speaker note:**
- Reinforce the “why separate pools” message.
- Tie this to capacity efficiency and, if the data supports it, fewer total GPUs needed.
- This is the business/operations payoff slide.

**Public evidence used in the PPTX (actual slide 42):** an explicitly labeled SLO-pass/GPU efficiency proxy derived from the same fixed-eight-GPU run. No GPU-utilization, asymmetric-traffic or GPU-count reduction claim is made. See [source provenance and calculations](kubecon-pd-assets/benchmarks/README.md).

### Slide 34 — When to use P/D, and when not to

Use a real decision matrix here instead of a generic pros/cons list.

**Recommended 2x2:**
- **X-axis:** KV-transfer cost / fabric quality
  - left = transfer is expensive, cross-node, or unreliable
  - right = transfer is cheap and fast enough
- **Y-axis:** how different prefill and decode really are
  - bottom = similar bottlenecks / similar scaling behavior
  - top = different bottlenecks, scaling behavior, or parallelism choices

|  | **KV transfer expensive / weak** | **KV transfer cheap / strong** |
|---|---|---|
| **Prefill and decode are similar** | **Stay aggregated**<br>Small models, short prompts, low concurrency, simple traffic. | **Usually stay aggregated**<br>You can try P/D, but the operational gain is often limited. |
| **Prefill and decode are meaningfully different** | **Maybe later / only with topology improvements**<br>There may be value in P/D, but the transfer path is likely to erase it. First improve locality, transport, or keep prefill/decode on the same node. | **Strong candidate for P/D**<br>Long prompts, retrieval-heavy traffic, long generations, high concurrency, or different scaling/parallelism needs. |

**Suggested visual:** a clean 2x2 matrix with the top-right quadrant highlighted in green and the bottom-left quadrant greyed out.

**Speaker note:**
- This is a better trust-building slide than a blanket recommendation.
- The audience should leave with one rule of thumb: **use P/D when prefill and decode want different shapes, and KV transfer is cheap enough not to erase the gain.**
- If you want one practical simplification: **single-node multi-GPU is the easiest place to win first; cross-node P/D raises the bar because the KV path matters much more.**

### Slide 35 — Production lessons
- startup ordering matters
- decode-side sidecar placement rules matter
- service / targetPort / label contracts matter
- KV transfer path and side-channel setup must be verified early

**Suggested visual:** four callout boxes or checklist slide.

**Speaker note:**
- Give practical advice, not just architecture.
- Make this feel like “here is what we learned the hard way.”
- This is a strong slide to leave platform engineers with something usable.

### Slide 36 — What’s next for KAITO + llm-d
- near term: precise prefix-cache routing based on KV events
- near term: tiered prefix cache across HBM, CPU RAM, and optional filesystem tiers
- next topology: E/P/D
- larger-scale systems: Wide Expert Parallelism and richer cross-node transport optimization

**Suggested visual:** roadmap slide with “current / next / later” swimlanes.

**Speaker note:**
- End with a concrete roadmap, not a vague future-work cloud.
- This is where you connect today’s P/D story to tomorrow’s richer inference topologies.

### Deck production notes
- Keep most slides to **one sentence headline + one diagram/chart + 2-3 bullets max**.
- Treat the numbered slides below as **modular blocks**, not a fixed page count.
- Slides 19, 23, 24, and 31-33 are the likely visual anchors of the deck.
- If you want a shorter version, the easiest merges are: 11+12, 13+14+15, 23+24, 26+27+28, and 31+32+33.
- If time runs short, Slides 15, 30, and part of 33 can be compressed quickly without losing the main story.
- If the benchmark section is weak, spend more time on Slides 16-30 and make the architecture + autoscaling story the center of gravity.

---

## Suggested Opening (30 seconds)

From the outside, LLM inference looks like one workload. But operationally, it’s really two different problems. Prefill wants compute and low latency. Decode wants memory bandwidth and steady throughput. If we force both into one GPU pool, we end up compromising both. So the question for this talk is: can we separate those phases in a way that actually feels native on Kubernetes? That’s where KAITO, GWIE, and llm-d come in.

---

## Suggested Closing (20-30 seconds)

The big idea here is not just that prefill and decode can be separated. It’s that advanced inference topologies need to become normal, operable Kubernetes patterns. KAITO is the layer that makes that possible. GWIE and llm-d provide the routing contract and the scheduling intelligence underneath. And from here, the direction is pretty clear: better cache-aware routing, cleaner per-role autoscaling, and support for even richer topologies beyond basic P/D.

---

## What to Cut from the 35-Minute Version

To fit 20 minutes, reduce or remove:

- long ecosystem background
- deep internal details of every component
- too much llm-d / Gateway API internals
- low-level port/env examples on slides
- large future-work section
- live demo unless it is extremely polished and guaranteed to fit

---

## What Must Stay

Do not cut these:

- the resource-profile difference between prefill and decode
- why colocated serving is suboptimal
- why orchestration complexity is the blocker
- what KAITO MultiRoleInference abstracts away
- why CPU-era autoscaling is a poor fit for LLM inference
- why KEDA / KAITO autoscaling is part of the story, not an appendix
- at least one page of evaluation results
- explicit guidance on when to use P/D

---

## Optional Variants

### Variant A — Architecture-first (recommended)
Best when the audience is mixed and time is tight.

- stronger on problem framing
- lighter on demo
- easier to keep on schedule

### Variant B — Demo-first
Best only if the demo is reliable and extremely compact.

- deployment YAML
- scale event
- quick metrics view
- one benchmark chart

Recommendation: use **Variant A** for the actual co-located talk.

---

## Reference Docs to Keep This Deck Aligned with KAITO

These are the official KAITO docs that should continue to anchor this deck's terminology, architecture, and user-experience claims:

1. **Gateway API Inference Extension with llm-d Router**  
   <https://kaito-project.github.io/kaito/docs/gateway-api-inference-extension>
   - Use this as the source for how to describe:
     - `InferencePool`
     - Gateway API Inference Extension (GWIE)
     - the llm-d Router as the EPP implementation
     - model-aware / cache-aware endpoint selection

2. **Prefill/Decode Disaggregation**  
   <https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation>
   - Use this as the source for how to describe:
     - `MultiRoleInference`
     - child `InferenceSet` generation for prefill and decode
     - decode-side routing sidecar behavior
     - NIXL-based pod-to-pod KV transfer
     - the concrete request flow and port model

3. **KEDA Auto-Scaler for inference workloads**  
   <https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference>
   - Use this as the source for how to describe:
     - `InferenceSet` as the natural autoscaling target
     - KEDA + keda-kaito-scaler integration
     - metric-based scaling UX
     - why P/D should expose clean per-role autoscaling through child `InferenceSet`s instead of forcing users to hand-author role-specific `ScaledObject`s

### Where these references should show up in the deck

- **Slides 14-16** → GWIE + llm-d Router positioning
- **Slides 17-21** → MultiRoleInference user experience and request flow
- **Slides 23-24** → KEDA / autoscaling UX for P/D
- **Slides 29-30** → production lessons and future integration direction

### Related conference talk

- [From Model Serving to Distributed Inference: How Llm-d Evolves AI Platforms on Kubernetes](https://www.youtube.com/watch?v=TXKfWGdns9s) — Kay Yan (DaoCloud) and Linbo He (Microsoft), KubeCon + CloudNativeCon Japan 2026.

## Next Draft Ideas

Possible follow-up artifacts from this outline:

1. a full slide-by-slide deck draft
2. speaker notes for each slide
3. a 5-minute lightning version
4. a polished abstract for the event page
5. a version aligned to actual benchmark screenshots/data


### Expanded motivation in the PPTX

Actual slides **7–9** expand why P/D can help. Slides **7–8** are now original native editable **conceptual diagrams, not benchmark results**: (7) shared-GPU prefill can delay ongoing decode, contrasted with separate-worker lanes; (8) editable token tiles contrast prompt-position versus active-sequence batching units. Their basis is the [NVIDIA Dynamo introduction, 18 March 2025](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/) and [current disaggregated-serving docs](https://docs.nvidia.com/dynamo/kubernetes/disaggregated-serving/overview), accessed 22 October 2026. No timings, optimal batch sizes, speedups or KAITO measurements are implied. Chunked prefill can mitigate colocated interference; separation removes direct prefill execution from the decode GPU, not all jitter. Slide 9 retains the independent-capacity discussion and workload-dependent bottleneck caveats. The former 2024 DistServe plots are archived, not relabeled or embedded. See [provenance and interpretation boundaries](kubecon-pd-assets/motivation/README.md). Prose labels throughout the PPTX use sentence case while technical acronyms, API names and code keep their exact capitalization.

### Prefill and decode foundations in the PPTX

Actual slides **3–4** explain a standard cached decoder-only Transformer before discussing disaggregation. All diagrams, table cells, arrows and labels remain native editable PowerPoint objects.

**Exact prompt:** `What does Kubernetes do?`

**Exact illustrative output:** `Kubernetes helps teams deploy and scale applications.`

#### Simple word-level teaching example

**Illustrative word-level tokens; not a real model tokenizer.** Assume one complete English word per token for this explanation; punctuation occupies a separate position. Spaces separate the displayed words and are not extra positions. This keeps “Kubernetes” intact so the audience can focus on prefill and decode rather than tokenization.

- Prompt positions: `What | does | Kubernetes | do | ?` (four words plus punctuation).
- Output positions: `Kubernetes | helps | teams | deploy | and | scale | applications | .` (seven words plus punctuation).

These are schematic tokens, **not actual Qwen tokens or a claim that typical production LLMs use word-level tokenization**. Real tokenizers can split words into subwords and handle whitespace/punctuation differently. The sentence is authored for teaching; **no tokenizer or model inference was run** for this example. The generator defines these word sequences directly and does not load a tokenizer manifest.

#### Phase and cache semantics

1. **Prefill:** process the 5 uncached prompt positions with a causal mask, build per-layer attention keys and values, then use final-position logits to select y1 = `Kubernetes` along this illustrative path. Immediately after selection, the cache contains prompt KV, **not** K/V for y1.
2. **Decode:** consume a selected token with past KV, append K/V for that consumed token, and select the next:

   | Step | Consume | Append to per-layer KV | Select next |
   | --- | --- | --- | --- |
   | 1 | y1 = Kubernetes | K/V for y1 | y2 = helps |
   | 2 | y2 = helps | K/V for y2 | y3 = teams |
   | 3 | y3 = teams | K/V for y3 | y4 = deploy |
   | 4 | y4 = deploy | K/V for y4 | y5 = and |
   | 5 | y5 = and | K/V for y5 | y6 = scale |
   | 6 | y6 = scale | K/V for y6 | y7 = applications |

   After row 6, output KV covers y1–y6; y7 is selected but not consumed/cached. The omitted final step consumes y7 = `applications` and selects y8 = `.`. If generation continued, consuming the period could select EOS. EOS normally is hidden and need not be consumed into KV when stopping; output limits and stop strings are alternatives. No EOS ID or actual model decision is asserted.
3. **Client timing:** the first six word arrivals illustrate request → first token (**TTFT**, the first word in this schematic) and five successive **ITL** gaps. Later arrivals are omitted; the timeline is not to scale. In real systems the first token need not be a complete word. Queueing, transport, detokenization and buffering affect observed timing, and stream chunks can group multiple tokens.

KV reuse avoids recomputing old K/V, but full-context attention still reads cached history. Notes qualify chunked prefill, prefix caching, static/sliding-window caches, ordinary autoregressive versus speculative decoding, and worker boundaries. These phase definitions do not assign first-token selection or delivery to a particular worker.

Reference: [Hugging Face Transformers — How caching works](https://huggingface.co/docs/transformers/en/cache_explanation).

The previous real-Qwen tokenization example is retained as an [archival optional reference](kubecon-pd-assets/tokenization/README.md); it is not used by the current slides or generator.
