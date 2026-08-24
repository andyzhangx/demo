# Deploy LLM Inference Service on AKS

This guide walks through deploying an LLM inference service (vLLM / SGLang) on Azure Kubernetes Service (AKS) with GPU nodes.

## 1. Create GPU Node Pool

```bash
# Create a GPU node pool (A100 example)
az aks nodepool add \
  --resource-group <rg> \
  --cluster-name <cluster> \
  --name gpupool \
  --node-count 2 \
  --node-vm-size Standard_NC96ads_A100_v4 \
  --node-taints sku=gpu:NoSchedule \
  --labels workload=llm-inference
```

### Common GPU SKUs

| SKU | GPU | VRAM | Suitable Models |
|---|---|---|---|
| Standard_NC24ads_A100_v4 | 1x A100 | 80GB | 7B-13B |
| Standard_NC48ads_A100_v4 | 2x A100 | 160GB | 13B-34B |
| Standard_NC96ads_A100_v4 | 4x A100 | 320GB | 70B+ |
| Standard_ND96isr_H100_v5 | 8x H100 | 640GB | 70B+ / MoE |

## 2. Verify GPU Driver

AKS auto-installs NVIDIA drivers by default. Verify:

```bash
kubectl get nodes -l workload=llm-inference -o json | \
  jq '.items[].status.capacity["nvidia.com/gpu"]'
```

If not auto-installed, manually deploy the NVIDIA device plugin:

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/deployments/static/nvidia-device-plugin.yml
```

## 3. Create Model Cache PVC

Use Azure Managed Disk to cache model weights and avoid re-downloading on every pod restart:

```yaml
# model-cache-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache-pvc
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: managed-premium
  resources:
    requests:
      storage: 200Gi
```

> **Tip:** For better performance, consider using Azure Blob + CSI driver or pre-built custom images with model weights baked in.

## 4. Create HuggingFace Token Secret

```bash
kubectl create secret generic hf-secret \
  --from-literal=token=<your-huggingface-token>
```

## 5. Deploy vLLM

```yaml
# vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      nodeSelector:
        workload: llm-inference
      tolerations:
      - key: sku
        value: gpu
        effect: NoSchedule
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - "--model"
        - "meta-llama/Llama-3.1-8B-Instruct"
        - "--tensor-parallel-size"
        - "1"
        - "--max-model-len"
        - "8192"
        - "--gpu-memory-utilization"
        - "0.9"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            cpu: "8"
            memory: "64Gi"
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-secret
              key: token
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 10
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

## 6. Deploy SGLang (Alternative)

If you prefer SGLang for better multi-turn conversation performance (RadixAttention) or structured output:

```yaml
# sglang-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sglang-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sglang
  template:
    metadata:
      labels:
        app: sglang
    spec:
      nodeSelector:
        workload: llm-inference
      tolerations:
      - key: sku
        value: gpu
        effect: NoSchedule
      containers:
      - name: sglang
        image: lmsysorg/sglang:latest
        command: ["python3", "-m", "sglang.launch_server"]
        args:
        - "--model-path"
        - "meta-llama/Llama-3.1-8B-Instruct"
        - "--tp"
        - "1"
        - "--port"
        - "8000"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            cpu: "8"
            memory: "64Gi"
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-secret
              key: token
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 10
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: sglang-service
spec:
  selector:
    app: sglang
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

## 7. Autoscaling

### HPA (Pod-level)

```yaml
# vllm-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-server
  minReplicas: 1
  maxReplicas: 4
  metrics:
  - type: Pods
    pods:
      metric:
        name: gpu_utilization  # Requires DCGM Exporter
      target:
        type: AverageValue
        averageValue: "70"
```

### Node-level

Use **Karpenter (NAP)** or **Cluster Autoscaler** to automatically provision GPU nodes when pods are pending.

## 8. Expose the Service

```yaml
# vllm-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vllm-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
spec:
  rules:
  - host: llm.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vllm-service
            port:
              number: 8000
```

## 9. Test the Service

```bash
# Port-forward for local testing
kubectl port-forward svc/vllm-service 8000:8000

# Send a request (OpenAI-compatible API)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 256
  }'
```

## Best Practices

- **Model Preloading** — Use init containers or pre-baked images to avoid cold starts (model download can take 30+ minutes)
- **Health Checks** — Set `initialDelaySeconds` high enough for model loading; only route traffic to ready pods
- **Resource Isolation** — Use taint/toleration to keep GPU nodes exclusively for inference workloads
- **Monitoring** — Deploy DCGM Exporter + Prometheus to track GPU utilization, VRAM usage, and inference latency
- **Cost Control** — Scale to 0 during off-peak; consider Spot instances for non-critical inference
- **Multi-node Inference** — For 70B+ models, use tensor parallelism across multiple GPUs or Ray + vLLM across nodes
- **Security** — Use network policies to restrict access; consider API key authentication in front of the service
