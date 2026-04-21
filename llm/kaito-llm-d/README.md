# KAITO + llm-d Inference Scheduler Migration Guide

## Overview

This guide covers migrating KAITO's default Endpoint Picker (EPP) from the upstream [Gateway API Inference Extension (GWIE)](https://github.com/kubernetes-sigs/gateway-api-inference-extension) EPP to the [llm-d inference scheduler](https://github.com/llm-d/llm-d-inference-scheduler).

### Why llm-d?

The llm-d inference scheduler consolidates the GWIE EPP implementation with advanced scheduling plugins. Per the [GIE to llm-d migration plan](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430), the EPP implementation and plugins are being moved to `llm-d-inference-scheduler` to accelerate development and avoid confusion on where to develop new plugins.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   KAITO Controller                   │
│  (InferenceSet controller creates Flux resources)    │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐    ┌────────────────────────┐
│  OCIRepository    │    │     HelmRelease         │
│  (GWIE chart)     │    │  (EPP image override    │
│  oci://registry.  │    │   to llm-d)             │
│  k8s.io/gateway-  │    │                         │
│  api-inference-   │    │  image:                  │
│  extension/charts │    │    hub: ghcr.io/llm-d    │
│  /inferencepool   │    │    name: llm-d-inference │
│                   │    │          -scheduler      │
│  Tag: v1.3.1      │    │    tag: v0.7.1           │
└──────────────────┘    └────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           ┌──────────────┐   ┌──────────────────┐
           │ InferencePool│   │ EPP Deployment    │
           │ CRD (GWIE)   │   │ (llm-d image)    │
           └──────────────┘   └──────────────────┘
```

**Key point**: The InferencePool Helm chart stays from GWIE. Only the EPP container image is overridden to use llm-d.

## Code Changes

The migration involves changes in 4 files in the [kaito](https://github.com/kaito-project/kaito) repo:

### 1. `pkg/utils/consts/consts.go`

Replace the old EPP image constant with hub/name/tag to match the InferencePool chart's image composition (`{hub}/{name}:{tag}`):

```go
// Before:
GatewayAPIInferenceExtensionImageRepository = "mcr.microsoft.com/oss/v2/gateway-api-inference-extension"

// After:
EPPImageHub  = "ghcr.io/llm-d"
EPPImageName = "llm-d-inference-scheduler"
EPPImageTag  = "v0.7.1"
```

### 2. `pkg/workspace/manifests/manifests.go`

Update `GenerateInferencePoolHelmRelease` to pass all three image fields:

```go
"inferenceExtension": map[string]any{
    "image": map[string]string{
        "hub":        consts.EPPImageHub,
        "name":       consts.EPPImageName,
        "tag":        consts.EPPImageTag,
        "pullPolicy": string(corev1.PullIfNotPresent),
    },
},
```

### 3. `pkg/workspace/manifests/manifests_test.go`

Update test expectations to match new consts.

### 4. `website/docs/gateway-api-inference-extension.md`

Update documentation to reflect llm-d EPP usage.

## Default Behavior (Zero Config)

After deploying the updated KAITO controller, **no additional configuration is needed** for basic usage. The InferencePool chart creates a `default-plugins.yaml` ConfigMap, e.g.

```yaml
# kubectl get configmap phi-4-mini-inferencepool-epp -o yaml
apiVersion: v1
data:
  default-plugins.yaml: |
    apiVersion: inference.networking.x-k8s.io/v1alpha1
    kind: EndpointPickerConfig
    plugins:
    - type: queue-scorer
    - type: kv-cache-utilization-scorer
    - type: prefix-cache-scorer
    schedulingProfiles:
    - name: default
      plugins:
      - pluginRef: queue-scorer
        weight: 2
      - pluginRef: kv-cache-utilization-scorer
        weight: 2
      - pluginRef: prefix-cache-scorer
        weight: 3
kind: ConfigMap
metadata:
  annotations:
    meta.helm.sh/release-name: phi-4-mini-inferencepool
    meta.helm.sh/release-namespace: default
  creationTimestamp: "2026-04-20T02:49:11Z"
  labels:
    app.kubernetes.io/managed-by: Helm
    helm.toolkit.fluxcd.io/name: phi-4-mini-inferencepool
    helm.toolkit.fluxcd.io/namespace: default
  name: phi-4-mini-inferencepool-epp
  namespace: default
  resourceVersion: "140558777"
  uid: 4b5ff03a-5d6b-4262-bed0-c004e8137913
```

The llm-d EPP binary is fully compatible with this config format (same `EndpointPickerConfig` API).

## Advanced: llm-d-Specific Plugins

### Precise Prefix Cache Scorer

More accurate KV cache matching with token-level prefix indexing:

```yaml
inferenceExtension:
  pluginsCustomConfig:
    custom-plugins.yaml: |
      apiVersion: inference.networking.x-k8s.io/v1alpha1
      kind: EndpointPickerConfig
      plugins:
      - type: precise-prefix-cache-scorer
        parameters:
          indexerConfig:
            tokenProcessorConfig:
              blockSize: 5
            kvBlockIndexConfig:
              maxPrefixBlocksToMatch: 256
      - type: decode-filter
      - type: max-score-picker
      - type: single-profile-handler
      schedulingProfiles:
      - name: default
        plugins:
        - pluginRef: decode-filter
        - pluginRef: max-score-picker
        - pluginRef: precise-prefix-cache-scorer
          weight: 50
  pluginsConfigFile: "custom-plugins.yaml"
```

### Prefill/Decode (P/D) Disaggregation

Separate prefill and decode phases to different pods for better GPU utilization:

```yaml
inferenceExtension:
  pluginsCustomConfig:
    custom-plugins.yaml: |
      apiVersion: inference.networking.x-k8s.io/v1alpha1
      kind: EndpointPickerConfig
      featureGates:
      - prepareDataPlugins
      plugins:
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
            inference-role: prefill
      - type: by-label-selector
        name: decode-filter
        parameters:
          matchLabels:
            inference-role: decode
      - type: precise-prefix-cache-scorer
      - type: max-score-picker
      schedulingProfiles:
      - name: prefill
        plugins:
        - pluginRef: prefill-filter
        - pluginRef: precise-prefix-cache-scorer
          weight: 50
      - name: decode
        plugins:
        - pluginRef: decode-filter
        - pluginRef: max-score-picker
  pluginsConfigFile: "custom-plugins.yaml"
```

**Note**: P/D disaggregation requires prefill and decode pods deployed separately with appropriate labels (`inference-role: prefill` / `inference-role: decode`).

### Label-Based Filtering

Route requests only to pods matching specific labels (e.g., GPU type):

```yaml
plugins:
- type: by-label-selector
  parameters:
    matchLabels:
      hardware-type: H100
```

## Feature Matrix

| Feature | Extra Config Needed? | Notes |
|---|---|---|
| Basic inference routing (queue/kv-cache/prefix-cache) | ❌ No | Default plugins work out of the box |
| Precise prefix cache matching | ✅ Yes | Custom `pluginsCustomConfig` |
| P/D disaggregated scheduling | ✅ Yes | Custom config + separate prefill/decode pods |
| Label-based pod filtering | ✅ Yes | Custom `pluginsCustomConfig` |
| BBR multi-model routing | ❌ No | Same as before, install BBR chart separately |

## How to Deploy

### Build and deploy custom KAITO controller

```bash
# Clone the branch with llm-d EPP changes
git clone -b migrate-to-llm-d-epp https://github.com/andyzhangx/kaito.git
cd kaito

# Build custom controller image
docker build -t <your-registry>/kaito-workspace:llm-d-epp .
docker push <your-registry>/kaito-workspace:llm-d-epp

# Install KAITO with custom image
export CLUSTER_NAME=kaito
helm repo add kaito https://kaito-project.github.io/kaito/charts/kaito
helm repo update
helm upgrade --install kaito-workspace kaito/workspace \
  --namespace kaito-workspace \
  --create-namespace \
  --set clusterName="$CLUSTER_NAME" \
  --set image.repository=<your-registry>/kaito-workspace \
  --set image.tag=llm-d-epp \
  --set featureGates.gatewayAPIInferenceExtension=true \
  --set featureGates.enableInferenceSetController=true \
  --wait --take-ownership
```

### Follow the standard GWIE quickstart

After deploying the custom controller, follow the standard quickstart:

1. **Install Istio and deploy Gateway** (same as before)
2. **Create InferenceSet** (same as before)
3. **Deploy DestinationRule and HTTPRoute** (same as before)
4. **Test inference** (same as before)

See the full quickstart: [gateway-api-inference-extension.md](https://github.com/andyzhangx/kaito/blob/migrate-to-llm-d-epp/website/docs/gateway-api-inference-extension.md)

### Verify EPP image

```bash
# Confirm the EPP pod is using llm-d image
kubectl get pod -l inferencepool=phi-4-mini-inferencepool-epp \
  -o jsonpath='{.items[*].spec.containers[*].image}'
# Expected: ghcr.io/llm-d/llm-d-inference-scheduler:v0.7.1
```

## BBR, HTTPRoute, DestinationRule, and EPP: How They Work Together

### Component Roles

| Component | Type | Role | Created By |
|---|---|---|---|
| **BBR** | Envoy ext-proc filter | Extract model name from request body → inject `X-Gateway-Model-Name` header | User (standalone Helm chart) |
| **HTTPRoute** | Gateway API CRD | **Routing rules**: match path/header → route to correct InferencePool | User (kubectl apply) |
| **DestinationRule** | Istio CRD | **TLS policy**: Gateway → EPP connection config (skip self-signed cert verification) | User (kubectl apply) |
| **EPP** | Envoy ext-proc filter | **Endpoint selection**: pick optimal pod within a pool | KAITO controller (via Flux) |

### Single Model Request Flow

```
                          Client Request
                    POST /v1/chat/completions
                    {"model": "phi-4-mini-instruct", ...}
                              │
                              ▼
                    ┌───────────────────┐
                    │      Gateway      │
                    │  (Envoy / Istio)  │
                    └────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │     HTTPRoute      │   ◄── Routing: path "/" → InferencePool
                   │                    │
                   │  rules:            │       apiVersion: gateway.networking.k8s.io/v1
                   │  - match: /        │       kind: HTTPRoute
                   │    backend:        │       spec:
                   │    phi-4-mini-pool │         rules:
                   └─────────┬──────────┘         - matches: [{path: /}]
                             │                      backendRefs: [phi-4-mini-inferencepool]
                             ▼
                   ┌────────────────────┐
                   │  DestinationRule   │   ◄── TLS Policy: Gateway → EPP
                   │                    │
                   │  host: phi-4-mini- │       apiVersion: networking.istio.io/v1
                   │  inferencepool-epp │       kind: DestinationRule
                   │  tls:              │       spec:
                   │    insecureSkip    │         host: phi-4-mini-inferencepool-epp
                   │    Verify: true    │         trafficPolicy:
                   └─────────┬──────────┘           tls: {mode: SIMPLE, insecureSkipVerify: true}
                             │
                   ┌─────────▼──────────┐
                   │   EPP (ext-proc)   │   ◄── Endpoint Selection: pick best pod
                   │                    │
                   │  llm-d inference   │       Scores pods by:
                   │  scheduler         │       - queue depth
                   │                    │       - KV cache utilization
                   │  ghcr.io/llm-d/    │       - prefix cache hit rate
                   │  llm-d-inference-  │
                   │  scheduler:v0.7.1  │
                   └──┬──┬──┬───────────┘
                      │  │  │
                      ▼  ▼  ▼
                   ┌────┐┌────┐┌────┐
                   │Pod ││Pod ││Pod │
                   │ 0  ││ 1  ││ 2  │
                   └────┘└────┘└────┘
                    phi-4-mini pods
```

### Multi-Model Request Flow (with BBR)

```
                          Client Request
                    POST /v1/chat/completions
                    {"model": "mistral-7b-instruct", ...}
                              │
                              ▼
                    ┌───────────────────┐
                    │      Gateway      │
                    │  (Envoy / Istio)  │
                    └────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │   BBR (ext-proc)   │   ◄── Step 1: Extract model name
                   │                    │       from JSON body, inject header:
                   │ body → header      │       X-Gateway-Model-Name: mistral-7b-instruct
                   │                    │
                   │ (one per cluster)  │
                   └─────────┬──────────┘
                             │  + header: X-Gateway-Model-Name: mistral-7b-instruct
                             ▼
                   ┌────────────────────┐
                   │     HTTPRoute      │   ◄── Step 2: Match header → route
                   │                    │
                   │ rules:             │       rules:
                   │ - header:          │       - match: X-Gateway-Model-Name=phi-4-mini-instruct
                   │   phi-4-mini →     │         → phi-4-mini-inferencepool
                   │   phi-4-pool       │       - match: X-Gateway-Model-Name=mistral-7b-instruct
                   │ - header:          │         → mistral-7b-inferencepool
                   │   mistral-7b →     │
                   │   mistral-pool     │
                   └──────┬─────────┬───┘
                          │         │
            ┌─────────────┘         └──────────────┐
            ▼                                      ▼
  ┌────────────────────┐              ┌────────────────────┐
  │  DestinationRule   │              │  DestinationRule   │  ◄── Step 3: TLS policy
  │  phi-4-mini-epp    │              │  mistral-7b-epp    │      per EPP service
  │  (skip TLS verify) │              │  (skip TLS verify) │
  └─────────┬──────────┘              └─────────┬──────────┘
            ▼                                   ▼
  ┌────────────────────┐              ┌────────────────────┐
  │  EPP (ext-proc)    │              │  EPP (ext-proc)    │  ◄── Step 4: Pick best pod
  │  llm-d scheduler   │              │  llm-d scheduler   │
  └──┬──┬──┬───────────┘              └──┬──┬──┬───────────┘
     │  │  │                             │  │  │
     ▼  ▼  ▼                             ▼  ▼  ▼
  ┌────┐┌────┐┌────┐                 ┌────┐┌────┐┌────┐
  │Pod ││Pod ││Pod │                 │Pod ││Pod ││Pod │
  │ 0  ││ 1  ││ 2  │                 │ 0  ││ 1  ││ 2  │
  └────┘└────┘└────┘                 └────┘└────┘└────┘
   phi-4-mini pods                    mistral-7b pods
```

### Why DestinationRule Is Needed

EPP runs with `--secure-serving=true` by default, generating a self-signed TLS certificate. Istio's sidecar proxy doesn't trust self-signed certs, so without the DestinationRule, the Gateway → EPP ext-proc connection **fails with TLS errors**.

The DestinationRule is a **workaround** that tells Istio to skip certificate verification:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: phi-4-mini-inferencepool-epp    # Must match EPP service name
spec:
  host: phi-4-mini-inferencepool-epp    # EPP service DNS name
  trafficPolicy:
    tls:
      mode: SIMPLE
      insecureSkipVerify: true          # Skip self-signed cert verification
```

**You need one DestinationRule per InferencePool/EPP service.**

### Summary: What Each Resource Does

```
HTTPRoute       = WHERE to send the request     (which InferencePool)
DestinationRule = HOW to connect to EPP          (TLS policy)
BBR             = WHAT model is being requested  (body → header extraction)
EPP             = WHICH pod serves the request   (optimal endpoint selection)
```

## BBR (Body-Based Routing) — No Changes Needed

BBR is **completely unaffected** by the EPP migration. It is an independent component with its own Helm chart, not managed by the KAITO controller.

### Why BBR doesn't change

1. **Separate chart**: BBR installs from `registry.k8s.io/gateway-api-inference-extension/charts/body-based-routing`, not through KAITO controller
2. **Independent function**: BBR only does body → header conversion (extracts model name from request body, injects `X-Gateway-Model-Name` header) — it doesn't interact with the EPP implementation
3. **Our change scope**: We only replaced the EPP image; the InferencePool chart and BBR chart are untouched

### Deploy BBR (same as before)

```bash
# Install BBR chart directly from GWIE
helm upgrade --install body-based-router \
  oci://registry.k8s.io/gateway-api-inference-extension/charts/body-based-routing \
  --version v1.3.0 \
  --set provider.name=istio \
  --wait
```

### Multi-model routing with BBR

1. Deploy a second InferenceSet (e.g., `mistral-7b-instruct`)
2. Deploy its DestinationRule
3. Install BBR chart (command above)
4. Apply the BBR-enabled HTTPRoute (`httproute-bbr.yaml`)

Everything works exactly as before — BBR routes by model name header, each InferencePool's llm-d EPP handles endpoint selection independently.

### Future Note

Per the [GIE to llm-d migration plan](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430) (Workstream 2), BBR will eventually move to a new repo `llm-d/llm-d-body-based-routing` with its own release infrastructure. At that point the chart URL and image will change, but for now v1.3.0 remains in the GWIE repo.

## References

- [llm-d inference scheduler](https://github.com/llm-d/llm-d-inference-scheduler)
- [GIE to llm-d migration issue](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430)
- [KAITO GWIE documentation](https://kaito-project.github.io/kaito/docs/gateway-api-inference-extension)
- [llm-d architecture docs](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/architecture.md)
- [KAITO branch with changes](https://github.com/andyzhangx/kaito/tree/migrate-to-llm-d-epp)
