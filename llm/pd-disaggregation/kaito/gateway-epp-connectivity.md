# Gateway → EPP Connectivity: Analysis & Fix

## Problem

When using Istio Gateway + InferencePool + EPP (ext_proc), requests from clients through the Gateway time out with:
```
upstream connect error or disconnect/reset before headers. reset reason: connection termination
```

## Root Cause Chain

### 1. Istio mTLS vs Plain gRPC Mismatch

The Istio Gateway envoy automatically uses **mTLS** (mutual TLS) for outbound connections to services within the mesh. The EPP container listens on **plain gRPC** (port 9002). When the EPP pod has an Istio sidecar:

- Gateway envoy → mTLS → EPP sidecar → plain → EPP container ✅ (should work)
- But: EPP sidecar iptables may not intercept inbound traffic correctly

When the EPP pod does NOT have a sidecar:
- Gateway envoy → mTLS → EPP container (plain gRPC) → `WRONG_VERSION_NUMBER` ❌

### 2. The `dummy` Cluster (Not a Bug)

In the Gateway envoy config dump, you'll see:
```json
{
  "name": "envoy.filters.http.ext_proc",
  "typed_config": {
    "grpc_service": {
      "envoy_grpc": { "cluster_name": "dummy" }
    },
    "failure_mode_allow": true
  }
}
```

**This is normal Istio design.** The `dummy` cluster is a top-level placeholder. The actual EPP cluster is set via per-route `typed_per_filter_config` override:
```json
{
  "grpc_service": {
    "envoy_grpc": {
      "cluster_name": "outbound|9002||phi-4-mini-inferencepool-epp.default.svc.cluster.local"
    }
  },
  "failure_mode_allow": false
}
```

### 3. `--secure-serving` Flag Parsing

If you pass `--secure-serving false` (space-separated), Go's flag parser treats it as `--secure-serving` (=true) + positional arg `false`. Always use:
```
--secure-serving=false
```

## Solution: DestinationRule DISABLE + No Sidecar

Remove Istio sidecar from the EPP pod and configure a DestinationRule to tell the Gateway envoy to use plaintext:

### Step 1: Disable sidecar injection for EPP

Add annotation to EPP deployment pod template:
```yaml
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"
```

### Step 2: Create DestinationRule

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

### Step 3: Verify

```bash
# Check EPP pod has no sidecar (2/2 or 1/1 containers, not 3/3)
kubectl get pods -l inferencepool=phi-4-mini-inferencepool-epp

# From Gateway pod, verify plaintext connection works
kubectl exec -it $(kubectl get pods -l gateway.networking.k8s.io/gateway-name=inference-gateway -o name) \
  -c istio-proxy -- curl -v http://phi-4-mini-inferencepool-epp.default.svc.cluster.local:9002
# Should return: grpc-status: 12 (UNIMPLEMENTED) — this means gRPC is reachable

# Check envoy cluster stats
kubectl exec -it $(kubectl get pods -l gateway.networking.k8s.io/gateway-name=inference-gateway -o name) \
  -c istio-proxy -- pilot-agent request GET "stats?filter=phi-4-mini-inferencepool-epp.*cx_total"
# Should show cx_total incrementing
```

## EPP Configuration

Working EPP args:
```
--pool-name phi-4-mini-inferencepool
--pool-namespace default
--pool-group inference.networking.k8s.io
--config-file /config/config.yaml
--secure-serving=false
--v 4
--tracing=false
```

## Debugging Tips

### Check if ext_proc is actually being invoked
```bash
# From Gateway pod
kubectl exec -it $GATEWAY_POD -c istio-proxy -- \
  pilot-agent request GET "stats?filter=ext_proc"
```

### Check EPP cluster health
```bash
kubectl exec -it $GATEWAY_POD -c istio-proxy -- \
  pilot-agent request GET "stats?filter=phi-4-mini-inferencepool-epp.*rq"
# rq_error > 0 with cx_connect_fail = 0 → TLS mismatch (connected but handshake failed)
# cx_connect_fail > 0 → network unreachable
```

### EPP logs
```bash
kubectl logs -l inferencepool=phi-4-mini-inferencepool-epp -c epp --tail=50
# Look for: "HandleRequestHeaders", "HandleResponseBody"
# If no log entries → ext_proc not reaching EPP
```

---

## P/D Routing: Why EPP Doesn't Do Two-Phase Routing

After fixing connectivity, you might see EPP receive requests but the response still times out or returns a tiny response (e.g., 22 bytes).

### How disagg-profile-handler Actually Works

The routing order in `disagg-profile-handler` is:

1. **Stage 1: Decode** — Always runs first. Selects a decode endpoint based on prefix cache state.
2. **Stage 2: Encode** (optional) — For multimodal content.
3. **Stage 3: Prefill** (optional) — Only if `prefix-based-pd-decider` returns `true`.

**The decode pod is always the primary target** (`PrimaryProfileName: "decode"`). The prefill endpoint is passed via **request headers** to the decode pod's routing sidecar, which handles the actual prefill→decode coordination.

### Why `prefix-based-pd-decider` May Return `false`

The decider checks:
1. `NonCachedTokens` config — if set to `0` (default), disaggregation is **disabled**
2. Endpoint's `PrefixCacheMatchInfo` — requires vLLM to expose prefix cache metrics

If you see `"Prefix-based PD disabled (NonCachedTokens=0)"` in EPP logs, set `nonCachedTokens` > 0 in the config:

```yaml
plugins:
  - type: prefix-based-pd-decider
    name: pd-decider
    parameters:
      nonCachedTokens: 128  # minimum non-cached tokens to trigger disaggregation
```

### What's Actually Needed for P/D

For the `prefix-based-pd-decider` to actually disaggregate:
1. vLLM must have `--enable-prefix-caching` enabled
2. vLLM must expose prefix cache metrics compatible with llm-d's data collector
3. EPP must successfully collect `PrefixCacheMatchInfo` from endpoints
4. `nonCachedTokens` must be > 0 in the decider config

**However**: In practice with KAITO's architecture, the simpler path is to use `disagg-headers-handler` (which always sets the prefill header) rather than relying on `prefix-based-pd-decider` (which requires prefix cache telemetry).

### Alternative: Always-Disaggregate with `disagg-headers-handler`

The `disagg-headers-handler` plugin simply reads headers like `x-prefiller-url` and routes accordingly, without needing prefix cache metrics. This is the approach documented in [pd-working-config.md](./pd-working-config.md).
