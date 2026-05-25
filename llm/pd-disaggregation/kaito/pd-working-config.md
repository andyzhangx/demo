# Working P/D Disaggregation Configuration (NIXL KV Transfer Verified)

## Overview

This documents the **confirmed working** configuration for P/D disaggregated inference with NIXL KV cache transfer using:
- KAITO MultiRoleInference CR
- llm-d-routing-sidecar v0.8.0
- vLLM with NixlConnector (kv_role=kv_both)
- EPP with disagg-headers-handler

## Architecture

```
Client → Envoy/Gateway → EPP (sets x-prefiller-host-port header)
  → Decode Sidecar:5000 (reads header, reverse-proxies prefill request)
    → Prefill vLLM:5000 (does prefill, returns kv_transfer_params with pod IP:5600)
  → Decode Sidecar forwards to local Decode vLLM:5001 (with kv_transfer_params)
    → Decode vLLM connects to Prefill ZMQ side channel (pod_ip:5600) for NIXL handshake
    → Decode vLLM reads KV cache via NIXL UCX from Prefill
    → Decode completes token generation
  → Response back through chain
```

**Key insight from llm-d docs:** "No sidecar or coordination logic is needed on the prefill or encode nodes."

## Critical Configuration Changes

### 1. Prefill Pod — NO Sidecar

The prefill pod runs **only the vLLM container** (no routing sidecar). The sidecar causes OOM or routing loops on prefill.

Required env var on the vLLM container:
```yaml
env:
  - name: VLLM_NIXL_SIDE_CHANNEL_HOST
    valueFrom:
      fieldRef:
        fieldPath: status.podIP
```

Without this, vLLM advertises `remote_host: "localhost"` in `kv_transfer_params`, and the decode vLLM cannot reach the prefill's ZMQ side channel from a different pod.

### 2. Decode Pod — Sidecar on Port 5000, vLLM on Port 5001

```yaml
containers:
  # vLLM container - port 5001
  - name: phi-4-mini-decode
    command:
      - /bin/sh
      - -c
      - "python3 /workspace/vllm/inference_api.py ... --port 5001"
    env:
      - name: VLLM_NIXL_SIDE_CHANNEL_HOST
        valueFrom:
          fieldRef:
            fieldPath: status.podIP
    ports:
      - containerPort: 5001
        protocol: TCP

  # Routing sidecar - port 5000
  - name: llm-d-routing-sidecar
    image: mcr.microsoft.com/oss/v2/llm-d/llm-d-routing-sidecar:v0.8.0
    args:
      - "--port=5000"
      - "--vllm-port=5001"
      - "--secure-proxy=false"
    ports:
      - containerPort: 5000
        protocol: TCP
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 2Gi
```

### 3. InferencePool — targetPort 5000

```yaml
apiVersion: inference.networking.k8s.io/v1alpha1
kind: InferencePool
metadata:
  name: phi-4-mini-inferencepool
spec:
  targetPorts:
    - number: 5000
  selector:
    matchLabels:
      apps.kubernetes.io/pod-index: "0"
      multiroleinference.kaito.sh/created-by: phi-4-mini
  endpointPickerRef:
    kind: Service
    name: phi-4-mini-inferencepool-epp
    port:
      number: 9002
    failureMode: FailClose
```

### 4. Pod Labels (required for EPP routing)

Prefill pod needs:
```yaml
labels:
  kaito.sh/inference-role: prefill
```

Decode pod needs:
```yaml
labels:
  kaito.sh/inference-role: decode
```

If KAITO doesn't set these automatically, add them manually:
```bash
kubectl label pod <prefill-pod> kaito.sh/inference-role=prefill
kubectl label pod <decode-pod> kaito.sh/inference-role=decode
```

## Why This Works

1. **EPP** receives request, runs `disagg-profile-handler`:
   - First selects a decode pod (via `decode-filter` + `load-aware-scorer`)
   - Then selects a prefill pod (via `prefill-filter` + `load-aware-scorer`)
   - Sets `x-prefiller-host-port: <prefill-pod-ip>:5000` header
   - Routes request to decode pod at port 5000 (sidecar)

