# KAITO + llm-d：How They Support Prefill/Decode Disaggregation

This file contains a ready-to-use slide section for explaining how **KAITO + llm-d** support **prefill/decode (P/D) disaggregation** on Kubernetes.

Positioning:
- `KAITO` = declarative control-plane abstraction and orchestration
- `GWIE` = Kubernetes-native inference routing contract and API surface
- `llm-d Router` = EPP-based routing implementation and scheduling substrate
- `vLLM + NIXL` = runtime execution and KV-cache handoff path

These slides are designed to fit naturally around the current **Slide 18: division of labor** material in `kubecon-na-2026-pd-disaggregation.md`.

---

## Slide 17 — What the llm-d Router brings to the stack

### Title
**What the llm-d Router Brings to the Stack**

### Subtitle
The routing intelligence KAITO builds on for P/D.

### Recommended body
- **EPP implementation** for the GWIE flow
- **Model-aware and role-aware endpoint selection**
- **KV-cache-aware and P/D-aware plugin chain**
- **A scheduling substrate KAITO can build on**

### Bottom takeaway box
**KAITO is not inventing a new routing brain here. It is building on llm-d Router as the EPP and scheduling substrate.**

### Suggested visual
An llm-d Router EPP box with plugin labels around it.

### Speaker note
Use this slide to answer one question only:

> **What new capability does llm-d add?**

Explain that KAITO is not inventing its own routing algorithm here; it is building on llm-d Router as the EPP implementation and scheduling substrate.

---

## Slide 18 — Why all three: KAITO + GWIE + llm-d Router

### Title
**Why All Three: KAITO + GWIE + llm-d Router**

### Subtitle
Three layers, three responsibilities, one usable P/D platform.

### Recommended body
- **KAITO** = declarative abstraction and orchestration
- **GWIE** = Kubernetes-native contract between gateway and inference backends
- **llm-d Router** = routing intelligence and P/D-aware scheduling
- **InferencePool** = the contract surface that binds them together

### Bottom takeaway box
**KAITO makes P/D operable. llm-d provides the routing intelligence. GWIE provides the Kubernetes-native contract.**

### Suggested visual
A 3-layer stack:

- **Top / User API layer**
  - `MultiRoleInference`
- **Middle / Kubernetes routing contract**
  - `InferencePool`
  - Gateway API Inference Extension
- **Bottom / execution & scheduling**
  - llm-d Router EPP
  - prefill workers
  - decode workers
  - KV transfer path

### Speaker note
Use one crisp line here:

> **llm-d gives the routing brain, GWIE gives the Kubernetes routing contract, and KAITO turns the whole thing into a usable platform workflow.**

Be precise here: KAITO still uses GWIE objects and integration patterns, but it does **not** rely on GWIE’s reference routing implementation for P/D behavior.

---

## Slide 19 — End-to-end architecture diagram

### Title
**End-to-End Architecture**

### Subtitle
One user endpoint, one gateway-facing contract surface, two role-specific backends, and a direct KV path.

### Recommended body
- **Client request enters through the gateway**
- **Gateway targets an InferencePool** as the GWIE contract surface
- **llm-d Router EPP selects decode and, when needed, prefill**
- **KAITO-managed child InferenceSets** provide the actual prefill/decode backends
- **KV data moves directly** between prefill and decode
- **One user endpoint, multiple coordinated runtime paths**

### Bottom takeaway box
**This is the concrete payoff slide: GWIE carries the contract, llm-d makes the routing decisions, and KAITO owns the topology and wiring.**

### Suggested visual
A full architecture diagram; this is one of the anchor slides.

### Speaker note
This is the concrete payoff slide for 17 and 18.

Show the audience where each piece from the previous slides lands in the real architecture. Make the child InferenceSets visible so the audience sees the real KAITO object model.

---

## Slide 20 — One MRI object describes the topology

### Title
**One MultiRoleInference Object Describes the Topology**

### Subtitle
Users declare intent once; the platform expands it into a runnable P/D system.

### Hero YAML snippet
```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: phi-4-mini
spec:
  model:
    name: phi-4-mini-instruct
  roles:
    - type: prefill
      replicas: 1
      instanceType: Standard_NC24ads_A100_v4
    - type: decode
      replicas: 1
      instanceType: Standard_NC24ads_A100_v4
```

