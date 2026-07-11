# Enable Distributed Cache (DACS) for KAITO Workspace

This guide applies the distributed cache configuration changes from [kaito-project/kaito#2169](https://github.com/kaito-project/kaito/pull/2169) to an existing KAITO workspace deployment.

## Prerequisites

- A running AKS cluster with KAITO workspace already installed
- `kubectl` configured with cluster access

## Step 1: Patch ClusterRole

Add `storage.azure.com` permissions for `caches` and `caches/status` resources:

```bash
kubectl patch clusterrole kaito-workspace-clusterrole --type='json' -p='[
  {"op":"add","path":"/rules/-","value":{"apiGroups":["storage.azure.com"],"resources":["caches"],"verbs":["get","list","watch"]}},
  {"op":"add","path":"/rules/-","value":{"apiGroups":["storage.azure.com"],"resources":["caches/status"],"verbs":["get"]}}
]'
```

## Step 2: Patch Deployment

Add DACS-related environment variables to the `kaito-workspace` deployment:

```bash
kubectl patch deploy kaito-workspace -n kaito-workspace --type='json' -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DACS_ENABLED","value":"true"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DACS_DISCOVERY_ENDPOINT","value":"<your-discovery-endpoint>"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DACS_KV_CACHE_ENABLED","value":"false"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DACS_KV_CONNECTOR_PROTOCOL","value":"<your-protocol>"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DACS_CLIENT_IMAGE","value":"<your-client-image>"}}
]'
```

Replace the placeholder values:
- `<your-discovery-endpoint>` — DACS discovery endpoint URL
- `<your-protocol>` — KV connector protocol (e.g., `tcp`, `rdma`)
- `<your-client-image>` — DACS client container image

## Step 3: Verify

```bash
# Verify ClusterRole has new rules
kubectl get clusterrole kaito-workspace-clusterrole -o yaml | grep -A6 "storage.azure.com"

# Verify Deployment has DACS env vars
kubectl get deploy kaito-workspace -n kaito-workspace \
  -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}' | grep DACS

# Check rollout status
kubectl rollout status deploy kaito-workspace -n kaito-workspace
```

## Reference

- PR: [kaito-project/kaito#2169](https://github.com/kaito-project/kaito/pull/2169)
- Changed files: `charts/kaito/workspace/templates/clusterrole.yaml`, `charts/kaito/workspace/templates/deployment.yaml`
