# MultiRoleInference + llm-d EPP: Prefill/Decode Disaggregation

## Overview

This document describes the end-to-end architecture for prefill/decode (P/D) disaggregated inference in KAITO using `MultiRoleInference` CRD with llm-d EPP as the routing layer. This replaces the vllm-router approach with the Kubernetes-native Gateway API + llm-d inference scheduler stack.

## Request Flow

```
Client
  │  POST /v1/chat/completions
  │  {"model": "deepseek-v32", "messages": [...]}
  ▼
Gateway (Envoy + Istio)
  │
  ▼
BBR (ext-proc)                          ◄── Extract model name from body
  │  Inject header: X-Gateway-Model-Name: deepseek-v32
  ▼
HTTPRoute                               ◄── Match header → route to InferencePool
  │  backendRef: deepseek-v32-inferencepool
  ▼
DestinationRule                          ◄── TLS policy: skip self-signed cert
  │
  ▼
llm-d EPP (ext-proc)                    ◄── P/D disaggregation scheduling
  │
  │  1. disagg-profile-handler decides: prefill or decode?
  │  2. by-label-selector filters pods by inference-role
  │  3. scorer ranks candidates
  │  4. picker selects best pod
  │
  ├──► prefill pod (inference-role=prefill)
  │      KV cache produced → NixlConnector → decode pod
  │
  └──► decode pod (inference-role=decode)
         KV cache consumed → generate tokens → response
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     MultiRoleInference CR                        │
│  name: deepseek-v32                                              │
│  roles: [prefill x2, decode x3]                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ controller reconcile
                           │
       ┌───────────────────┼───────────────────────────┐
       │                   │                           │
       ▼                   ▼                           ▼
┌──────────────┐   ┌──────────────┐   ┌────────────────────────────┐
│ InferenceSet │   │ InferenceSet │   │ InferencePool              │
│              │   │              │   │ deepseek-v32               │
│ prefill-0    │   │ decode-0     │   │                            │
│ prefill-1    │   │ decode-1     │   │ selector:                  │
│              │   │ decode-2     │   │   apps: deepseek-v32       │
│ pod labels:  │   │ pod labels:  │   │                            │
│  apps:       │   │  apps:       │   │ ┌────────────────────────┐ │
│   deepseek-  │   │   deepseek-  │   │ │ llm-d EPP              │ │
│   v32        │   │   v32        │   │ │ disagg-profile-handler │ │
│  inference-  │   │  inference-  │   │ │ prefill-filter         │ │
│   role:      │   │   role:      │   │ │ decode-filter          │ │
│   prefill    │   │   decode     │   │ └────────────────────────┘ │
└──────────────┘   └──────────────┘   └────────────────────────────┘
                                                ▲
                                                │ ext-proc
                                      ┌─────────┴──────────┐
                                      │  Gateway (Envoy)    │
                                      │  + BBR              │
                                      │  + HTTPRoute        │
                                      │  + DestinationRule  │
                                      └────────────────────┘
```

## MultiRoleInference CRD

### User-Facing CR

```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v32
  namespace: default
spec:
  labelSelector:
    matchLabels:
      apps: deepseek-v32
  inference:
    preset:
      name: deepseek-ai/DeepSeek-V3.2
      presetOptions:
        modelAccessSecret: hf-token
  # Optional: custom EPP plugins. If not set, controller auto-generates P/D config.
  eppPluginsConfigRef:
    name: deepseek-v32-epp-plugins
  roles:
    - name: prefill
      replicas: 2
      instanceType: Standard_NC24ads_A100_v4
      config: prefill-params        # optional ConfigMap for role-specific vLLM args
    - name: decode
      replicas: 3
      instanceType: Standard_NC24ads_A100_v4
      config: decode-params         # optional ConfigMap for role-specific vLLM args
```

### API Types

