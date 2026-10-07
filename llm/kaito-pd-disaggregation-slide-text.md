# KAITO + P/D Slide Text Snippets

This file contains ready-to-paste copy for the slides that benefit most from polished wording: positioning, CRD/resource expansion, request flow, runtime contracts, benchmark framing, and lessons learned.

---

## Slide 5 — Why KAITO on top of llm-d / Dynamo / manual stack

### Title
**Why Put KAITO on Top of llm-d?**

### Subtitle
llm-d gives strong routing primitives. KAITO turns them into a Kubernetes-native operator workflow.

### Recommended body layout
Use a 3-column comparison table.

| Approach | What it gives you | What still hurts |
|---|---|---|
| Manual llm-d stack | InferencePool, EPP, routing plugins, P/D primitives | Too much wiring: sidecars, labels, ports, configmaps, autoscaling, lifecycle ownership |
| Dynamo | Full-stack disaggregated inference framework | Heavier runtime coupling, more integration surface, less natural fit for K8s operators |
| **KAITO + llm-d** | Declarative K8s abstraction on top of proven routing primitives | Best balance for platform teams already running Kubernetes |

### Three punchy bullets under the table
- **llm-d solves routing and scheduling.** It is the right substrate for cache-aware and P/D-aware inference decisions.
- **KAITO solves lifecycle and platform automation.** It owns the CRD, resource generation, GPU workflow, and scaling ergonomics.
- **Together they reduce operator burden.** Users describe intent once; the platform expands it into runnable infrastructure.

### Bottom takeaway box
**Best mental model:** llm-d is the distributed inference substrate; KAITO is the operator layer that makes it usable in production Kubernetes environments.

### Speaker line
If you are already a Kubernetes platform team, the problem is not “can llm-d route requests?” The problem is “who owns all the surrounding contracts?” KAITO is the layer that owns those contracts.

---

## Slide 11 — MultiRoleInference: one CRD for P/D disaggregation

### Title
**MultiRoleInference: One CRD for P/D Disaggregation**

### Subtitle
Describe the topology once; let KAITO generate the serving resources.

### Hero YAML snippet
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

### Three callout bullets
- **Shared model intent:** one model preset and one service topology
- **Role-specific scaling:** prefill and decode can use different replica counts and policies
- **Declarative interface:** users express *what* they want, not *how* to wire the stack

### Bottom takeaway box
**The CRD is the product surface.** Everything else — routing resources, sidecars, plugin config, labels, and autoscaling plumbing — should be generated or enforced by the controller.

### Speaker line
The real value here is not reducing YAML for its own sake. The value is collapsing multiple failure-prone integration points into one API boundary.

---

## Slide 12 — What one MRI CR generates

### Title
**What One MultiRoleInference CR Generates**

### Subtitle
One user-facing object expands into a full P/D serving topology.

### Recommended expansion list
Start with **MultiRoleInference** in the center, then fan out to:
- **Prefill InferenceSet**
- **Decode InferenceSet**
- **Shared InferencePool**
- **EPP plugin configuration**
- **Gateway-facing routing resources**
- **KEDA scaling objects / annotations**

### Caption for each generated piece
- **Prefill InferenceSet** — runs prefill workers with the right role labels and runtime config
- **Decode InferenceSet** — runs decode workers and injects the routing sidecar where required
- **InferencePool** — gives llm-d one pool abstraction across the role-specific workers
- **EPP plugins** — encode the P/D routing policy, role filters, and worker selection logic
- **Gateway resources** — connect requests from the gateway into the right inference pool
- **KEDA integration** — lets each role scale against the signals that actually matter

### Bottom takeaway box
**KAITO does not replace llm-d.** It generates, owns, and keeps the llm-d-facing resources consistent.

### Speaker line
This is the core abstraction jump: instead of hand-assembling a routing stack, the user creates one higher-level object and the platform expands it into the right graph of resources.

---

## Slide 13 — Request flow: Gateway → EPP → Decode → Prefill → KV transfer

### Title
**End-to-End Request Flow**

### Subtitle
Simple control plane, non-trivial runtime path.

### Numbered flow copy
1. **Client sends an OpenAI-compatible request** to the inference gateway.
2. **Gateway / HTTPRoute forwards to the InferencePool** for the target model.
3. **llm-d EPP picks a decode worker first** and decides whether prefill should be separated.
4. **If disaggregation is needed, EPP also selects a prefill worker** and passes that decision along.
5. **The request lands on the decode sidecar**, which coordinates the P/D workflow.
6. **Prefill vLLM processes the prompt and produces KV cache state.**
7. **Decode vLLM pulls KV cache via NIXL** and continues token generation locally.
8. **The response returns through the same gateway path** back to the client.

### Right-side callout bullets
- **Decode is the coordination point**
- **Prefill is selected only when it helps**
- **KV transfer is the bridge between the two phases**

### Bottom takeaway box
**The user sees one endpoint.** Under the hood, the platform is coordinating scheduling, prefill placement, KV movement, and decode execution across multiple pods.

### Speaker line
This slide is where the value of the abstraction becomes obvious: the runtime path is too complex to expect every user to wire correctly by hand.

---

## Slide 14 — decode-only sidecar / port / label / env contracts

### Title
**The Runtime Contracts That Make P/D Actually Work**

### Subtitle
Most production failures here are contract bugs, not model bugs.

### Core table
| Contract | Prefill | Decode | Why it matters |
|---|---|---|---|
| Routing sidecar | No | Yes | Decode is the coordination point; prefill stays simple |
| vLLM port | 5000 | 5001 | Avoids sidecar ↔ local vLLM port collision |
| Sidecar ingress port | N/A | 5000 | Lets the decode sidecar sit in front of local vLLM |
| Role label | `prefill` | `decode` | EPP filters workers by role |
| NIXL side-channel host | Pod IP | Pod IP | Cross-pod KV handshake must advertise a reachable address |

### Final bullets
- **Decode-only sidecar is the stable pattern.** Prefill should stay lightweight and focus only on prompt processing.
- **`InferencePool.targetPort` is not just a config detail.** It is part of the routing contract across the pool.
- **Labels are functional metadata.** If role labels drift, routing decisions drift with them.
- **Pod IP wiring must be automatic.** Hand-configuring NIXL endpoint env vars is too fragile for production.

### Bottom takeaway box
**If these contracts are not enforced by the controller, users end up debugging infrastructure wiring as if it were model behavior.**

### Speaker line
This is where most of the painful bugs live: wrong port, wrong label, wrong env var, wrong targetPort. The platform has to make these contracts boring and automatic.

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
