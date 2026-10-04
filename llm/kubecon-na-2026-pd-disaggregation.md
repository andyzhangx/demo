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

**Prefill/decode disaggregation** fixes this by placing the two phases on separate GPU pools. The challenge is not the idea itself — the challenge is the orchestration complexity: routing, KV cache transfer, sidecars, per-role autoscaling, ports, labels, and startup ordering.

The main value of **KAITO MultiRoleInference** is that it turns this complexity into a **Kubernetes-native declarative abstraction** built on top of llm-d, Gateway API Inference Extension, and KEDA.

### What KAITO is

For this talk, KAITO should be introduced plainly as:

> **KAITO is a Kubernetes-native AI operator and inference platform abstraction that helps users deploy, scale, and manage model-serving topologies with higher-level APIs instead of hand-wiring all runtime pieces themselves.**

In this specific story, KAITO is **not**:

- the base model server runtime itself
- the low-level routing scheduler itself
- a one-off demo script around vLLM

Its value is that it **packages complex inference topology into a declarative Kubernetes UX**:

- model-serving roles are described at the API layer
- child runtime objects are generated automatically
- llm-d routing pieces are wired in for scheduling
- autoscaling and role-specific runtime plumbing are integrated into one workflow
- users reason about topology and policy, not every individual sidecar, port, label, and service object

A good short phrasing for the talk is:

> **llm-d provides the advanced routing and scheduling layer; KAITO provides the Kubernetes-native abstraction and orchestration layer on top.**

If time allows, also mention that KAITO is meant to make advanced serving patterns look like normal Kubernetes operations:

- declare desired serving topology
- let controllers synthesize the lower-level objects
- keep the platform extensible as routing capabilities evolve underneath

That framing matters for the audience, because otherwise people may confuse KAITO with the runtime or with llm-d itself.

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
4. **Not every workload needs P/D; there is a clear break-even point.**

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
  - NVIDIA Dynamo: powerful, but more tightly coupled to the NVIDIA stack
  - llm-d standalone: Kubernetes-native direction, but still operationally manual
- Emphasize the real source of complexity:
  - topology-aware routing
  - KV cache transfer
  - sidecar lifecycle
  - role-specific autoscaling
  - port/env/label contracts
- Key message:
  - P/D is valuable, but the setup complexity blocks mainstream adoption

### 4) KAITO MultiRoleInference: the abstraction layer (7:00 - 12:30)
- First explain **what KAITO is**:
  - a Kubernetes-native abstraction layer for AI model serving and orchestration
  - not just another model server, but the layer that turns complex inference topologies into declarative APIs
- Show a simple architecture diagram:
  - client / gateway
  - prefill pool
  - KV cache handoff
  - decode pool
- Explain what a single MultiRoleInference CRD generates:
  - prefill StatefulSet
  - decode StatefulSet
  - llm-d routing pieces
  - InferencePool / Gateway API integration
  - KEDA ScaledObjects per role
- Highlight the design value:
  - users declare the topology they want
  - KAITO wires the plumbing automatically
- Mention a few implementation details only as proof points:
  - decode-only sidecar placement
  - port conventions
  - label contracts

### 5) Results: when P/D helps and when it does not (12:30 - 16:30)
- Show only the most convincing evaluation outputs:
  - TTFT comparison
  - throughput comparison
  - GPU utilization under mixed load
- Interpret the data rather than dumping charts
- Make the talk more credible by saying explicitly:
  - P/D is not automatically better for every workload
- Good fit:
  - long prompts
  - prefill-heavy or bursty traffic
  - TTFT-sensitive interactive workloads
  - environments where GPU efficiency matters
- Not always worth it:
  - small PoCs
  - short-prompt low-concurrency workloads
  - teams not ready to operate a more advanced inference topology

### 6) Production lessons + closing (16:30 - 20:00)
- Share a short list of practical lessons:
  - startup ordering matters
  - sidecar placement rules matter
  - KV transfer path must be validated early
  - autoscaling metrics must be role-specific
- Add a short **future integration roadmap** for KAITO + llm-d:
  - enable **precise prefix-cache routing** based on KV events rather than only approximate prefix matching
  - productize **tiered prefix cache** so routing and runtime can use HBM, CPU RAM, and optional filesystem-backed cache tiers more effectively
  - support **Wide Expert Parallelism** for larger MoE deployment topologies beyond today's first-class P/D flow
- Final takeaway:
  - the challenge is no longer whether P/D works
  - the challenge is how to make advanced inference topologies feel native on Kubernetes
- Close with next steps:
  - E/P/D
  - speculative decoding
  - more advanced transport / cross-node optimization
  - deeper KAITO integration with llm-d scheduling capabilities