```go
type MultiRoleInferenceRoleName string

const (
    MultiRoleInferenceRolePrefill MultiRoleInferenceRoleName = "prefill"
    MultiRoleInferenceRoleDecode  MultiRoleInferenceRoleName = "decode"
)

type MultiRoleInferencePresetSpec struct {
    Name          string            `json:"name,omitempty"`
    PresetOptions map[string]string `json:"presetOptions,omitempty"`
}

type MultiRoleInferenceSharedInferenceSpec struct {
    Preset *MultiRoleInferencePresetSpec `json:"preset,omitempty"`
}

type MultiRoleInferenceRoleSpec struct {
    // Name is the role name. Supported values: prefill, decode.
    // +kubebuilder:validation:Enum=prefill;decode
    Name MultiRoleInferenceRoleName `json:"name"`

    // Replicas is the number of InferenceSet resources to create for this role.
    // +kubebuilder:validation:Minimum=1
    // +optional
    Replicas *int32 `json:"replicas,omitempty"`

    // InstanceType specifies the GPU node SKU.
    // +optional
    InstanceType string `json:"instanceType,omitempty"`

    // Config references a ConfigMap with role-specific inference arguments.
    // +optional
    Config string `json:"config,omitempty"`
}

type MultiRoleInferenceSpec struct {
    // LabelSelector is propagated to generated child workloads.
    // +optional
    LabelSelector *metav1.LabelSelector `json:"labelSelector,omitempty"`

    // Inference defines the shared inference configuration across roles.
    // +optional
    Inference *MultiRoleInferenceSharedInferenceSpec `json:"inference,omitempty"`

    // EPPPluginsConfigRef references a ConfigMap containing custom EPP plugins configuration.
    // If not set, the controller auto-generates a P/D disaggregation plugin config.
    // +optional
    EPPPluginsConfigRef *corev1.LocalObjectReference `json:"eppPluginsConfigRef,omitempty"`

    // Roles defines the role topology of this inference service.
    // +optional
    Roles []MultiRoleInferenceRoleSpec `json:"roles,omitempty"`
}

type MultiRoleInferenceStatus struct {
    Conditions         []metav1.Condition `json:"conditions,omitempty"`
    ObservedGeneration int64              `json:"observedGeneration,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Ready",type="string",JSONPath=".status.conditions[?(@.type=='Ready')].status"
// +kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"
type MultiRoleInference struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              MultiRoleInferenceSpec   `json:"spec,omitempty"`
    Status            MultiRoleInferenceStatus `json:"status,omitempty"`
}
```

## Controller-Generated Resources

The MultiRoleInference controller reconciles one CR into the following 6 types of resources:

### 1. Prefill InferenceSet(s)

For each prefill replica, the controller creates one InferenceSet:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: InferenceSet
metadata:
  name: deepseek-v32-prefill-0
  namespace: default
  labels:
    kaito.sh/parent: deepseek-v32
    kaito.sh/role: prefill
  ownerReferences:
    - apiVersion: kaito.sh/v1alpha1
      kind: MultiRoleInference
      name: deepseek-v32
      controller: true
      blockOwnerDeletion: true
spec:
  replicas: 1
  labelSelector:
    matchLabels:
      apps: deepseek-v32
  template:
    metadata:
      labels:
        apps: deepseek-v32
        inference-role: prefill
        kaito.sh/parent: deepseek-v32
    resource:
      instanceType: Standard_NC24ads_A100_v4
    inference:
      preset:
        name: deepseek-ai/DeepSeek-V3.2
        presetOptions:
          modelAccessSecret: hf-token
      config: deepseek-v32-prefill-vllm-config
```

### 2. Decode InferenceSet(s) with Sidecar Container

Same structure as prefill, with `inference-role: decode` label and decode vLLM config. **Critically, decode pods require a sidecar container** for P/D coordination.

#### Why Decode Pods Need a Sidecar

In the llm-d P/D architecture ([disaggregation docs](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/disaggregation.md)), all requests are routed to the **decode worker first**. The decode worker's sidecar is responsible for:

