# Test P/D Disaggregation with KAITO

This document describes how to verify that Prefill/Decode (P/D) disaggregation is working correctly with KAITO's `MultiRoleInference`.

## Prerequisites

- AKS cluster with KAITO installed and `MultiRoleInference` deployed
- `kubectl` configured with cluster access
- The `MultiRoleInference` resource should show all conditions as `True`:
  ```
  PrefillReady: True
  DecodeReady: True
  InferencePoolReady: True
  Ready: True
  ```

## Step 1: Verify Pod Status

```bash
# Check prefill and decode pods are running
kubectl get pods | grep -E "prefill|decode"
```

Expected output:
```
phi-4-mini-decode-spqrz-0    2/2     Running   0   ...
phi-4-mini-prefill-kmwss-0   1/1     Running   0   ...
```

- Decode pod has 2 containers: vLLM engine + routing sidecar (`llm-d-routing-sidecar`)
- Prefill pod has 1 container: vLLM engine only (no sidecar)

## Step 2: Verify Services and Gateway

```bash
# Check inference gateway and EPP services
kubectl get svc | grep -E "inference-gateway|epp"
```

Expected:
```
inference-gateway-istio                LoadBalancer   ...   80:xxxxx/TCP
phi-4-mini-inferencepool-epp           ClusterIP      ...   9002/TCP,9090/TCP
phi-4-mini-prefill-inferencepool-epp   ClusterIP      ...   9002/TCP,9090/TCP
phi-4-mini-decode-inferencepool-epp    ClusterIP      ...   9002/TCP,9090/TCP
```

## Step 3: Send a Test Request

```bash
# Send a chat completion request via the inference gateway
kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s -X POST "http://inference-gateway-istio.default.svc.cluster.local/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi-4-mini-instruct",
    "messages": [{"role": "user", "content": "What is 2+2? Answer briefly."}],
    "max_tokens": 30
  }'
```

Expected response:
```json
{
  "id": "chatcmpl-...",
  "model": "phi-4-mini-instruct",
  "choices": [{"message": {"content": "Four."}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 21, "completion_tokens": 3, "total_tokens": 24}
}
```

## Step 4: Verify P/D Split in Pod Logs

After sending the request, check both pod logs to confirm the request was processed by both pods:

### Check Prefill Pod

```bash
kubectl logs phi-4-mini-prefill-kmwss-0 --tail=5 --since=60s
```

Expected: `Avg prompt throughput` shows non-zero value (prompt processing happened here):
```
Engine 000: Avg prompt throughput: 0.5 tokens/s, Avg generation throughput: 0.1 tokens/s, ...
```

### Check Decode Pod

```bash
kubectl logs phi-4-mini-decode-spqrz-0 -c phi-4-mini-decode-spqrz --tail=5 --since=60s
```

Expected: `generation throughput` is non-zero AND **KV Transfer metrics** appear:
```
Engine 000: Avg prompt throughput: 0.1 tokens/s, Avg generation throughput: 10.0 tokens/s, ...
KV Transfer metrics: Num successful transfers=1, Avg xfer time (ms)=8.5, ... Throughput (MB/s)=235.2, Avg number of descriptors=64.0
```

## Step 5: Confirm KV Transfer (Key Indicator)

The **most important indicator** that P/D disaggregation is working is the `KV Transfer metrics` log line in the decode pod:

```
KV Transfer metrics: Num successful transfers=1, Avg xfer time (ms)=8.505, P90 xfer time (ms)=8.505, Avg post time (ms)=4.581, P90 post time (ms)=4.581, Avg MB per transfer=2.0, Throughput (MB/s)=235.156, Avg number of descriptors=64.0
```

This confirms:
- ✅ Prefill pod computed the KV cache
- ✅ KV cache was transferred to the decode pod via NIXL
- ✅ Decode pod used the transferred KV cache for token generation
- ✅ Transfer throughput: ~235 MB/s (expected range: 200-300 MB/s on A100)

## Summary of P/D Flow

```
Client Request
    │
    ▼
Inference Gateway (Istio)
    │
    ▼
EPP (Endpoint Picker Plugin)
    │  ── decides: prefill or decode? ──
    │
    ├──► Prefill Pod: processes prompt tokens, produces KV cache
    │         │
    │         │ (NIXL KV Transfer ~8ms, ~235 MB/s)
    │         ▼
    └──► Decode Pod: receives KV cache, generates output tokens
              │
              ▼
         Response back to client
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No KV Transfer metrics in decode log | Check EPP configmap has `prefix-based-pd-decider` and `by-label-selector` plugins configured |
| `model does not exist` error | Use full model name `phi-4-mini-instruct` (not `phi-4-mini`) |
| Prefill pod shows no throughput | Check EPP logs: `kubectl logs -l app=phi-4-mini-inferencepool-epp --tail=20` |
| KV transfer failures | Verify `VLLM_NIXL_SIDE_CHANNEL_HOST=status.podIP` env is set on both pods |