2. **Decode sidecar** (port 5000):
   - Reads `x-prefiller-host-port` header
   - Sends prefill request to prefill vLLM (with `max_tokens=1`)
   - Prefill vLLM returns `kv_transfer_params` (engine_id, block_ids, remote_host=pod_ip, remote_port=5600)
   - Sidecar forwards decode request to local vLLM:5001 with `kv_transfer_params`

3. **Decode vLLM** (port 5001):
   - Receives request with `kv_transfer_params`
   - Connects to prefill's ZMQ side channel (`<prefill_pod_ip>:5600`) for NIXL handshake
   - Registers prefill engine metadata (block_size, num_blocks, etc.)
   - Reads KV cache from prefill via NIXL UCX transport
   - Performs decode (token generation) using transferred KV cache

## Verified Results

```
KV Transfer metrics: Num successful transfers=1, Avg xfer time (ms)=15.816,
Avg MB per transfer=4.0, Throughput (MB/s)=252.908, Avg number of descriptors=128.0
```

## Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `KeyError: '<engine_id>'` in nixl_connector.py | Decode vLLM can't reach prefill ZMQ side channel (handshake fails) | Set `VLLM_NIXL_SIDE_CHANNEL_HOST` to pod IP on both pods |
| Prefill sidecar OOM (>2Gi) | Sidecar with `--inference-pool-name` triggers endpoint watcher memory leak | Remove prefill sidecar entirely |
| `kv_transfer_params: null` but request succeeds | Request not routed through P/D path (went to prefill directly without disagg) | Check EPP logs for decode profile selection; verify pod labels |
| `connection refused` to vLLM:5001 | vLLM still initializing NIXL (takes ~3min for model load + NIXL init) | Wait for NIXL init: look for "NIXL KV cache metadata published" in vLLM logs |
| `http: proxy error: EOF` from sidecar | Prefill sidecar's NIXL v2 handler crashes on incoming disagg request | Don't use sidecar on prefill pod |

## Environment Variables

| Variable | Value | Required On | Purpose |
|----------|-------|-------------|---------|
| `VLLM_NIXL_SIDE_CHANNEL_HOST` | `status.podIP` (downward API) | Both prefill & decode vLLM | Advertise reachable IP for ZMQ handshake |
| `VLLM_NIXL_SIDE_CHANNEL_PORT` | `5600` (default) | Optional | ZMQ side channel port |

## vLLM kv_transfer_config

Both prefill and decode vLLM use the same config (via KAITO inference_config.yaml):
```yaml
kv_transfer_config:
  kv_connector: NixlConnector
  kv_role: kv_both
  kv_load_failure_policy: fail
```

`kv_role: kv_both` means each instance can act as either sender or receiver — this is the correct llm-d design for flexible scheduling.

---

## Why Sidecar Must Be on Port 5000 (Not 5001)

### Constraint

The EPP uses `InferencePool.spec.targetPorts` to construct **both** the decode routing destination AND the `x-prefiller-host-port` header value. There is only ONE targetPort shared across all pods in the pool.

This means:
- `x-prefiller-host-port` = `<prefill_pod_ip>:<targetPort>`
- Decode routing destination = `<decode_pod_ip>:<targetPort>`

### Why `targetPort=5001` Doesn't Work

| Component | Port 5000 | Port 5001 |
|-----------|-----------|-----------|
| Prefill pod (no sidecar) | ✅ vLLM listening | ❌ nothing |
| Decode pod | sidecar | vLLM |

If `targetPort=5001`:
- EPP routes decode request to `decode_ip:5001` → hits sidecar ✅
- EPP sets header `x-prefiller-host-port: prefill_ip:5001` → **nothing listening on prefill:5001** ❌ → connection refused

### Why `targetPort=5000` Works

| Component | Port 5000 | Port 5001 |
|-----------|-----------|-----------|
| Prefill pod (no sidecar) | ✅ vLLM listening | — |
| Decode pod | ✅ sidecar listening | vLLM |

If `targetPort=5000`:
- EPP routes decode request to `decode_ip:5000` → hits sidecar ✅
- EPP sets header `x-prefiller-host-port: prefill_ip:5000` → hits prefill vLLM ✅

### Rule

> **InferencePool targetPort must equal the port that prefill vLLM listens on**, because the EPP uses the same targetPort for all pods in the pool.

The decode sidecar must therefore be configured to listen on that same port, with vLLM moved to a different port (5001).