1. Receiving EPP metadata (selected decode pod + optional prefill pod via `x-prefiller-host-port` header)
2. If prefill is disaggregated → forwarding the prefill request to the selected prefill worker and waiting for KV cache parameters
3. Sending the decode request to the local vLLM engine with `remote_prefill=true` and the KV cache block IDs
4. Returning the final response through the inference gateway

> **Note**: No sidecar or coordination logic is needed on prefill pods. Prefill pods are stateless workers that process prompts and produce KV cache.

#### P/D Request Sequence

```
1. Client → Inference Gateway (Envoy + EPP)
2. EPP runs disagg-profile-handler:
   a. Decode stage: select a decode pod (always runs first)
   b. Prefill stage: PD decider evaluates prompt length + prefix cache hit
      - High cache hit or short prompt → skip prefill, decode handles everything
      - Low cache hit + long prompt → select a prefill pod
3. Request lands on Decode Worker Sidecar
   a. If x-prefiller-host-port header exists:
      - Sidecar → Prefill Worker: send prompt (max_tokens=1)
      - Prefill Worker: run prefill, produce KV cache
      - Prefill Worker → Sidecar: return KV cache parameters (prefill ID + memory block IDs)
      - Sidecar → local vLLM: decode with remote_prefill=true
      - local vLLM → Prefill Worker: read KV cache via NixlConnector
      - local vLLM: run decode, generate tokens
   b. If no prefill header → run both prefill + decode locally
4. Decode Worker → Sidecar → Gateway → Client
```

#### Generated Decode InferenceSet

```yaml
apiVersion: kaito.sh/v1alpha1
kind: InferenceSet
metadata:
  name: deepseek-v32-decode-0
  namespace: default
  labels:
    kaito.sh/parent: deepseek-v32
    kaito.sh/role: decode
  ownerReferences:
    - apiVersion: kaito.sh/v1alpha1
      kind: MultiRoleInference
      name: deepseek-v32
      controller: true
      blockOwnerDeletion: true
spec:
  replicas: 1
  labelSelector:
    matchLabels:
      apps: deepseek-v32
  template:
    metadata:
      labels:
        apps: deepseek-v32
        inference-role: decode
        kaito.sh/parent: deepseek-v32
    resource:
      instanceType: Standard_NC24ads_A100_v4
    inference:
      preset:
        name: deepseek-ai/DeepSeek-V3.2
        presetOptions:
          modelAccessSecret: hf-token
      config: deepseek-v32-decode-vllm-config
```

#### Sidecar Injection

The MultiRoleInference controller must inject a sidecar container into the decode InferenceSet's pod template. The sidecar is the [llm-d routing sidecar](https://github.com/llm-d/llm-d-routing-sidecar), which handles P/D coordination:

```yaml
# Injected into decode pod spec by the controller
containers:
  - name: vllm                          # main inference container (existing)
    # ...
  - name: llm-d-routing-sidecar         # sidecar (injected by controller)
    image: mcr.microsoft.com/oss/v2/llm-d/llm-d-routing-sidecar:v0.7.0
    ports:
      - containerPort: 8080             # sidecar listens for incoming requests
        name: sidecar
    env:
      - name: BACKEND_URL
        value: "http://localhost:5000"  # local vLLM engine
      - name: POD_IP
        valueFrom:
          fieldRef:
            fieldPath: status.podIP
```

The sidecar sits in front of the vLLM engine on decode pods:
- Incoming requests hit the sidecar (port 8080)
- Sidecar orchestrates prefill (if needed) and then forwards to local vLLM (port 5000)
- The InferencePool `targetPortNumber` should point to the sidecar port (8080) for decode pods

> **Implementation Note**: The exact sidecar injection mechanism needs to be designed. Options include:
> 1. Controller directly patches the StatefulSet pod template after InferenceSet creates it
> 2. InferenceSet API supports additional containers in the pod template
> 3. Use a mutating webhook to inject the sidecar based on `inference-role: decode` label

### InferencePool and EPP Ownership

In the standard (non-disaggregated) flow, each InferenceSet creates its own InferencePool and EPP via `ensureGatewayAPIInferenceExtension()`. With MultiRoleInference, this changes:

