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

For a 20-minute co-located talk, **20-22 slides is reasonable** as long as most slides carry one idea and use diagrams or short bullets rather than dense text. Below is a **20-slide structure**.

### Slide 1 — Title
**Prefill Here, Decode There**  
Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d

Speaker note:
- Start with the operational problem, not the project names.

### Slide 2 — One user request, two different systems problems
- LLM inference looks like one workload from the outside
- Internally it splits into prefill and decode

Speaker note:
- This is the setup slide for the rest of the talk.

### Slide 3 — Prefill characteristics
- compute-bound
- latency-sensitive
- bursty under prompt-heavy traffic

Speaker note:
- Keep this concrete and intuitive.

### Slide 4 — Decode characteristics
- memory-bandwidth-bound
- KV-cache-sensitive
- throughput-oriented

Speaker note:
- Make the contrast with prefill visually obvious.

### Slide 5 — Why one shared GPU pool is a bad compromise
- two bottlenecks sharing one pool
- either overprovisioning or poor TTFT / throughput

Speaker note:
- This is the "why care" slide.

### Slide 6 — What P/D disaggregation changes
- prefill and decode run on separate pools
- capacity can scale independently
- KV cache has to move between roles

Speaker note:
- Introduce the benefit and the new complexity at the same time.

### Slide 7 — Why this is still hard on Kubernetes
- routing
- KV handoff
- role-specific services
- labels, ports, sidecars, startup ordering

Speaker note:
- Explain that the hard part is orchestration, not the idea.

### Slide 8 — Existing paths in the ecosystem
- NVIDIA Dynamo
- llm-d standalone
- need for a higher-level Kubernetes-native abstraction

Speaker note:
- Keep this brief; this is not a comparison talk.

### Slide 9 — What KAITO is
- Kubernetes-native AI operator / abstraction layer
- turns serving topology into declarative APIs
- generates lower-level runtime objects automatically

Speaker note:
- Be explicit that KAITO is the control-plane abstraction.

### Slide 10 — What llm-d brings to the stack
- routing and scheduling plugins
- role-aware endpoint selection
- prefix/cache-aware decisions

Speaker note:
- Be explicit that llm-d is the routing/scheduling layer underneath.

### Slide 11 — KAITO + llm-d together
- KAITO expresses topology
- llm-d drives routing decisions
- Gateway API / InferencePool / sidecars connect the pieces

Speaker note:
- This slide should answer "why both?".

### Slide 12 — P/D architecture on Kubernetes
- client / gateway
- prefill pool
- KV cache transfer
- decode pool

Speaker note:
- This is the central architecture diagram slide.

### Slide 13 — What one MultiRoleInference CRD generates
- prefill StatefulSet
- decode StatefulSet
- llm-d routing pieces
- InferencePool / Gateway integration
- per-role autoscaling objects

Speaker note:
- This is where KAITO’s value becomes concrete.

### Slide 14 — Request flow
- request enters gateway
- EPP decides prefill/decode path
- sidecar coordinates prefill
- KV moves to decode
- decode streams response

Speaker note:
- Walk through one request, step by step.

### Slide 15 — Why the decode-side sidecar matters
- keeps the user-facing entrypoint stable
- hides prefill orchestration from clients
- lets decode remain the serving endpoint

Speaker note:
- Good place for one simple sequence diagram.

### Slide 16 — Independent autoscaling by role
- prefill scales on one pressure signal
- decode scales on another
- better behavior under bursty or asymmetric traffic

Speaker note:
- Connect architecture to operational outcomes.

### Slide 17 — Evaluation results: TTFT
- compare colocated vs disaggregated TTFT
- explain what workload shape benefits most

Speaker note:
- One chart, one message.

### Slide 18 — Evaluation results: throughput / utilization
- throughput comparison
- GPU utilization under mixed load

Speaker note:
- Avoid chart overload; use only the most persuasive evidence.

### Slide 19 — When to use P/D, and when not to
- good fit: long prompts, bursty prefill, interactive latency goals
- not always worth it: tiny PoCs, short prompts, low concurrency

Speaker note:
- This is important for credibility and audience trust.

### Slide 20 — What’s next for KAITO + llm-d
- enable precise prefix-cache routing based on KV events
- productize tiered prefix cache
- support Wide Expert Parallelism
- E/P/D, speculative decoding, richer inference topologies

Speaker note:
- End with a roadmap that feels concrete, not generic.

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
