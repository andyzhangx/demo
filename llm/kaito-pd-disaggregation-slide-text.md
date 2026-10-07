# KAITO + P/D Slide Text Snippets

This file contains ready-to-paste copy for the two slides that usually take the longest to word well: the benchmark / break-even slide and the AKS lessons learned slide.

---

## Slide 18 — Benchmark / break-even analysis

### Title
**When Does P/D Disaggregation Pay Off?**

### Subtitle
P/D wins once prefill pressure dominates and KV transfer overhead is smaller than the saved prefill compute.

### Chart title
**P95 TTFT vs. Prompt Length**

### Axes
- **X-axis:** prompt length (input tokens)
- **Y-axis:** P95 TTFT (seconds)

### Series labels
- **Colocated serving**
- **P/D disaggregation**

### Chart callouts
- **Short prompts:** colocated is competitive because routing + KV-transfer overhead is not yet amortized
- **Break-even zone:** around **[X] input tokens** / **[Y]% cache miss rate**, P/D starts to reduce TTFT consistently
- **Long prompts:** P/D separates prefill pressure from decode throughput, so TTFT grows more slowly

### Summary table

| Workload region | Winner | Why |
|---|---|---|
| Short prompts / high cache hit | Colocated or near-tie | Little prefill to offload; extra coordination can dominate |
| Medium prompts / mixed cache hit | Break-even zone | Routing quality and KV-transfer efficiency decide the outcome |
| Long prompts / prefill-heavy | **P/D disaggregation** | Prefill no longer steals decode capacity |

### Metrics strip
- **Primary metric:** P95 TTFT
- **Secondary metrics:** throughput, TPOT / ITL, GPU utilization, GPUs needed for the same SLO

### Figure caption
Benchmark setup: same model, same total GPU budget, same request distribution; only serving topology changes (colocated vs. P/D).

### Bottom takeaway box
**Break-even rule of thumb:** below the break-even point, keep it simple; above it, P/D buys lower TTFT and better decode stability.

### Speaker line
P/D is not a universal win. It becomes compelling when prompt length, cache-miss rate, or prefill concurrency is high enough that separating prefill from decode recovers more GPU efficiency than the extra coordination costs.

---

## Slide 19 — AKS lessons learned

### Title
**AKS Lessons Learned: The Hard Part Is the Contracts**

### Final bullets
- **Use a decode-only sidecar.** Putting the routing sidecar on prefill pods added instability and unnecessary memory pressure; the stable pattern is sidecar on decode, no sidecar on prefill.
- **Treat ports as API contracts.** `InferencePool.targetPort`, decode sidecar port, and prefill vLLM port must line up exactly, or routing fails in ways that look like runtime bugs.
- **Treat labels as routing inputs.** `kaito.sh/inference-role=prefill|decode` is not cosmetic metadata — the EPP depends on it to select the right workers.
- **Automate NIXL endpoint wiring in the controller.** `VLLM_NIXL_SIDE_CHANNEL_HOST=status.podIP` must be correct on both prefill and decode pods, otherwise KV handshakes fail across pods.
- **Observe the stack at three layers.** You need EPP routing signals, vLLM inference metrics, and KV-transfer / KV-event visibility together; none of them alone is enough to debug P/D.
- **Invest in CPU-only E2E before scaling out GPU tests.** GPU node mocker and mocked NodeClaim → Node → Pod flows are what make fast iteration and safe regression testing practical on AKS.

### Optional closing line
P/D disaggregation is easy to explain on a whiteboard. Making the contracts reliable in a real AKS deployment is the real engineering work.