| | Standard InferenceSet | MultiRoleInference |
|---|---|---|
| **Mapping** | 1 InferenceSet → 1 InferencePool → 1 EPP | 1 MRI → N child InferenceSets → **1 shared InferencePool** → 1 EPP |
| **InferencePool created by** | InferenceSet controller | MultiRoleInference controller |
| **EPP sees** | All pods from 1 InferenceSet | All prefill + decode pods (filtered by `by-label-selector` plugin) |

Child InferenceSets must **skip** the GWIE logic to avoid creating redundant InferencePool/EPP resources:

```go
// In InferenceSet controller's ensureGatewayAPIInferenceExtension()
func (c *InferenceSetReconciler) ensureGatewayAPIInferenceExtension(ctx context.Context, iObj *kaitov1alpha1.InferenceSet) error {
    // Skip GWIE for child InferenceSets managed by MultiRoleInference.
    // The parent MultiRoleInference controller owns the shared InferencePool and EPP.
    if iObj.Labels["kaito.sh/parent"] != "" {
        return nil
    }
    // ... existing logic for standalone InferenceSets ...
}
```

### 3. InferencePool

One InferencePool per MultiRoleInference, selecting ALL prefill + decode pods:

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: InferencePool
metadata:
  name: deepseek-v32
  namespace: default
spec:
  targetPortNumber: 5000
  selector:
    matchLabels:
      apps: deepseek-v32
```

The EPP inside this pool sees all pods and uses `by-label-selector` plugin to filter by `inference-role`.

### 4. EPP Plugin ConfigMap (auto-generated if not provided)

When `eppPluginsConfigRef` is not set, the controller generates a default P/D disaggregation config:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deepseek-v32-epp-plugins
  namespace: default
  ownerReferences:
    - kind: MultiRoleInference
      name: deepseek-v32
data:
  config.yaml: |
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
      - type: kv-cache-utilization-scorer
      - type: queue-scorer
      - type: max-score-picker
    schedulingProfiles:
      - name: prefill
        plugins:
          - pluginRef: prefill-filter
          - pluginRef: kv-cache-utilization-scorer
            weight: 2
          - pluginRef: queue-scorer
            weight: 1
      - name: decode
        plugins:
          - pluginRef: decode-filter
          - pluginRef: max-score-picker
```

### 5. OCI Repository + HelmRelease (InferencePool chart with llm-d EPP)

Reuses the existing GWIE InferencePool chart, overriding the EPP image to llm-d:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: deepseek-v32-inferencepool
  namespace: default
  ownerReferences:
    - kind: MultiRoleInference
      name: deepseek-v32
spec:
  url: oci://registry.k8s.io/gateway-api-inference-extension/charts/inferencepool
  ref:
    tag: v1.3.1
  interval: 10m
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: deepseek-v32-inferencepool
  namespace: default
  ownerReferences:
    - kind: MultiRoleInference
      name: deepseek-v32
spec:
  chartRef:
    kind: OCIRepository
    name: deepseek-v32-inferencepool
  interval: 10m
  values:
    inferenceExtension:
      runtime: llm-d
      image:
        hub: mcr.microsoft.com/oss/v2/llm-d
        name: llm-d-inference-scheduler
        tag: v0.7.1
        pullPolicy: IfNotPresent
      # Inject custom P/D plugin config
      pluginsConfigFile: "custom-plugins.yaml"
      pluginsCustomConfig:
        custom-plugins.yaml: |
          # content from deepseek-v32-epp-plugins ConfigMap
          ...
    inferencePool:
      name: deepseek-v32
      targetPortNumber: 5000
      selector:
        apps: deepseek-v32