### Callout bullets
- **One logical service** with role-specific backends
- **Role-specific scaling intent** for prefill and decode
- **Users describe what they want**, not how to wire the stack

### Bottom takeaway box
**The CRD is the product surface.** Users express topology intent; controllers own the plumbing.

### Suggested visual
Left: minimal MRI YAML.  
Right: arrow to “full P/D topology”.

### Speaker note
This is the abstraction jump:

> **The user is not hand-assembling a routing stack. The user is declaring a prefill/decode topology.**

---

## Slide 21 — What KAITO synthesizes automatically

### Title
**What KAITO Automatically Generates for P/D**

### Subtitle
KAITO acts like the control-plane compiler for the topology.

### Recommended body
From one `MultiRoleInference`, KAITO generates and wires:

- **Prefill child InferenceSet**
- **Decode child InferenceSet**
- **One shared InferencePool**
- **EPP-facing routing resources**
- **Decode-side routing sidecar injection**
- **NIXL side-channel env vars**
- **Role labels, ports, services, and ownership links**
- **Hooks for per-role autoscaling**

### Bottom takeaway box
**KAITO does not replace llm-d. It generates, owns, and keeps the llm-d-facing resources consistent.**

### Suggested visual
Center box: `MultiRoleInference`  
Fan-out boxes:
- `InferenceSet(prefill)`
- `InferenceSet(decode)`
- `InferencePool`
- `llm-d Router EPP`
- `sidecar injection`
- `NIXL env wiring`

### Speaker note
A good punchline here:

> **KAITO is the control-plane compiler for P/D topology.**

---

## Slide 22 — End-to-end request flow

### Title
**How a P/D Request Actually Executes**

### Subtitle
One endpoint for the user; multiple coordinated steps underneath.

### Numbered flow
1. **Client sends an OpenAI-compatible request** to the inference gateway.
2. **Gateway / HTTPRoute forwards to the InferencePool** for the model.
3. **llm-d Router EPP decides** whether prefill work is needed and selects the role-specific backends.
4. **The request is routed to a decode pod** as the final execution destination.
5. **The decode-side routing sidecar coordinates prefill** on the selected prefill pod.
6. **The prefill pod processes the prompt and builds the KV cache.**
7. **KV cache is transferred directly to the decode pod via NIXL.**
8. **The local decode vLLM continues token generation** and streams the response back.

### Right-side callouts
- **Decode is the coordination point**
- **Prefill is selected only when it helps**
- **KV transfer is the bridge between the two phases**

### Bottom takeaway box
**The user sees one endpoint. GWIE carries the gateway-facing contract, llm-d makes the routing decisions, and the platform coordinates prefill placement, KV movement, and decode execution across multiple pods.**

### Suggested visual
A left-to-right request flow:

`Client -> Gateway -> InferencePool -> llm-d Router EPP -> Decode sidecar -> Prefill -> NIXL KV handoff -> Decode vLLM -> Response`

### Speaker note
Important clarification:

> **The request is not externally split into two services by the user. The gateway, EPP, and decode-side sidecar coordinate that split internally.**

---

## Slide 23 — Why the sidecar lives on decode pods

### Title
**Why the Routing Sidecar Lives on Decode Pods**

### Subtitle
Sidecar placement is an execution design choice, not an incidental implementation detail.

### Recommended body
- **Decode pods are the final response point** for user traffic.
- The **routing sidecar** sits in front of decode vLLM and:
  - receives the routing decision from EPP
  - coordinates the prefill call
  - waits for KV handoff
  - forwards the request to local vLLM for generation
- This makes the external targetPort model cleaner:
  - **sidecar on 5000**
  - **local decode vLLM on 5001**
- Prefill pods stay simpler and focus only on prompt processing.

### Bottom takeaway box
**Decode-side sidecar placement turns the decode pod into the coordination point for P/D execution.**

### Suggested visual
A decode pod cutaway:
- port 5000 = routing sidecar
- port 5001 = local vLLM
- incoming request from EPP
- incoming KV path from prefill via NIXL

### Speaker note
Good stage line:

> **The sidecar is what lets the decode pod coordinate prefill and then resume generation locally.**

