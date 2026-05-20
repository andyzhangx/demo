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
