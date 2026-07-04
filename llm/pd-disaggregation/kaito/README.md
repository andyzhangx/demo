# EPP Configuration Notes for P/D Disaggregation with KAITO

## Current Setup (llm-d-inference-scheduler v0.8.0)

### Issues Encountered and Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| tokenizer crash: `Failed to infer device type` | GPU-only vllm image on CPU node | Use `vllm/vllm-openai-cpu:v0.21.0` image + `VLLM_TARGET_DEVICE=cpu` env |
| tokenizer crash: `Invalid repository ID` | Short model name `phi-4-mini-instruct` | Use full HuggingFace ID: `microsoft/phi-4-mini-instruct` |
| epp crash: `plugin type 'token-producer' is not registered` | `token-producer` not in v0.7.1 or v0.8.0 release branch | Remove `token-producer` from config (only available in main branch, coming in v0.9.0) |
| epp crash: `feature gate 'prepareDataPlugins' is unknown` | Feature gate removed in GIE v1.5.0 | Remove `featureGates` section from config |
| epp crash: `modelName is required in indexerConfig.tokenizersPoolConfig` | `precise-prefix-cache-scorer` requires tokenizer config | Add `tokenizersPoolConfig.modelName` |
| epp crash: `dial unix /tmp/tokenizer/tokenizer-uds.socket: no such file` | v0.8.0 `precise-prefix-cache-scorer` only supports UDS tokenizer, not HTTP | Remove `precise-prefix-cache-scorer` entirely (no public UDS tokenizer image exists) |
| epp crash: `references undefined plugin 'precise-prefix-cache-scorer'` | Removed from plugins but still referenced in schedulingProfiles | Remove from both `plugins` list AND `schedulingProfiles` |
| epp error: `no pods available in datastore` | InferencePool `spec.selector.matchLabels` requires both `apps.kubernetes.io/pod-index: "0"` and `multiroleinference.kaito.sh/created-by: phi-4-mini`, but model pods don't have matching labels (e.g., Deployment pods lack `apps.kubernetes.io/pod-index`) | Verify model pod labels match InferencePool selector: `kubectl get pods -l "multiroleinference.kaito.sh/created-by=phi-4-mini" --show-labels`. If using Deployment instead of StatefulSet, remove `apps.kubernetes.io/pod-index` from InferencePool selector or switch to StatefulSet |
| epp error: `failed to find available decode workerspod` (InferencePoolResourceExhausted) | EPP `by-label-selector` plugin expects `kaito.sh/inference-role: prefill/decode` labels, but KAITO pods only have `inferenceset.kaito.sh/created-by: phi-4-mini-prefill/decode` | Either add labels to pods: `kubectl label pod <pod> kaito.sh/inference-role=decode`, or update EPP configmap `by-label-selector` matchLabels to use `inferenceset.kaito.sh/created-by: phi-4-mini-decode` / `phi-4-mini-prefill`, then restart EPP |
| NIXL error: `Remote NIXL agent engine ID mismatch` / `handshake_setup_failed`, `'remote_host': 'localhost'` | vLLM NIXL connector reads `VLLM_NIXL_SIDE_CHANNEL_HOST` env (defaults to `localhost`). `POD_IP` and `VLLM_HOST_IP` alone are NOT sufficient — NIXL side channel uses its own env var. Decode tries to connect to itself instead of prefill pod | Add `VLLM_NIXL_SIDE_CHANNEL_HOST` env var (from `status.podIP` fieldRef) to **both** prefill and decode vLLM containers. Also add `POD_IP` and `VLLM_HOST_IP` for completeness. See [NIXL POD_IP Fix](#nixl-pod_ip-fix) section below |
| Gateway → EPP: 500 `upstream connect error or disconnect/reset before headers. reset reason: connection termination` | EPP ext-proc gRPC port 9002 uses TLS by default in `llm-d-inference-scheduler:v0.8.0`, even with `--secure-serving=false`. DestinationRule `tls.mode: DISABLE` sends plaintext → TLS server resets connection | Change DestinationRule to `tls.mode: SIMPLE` with `insecureSkipVerify: true`. See [Gateway TLS Fix](#gateway--epp-tls-fix) section below |
| Gateway → EPP: 500 `connection termination` (with Istio sidecar injected on EPP) | Namespace has `istio-injection=enabled`, EPP pod gets Istio sidecar (native sidecar pattern). Sidecar intercepts inbound gRPC on port 9002, but Gateway ext_proc connects directly (not through mesh mTLS path), causing connection reset | Add `traffic.sidecar.istio.io/excludeInboundPorts: "9002"` annotation to EPP deployment + set DestinationRule `tls.mode: DISABLE`. See [Istio Sidecar on EPP Fix](#istio-sidecar-on-epp-fix) section below |
| epp error: `metric family "vllm:lora_requests_info" not found` | EPP `core-metrics-extractor` expects LoRA metrics by default, but vLLM is not configured with LoRA | Non-fatal, can be ignored. To suppress: configure `--lora-metric=""` in EPP args |
| epp error: `poll failed ... dial tcp <pod-ip>:5001: connect: connection refused` | EPP metrics collector uses InferencePool `targetPort` (5001, routing sidecar) to scrape vLLM `/metrics`, but vLLM metrics are on port 5000 | Add `--model-server-metrics-port=5000` to EPP args (deprecated but functional in GIE v1.5.0) |
| epp error: `unable to read prefix cache state` | `prefix_based_pd_decider` reads `PrefixCacheMatchInfoKey` from EPP internal plugin state (not prometheus metrics). This data is produced by `approx-prefix-cache-producer` plugin. If this plugin or its dependency `token-producer` is not configured, the key is never written | Requires `token-producer` + `approx-prefix-cache-producer` plugins (available in GIE v1.5.0 / llm-d main branch). Without these, `prefix-based-pd-decider` cannot determine prefix cache hit ratio. Add `approx-prefix-cache-producer` plugin (built into GIE v1.5.0) before `prefix-based-pd-decider` in the EPP configmap. This plugin uses approximate hash-based prefix matching without needing a tokenizer sidecar. See config example below |

---

## Working EPP ConfigMap (v0.8.0 + GIE v1.5.0)

The following `config.yaml` is confirmed working for P/D disaggregation with prefix cache-aware routing:

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPickerConfig
plugins:
  - type: disagg-headers-handler
  - type: approx-prefix-cache-producer
    parameters:
      blockSizeTokens: 64
      autoTune: true
  - type: prefix-based-pd-decider
    parameters:
      nonCachedTokens: 4
  - type: disagg-profile-handler
    parameters:
      deciders:
        prefill: prefix-based-pd-decider
  - type: by-label-selector
    name: prefill-filter
    parameters:
      matchLabels:
        kaito.sh/inference-role: prefill
  - type: by-label-selector
    name: decode-filter
    parameters:
      matchLabels:
        kaito.sh/inference-role: decode
  - type: load-aware-scorer
    parameters:
      threshold: 10
  - type: max-score-picker
schedulingProfiles:
  - name: prefill
    plugins:
      - pluginRef: prefill-filter
      - pluginRef: load-aware-scorer
        weight: 10
      - pluginRef: max-score-picker
  - name: decode
    plugins:
      - pluginRef: decode-filter
      - pluginRef: load-aware-scorer
        weight: 10
      - pluginRef: max-score-picker
```

### Key: `approx-prefix-cache-producer`
- Built into GIE v1.5.0 (no extra image needed)
- Uses approximate hash-based prefix matching to compute `PrefixCacheMatchInfoKey` per endpoint
- Must be listed **before** `prefix-based-pd-decider` in plugins (it produces data that the decider consumes)
- Does NOT require a tokenizer sidecar — works with character-level approximation
- `autoTune: true` automatically adjusts block size based on `vllm:cache_config_info` metrics

### EPP args
Also add to EPP deployment args:
```
--model-server-metrics-port=5000
```
This tells the metrics collector to scrape vLLM metrics from port 5000 (where vLLM serves `/metrics`) instead of the InferencePool targetPort 5001 (routing sidecar).

---

## What to REMOVE from ConfigMap config.yaml

```yaml
# DELETE: feature gate not registered in v0.8.0
featureGates:
  prepareDataPlugins: true

# DELETE: plugin not available in v0.8.0 (only in main branch)
- type: token-producer
  parameters:
    modelName: "phi-4-mini-instruct"
    vllm:
      http: "http://localhost:8100"

# DELETE: requires UDS tokenizer socket not available
- type: precise-prefix-cache-scorer
  parameters:
    indexerConfig:
      kvBlockIndexConfig:
        enableMetrics: true
      tokenizersPoolConfig:
        modelName: "microsoft/phi-4-mini-instruct"
    tokenProcessorConfig:
      blockSize: 64

# DELETE from schedulingProfiles (both prefill and decode):
- pluginRef: precise-prefix-cache-scorer
  weight: 50
```

## What to MODIFY in Deployment

```yaml
# CHANGE tokenizer image: GPU image → CPU image
# Before:
image: vllm/vllm-openai:latest
# After:
image: vllm/vllm-openai-cpu:v0.21.0

# ADD env to tokenizer container:
env:
  - name: VLLM_TARGET_DEVICE
    value: "cpu"

# CHANGE model name in tokenizer args:
# Before:
args: ["launch", "render", "phi-4-mini-instruct", "--port=8100"]
# After:
args: ["launch", "render", "microsoft/phi-4-mini-instruct", "--port=8100"]

# CHANGE epp image for token-producer support (when available):
# v0.7.1 → v0.8.0 (minimum for disagg plugins)
image: mcr.microsoft.com/oss/v2/llm-d/llm-d-inference-scheduler:v0.8.0
```

---

## Future (v0.9.0 / main branch)

When `llm-d-inference-scheduler` v0.9.0 is released, re-enable:

```yaml
# ADD back to plugins:
- type: token-producer
  parameters:
    modelName: "microsoft/phi-4-mini-instruct"
    vllm:
      http: "http://localhost:8100"

# ADD back to plugins (no tokenizersPoolConfig needed — reads from CycleState):
- type: precise-prefix-cache-scorer
  parameters:
    indexerConfig:
      kvBlockIndexConfig:
        enableMetrics: true
    tokenProcessorConfig:
      blockSize: 64

# ADD back to schedulingProfiles:
- pluginRef: precise-prefix-cache-scorer
  weight: 50
```

The `token-producer` plugin tokenizes via HTTP (`vllm launch render` sidecar),
writes to CycleState, and `precise-prefix-cache-scorer` reads from it —
no UDS socket needed.

---

## UDS Tokenizer Investigation

In v0.8.0, `precise-prefix-cache-scorer` connects to a tokenizer via Unix Domain Socket
at `/tmp/tokenizer/tokenizer-uds.socket` (gRPC). There is **no public UDS tokenizer image**
in the llm-d project.

### llm-d repos checked:
- `llm-d/llm-d-router` — main source, contains plugin code
- `llm-d/llm-d-routing-sidecar` — "Incubating P/D sidecar", does NOT provide UDS tokenizer
- `llm-d/llm-d-inference-sim` — simulation only
- No dedicated tokenizer repo exists

### How UDS tokenizer was intended to work (internal/unreleased):
The UDS tokenizer is a gRPC service implementing `InitializeTokenizer` and `Tokenize` RPCs
over a Unix socket mounted at `/tmp/tokenizer/tokenizer-uds.socket`. It was used in internal
testing but never shipped as a public container image.

### Conclusion:
- **v0.8.0**: Cannot use `precise-prefix-cache-scorer` without building a custom UDS tokenizer
- **v0.9.0+**: Use `token-producer` plugin (HTTP-based) which writes to CycleState;
  `precise-prefix-cache-scorer` reads from CycleState instead of calling tokenizer directly

---

## P/D Disaggregation — Is `precise-prefix-cache-scorer` Required?

**No.** P/D routing works without it. The core disaggregation plugins are:

| Plugin | Role | Required for P/D? |
|--------|------|-------------------|
| `disagg-headers-handler` | Parse disagg headers from request | ✅ Yes |
| `disagg-profile-handler` | Route to prefill or decode profile | ✅ Yes |
| `prefix-based-pd-decider` | Decide prefill vs decode based on prefix | ✅ Yes |
| `by-label-selector` (prefill-filter/decode-filter) | Filter pods by role label | ✅ Yes |
| `load-aware-scorer` | Score pods by load | ✅ Yes (or any scorer) |
| `max-score-picker` | Pick highest-scored pod | ✅ Yes |
| `precise-prefix-cache-scorer` | Score by KV cache hit rate | ❌ Optimization only |
| `token-producer` | Pre-tokenize for cache scorer | ❌ Only needed with precise-prefix-cache-scorer |

Without `precise-prefix-cache-scorer`, the scheduler uses `load-aware-scorer` to pick
among prefill/decode pods by load — P/D separation still works correctly.

---

## NIXL POD_IP Fix

vLLM's NIXL connector uses the `VLLM_NIXL_SIDE_CHANNEL_HOST` environment variable to determine what IP address to register in the NIXL metadata for cross-pod KV transfer. **Without this env var, it defaults to `localhost`, causing cross-pod KV transfer to fail.**

> ⚠️ **Important (vLLM v0.19.1+):** Setting `POD_IP` alone is **NOT sufficient**. The NIXL connector reads `VLLM_NIXL_SIDE_CHANNEL_HOST` specifically (see `nixl_connector.py` line 556: `self.side_channel_host = envs.VLLM_NIXL_SIDE_CHANNEL_HOST`). `VLLM_HOST_IP` is used for general network binding but does NOT affect the NIXL side channel registration.

### Symptoms
- `NIXL transfer failure: handshake_setup_failed`
- `RuntimeError: Remote NIXL agent engine ID mismatch. Expected <prefill-id>, received <decode-id>`
- Error context shows `'remote_host': 'localhost', 'remote_port': 5600` (should be a real pod IP)
- `KeyError: '<engine-id>'` in `block_size_ratio_from_engine_id`

### Root Cause
Decode pod attempts NIXL handshake to `localhost:5600`, which connects to itself (same pod) instead of the remote prefill pod. The engine ID received is its own ID, not the expected prefill engine ID.

The NIXL connector's side channel host is determined by:
```python
# vllm/distributed/kv_transfer/kv_connector/v1/nixl_connector.py
self.side_channel_host = envs.VLLM_NIXL_SIDE_CHANNEL_HOST  # defaults to "localhost"
```

### Fix
Add `VLLM_NIXL_SIDE_CHANNEL_HOST` env var to **both** prefill and decode StatefulSets' **vLLM containers** (container index 0). Also add `VLLM_HOST_IP` and `POD_IP` for completeness:

```bash
# Patch prefill StatefulSet
kubectl patch statefulset <prefill-sts> --type=json \
  -p='[
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"POD_IP","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}},
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"VLLM_HOST_IP","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}},
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"VLLM_NIXL_SIDE_CHANNEL_HOST","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}}
  ]'

# Patch decode StatefulSet (both vLLM container[0] and sidecar container[1])
kubectl patch statefulset <decode-sts> --type=json \
  -p='[
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"POD_IP","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}},
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"VLLM_HOST_IP","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}},
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"VLLM_NIXL_SIDE_CHANNEL_HOST","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}},
    {"op":"add","path":"/spec/template/spec/containers/1/env/-","value":{"name":"VLLM_NIXL_SIDE_CHANNEL_HOST","valueFrom":{"fieldRef":{"fieldPath":"status.podIP"}}}}
  ]'
```

After patching, delete the pods to trigger recreation:
```bash
kubectl delete pod <prefill-pod> <decode-pod>
```

### Verification
Confirm the env is correctly set inside the running pods:
```bash
kubectl exec <prefill-pod> -- python3 -c "from vllm import envs; print(envs.VLLM_NIXL_SIDE_CHANNEL_HOST)"
# Should print a real pod IP like 10.244.x.x, NOT "localhost"
```

> **Note:** This is a KAITO controller bug — it should inject `VLLM_NIXL_SIDE_CHANNEL_HOST` (set to Pod IP) into the vLLM containers automatically when P/D disaggregation is enabled. A fix PR has been proposed: https://github.com/kaito-project/kaito/pull/XXX (promote InferenceSet to beta + enable by default).

---

## Gateway → EPP TLS Fix

### Why is a DestinationRule always required?

When using Istio as the Gateway API provider, a DestinationRule is **always required** for the EPP service. This is because:

1. **EPP runs without an Istio sidecar** — The EPP pod is deployed by the llm-d-router Helm chart and does not have Istio sidecar injection. Without a sidecar, Istio cannot auto-negotiate mTLS.

2. **Istio Gateway doesn't know how to connect** — Without explicit configuration, the Istio Gateway (Envoy) may attempt TLS or mTLS to reach the EPP's ext-proc gRPC port 9002, but the EPP isn't set up for that.

3. **Injecting an Istio sidecar on EPP does NOT work** — We tested adding `sidecar.istio.io/inject: "true"` to the EPP deployment. The sidecar gets injected (pod becomes 2/2), but the Gateway's ext-proc filter connects directly to the EPP service (not through mesh mTLS), so the sidecar intercepts the inbound traffic and expects mTLS that the Gateway isn't sending via the ext-proc path → `connection termination` errors. See also [Istio Sidecar on EPP Fix](#istio-sidecar-on-epp-fix) for the case where sidecar is auto-injected by namespace label.

### Which DestinationRule mode to use?

| EPP version | `--secure-serving` | EPP listens on | DestinationRule mode |
|---|---|---|---|
| `llm-d-inference-scheduler:v0.8.0` | `true` (default) | TLS gRPC (self-signed cert) | `mode: SIMPLE` + `insecureSkipVerify: true` |
| `llm-d-router-endpoint-picker:v0.9.1` | `false` | Plaintext gRPC | `mode: DISABLE` |

- **`mode: SIMPLE`** = Gateway sends TLS but skips certificate verification (for self-signed certs)
- **`mode: DISABLE`** = Gateway sends plaintext (no TLS at all)

Using the wrong mode causes `WRONG_VERSION_NUMBER` (plaintext hitting TLS server) or `connection termination` (TLS hitting plaintext server).

### v0.8.0 (secure-serving=true, default)

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: phi-4-mini-inferencepool-epp
spec:
  host: phi-4-mini-inferencepool-epp
  trafficPolicy:
    tls:
      mode: SIMPLE
      insecureSkipVerify: true
```

### v0.9.1 (secure-serving=false)

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: phi-4-mini-inferencepool-epp
spec:
  host: phi-4-mini-inferencepool-epp.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: DISABLE
```

### Symptoms when DestinationRule is wrong or missing
- All requests through the Istio gateway return HTTP 500 or timeout
- Gateway (Envoy) logs: `Received gRPC error on stream: 14` with either:
  - `WRONG_VERSION_NUMBER` — Gateway sends TLS to plaintext EPP (need `mode: DISABLE`)
  - `connection termination` — Gateway sends plaintext to TLS EPP (need `mode: SIMPLE`)
- EPP logs show **no incoming requests** (connection fails before reaching ext-proc handler)
- With `failureMode: FailOpen`, traffic still reaches model pods but **without P/D-aware routing** (EPP is bypassed)

---

## Istio Sidecar on EPP Fix

### Problem

When the `default` namespace has `istio-injection=enabled`, the EPP pod automatically gets an Istio sidecar injected (native sidecar pattern — `istio-proxy` as a restartable init container). This causes **all Gateway ext_proc gRPC connections to EPP to fail** with:

```
Received gRPC error on stream: 14, message upstream connect error or disconnect/reset before headers.
reset reason: connection termination{upstream_reset_before_response_started{connection_termination}}
```

### Root Cause

The Istio sidecar's iptables rules (configured by `istio-init`) intercept **all inbound traffic** (`-b *`), including port 9002 (EPP ext-proc gRPC). The Gateway envoy connects to EPP's service IP, but the traffic hits the sidecar's inbound listener first. The sidecar expects either:
- mTLS from other mesh services, OR
- Plaintext in PERMISSIVE mode

However, the Istio Gateway's ext_proc filter uses a **separate gRPC connection** that doesn't go through the standard Istio mTLS negotiation path. This causes the sidecar to terminate the connection before it reaches the EPP application.

Key findings:
- `DestinationRule` changes (DISABLE, ISTIO_MUTUAL, or deletion) do **NOT** fix this
- Auto-mTLS does **NOT** work for ext_proc connections to sidecar-injected pods
- The issue only occurs when `istio-injection=enabled` on the namespace

### Fix

Exclude port 9002 from Istio sidecar inbound interception so Gateway traffic goes directly to the EPP application:

```bash
kubectl patch deployment <epp-deployment> --type='merge' \
  -p '{"spec":{"template":{"metadata":{"annotations":{"traffic.sidecar.istio.io/excludeInboundPorts":"9002"}}}}}'
```

Then set the DestinationRule to `DISABLE` (since traffic now bypasses the sidecar):

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: <mri-name>-inferencepool-epp
spec:
  host: <mri-name>-inferencepool-epp
  trafficPolicy:
    tls:
      mode: DISABLE
```

### How to Detect This Issue

1. EPP pod shows `2/2` Running (sidecar injected) or has `istio-proxy` as init container with state `running`
2. Gateway envoy logs show repeated `connection termination` errors for ext_proc
3. EPP application logs show **no incoming requests** (requests never reach the app)
4. Direct `curl` to EPP pod IP:9002 returns `server: envoy` header (traffic going through sidecar)

### Verification After Fix

```bash
# Confirm new EPP pod has the annotation
kubectl get pod <new-epp-pod> -o jsonpath='{.metadata.annotations.traffic\.sidecar\.istio\.io/excludeInboundPorts}'
# Should output: 9002

# Test request through gateway
curl -s http://<gateway-ip>/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"phi-4-mini-instruct","prompt":"Hello","max_tokens":10}'
# Should return a valid JSON response with choices

# Confirm no ext_proc errors in gateway logs
kubectl logs <gateway-pod> --since=30s | grep -c "ext_proc"
# Should output: 0
```

> **Note for KAITO E2E tests:** When the E2E setup installs Istio with `istio-injection=enabled` on the namespace where EPP runs, the test must also add `traffic.sidecar.istio.io/excludeInboundPorts: "9002"` to the EPP deployment. See [PR #2149](https://github.com/kaito-project/kaito/pull/2149) for the E2E test that validates P/D disaggregation.

---

## ✅ End-to-End Working P/D with NIXL KV Transfer (2026-05-25)

See [`pd-working-config.md`](pd-working-config.md) for the verified working configuration.

### Quick Summary of Required Changes

| Component | Change | Why |
|-----------|--------|-----|
| Prefill pod | Remove sidecar container | Sidecar causes OOM or routing loops on prefill |
| Prefill pod | Add `VLLM_NIXL_SIDE_CHANNEL_HOST=status.podIP` env | NIXL ZMQ handshake needs reachable IP, not "localhost" |
| Decode pod | Sidecar: `--port=5000 --vllm-port=5001` | Sidecar receives traffic on InferencePool targetPort |
| Decode pod | vLLM: append `--port 5001` | Move vLLM to different port than sidecar |
| Decode pod | Add `VLLM_NIXL_SIDE_CHANNEL_HOST=status.podIP` env | Same reason as prefill |
| InferencePool | `targetPorts: [{number: 5000}]` | Route to decode sidecar, not vLLM directly |

### Patch Scripts
- [`prefill-patch.sh`](prefill-patch.sh) — Remove sidecar + add NIXL env
- [`decode-patch.sh`](decode-patch.sh) — Swap ports + add NIXL env + patch InferencePool

### Verified Performance
```
NIXL KV Transfer: 4MB in 15.8ms = 252.9 MB/s throughput
```

---

## Related KAITO PRs

| PR | Description | Status |
|----|-------------|--------|
| [#2093](https://github.com/kaito-project/kaito/pull/2093) | feat: support P/D disaggregation | WIP |
| [#2149](https://github.com/kaito-project/kaito/pull/2149) | test: add P/D disaggregation E2E validation for MultiRoleInference | Open |
| New PR (TBD) | feat: promote InferenceSet to beta & enable `EnableInferenceSetController` by default | Planned |

### InferenceSet Promotion to Beta

The `InferenceSet` CRD (currently alpha, gated behind `EnableInferenceSetController` feature flag) should be promoted to **beta** and **enabled by default**. This is required because:

1. **P/D disaggregation depends on InferenceSet** — the `MultiRoleInference` controller creates `InferenceSet` resources for prefill/decode roles
2. **NIXL env injection should be automatic** — the InferenceSet controller should inject `VLLM_NIXL_SIDE_CHANNEL_HOST` (set to Pod IP via `status.podIP` fieldRef) into vLLM containers when the inference role is `prefill` or `decode`. Currently users must manually patch StatefulSets.
3. **Production readiness** — InferenceSet has been stable since v0.6.x and is actively used for multi-role inference workloads

Expected changes in the PR:
- Move `InferenceSet` CRD from `v1alpha1` to `v1beta1`
- Set `EnableInferenceSetController` feature gate default to `true`
- Auto-inject `VLLM_NIXL_SIDE_CHANNEL_HOST`, `VLLM_HOST_IP`, and `POD_IP` env vars into vLLM inference containers when `KAITO_INFERENCE_ROLE` is `prefill` or `decode`

---

## NIXL on A10 (or any GPU without RDMA/NVLink)

**TL;DR:** NIXL is a multi-backend framework, not a single protocol. On A10 nodes it falls back to **UCX/TCP over host memory** — slower than RDMA, but functionally works. If a test prints:

```
WARNING: KV transfer metrics not observed — NIXL may not be available in this environment (requires RDMA/NVLink). Skipping KV transfer assertion.
```

but the decode pod still shows `generation throughput > 0`, KV transfer **did happen** — the warning is misleading. The real cause is that the `nixl_*` / `vllm:kv_transfer_*` Prometheus metrics weren't scraped, not that NIXL was unavailable.

### NIXL backends (highest → lowest performance)

| Backend | Requires | Notes |
|---|---|---|
| UCX + GPUDirect RDMA (IB/RoCE) | A100/H100 + IB HCA + GDR firmware | Zero-copy GPU→NIC→GPU, µs latency |
| UCX + NVLink (NVLS/P2P) | Intra-node NVLink | Only within a single node |
| **UCX + TCP** | Any NIC | **A10 fallback path** — GPU→pinned host→TCP→pinned host→GPU |
| Mooncake / Redis / etc. | External store | Slowest, hardware-agnostic |

### Why A10 can't use the fast paths

- A10 has **no NVLink** (Ampere consumer/entry datacenter SKU stripped it out; only A100 has it).
- A10 is not certified for **GPUDirect RDMA over InfiniBand** — the driver/firmware combo needed for GDR ships with A100/H100.
- On Azure `Standard_NV*_A10_v5` VMs the NIC is a Mellanox VF via Accelerated Networking, **not an IB HCA**.

### What actually happens on A10 → A10

```
prefill GPU (A10)
  ↓ cudaMemcpy D2H (pinned)
prefill host RAM
  ↓ TCP over VNet (~3–6 GB/s on 25/50 Gbps NICs)
decode host RAM
  ↓ cudaMemcpy H2D (pinned)
decode GPU (A10)
```

- **Bandwidth:** ~3–6 GB/s (vs ~25+ GB/s with RDMA on A100)
- **Latency:** extra D2H/H2D `cudaMemcpy` + TCP round-trip on top of the network hop
- **CPU cost:** pinned buffers + TCP stack burn host CPU

### Why the KV-transfer metrics might be empty even when transfer works

The `WARNING: NIXL may not be available` really means "we didn't see the metrics we expected." Likely reasons:

1. **vLLM version too old** — `vllm:kv_transfer_*` counters were added in `v0.6.4` / `v0.7.x` disagg pipeline.
2. **KV metrics not enabled** at vLLM startup (they're opt-in behind `--enable-metrics` + connector-specific flags).
3. **Different KV connector selected** — vLLM has `NixlConnector`, `PyNcclConnector`, `LMCacheConnector`, `MooncakeConnector`, etc. Not all of them emit the same metric names.
4. **Prometheus scrape wasn't wired** — metrics endpoint not exposed on the pod's Service.

### Recommendations for E2E tests on A10

**Preferred: assert on transport-agnostic signals** rather than `nixl_*` counters:

- Decode pod's `vllm:num_requests_running > 0` and **TTFT (time-to-first-token) significantly lower** than a non-disagg baseline → proves it reused KV from prefill.
- Prefill pod's `vllm:prompt_tokens_total > 0` while decode pod's `vllm:prompt_tokens_total ≈ 0` → confirms decode is not re-doing prefill.

**Alternative: force the backend + enable NIXL metrics explicitly.** Example:

```yaml
- --kv-transfer-config
- '{"kv_connector":"NixlConnector","kv_role":"kv_both","kv_buffer_device":"cuda","kv_parallel_size":1}'
```

Then verify inside the container:

```bash
ucx_info -d | grep -E 'tcp|rdma'   # confirm which transports UCX built with
```

On A10 you should see `tcp` device; `nixl_*` counters should then be emitted (backed by TCP under the hood).

### Rewording the warning

The current message conflates two things ("NIXL unavailable" vs "metrics not scraped"). Better wording:

> `WARNING: KV transfer metrics not exposed (nixl_* / vllm:kv_transfer_* absent). Skipping metrics-based KV transfer assertion. Transfer itself may still have succeeded via UCX/TCP fallback on non-RDMA GPUs (e.g., A10).`

---

## P/D Prometheus Metrics — What's Available

P/D observability is split across three layers. There is no single "P/D dashboard metric"; you compose one from EPP (routing decisions), vLLM (per-stage timing + KV cache), and — if KAITO PR [#1890](https://github.com/kaito-project/kaito/pull/1890) is applied — a KV cache events subscriber.

### 1. llm-d EPP (`llm-d-inference-scheduler`) — port `:9090`

P/D-specific counter (ALPHA), prefix `llm_d_inference_scheduler_`:

| Metric | Type | Labels | Notes |
|---|---|---|---|
| **`disagg_decision_total`** | Counter | `model_name`, `decision_type` | `decision_type` ∈ `decode-only` / `prefill-decode` / `encode-decode` / `encode-prefill-decode`. Use this as the top-level "how often did we actually disaggregate" panel |
| `pd_decision_total` *(deprecated)* | Counter | `model_name`, `decision_type` | Old 2-value counter; only present when the deprecated `pd-profile-handler` is configured. Prefer `disagg_decision_total` |

Flow control (only when `flowControl` feature gate is enabled), prefix `llm_d_epp_`:

- `flow_control_request_queue_duration_seconds` (Histogram, `outcome=Dispatched|RejectedCapacity|EvictedTTL|…`)
- `flow_control_dispatch_cycle_duration_seconds` (Histogram)
- `flow_control_request_enqueue_duration_seconds` (Histogram)
- `flow_control_queue_size` / `flow_control_queue_bytes` (Gauge)
- `flow_control_pool_saturation` (Gauge, 0–1) — sustained 1.0 = all backends at capacity

ext_proc gRPC stream lifecycle (only with `--enable-grpc-stream-metrics`), prefix `llm_d_epp_`:

- `extproc_streams_inflight` (Gauge)
- `extproc_stream_duration_seconds` (Histogram)
- `extproc_streams_total{code=OK|Canceled|DeadlineExceeded|Internal|…}` (Counter)

Plus generic GIE metrics inherited from `gateway-api-inference-extension` (e.g. `inference_pool_ready_pods`, `inference_extension_scheduler_plugin_duration_seconds` — useful for tracking `prefix-based-pd-decider` / `load-aware-scorer` plugin latency).

### 2. vLLM engine — port `:5000/metrics` (prefix `vllm:`)

Stage-split timing (this is where P/D actually shows up):

| Metric | Type | Meaning |
|---|---|---|
| **`vllm:request_prefill_time_seconds`** | Histogram | Per-request prefill phase duration |
| **`vllm:request_decode_time_seconds`** | Histogram | Per-request decode phase duration |
| `vllm:time_to_first_token_seconds` (TTFT) | Histogram | Best single-signal for prefill quality |
| `vllm:inter_token_latency_seconds` (TPOT/ITL) | Histogram | Best single-signal for decode quality |
| `vllm:request_queue_time_seconds` | Histogram | Time in engine queue before scheduling |
| `vllm:e2e_request_latency_seconds` | Histogram | End-to-end |

KV cache — critical for judging P/D routing quality:

- `vllm:kv_cache_usage_perc` (Gauge)
- `vllm:prefix_cache_queries` / `vllm:prefix_cache_hits` (Counter) — **hit ratio is the primary signal that P/D routing is landing decode on the right pod**
- `vllm:kv_block_lifetime_seconds` / `vllm:kv_block_idle_before_evict_seconds` / `vllm:kv_block_reuse_gap_seconds` (Histograms, sampled — enable with `--kv-cache-metrics-sample`)

Throughput / counts:

- `vllm:num_requests_running` / `_waiting` / `_swapped`
- `vllm:prompt_tokens_total` / `vllm:generation_tokens_total`
- `vllm:num_preemptions_total`
- `vllm:request_success_total{finish_reason=…}`

**Important scrape gotcha:** the InferencePool `targetPort` (5001) points at the P/D routing sidecar, not vLLM. Prometheus must scrape vLLM's own `/metrics` on port 5000. On the EPP side this is done via `--model-server-metrics-port=5000` (see [Working EPP ConfigMap](#working-epp-configmap-v080--gie-v150)).

### 3. KV cache transfer (NIXL / Mooncake) — the observability gap

- **NIXL connector:** as of the versions used here (vLLM v0.19.1 – v0.21), there is **no stable `nixl_*` or `vllm:kv_transfer_*` Prometheus metric family**. Handshake / transfer failures are surfaced only in logs (see [NIXL on A10](#nixl-on-a10-or-any-gpu-without-rdmanvlink)). Any e2e test that asserts on `nixl_*` counters will produce false negatives.
- **Mooncake connector:** vLLM v0.21+ added bi-directional KV transfers with **Mooncake transfer telemetry**. If you can pick the connector, Mooncake is currently the better-observed option.
- **Practical workaround** for NIXL: assert on transport-agnostic signals — decode pod's `vllm:num_requests_running > 0` with TTFT well below the non-disagg baseline, plus decode pod's `vllm:prompt_tokens_total ≈ 0`, is a reliable proxy that KV was actually reused from prefill.

### 4. KAITO PR [#1890](https://github.com/kaito-project/kaito/pull/1890) — KV cache events (ZMQ, not Prometheus)

With #1890 applied, vLLM pods expose a **ZMQ PUB** stream on port **5557** (`kv-events`) that emits per-block lifecycle events:

- `BlockStored` — new KV block cached
- `BlockRemoved` — block evicted
- `AllBlocksCleared` — cache flush

Not scrape-able by Prometheus directly. Two uses:

1. **Feed llm-d's `precise-prefix-cache-scorer`** — the accurate (vs. approximate hash-based) prefix cache scorer consumes this ZMQ stream to build a global KV block index. This is the real payoff of #1890: unlocking precise P/D routing without a UDS tokenizer sidecar.
2. **Turn events into Prometheus counters** yourself with a small subscriber (pyzmq, ~20 LoC). Suggested metrics: `kv_blocks_stored_total{pod,role}`, `kv_blocks_removed_total{pod,role}`, and derived `kv_cache_churn_rate` = eviction/s (high churn ⇒ capacity too small, decode hit-rate will drop).

**Security:** port 5557 is unauthenticated / unencrypted. PR #1890 only exposes it on `ClusterIP` Services (not LoadBalancer), but any in-cluster pod can subscribe. Add a `NetworkPolicy` restricting ingress to EPP + your subscriber in production.

### 5. Full observability map

| Layer | Endpoint | Format | Key P/D signals |
|---|---|---|---|
| llm-d EPP | `:9090/metrics` | Prometheus | `disagg_decision_total`, flow control queue depth, pool saturation, plugin latency |
| vLLM engine | `:5000/metrics` | Prometheus | `request_prefill_time_seconds`, `request_decode_time_seconds`, TTFT, ITL, `prefix_cache_hits` |
| vLLM KV events (KAITO #1890) | `:5557` | **ZMQ PUB** | `BlockStored` / `BlockRemoved` / `AllBlocksCleared` — needs subscriber |
| NIXL / Mooncake | — | logs (NIXL) / metrics (Mooncake v0.21+) | KV transfer bytes / latency (only on Mooncake today) |

### 6. Starter PromQL for a P/D dashboard

```promql
# 1. Routing distribution: how often does EPP actually disaggregate?
sum by (decision_type) (
  rate(llm_d_inference_scheduler_disagg_decision_total[5m])
)

# 2. Prefill TTFT p95 (label pods with role=prefill)
histogram_quantile(0.95,
  sum by (le) (
    rate(vllm:time_to_first_token_seconds_bucket{role="prefill"}[5m])
  )
)

# 3. Decode ITL p95
histogram_quantile(0.95,
  sum by (le) (
    rate(vllm:inter_token_latency_seconds_bucket{role="decode"}[5m])
  )
)

# 4. Prefix cache hit ratio — primary signal for P/D routing quality
sum(rate(vllm:prefix_cache_hits[5m]))
  / sum(rate(vllm:prefix_cache_queries[5m]))

# 5. Flow control saturation per pool
max by (inference_pool) (llm_d_epp_flow_control_pool_saturation)

# 6. Prefill vs decode phase time (stage cost breakdown)
histogram_quantile(0.5, sum by (le)(rate(vllm:request_prefill_time_seconds_bucket[5m])))
histogram_quantile(0.5, sum by (le)(rate(vllm:request_decode_time_seconds_bucket[5m])))
```

### 7. Common misreads

- **"No P/D metrics exist"** — false. `disagg_decision_total` (EPP) and `request_prefill_time_seconds` / `request_decode_time_seconds` (vLLM) are shipping today.
- **"NIXL will show up in Prometheus"** — false today. Only Mooncake exposes KV transfer telemetry as of vLLM v0.21.
- **Scraping port 5001 returns nothing useful** — that's the routing sidecar. Scrape 5000 for vLLM engine metrics.
- **`vllm:lora_requests_info` warnings from EPP `core-metrics-extractor`** — non-fatal when LoRA is not configured; safe to ignore or suppress with `--lora-metric=""`.

### 8. References

- llm-d EPP metrics: <https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/metrics.md>
- vLLM metrics design: <https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md>
- GIE metrics guide: <https://github.com/kubernetes-sigs/gateway-api-inference-extension/blob/main/site-src/guides/metrics-and-observability.md>
- KAITO #1890 (KV cache events on vLLM): <https://github.com/kaito-project/kaito/pull/1890>

