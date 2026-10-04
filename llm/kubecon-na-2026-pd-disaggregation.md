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
- Final takeaway:
  - the challenge is no longer whether P/D works
  - the challenge is how to make advanced inference topologies feel native on Kubernetes
- Close with next steps:
  - E/P/D
  - speculative decoding
  - more advanced transport / cross-node optimization

---

## Suggested Slide-by-Slide Story

### Slide 1 — Title
**Prefill Here, Decode There**  
Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d

Speaker note:
- Start with the operational problem, not the project names.

### Slide 2 — One request, two very different phases
- Prefill: compute-bound, latency-sensitive
- Decode: memory-bandwidth-bound, throughput-sensitive

Speaker note:
- This is the foundational idea for the whole talk.

### Slide 3 — Why colocated serving wastes GPUs
- Same GPU pool must satisfy two conflicting objectives
- Results in either overprovisioning or poor TTFT

Speaker note:
- Make this intuitive for non-specialists.

### Slide 4 — Today’s landscape
- Dynamo
- llm-d standalone
- Need for a Kubernetes-native higher-level abstraction

Speaker note:
- Keep this short; do not turn it into a vendor comparison talk.

### Slide 5 — P/D architecture on Kubernetes
- Gateway / routing
- Prefill pool
- KV cache transfer
- Decode pool

Speaker note:
- This diagram is the heart of the talk.

### Slide 6 — What MultiRoleInference generates
- CRD -> multiple coordinated runtime objects
- hides the manual plumbing

Speaker note:
- This is where KAITO’s value becomes concrete.

### Slide 7 — Independent autoscaling by role
- Prefill scales on one signal
- Decode scales on another
- Better behavior under bursty traffic

Speaker note:
- Connect architecture to operational outcomes.

### Slide 8 — Evaluation results
- TTFT
- throughput
- utilization

Speaker note:
- Use only 2-3 charts and explain them clearly.

### Slide 9 — When to use P/D
- good fit / bad fit matrix

Speaker note:
- This is important for audience trust.

### Slide 10 — Production lessons
- orchestration details matter more than the concept

Speaker note:
- Give pragmatic advice, not just theory.

### Slide 11 — Key takeaways
- Two workloads
- Separate GPU pools
- Declarative Kubernetes abstraction

### Slide 12 — What’s next
- E/P/D
- speculative decoding
- richer inference topologies

---

## Suggested Opening (30 seconds)

LLM inference looks like one workload from the outside, but inside it has two very different phases. Prefill wants raw compute and low latency. Decode wants memory bandwidth and steady throughput. If we force both into one GPU pool, we compromise both. In this talk, we’ll show why prefill/decode disaggregation helps, why it is still hard to operate on Kubernetes, and how KAITO plus llm-d turns that topology into something declarative and production-friendly.

---

## Suggested Closing (20-30 seconds)

The important shift is not just separating prefill and decode. The bigger shift is making advanced inference topologies first-class citizens on Kubernetes. If training infrastructure can be Kubernetes-native, modern inference infrastructure should be too.

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
