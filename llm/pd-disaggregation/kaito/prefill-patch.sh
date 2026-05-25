# Prefill StatefulSet Patch for P/D Disaggregation
# Apply after KAITO creates the MultiRoleInference resources
#
# This patch:
# 1. Removes the routing sidecar container (not needed on prefill)
# 2. Adds VLLM_NIXL_SIDE_CHANNEL_HOST env var for NIXL discovery
#
# Usage:
#   kubectl patch sts <prefill-statefulset-name> --type=json -p "$(cat prefill-patch.json)"
#   kubectl delete pod <prefill-pod> --force  # force restart

# Step 1: Add VLLM_NIXL_SIDE_CHANNEL_HOST to prefill vLLM container
kubectl patch sts <PREFILL_STS_NAME> --type=json -p '[
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/env/-",
    "value": {
      "name": "VLLM_NIXL_SIDE_CHANNEL_HOST",
      "valueFrom": {
        "fieldRef": {
          "fieldPath": "status.podIP"
        }
      }
    }
  }
]'

# Step 2: Remove sidecar container (index 1) if present
# Only run this if prefill StatefulSet has a sidecar container
kubectl patch sts <PREFILL_STS_NAME> --type=json -p '[
  {
    "op": "remove",
    "path": "/spec/template/spec/containers/1"
  }
]'
