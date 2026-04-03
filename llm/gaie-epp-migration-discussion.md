# Proposal to Move EPP and BBR from GAIE to llm-d

> Summary of [kubernetes-sigs/gateway-api-inference-extension#2430](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430)
>
> Date: 2026-04-03

## Background

The Gateway API Inference Extension (GAIE) project under `kubernetes-sigs` currently has three distinct parts:

1. **InferencePool API + EPP Protocol** — Open standard that defines how a Kubernetes Gateway delegates inference-optimized routing to an external Endpoint Picker service.
2. **Conformant Gateway ecosystem** — GKE Gateway, Istio, kGateway, NGINX Gateway Fabric.
3. **EPP (Endpoint Picker) implementation** — The actual scheduling logic (LoRA affinity, KV-cache aware routing, latency prediction, etc.).

The problem: the EPP code is split across two repos — the upstream GAIE repo and the `llm-d/llm-d-inference-scheduler` repo. Advanced plugins (P/D scheduling, precise KV-cache scheduling) are mostly developed in the llm-d repo, causing **fragmented code, duplicate maintenance, and developer/user confusion**.

## Proposal

| Component | Destination |
|-----------|-------------|
| InferencePool API + EPP Protocol + Conformance Tests | **Stay in kubernetes-sigs** (may move to Gateway API repo eventually) |
| EPP implementation code | **Move to llm-d repo** |
| BBR (Body-Based Routing) | **Move to separate llm-d repo** |
| InferenceObjective / InferenceModelRewrite APIs | **Move with EPP** (EPP-specific, not Gateway-related) |

## Key Arguments

### In Favor (kfswain, ahg-g, danehans)

- Almost all EPP/BBR contributors are also llm-d contributors — maintaining two repos creates unnecessary friction and reduces development velocity.
- Advancing EPP optimizations requires deep AI/ML expertise and tight integration with model servers (vLLM, SGLang). The llm-d community (applying for CNCF Sandbox) is the right home for this work.
- The API/protocol standard stays in Kubernetes org, preserving neutrality. Moving the _implementation_ out is similar to how Gateway API doesn't ship a specific proxy — it defines the standard.
- llm-d is Apache-licensed and aims for CNCF governance, so it's open and neutral.

### Concerns (keithmattix, ed-pai)

- **Neutrality**: Kubernetes org is inherently more neutral than a downstream project. Moving EPP out could "implicitly crown a winner" — other inference frameworks wanting to build an EPP would have to start from scratch or import a competitor's code.
- **Reference implementation gravity**: While anyone _can_ write their own EPP, in practice llm-d's EPP will be the only complete implementation. This creates a de facto monopoly even if the standard is open.
- **Standard-implementation coupling**: If the standard's main contributors are also llm-d maintainers, they may evolve the standard to favor their implementation.
- **BBR should stay**: BBR directly implements GAIE standard behavior and should remain in the kubernetes-sigs repo.
- **Developer experience**: llm-d was previously difficult to deploy (non-standard vLLM, confusing setup), though it has improved.

## Current Status (as of 2026-04-02)

- **EPP migration**: Mostly agreed upon. Even skeptics (keithmattix) conditionally support it, provided:
  - Conformance tests and EPP protocol continue to evolve in a vendor-neutral way under GAIE.
  - A lightweight reference EPP remains in GAIE for running conformance tests.
  - The standard does not prioritize llm-d over other implementations.
- **BBR migration**: Still disputed. keithmattix argues BBR implements standard behavior and should stay in GAIE.
- **No final decision**: The discussion is still open with 29 comments. The last exchange (2026-03-30 to 2026-04-02) got somewhat tense, with questions about contribution levels and governance philosophy.

## Architecture After Migration

```
kubernetes-sigs/gateway-api-inference-extension (GAIE)
├── InferencePool API definition         ← Standard (stays)
├── EPP Protocol definition              ← Standard (stays)
├── Conformance tests                    ← Stays
└── Lightweight reference EPP            ← For conformance testing

llm-d/llm-d-inference-scheduler
└── Full EPP implementation              ← Migrated from GAIE
    ├── LoRA affinity scheduling
    ├── KV-cache aware routing
    ├── P/D disaggregated scheduling
    ├── Latency prediction
    └── Advanced plugins

llm-d/<new-bbr-repo>                     ← Proposed (disputed)
└── BBR implementation
```

## Analogy

This is similar to how:
- **Gateway API** is the standard → Istio, Envoy Gateway, NGINX each implement it
- **CNI** is the standard → Calico, Cilium, Flannel each implement it
- **EPP Protocol** would be the standard → llm-d's EPP is one implementation, others can follow

The concern is whether, in practice, a single dominant implementation undermines the value of having an open standard.

## References

- Issue: https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430
- SIG-NET discussion (2026-03-12): [Google Doc](https://docs.google.com/document/d/1bEA0F8WddLMnQp7zUfr1rZOwRqX6g2y4kcylEcGATHo/edit?tab=t.0)
- Overall migration plan: [Google Doc](https://docs.google.com/document/d/17ZVd4poQfLHSBmKSgLrhGGEBhbwQzH4DJes-D4MLYd4/edit?tab=t.0)
- EPP-specific migration: [Google Doc](https://docs.google.com/document/d/1PMJfVNPZEDDSVU33qgH95g6v09ZNBIINbU8AZVilKpY/edit?tab=t.0#heading=h.sjv62khj5lf9)
