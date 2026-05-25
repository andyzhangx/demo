# Decode StatefulSet Patch for P/D Disaggregation
# Apply after KAITO creates the MultiRoleInference resources
#
# This patch:
# 1. Changes vLLM port from 5000 to 5001
# 2. Changes sidecar port from 5001 to 5000
# 3. Adds VLLM_NIXL_SIDE_CHANNEL_HOST env var for NIXL discovery
#
# Usage:
#   kubectl patch sts <decode-statefulset-name> --type=json -p "$(cat decode-sts-patch.json)"
#   kubectl delete pod <decode-pod> --force  # force restart

# Step 1: Patch decode StatefulSet command to use port 5001
# (Append --port 5001 to the vLLM command)
kubectl patch sts <DECODE_STS_NAME> --type=json -p '[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/command",
    "value": ["/bin/sh", "-c", "python3 /workspace/vllm/inference_api.py --trust-remote-code --dtype=bfloat16 --chat-template=/workspace/chat_templates/tool-chat-phi4-mini.jinja --gpu-memory-utilization=0.84 --tensor-parallel-size=1 --load_format=auto --config_format=auto --served-model-name=phi-4-mini-instruct --max-model-len=131072 --model=microsoft/phi-4-mini-instruct --download-dir=/workspace/weights --kaito-config-file=/mnt/config/inference_config.yaml --tokenizer_mode=auto --enable-prefix-caching --port 5001"]
  },
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

# Step 2: Patch sidecar args to use port 5000 (proxy) → vLLM 5001 (backend)
kubectl patch sts <DECODE_STS_NAME> --type=json -p '[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/1/args",
    "value": ["--port=5000", "--vllm-port=5001", "--secure-proxy=false"]
  }
]'

# Step 3: Patch InferencePool targetPort to 5000
kubectl patch inferencepool <INFERENCEPOOL_NAME> --type=merge -p '{"spec":{"targetPorts":[{"number":5000}]}}'