---

## Suggested Slide-by-Slide Story

For a 20-minute co-located talk, **~30 slides can still work well** if most slides carry a single idea, use diagrams or short bullets, and advance quickly. That often feels better than 12-15 overloaded slides. Below is a **30-slide structure** that is closer to an actual deck draft: each slide includes the core message, a suggested visual, and the intended speaker emphasis.

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
- routing
- KV transfer
- per-role services
- autoscaling signals
- startup ordering

**Suggested visual:** checklist or layered stack with many moving parts.

**Speaker note:**
- Emphasize orchestration complexity.
- This sets up why an abstraction layer matters.

### Slide 10 — Existing approaches in the ecosystem
- NVIDIA Dynamo
- llm-d standalone
- need for a Kubernetes-native abstraction layer

**Suggested visual:** simple ecosystem map, not a competitive matrix.

**Speaker note:**
- Keep this balanced and brief.
- The point is not who is better; the point is where the abstraction gap still exists.

### Slide 11 — What KAITO is
- Kubernetes-native AI operator
- control-plane abstraction for serving topologies
- API-first workflow for model serving

**Suggested visual:** KAITO logo / box sitting above multiple runtime objects.

**Speaker note:**
- This is the first real KAITO definition slide.
- Say clearly that KAITO is the Kubernetes-facing abstraction layer.

### Slide 12 — What KAITO is not
- not the model server runtime itself
- not the low-level scheduler itself
- not just a YAML bundle around vLLM

**Suggested visual:** “KAITO is not...” three-column anti-confusion slide.

**Speaker note:**
- This avoids audience confusion early.
- It also protects you from people mentally flattening KAITO and llm-d together.

### Slide 13 — Why KAITO matters here
- turns topology into declarative APIs
- synthesizes lower-level objects automatically
- integrates scaling and routing workflow

**Suggested visual:** CRD -> generated objects pipeline.

**Speaker note:**
- Explain the operator value.
- This is where you shift from problem framing to product value.

### Slide 14 — What llm-d brings to the stack
- routing and scheduling plugins
- role-aware endpoint selection
- cache-aware decisions
- future advanced scheduling surface

**Suggested visual:** llm-d EPP box with plugin labels around it.

**Speaker note:**
- Explain llm-d as the scheduling layer underneath.
- Mention that this gives KAITO room to grow into richer inference topologies later.

### Slide 15 — KAITO + llm-d: division of labor
- KAITO = abstraction / orchestration
- llm-d = routing / scheduling
- Gateway API / InferencePool connect the layers

**Suggested visual:** layered diagram with explicit separation of concerns.

**Speaker note:**
- This slide should answer “why both?” very clearly.
- If the audience only remembers one stack diagram, let it be this one or Slide 16.

### Slide 16 — End-to-end architecture diagram
- client
- gateway
- llm-d EPP
- prefill pool
- decode pool
- KV path

**Suggested visual:** full architecture diagram; this is one of the anchor slides.

**Speaker note:**
- This is the main reference diagram for the rest of the talk.
- Keep returning to it when later slides discuss request flow or autoscaling.

### Slide 17 — What MultiRoleInference declares
- one logical inference service
- two roles
- role-specific scaling and runtime behavior

**Suggested visual:** small YAML snippet or CRD field summary.

**Speaker note:**
- Show the API intent before the generated objects.
- Focus on user intent, not every field.

### Slide 18 — What MultiRoleInference generates
- prefill StatefulSet
- decode StatefulSet
- InferencePool
- llm-d routing pieces
- autoscaling objects

**Suggested visual:** generated-object tree or exploded diagram from the CRD.

**Speaker note:**
- Show what KAITO creates for the user.
- This is one of the strongest “abstraction value” slides in the deck.

### Slide 19 — Why the decode-side sidecar exists
- stable client-facing entrypoint
- internal prefill coordination
- local decode remains stream owner

**Suggested visual:** decode pod diagram with sidecar and local vLLM ports.

**Speaker note:**
- This is a good concrete implementation slide.
- Explain why the sidecar placement is deliberate, not accidental.

### Slide 20 — Request flow, part 1
- request enters gateway
- EPP decides whether prefill work is needed
- decode endpoint is selected

**Suggested visual:** sequence diagram, phase 1 only.

**Speaker note:**
- Animate this if possible.
- Keep this slide narrowly focused on entry, decision, and endpoint choice.

### Slide 21 — Request flow, part 2
- sidecar coordinates prefill
- prefill builds KV cache
- KV moves to decode
- decode streams output

**Suggested visual:** sequence diagram, phase 2 continuation.

