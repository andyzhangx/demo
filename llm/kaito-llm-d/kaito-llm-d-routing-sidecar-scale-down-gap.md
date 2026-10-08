# KAITO `llm-d-routing-sidecar` scale-down gap

## TL;DR

KAITO currently injects `llm-d-routing-sidecar` into decode pods as a regular container, but without sidecar-specific drain/readiness/preStop handling. That means scale-down does **not** currently guarantee that:

- no new requests will enter a soon-to-be-terminated decode pod;
- the routing sidecar will stay alive until all in-flight requests complete;
- distributed workers will wait for leader-side completion before teardown.

So yes, there is a real scale-down correctness gap today. The safest direction is a **unified preStop-based drain model**: mark pod/path draining first, stop new traffic, wait for sidecar + vLLM inflight completion, then exit.

_Date: 2026-10-08_

## Problem statement

In KAITO's current P/D (prefill/decode) disaggregation implementation, the `llm-d-routing-sidecar` injected into decode pods does not appear to have dedicated scale-down drain handling.

This creates a correctness gap during pod termination / scale-down:

- new requests may still arrive during the endpoint propagation window after a pod is marked for deletion;
- the routing sidecar may terminate before in-flight requests fully complete;
- for distributed inference (for example Ray-style leader/worker topologies), worker teardown may race with leader completion.

The practical concern is: **how do we guarantee no new requests enter a soon-to-be-terminated decode pod, while also allowing active requests to finish cleanly?**

## What the sidecar does

`llm-d-routing-sidecar` is the P/D orchestration proxy injected into decode pods.

It sits in front of local vLLM:

- listens on port `5000`;
- reads the routing/EPP header that identifies the selected prefill pod;
- sends the prompt to the selected prefill pod;
- forwards the request with KV-transfer context to local vLLM on port `5001`;
- local vLLM then pulls KV cache and continues decode/generation.

Without this sidecar, there is no component in the pod coordinating the prefill -> decode handoff.

## Current KAITO implementation observations

### 1. Sidecar injection is minimal

In `kaito/pkg/workspace/inference/preset_inferences.go`, `injectRoutingSidecar(...)` appends the sidecar container into `spec.Containers` and configures:

- `Name`
- `Image`
- `Args`
- `Ports`
- `Env`

But it does **not** configure:

- `Lifecycle.PreStop`
- sidecar-specific `ReadinessProbe`
- sidecar-specific `LivenessProbe`
- explicit drain/shutdown coordination for in-flight requests

### 2. Sidecar is a regular container, not a native sidecar with shutdown ordering semantics

The sidecar is added to normal `containers`, so Kubernetes does not automatically guarantee the shutdown ordering needed for "wait for main container request completion, then stop the sidecar" behavior.

### 3. Main container probes are on vLLM port 5001, not on the routing sidecar

For decode pods, KAITO rewrites the main vLLM container to port `5001` and the routing sidecar occupies port `5000`.

The main container gets startup/liveness/readiness probes, but the sidecar itself does not have an explicit readiness/drain contract.

## Why this is a scale-down risk

### Risk 1: endpoint propagation lag

Even if deletion/removal events propagate quickly, there is still a short window where routing components (for example EPP) may continue sending requests to a pod that was just marked for deletion.

If the pod has not yet switched into a strong draining/unready state, a new request can land on a pod already entering teardown.

### Risk 2: sidecar may exit before request chain finishes

The sidecar is part of the serving path, not an optional helper.

If it exits too early during termination:

- prompt forwarding to the prefill pod may be interrupted;
- local request proxying to vLLM may fail;
- streaming responses may be cut off;
- clients may see 5xx / reset / timeout behavior.

### Risk 3: vLLM-only drain is not enough

Even if vLLM has built-in drain behavior, that alone does not fully solve the issue because the routing sidecar is the actual entrypoint for decode pods.

So a solution that only drains vLLM but does not explicitly coordinate the routing sidecar still leaves a gap.

### Risk 4: distributed teardown ordering

For distributed inference, workers should not terminate before leader-side completion has finished.

If worker teardown happens too early, the last in-flight request can still fail even if leader-side drain logic exists.

## Suggested direction

A unified pod-level drain model is preferable:

1. **Stop taking new requests first**
   - Mark the pod / relevant serving path as draining or unready as soon as scale-down starts.
   - Ensure routing components stop selecting the pod as quickly as possible.

2. **Wait for in-flight completion**
   - Keep both vLLM and `llm-d-routing-sidecar` alive until active requests finish.
   - For distributed inference, workers should wait for leader completion before teardown.

3. **Only then exit**
   - Respect a sufficiently large `terminationGracePeriodSeconds` so long-running requests are not cut off prematurely.

## Possible implementation options discussed

### Option A: add a KAITO endpoint and use sidecar `httpGet` preStop

Because the routing sidecar image is distroless and cannot easily run a shell script, one option is:

- add a KAITO drain endpoint that blocks until vLLM / serving path has no in-flight requests;
- invoke that endpoint from an `httpGet` preStop hook on the sidecar.

Pros:

- explicit drain semantics;
- works with distroless image constraints;
- easier to reason about and observe.

### Option B: convert the routing sidecar to a native sidecar

This helps with shutdown ordering, but by itself it does **not** fully express the drain contract.

It can improve container stop sequencing, but still does not automatically guarantee:

- no new requests are accepted after drain starts;
- in-flight requests are fully completed;
- distributed worker/leader teardown is coordinated.

## Recommendation

Prefer a **preStop-based unified drain solution** over relying only on vLLM built-in drain or only on native-sidecar ordering.

Recommended semantics:

- pod enters draining/unready immediately on scale-down;
- EPP/routing stops sending new traffic;
- sidecar + vLLM wait for in-flight completion;
- distributed workers wait for leader completion;
- containers exit only after drain completes or grace period expires.

## Bottom line

**Yes, there is a current scale-down gap for KAITO-injected `llm-d-routing-sidecar`.**

It may not fail on every scale-down event, especially under low concurrency, but from a design/correctness perspective it does not currently guarantee safe shutdown of the full P/D request path.