```

### 6. DestinationRule (TLS bypass for EPP)

> **Note**: The DestinationRule is a temporary workaround. It will be removed once [kaito-project/kaito#1983](https://github.com/kaito-project/kaito/pull/1983) lands, which disables EPP secure serving (`--secure-serving=false`) so that the Gateway → EPP connection no longer requires TLS bypass.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: deepseek-v32-inferencepool-epp
  namespace: default
  ownerReferences:
    - kind: MultiRoleInference
      name: deepseek-v32
spec:
  host: deepseek-v32-inferencepool-epp
  trafficPolicy:
    tls:
      mode: SIMPLE
      insecureSkipVerify: true
```

## EPP Plugin Chain: How P/D Routing Works

### Plugin Execution Flow

```
Incoming Request
      │
      ▼
┌─────────────────────────┐
│ disagg-profile-handler  │  Step 1: Decide prefill or decode
│                         │
│  Uses prefix-based-     │  - New prompt with uncached tokens → "prefill" profile
│  pd-decider to check    │  - KV cache already available      → "decode" profile
│  if KV cache exists     │
└──────────┬──────────────┘
           │
           │  profile = "prefill" or "decode"
           ▼
┌─────────────────────────┐
│ by-label-selector       │  Step 2: Filter pods by role
│                         │
│  prefill profile →      │  - Only pods with inference-role=prefill
│    prefill-filter       │
│  decode profile →       │  - Only pods with inference-role=decode
│    decode-filter        │
└──────────┬──────────────┘
           │
           │  filtered pod list
           ▼
┌─────────────────────────┐
│ scorer plugins          │  Step 3: Rank candidate pods
│                         │
│  prefill profile:       │  - kv-cache-utilization-scorer (weight: 2)
│    kv-cache + queue     │  - queue-scorer (weight: 1)
│                         │
│  decode profile:        │  - max-score-picker (pick best)
│    max-score-picker     │
└──────────┬──────────────┘
           │
           │  selected pod
           ▼
     Envoy forwards request to selected pod
```

### KV Cache Transfer Between Prefill and Decode

