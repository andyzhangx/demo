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
  - **next topology:** E/P/D and speculative decoding
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
- prefill
- decode

**Suggested visual:** very simple request timeline with prefill then decode.

**Speaker note:**
- Keep this simple and visual.
- Do not go deep into internals yet.

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

### Slide 10 — Existing approaches in the ecosystem
- NVIDIA Dynamo: powerful, but tightly coupled to the NVIDIA stack
- llm-d standalone: Kubernetes-native, but still operationally manual
- need for a declarative Kubernetes abstraction layer on top

**Suggested visual:** simple ecosystem map, not a competitive matrix.

**Speaker note:**
- Keep this balanced and brief.
- The point is not who is better; the point is where the abstraction gap still exists.

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
- Instead of saying what KAITO is not, show how its API surface grows with the problem.
- A good line here is: “KAITO adds higher-level Kubernetes objects as the serving topology gets more sophisticated.”

### Slide 13 — Why KAITO matters here
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

### Slide 14 — What the llm-d Router brings to the stack
- EPP for Gateway API Inference Extension
- model-aware and role-aware endpoint selection
- KV-cache-aware and P/D-aware plugin chain
- future advanced scheduling surface

**Suggested visual:** llm-d Router EPP box with plugin labels around it.

**Speaker note:**
- Explain that Gateway API Inference Extension gives the abstraction pattern, and the llm-d Router provides the advanced EPP implementation KAITO uses.
- Mention that this gives KAITO room to grow into richer inference topologies later.

### Slide 15 — KAITO + llm-d Router + GWIE: division of labor
- KAITO = declarative abstraction / orchestration
- Gateway API Inference Extension = inference routing contract
- llm-d Router = routing / scheduling substrate
- InferencePool connects the gateway and the serving backends

**Suggested visual:** layered diagram with explicit separation of concerns.

**Speaker note:**
- This slide should answer “why all three?” very clearly.
- Say explicitly: GWIE gives the Kubernetes-native routing pattern, llm-d Router supplies the smart EPP, and KAITO makes the topology operable for platform teams.
- If the audience only remembers one stack diagram, let it be this one or Slide 16.

### Slide 16 — End-to-end architecture diagram
- client
- gateway
- InferencePool
- llm-d Router EPP
- prefill child InferenceSet
- decode child InferenceSet
- KV path

**Suggested visual:** full architecture diagram; this is one of the anchor slides.

**Speaker note:**
- This is the main reference diagram for the rest of the talk.
- Make the child InferenceSets visible so the audience sees the real KAITO object model.
- Keep returning to it when later slides discuss request flow or autoscaling.

### Slide 17 — What MultiRoleInference declares
- one logical inference service
- two roles
- role-specific scaling and runtime behavior
- a single user-facing object for the whole P/D topology

**Suggested visual:** small YAML snippet or CRD field summary.

**Speaker note:**
- Show the API intent before the generated objects.
- Focus on user intent, not every field.
- This is a good place to say the user experience starts with one object, not a pile of hand-wired components.

### Slide 18 — What MultiRoleInference generates
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

### Slide 19 — Why the decode-side sidecar exists
- stable client-facing entrypoint on port 5000
- internal prefill coordination
- local decode remains stream owner on vLLM port 5001

**Suggested visual:** decode pod diagram with sidecar and local vLLM ports.

**Speaker note:**
- This is a good concrete implementation slide.
- Explain why the sidecar placement is deliberate, not accidental.
- Say that this is one of those details that is easy to hand-wire incorrectly and valuable to standardize.

### Slide 20 — Request flow, part 1
- request enters gateway
- gateway targets the InferencePool
- llm-d Router EPP decides whether prefill work is needed
- decode endpoint is selected

**Suggested visual:** sequence diagram, phase 1 only.

**Speaker note:**
- Animate this if possible.
- Keep this slide narrowly focused on entry, decision, and endpoint choice.
- Mention the P/D-aware scheduling profile and decider only briefly, as proof that the routing logic is specialized.

### Slide 21 — Request flow, part 2
- decode-side sidecar coordinates prefill
- prefill builds KV cache
- KV moves pod-to-pod via NIXL
- local decode streams output

**Suggested visual:** sequence diagram, phase 2 continuation.

**Speaker note:**
- Keep it stepwise, not all at once.
- This is where the audience should see why the topology is helpful but nontrivial.
- Make clear that the gateway is not shuttling KV cache; the data path is directly between pods.

### Slide 22 — Why KV transfer matters
- P/D is only useful if KV movement is fast and reliable
- validate the transfer path and side-channel setup early in production