---

## Slide 24 — Runtime contracts that make P/D work

### Title
**The Runtime Contracts That Make P/D Actually Work**

### Subtitle
Most real failures here are contract bugs, not model bugs.

### Table
| Contract | Prefill | Decode | Why it matters |
|---|---|---|---|
| Routing sidecar | No | Yes | Decode is the coordination point |
| vLLM port | 5000 | 5001 | Avoid sidecar ↔ local vLLM collision |
| Sidecar ingress port | N/A | 5000 | Gives decode a stable external entry point |
| Role label | `prefill` | `decode` | EPP filters workers by role |
| NIXL side-channel host | Pod IP | Pod IP | KV handoff must advertise a reachable address |
| InferencePool targetPort | Shared external contract | Shared external contract | Gateway/EPP expect consistent routing semantics |

### Final bullets
- **Contracts must be controller-enforced**
- **Labels are functional metadata, not decoration**
- **TargetPort is part of the serving contract**
- **Pod IP / env wiring must be automatic**

### Bottom takeaway box
**If these contracts are not enforced by the controller, users debug infrastructure wiring as if it were model behavior.**

### Speaker note
This is where many production bugs live:
- wrong port
- wrong label
- wrong targetPort
- wrong side-channel address

And that is exactly why platform automation matters.

---

## Slide 25 — What llm-d contributes that KAITO does not replace

### Title
**KAITO Does Not Replace llm-d — It Operationalizes It**

### Subtitle
The two projects solve different layers of the same problem.

### Two-column comparison
| llm-d Router | KAITO |
|---|---|
| EPP implementation | CRD abstraction |
| endpoint picking | child resource generation |
| scheduling profiles | lifecycle orchestration |
| P/D-aware plugins | Kubernetes-native UX |
| routing execution | integration with InferenceSet / autoscaling |
| future scheduling surface | future topology APIs |

### Bottom takeaway box
**This is not KAITO vs. llm-d. KAITO builds on llm-d and turns it into a cleaner Kubernetes workflow.**

### Suggested visual
A two-column responsibility chart with arrows showing KAITO building on top of llm-d rather than replacing it.

### Speaker note
This slide prevents a common misunderstanding:

> **llm-d is the routing and scheduling substrate; KAITO is the operator layer that makes it usable for platform teams.**

---

## Slide 26 — What users manage vs. what the platform manages

### Title
**What Users Manage vs. What the Platform Manages**

### Subtitle
P/D becomes usable when the ownership boundary is clean.

### Left column — user intent
Users should manage:
- model choice
- prefill/decode role definitions
- replica intent
- instance types
- autoscaling intent
- policy-level topology decisions

### Right column — platform-owned plumbing
The platform should manage:
- child InferenceSets
- InferencePool
- llm-d Router EPP resources
- sidecar injection
- labels / services / targetPorts
- env wiring for NIXL
- ownership references
- request path correctness
- per-role wiring consistency

### Bottom takeaway box
**The platform value is not fewer YAML files. The platform value is a cleaner operational ownership boundary.**

### Suggested visual
A split slide with “User intent” on the left and “Platform-managed plumbing” on the right.

### Speaker note
This is a very strong close for the architecture section, because it reframes P/D from “advanced runtime trick” into **a platform responsibility problem**.

---

## Optional closing transition slide

### Title
**Why This Matters Operationally**

### Recommended body
- P/D is useful because prefill and decode have different resource profiles.
- llm-d is useful because routing and scheduling need role awareness.
- KAITO is useful because platform teams need a Kubernetes-native control-plane abstraction.
- Together they turn P/D from a manual stack into a repeatable platform workflow.

### Speaker note
Transition from architecture into:
- per-role autoscaling
- benchmark / break-even analysis
- production lessons

---

## Suggested one-line summary for this section

> **KAITO turns llm-d-style prefill/decode disaggregation from a manual routing stack into a declarative Kubernetes workflow.**

---

## References

- KAITO P/D docs: <https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation>
- Existing talk outline: `llm/kubecon-na-2026-pd-disaggregation.md`
- Existing deck support files:
  - `llm/kaito-pd-disaggregation-slide-text.md`
  - `llm/kaito-pd-disaggregation-deck-outline.md`
