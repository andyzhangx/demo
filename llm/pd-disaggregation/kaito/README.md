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