**Suggested visual:** KV transfer path callout, maybe with “critical path” highlighted.

**Speaker note:**
- This is a good operational-truth slide.
- Explicitly say this is one of the first things to validate in real deployments.
- If this path is wrong, the theoretical benefit of P/D disappears quickly.

### Slide 23 — Independent autoscaling by role
- today, KEDA already scales standard InferenceSet replicas well
- KAITO docs already show cron-based and metric-based autoscaling
- in P/D, prefill and decode should not share one scaling signal
- prefill example metric: `vllm:num_requests_waiting`
- decode example signals: KV/cache pressure or sustained decode saturation

**Suggested visual:** two side-by-side scaling graphs, plus a small “MRI -> child InferenceSets -> ScaledObjects” flow.

**Speaker note:**
- Keep this very practical.
- Say: “once prefill and decode are separate backends, they should scale like separate backends.”
- Then add the UX point: users should express that once at the MRI layer, not by hand-authoring multiple ScaledObjects.

### Slide 24 — Why this abstraction helps operators
- fewer manually coordinated objects
- fewer implicit contracts around ports / labels / env / targetPort wiring
- one user-facing MRI object instead of hand-wired child resources
- easier to reason about desired topology

**Suggested visual:** “manual plumbing” vs “declarative abstraction” comparison.

**Speaker note:**
- Bring the value back to the platform team audience.
- Mention that abstraction is not about hiding power; it is about making the topology operable.
- This is a good place to say the user should reason about topology and policy, not every plumbing detail.

### Slide 25 — Evaluation results: TTFT
- colocated vs disaggregated
- explain which workloads gain most

**Suggested visual:** one clean TTFT chart with 1-2 highlighted takeaways.

**Speaker note:**
- One chart, one interpretation.
- Highlight prompt-length-sensitive gain rather than narrating every series.
- Resist the urge to explain every line.

### Slide 26 — Evaluation results: throughput
- compare throughput under mixed load

**Suggested visual:** throughput chart with one highlighted region where separation helps.

**Speaker note:**
- Keep narration high signal.
- Tie the result back to earlier “two workloads, one pool” framing.
- Mixed-load behavior matters more here than peak synthetic throughput.

### Slide 27 — Evaluation results: utilization / efficiency
- show GPU utilization or capacity efficiency under asymmetric traffic

**Suggested visual:** utilization bars, efficiency table, or stacked pool usage chart.

**Speaker note:**
- Reinforce the “why separate pools” message.
- Tie this to capacity efficiency and, if the data supports it, fewer total GPUs needed.
- This is the business/operations payoff slide.

### Slide 28 — When to use P/D, and when not to

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

### Slide 29 — Production lessons
- startup ordering matters
- decode-side sidecar placement rules matter
- service / targetPort / label contracts matter
- KV transfer path and side-channel setup must be verified early

**Suggested visual:** four callout boxes or checklist slide.

**Speaker note:**
- Give practical advice, not just architecture.
- Make this feel like “here is what we learned the hard way.”
- This is a strong slide to leave platform engineers with something usable.

### Slide 30 — What’s next for KAITO + llm-d
- near term: precise prefix-cache routing based on KV events
- near term: tiered prefix cache across HBM, CPU RAM, and optional filesystem tiers
- next topology: E/P/D and speculative decoding
- larger-scale systems: Wide Expert Parallelism and richer cross-node transport optimization

**Suggested visual:** roadmap slide with “current / next / later” swimlanes.

**Speaker note:**
- End with a concrete roadmap, not a vague future-work cloud.
- This is where you connect today’s P/D story to tomorrow’s richer inference topologies.

### Deck production notes
- Keep most slides to **one sentence headline + one diagram/chart + 2-3 bullets max**.
- Treat the numbered slides below as **modular blocks**, not a fixed page count.
- Slides 16, 20, 21, and 25-27 are the likely visual anchors of the deck.
- If you want a shorter version, the easiest merges are: 3+4+5, 10+11+12, 20+21, and 25+26+27.
- If time runs short, Slides 12, 24, and part of 27 can be compressed quickly without losing the main story.
- If the benchmark section is weak, spend more time on Slides 15-24 and make the architecture story the center of gravity.

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

## Next Draft Ideas

Possible follow-up artifacts from this outline:

1. a full slide-by-slide deck draft
2. speaker notes for each slide
3. a 5-minute lightning version
4. a polished abstract for the event page
5. a version aligned to actual benchmark screenshots/data