**Speaker note:**
- Keep it stepwise, not all at once.
- This is where the audience should see why the topology is helpful but nontrivial.

### Slide 22 — Why KV transfer matters
- P/D is only useful if KV movement is fast and reliable
- validate this path early in production

**Suggested visual:** KV transfer path callout, maybe with “critical path” highlighted.

**Speaker note:**
- This is a good operational-truth slide.
- Explicitly say this is one of the first things to validate in real deployments.

### Slide 23 — Independent autoscaling by role
- prefill scale signal
- decode scale signal
- better fit for asymmetric traffic

**Suggested visual:** two side-by-side scaling graphs or two KEDA callouts.

**Speaker note:**
- Connect architecture to platform operations.
- This is where the “Kubernetes-native” claim starts paying off in operator language.

### Slide 24 — Why this abstraction helps operators
- fewer manually coordinated objects
- fewer implicit contracts around ports/labels/env
- easier to reason about desired topology

**Suggested visual:** “manual plumbing” vs “declarative abstraction” comparison.

**Speaker note:**
- Bring the value back to the platform team audience.
- Mention that abstraction is not about hiding power; it is about making the topology operable.

### Slide 25 — Evaluation results: TTFT
- colocated vs disaggregated
- explain which workloads gain most

**Suggested visual:** one clean TTFT chart with 1-2 highlighted takeaways.

**Speaker note:**
- One chart, one interpretation.
- Resist the urge to explain every line.

### Slide 26 — Evaluation results: throughput
- compare throughput under mixed load

**Suggested visual:** throughput chart with one highlighted region where separation helps.

**Speaker note:**
- Keep narration high signal.
- Tie the result back to earlier “two workloads, one pool” framing.

### Slide 27 — Evaluation results: utilization / efficiency
- show GPU utilization or capacity efficiency under asymmetric traffic

**Suggested visual:** utilization bars, efficiency table, or stacked pool usage chart.

**Speaker note:**
- Reinforce the “why separate pools” message.
- This is the business/operations payoff slide.

### Slide 28 — When to use P/D, and when not to
- good fit: long prompts, bursty prefill, latency-sensitive interactive traffic
- not always worth it: tiny PoCs, low concurrency, short prompts

**Suggested visual:** 2-column “good fit / not worth it yet” matrix.

**Speaker note:**
- This improves trust with the audience.
- Explicitly saying “not for everyone” makes the talk more credible.

### Slide 29 — Production lessons
- startup ordering matters
- sidecar placement rules matter
- autoscaling metrics must be role-specific
- KV transfer path must be verified early

**Suggested visual:** four callout boxes or checklist slide.

**Speaker note:**
- Give practical advice, not just architecture.
- This is a strong slide to leave platform engineers with something usable.

### Slide 30 — What’s next for KAITO + llm-d
- precise prefix-cache routing based on KV events
- tiered prefix cache
- Wide Expert Parallelism
- E/P/D, speculative decoding, richer inference topologies

**Suggested visual:** roadmap slide with “current / next / later” swimlanes.

**Speaker note:**
- End with a concrete roadmap, not a vague future-work cloud.
- This is where you connect today’s P/D story to tomorrow’s richer inference topologies.

### Deck production notes
- Keep most slides to **one sentence headline + one diagram/chart + 2-3 bullets max**.
- Slides 16, 20, 21, and 25-27 are the likely visual anchors of the deck.
- If time runs short, Slides 12, 24, and part of 27 can be compressed quickly without losing the main story.
- If the benchmark section is weak, spend more time on Slides 15-24 and make the architecture story the center of gravity.

---

## Suggested Opening (30 seconds)

LLM inference looks like one workload from the outside, but inside it has two very different phases. Prefill wants raw compute and low latency. Decode wants memory bandwidth and steady throughput. If we force both into one GPU pool, we compromise both. In this talk, we’ll show why prefill/decode disaggregation helps, why it is still hard to operate on Kubernetes, and how KAITO plus llm-d turns that topology into something declarative and production-friendly.

---

## Suggested Closing (20-30 seconds)

The important shift is not just separating prefill and decode. The bigger shift is making advanced inference topologies first-class citizens on Kubernetes. KAITO is the abstraction layer that can make those topologies usable, while llm-d keeps expanding the routing and scheduling capabilities underneath. The next step is to close that gap even further with precise prefix-cache routing, tiered prefix cache, and eventually support for topologies like Wide Expert Parallelism.

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

## Next Draft Ideas

Possible follow-up artifacts from this outline:

1. a full slide-by-slide deck draft
2. speaker notes for each slide
3. a 5-minute lightning version
4. a polished abstract for the event page
5. a version aligned to actual benchmark screenshots/data
