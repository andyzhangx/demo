# Istio Gateway + EPP: Required Configuration Fixes

## Problem

When using Istio Gateway API with `gateway-api-inference-extension` EPP (ext_proc), the default Istio mTLS configuration breaks connectivity because:
1. EPP pod has no Istio sidecar → Gateway envoy's auto-mTLS fails (TLS handshake to plain gRPC)
2. Backend vLLM pods have no sidecar → same mTLS mismatch

## Required Fixes

### 1. DestinationRule DISABLE for EPP Service

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: phi-4-mini-inferencepool-epp
  namespace: default
spec:
  host: phi-4-mini-inferencepool-epp.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: DISABLE
```

### 2. DestinationRule DISABLE for Backend Service

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: phi-4-mini-inferencepool-backend
  namespace: default
spec:
  host: phi-4-mini-inferencepool-ip-3ecb0ff8.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: DISABLE
```

### 3. EPP Pod: Disable Sidecar Injection

```yaml
metadata:
  annotations:
    sidecar.istio.io/inject: "false"
```

### 4. EPP ConfigMap (with P/D disaggregation plugins)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: phi-4-mini-inferencepool-epp
  namespace: default
data:
  config.yaml: |
    apiVersion: llm-d.ai/v1alpha1
    kind: EndpointPickerConfig
    plugins:
    - type: approx-prefix-cache-producer
      parameters:
        autoTune: true
        lruCapacityPerServer: 1000
    - type: disagg-headers-handler
    - type: prefix-based-pd-decider
      parameters:
        nonCachedTokens: 4
    - type: disagg-profile-handler
      parameters:
        deciders:
          prefill: prefix-based-pd-decider
    - name: prefill-filter
      type: by-label-selector
      parameters:
        matchLabels:
          kaito.sh/inference-role: prefill
    - name: decode-filter
      type: by-label-selector
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

**Key config notes:**
- `nonCachedTokens: 4` — must be > 0, otherwise `prefix-based-pd-decider` is disabled and all requests skip prefill
- `approx-prefix-cache-producer` — EPP-internal plugin that estimates prefix cache hits via prompt hashing (no vLLM metrics export needed)
- `by-label-selector` filters use KAITO labels (`kaito.sh/inference-role: prefill|decode`)

## Verification

### From inside the cluster:
```bash
kubectl run -it --rm --restart=Never --image=curlimages/curl test-post -- \
  curl -s --max-time 15 \
  http://inference-gateway-istio.default.svc.cluster.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"phi-4-mini-instruct","messages":[{"role":"user","content":"Say hello"}],"max_tokens":5}'
```

### Expected response:
```json
{"id":"chatcmpl-...","object":"chat.completion","model":"phi-4-mini-instruct","choices":[{"message":{"role":"assistant","content":"\"Hello!\""}}]}
```

## Debugging Notes

### How ext_proc routing works with Istio Gateway

1. Istio generates a top-level `ext_proc` filter with `request_header_mode: SKIP` pointing to a `"dummy"` cluster
2. Per-route `typed_per_filter_config` overrides this with the real EPP cluster and `FULL_DUPLEX_STREAMED` body mode
3. EPP uses `x-gateway-destination-endpoint` metadata (in `envoy.lb` namespace) to select backend pods via `override_host` LB policy
4. Route name format: `default.<httproute-name>.0` (e.g., `default.llm-route.0`)

### Health probes returning 404/500

Azure LB sends `GET /` health probes. vLLM returns 404 for `/` path. EPP routes these via `GetRandomEndpoint()` (no body = random backend). This may cause LB to mark backends unhealthy → external IP unreachable.

**Fix options:**
- Configure LB health probe to use `/v1/models` path
- Or use `externalTrafficPolicy: Local` with node-level health check

### Common errors and their meaning

| Error | Meaning |
|-------|---------|
| `gRPC error on stream: 14, message Cluster not available` | ext_proc per-route override missing or EnvoyFilter wiped `grpc_service` |
| `gRPC error on stream: 14, message no healthy upstream` | EPP pod unhealthy or DestinationRule not applied |
| `connection termination{upstream_reset_before_response_started}` | mTLS → plain gRPC mismatch (need DestinationRule DISABLE) |
| `The message had no body` | Normal for GET requests; ext_proc skips body processing |
| 22 bytes response body = `{"detail":"Not Found"}` | vLLM 404 for invalid path (GET `/` from health probes) |