The current P/D disaggregation design uses [NixlConnector](https://github.com/ai-dynamo/nixl) as the default KV cache transfer mechanism. NixlConnector enables high-performance KV cache transfer between prefill and decode pods via RDMA (when available) or TCP fallback. The controller automatically injects the required vLLM environment variables (`VLLM_KV_CONNECTOR=NixlConnector`, `VLLM_KV_ROLE=kv_producer/kv_consumer`) into the prefill and decode pods respectively.

```
Prefill Pod                              Decode Pod
┌──────────────────────┐                ┌──────────────────────┐
│ vLLM                 │                │ vLLM                 │
│                      │                │                      │
│ Role: kv_producer    │  NixlConnector │ Role: kv_consumer    │
│                      │ ──────────────>│                      │
│ 1. Process prompt    │  KV cache      │ 4. Receive KV cache  │
│ 2. Build KV cache    │  transfer      │ 5. Generate tokens   │
│ 3. Send KV to decode │  (RDMA/TCP)    │ 6. Return response   │
└──────────────────────┘                └──────────────────────┘
```

## KEDA Autoscaling Integration

Each child InferenceSet is a standard InferenceSet with `/scale` subresource, so keda-kaito-scaler works with **zero modifications**.

### Option A: Annotation-Based Auto-Provision (Per InferenceSet)

The MultiRoleInference controller propagates KEDA annotations to child InferenceSets:

```yaml
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v32
  annotations:
    # Prefill scaling config
    scaledobject.kaito.sh/prefill-auto-provision: "true"
    scaledobject.kaito.sh/prefill-metricName: "vllm:num_requests_waiting"
    scaledobject.kaito.sh/prefill-threshold: "10"
    scaledobject.kaito.sh/prefill-min-replicas: "1"
    scaledobject.kaito.sh/prefill-max-replicas: "4"
    # Decode scaling config
    scaledobject.kaito.sh/decode-auto-provision: "true"
    scaledobject.kaito.sh/decode-metricName: "vllm:gpu_cache_usage_perc"
    scaledobject.kaito.sh/decode-threshold: "80"
    scaledobject.kaito.sh/decode-min-replicas: "2"
    scaledobject.kaito.sh/decode-max-replicas: "6"
spec:
  roles:
    - name: prefill
      replicas: 2
      instanceType: Standard_NC24ads_A100_v4
    - name: decode
      replicas: 3
      instanceType: Standard_NC24ads_A100_v4
```

Controller translates to per-InferenceSet annotations:

```yaml
# Generated: deepseek-v32-prefill-0
apiVersion: kaito.sh/v1alpha1
kind: InferenceSet
metadata:
  name: deepseek-v32-prefill-0
  annotations:
    scaledobject.kaito.sh/auto-provision: "true"
    scaledobject.kaito.sh/metricName: "vllm:num_requests_waiting"
    scaledobject.kaito.sh/threshold: "10"
    scaledobject.kaito.sh/max-replicas: "4"
# ...

# Generated: deepseek-v32-decode-0
apiVersion: kaito.sh/v1alpha1
kind: InferenceSet
metadata:
  name: deepseek-v32-decode-0
  annotations:
    scaledobject.kaito.sh/auto-provision: "true"
    scaledobject.kaito.sh/metricName: "vllm:gpu_cache_usage_perc"
    scaledobject.kaito.sh/threshold: "80"
    scaledobject.kaito.sh/max-replicas: "6"
# ...
```

keda-kaito-scaler sees standard InferenceSet annotations → creates ScaledObject → KEDA scales `spec.replicas` (workspace count) via `/scale` subresource.

### Option B: Scale MultiRoleInference Roles (Future)

Scale the number of InferenceSet instances per role (e.g., add a 3rd prefill InferenceSet). This requires keda-kaito-scaler to understand MultiRoleInference and patch `roles[].replicas`.

### Scaling Dimensions

```
                    ┌──────────────────────────────────┐
                    │     MultiRoleInference            │
                    │                                    │
                    │  prefill.replicas: 2  ◄─── Dimension 1: Number of InferenceSets
                    │  decode.replicas: 3       (future: KEDA patches MRI CR)
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ InferenceSet │  │ InferenceSet │  │ InferenceSet │
     │ prefill-0    │  │ decode-0     │  │ decode-1     │ ...
     │              │  │              │  │              │
     │ replicas: 1  │  │ replicas: 1  │  │ replicas: 1  │
     │      ▲       │  │      ▲       │  │      ▲       │
     │      │       │  │      │       │  │      │       │
     │ Dimension 2  │  │ Dimension 2  │  │ Dimension 2  │
     │ Workspace    │  │ Workspace    │  │ Workspace    │
     │ count per IS │  │ count per IS │  │ count per IS │
     │ (KEDA today) │  │ (KEDA today) │  │ (KEDA today) │
     └──────────────┘  └──────────────┘  └──────────────┘
```

## User Experience

### Deploy

```bash
# 1. Prerequisites: Istio, Gateway, BBR (same as standard KAITO GWIE setup)

# 2. Create MultiRoleInference
kubectl apply -f - <<EOF
apiVersion: kaito.sh/v1alpha1
kind: MultiRoleInference
metadata:
  name: deepseek-v32
  namespace: default
spec:
  labelSelector:
    matchLabels:
      apps: deepseek-v32
  inference:
    preset:
      name: deepseek-ai/DeepSeek-V3.2
      presetOptions:
        modelAccessSecret: hf-token
  roles:
    - name: prefill
      replicas: 2
      instanceType: Standard_NC24ads_A100_v4
    - name: decode
      replicas: 3
      instanceType: Standard_NC24ads_A100_v4
EOF

# 3. Create HTTPRoute for the model
kubectl apply -f - <<EOF
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: deepseek-v32
spec:
  parentRefs:
    - name: inference-gateway
  rules:
    - matches:
        - headers:
            - name: X-Gateway-Model-Name
              value: deepseek-v32
      backendRefs:
        - group: inference.networking.x-k8s.io
          kind: InferencePool
          name: deepseek-v32
          port: 5000
EOF
```

### Monitor

```bash
# Check MultiRoleInference status
kubectl get mri deepseek-v32
# NAME            READY   AGE
# deepseek-v32    True    10m

# Check child InferenceSets
kubectl get is -l kaito.sh/parent=deepseek-v32
# NAME                      REPLICAS   READYREPLICAS   AGE
# deepseek-v32-prefill-0    1          1               10m
# deepseek-v32-prefill-1    1          1               10m
# deepseek-v32-decode-0     1          1               10m
# deepseek-v32-decode-1     1          1               10m
# deepseek-v32-decode-2     1          1               10m

# Check InferencePool and EPP
kubectl get inferencepool deepseek-v32
kubectl get pod -l inferencepool=deepseek-v32-inferencepool-epp

# Verify pod labels
kubectl get pods -l apps=deepseek-v32 --show-labels
# NAME                                    LABELS
# deepseek-v32-prefill-0-ws-xxx           apps=deepseek-v32,inference-role=prefill
# deepseek-v32-prefill-1-ws-xxx           apps=deepseek-v32,inference-role=prefill
# deepseek-v32-decode-0-ws-xxx            apps=deepseek-v32,inference-role=decode
# deepseek-v32-decode-1-ws-xxx            apps=deepseek-v32,inference-role=decode
# deepseek-v32-decode-2-ws-xxx            apps=deepseek-v32,inference-role=decode
```

### Test

```bash
# Send request through Gateway
curl -s http://<gateway-ip>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v32",
    "messages": [{"role": "user", "content": "Explain KV cache in transformers"}]
  }'
```

## Implementation Checklist

| Phase | Step | Description | Dependencies |
|-------|------|-------------|-------------|
| **Phase 1: Core** | 1 | MultiRoleInference CRD types (prefill + decode roles, no router) | None |
| | 2 | Controller: create prefill/decode child InferenceSets with `inference-role` label | None |
| | 3 | Controller: generate vLLM NixlConnector ConfigMaps (kv_producer / kv_consumer) | vLLM disagg support |
| | 4 | Controller: create InferencePool (selector matches all prefill + decode pods) | None |
| | 5 | Controller: auto-generate P/D EPP plugin ConfigMap | llm-d disagg-profile-handler |
| | 6 | Controller: create OCI Repository + HelmRelease (llm-d EPP image) | llm-d image in MCR |
| | 7 | Controller: create DestinationRule (TLS bypass) | Istio |
| | 8 | Controller: status aggregation from child InferenceSets + InferencePool | None |
| | 9 | Webhook: validation + defaulting | None |
| **Phase 2: Autoscaling** | 10 | Controller: propagate KEDA annotations from MRI to child InferenceSets | keda-kaito-scaler |
| | 11 | keda-kaito-scaler: understand role-specific metrics (prefill vs decode) | keda-kaito-scaler changes |
| **Phase 3: Advanced** | 12 | Support custom `eppPluginsConfigRef` for user-defined EPP plugins | None |
| | 13 | Support llm-d routing sidecar for precise prefix cache scoring | llm-d-routing-sidecar |
| | 14 | Scale MRI roles[].replicas (add/remove InferenceSet instances) | keda-kaito-scaler MRI support |

## References

- [MultiRoleInference proposal (PR #1846)](https://github.com/kaito-project/kaito/pull/1846)
- [llm-d EPP migration proposal](https://github.com/kaito-project/kaito/blob/main/docs/proposals/20260421-migrate-epp-to-llm-d-inference-scheduler.md)
- [llm-d inference scheduler](https://github.com/llm-d/llm-d-inference-scheduler)
- [llm-d disagg-profile-handler](https://github.com/llm-d/llm-d-inference-scheduler/tree/main/pkg/plugins)
- [keda-kaito-scaler](https://github.com/kaito-project/keda-kaito-scaler)
- [vLLM disaggregated prefill](https://docs.vllm.ai/en/latest/features/disagg_prefill.html)
- [Gateway API Inference Extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension)
- [GWIE to llm-d migration plan](https://github.com/kubernetes-sigs/gateway-api-inference-extension/issues/2430)
