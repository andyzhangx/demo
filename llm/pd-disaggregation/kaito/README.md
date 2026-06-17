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

The `llm-d-inference-scheduler:v0.8.0` image serves ext-proc gRPC on port 9002 with **TLS enabled by default**, regardless of the `--secure-serving=false` flag (this flag only affects non-ext-proc endpoints in v0.8.0).

### Symptoms
- All requests through the Istio gateway return HTTP 500
- Gateway logs: `Received gRPC error on stream: 14, message upstream connect error or disconnect/reset before headers. reset reason: connection termination`
- EPP logs show **no incoming requests** (connection terminated before reaching ext-proc handler)
- `grpcurl -plaintext <pod-ip>:9002` times out, but `grpcurl -insecure <pod-ip>:9002` works

### Fix
Update the EPP DestinationRule to use TLS:

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

> **Note:** This is needed because v0.8.0's ext-proc server uses a self-signed certificate. `insecureSkipVerify: true` skips cert validation.

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
