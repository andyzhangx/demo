# Proposal to Move EPP and BBR from GAIE to llm-d

> Summary of [kubernetes-sigs/gateway-api-inference-extension#2430](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430)
>
> Last updated: 2026-04-11

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
- NVIDIA/Dynamo considers llm-d neutral enough to include in their ecosystem diagrams (per kfswain, referencing GTC material).

### Concerns (keithmattix, ed-pai, howardjohn)

- **Neutrality**: Kubernetes org is inherently more neutral than a downstream project. Moving EPP out could "implicitly crown a winner" — other inference frameworks wanting to build an EPP would have to start from scratch or import a competitor's code.
- **Reference implementation gravity**: While anyone _can_ write their own EPP, in practice llm-d's EPP will be the only complete implementation. This creates a de facto monopoly even if the standard is open.
- **Standard-implementation coupling**: If the standard's main contributors are also llm-d maintainers, they may evolve the standard to favor their implementation.
- **BBR should stay**: BBR directly implements GAIE standard behavior and should remain in the kubernetes-sigs repo (keithmattix strongly advocates this).
- **Developer experience**: llm-d was previously difficult to deploy (non-standard vLLM, confusing setup). ed-pai noted he "gave up and built our own platform" a couple months ago, though he later adapted to llm-d inference-scheduler and found it "wasn't a drop-in replacement, but was close enough."
- **Contribution-gating tone**: howardjohn (Istio maintainer) called out kfswain for suggesting that keithmattix's feedback carried less weight due to limited code contributions, noting this was "dismissive" and that "raising valid concerns about project direction is contributing."

## Current Status (as of 2026-04-11)

### EPP Migration: **Consensus reached — moving forward**

- keithmattix, the most vocal skeptic, explicitly stated (2026-03-27): "I'm aligned with the EPP move" with conditions:
  - Conformance tests and EPP protocol continue to evolve in a vendor-neutral way under GAIE.
  - A lightweight reference EPP remains in GAIE for running conformance tests (confirmed by ahg-g).
  - The standard does not prioritize llm-d over other implementations.
- ed-pai confirmed he was able to adapt his platform to use `llm-d/inference-scheduler`: "It wasn't a drop-in replacement, but was close enough" — command changed from `/epp` to using Args, plus some extra flags.

### BBR Migration: **Still disputed, leaning toward move**

- keithmattix maintains BBR implements standard behavior and "should stay."
- ahg-g argues BBR is "only useful in the context of EPP" and should move with it, countering that "the standard didn't require BBR."
- keithmattix's latest position (2026-03-27): "my concerns over BBR aren't about where it's housed, but rather about the _standard_ continuing to evolve" — suggesting conditional acceptance.

### Tone/Governance Friction: **Acknowledged and de-escalated**

- kfswain's comment (2026-03-30) implying keithmattix's concerns were less valid due to limited code contributions drew pushback from howardjohn (Istio): "I consider raising valid concerns about project direction to be contributing. Dismissing that seems problematic."
- kfswain responded (2026-04-07): "If there was any disrespect conveyed, that was not intended" and proposed to "agree to disagree."
- keithmattix (2026-04-07): "+1 on agreeing to disagree. I've raised my concerns and that's all I can do. I'm encouraged by the direction of #2790 and will contribute to other similar initiatives as I am able."
- The discussion has effectively concluded with no further comments since April 7th.

### Follow-up Work

- Issue [#2790](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2790) was referenced by keithmattix as an encouraging direction — likely related to conformance/neutrality guarantees.

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
    ├── Prefix-cache aware routing
    └── Advanced plugins (scorers/filters)

llm-d/<new-bbr-repo>                     ← Proposed (conditional consensus)
└── BBR implementation
```

## Technical Compatibility Note

As of today (2026-04-11), **llm-d's EPP uses the same upstream GWIE `inferencepool` Helm chart** (`oci://registry.k8s.io/gateway-api-inference-extension/charts/inferencepool`). The only difference is the EPP image override in values:

```yaml
inferenceExtension:
  image:
    name: llm-d-inference-scheduler
    hub: ghcr.io/llm-d
    tag: v0.7.0
```

This means downstream consumers (like KAITO) that deploy via this Helm chart only need to change the image reference — the chart schema, InferencePool CRD, and overall wiring remain identical.

## Impact on KAITO

KAITO's InferenceSet controller ([`pkg/utils/consts/consts.go`](https://github.com/kaito-project/kaito/blob/main/pkg/utils/consts/consts.go#L71)) hardcodes:
- `InferencePoolChartURL` — points to GWIE chart (no change needed)
- `GatewayAPIInferenceExtensionImageRepository` — points to MCR mirror (change to `ghcr.io/llm-d` for llm-d EPP)
- `InferencePoolChartVersion` — `v1.3.1` (update to match llm-d version)

The HelmRelease values in [`pkg/workspace/manifests/manifests.go`](https://github.com/kaito-project/kaito/blob/main/pkg/workspace/manifests/manifests.go#L382) also need an additional `name` field since llm-d's image name (`llm-d-inference-scheduler`) differs from the chart default (`epp`).

## Analogy

This is similar to how:
- **Gateway API** is the standard → Istio, Envoy Gateway, NGINX each implement it
- **CNI** is the standard → Calico, Cilium, Flannel each implement it
- **EPP Protocol** would be the standard → llm-d's EPP is one implementation, others can follow

The concern is whether, in practice, a single dominant implementation undermines the value of having an open standard.

## References

- Issue: https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430
- Follow-up conformance work: https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2790
- SIG-NET discussion (2026-03-12): [Google Doc](https://docs.google.com/document/d/1bEA0F8WddLMnQp7zUfr1rZOwRqX6g2y4kcylEcGATHo/edit?tab=t.0)
- Overall migration plan: [Google Doc](https://docs.google.com/document/d/17ZVd4poQfLHSBmKSgLrhGGEBhbwQzH4DJes-D4MLYd4/edit?tab=t.0)
- EPP-specific migration: [Google Doc](https://docs.google.com/document/d/1PMJfVNPZEDDSVU33qgH95g6v09ZNBIINbU8AZVilKpY/edit?tab=t.0#heading=h.sjv62khj5lf9)
