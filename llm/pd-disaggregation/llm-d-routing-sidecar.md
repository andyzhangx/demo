# llm-d Routing Sidecar

## Overview

Routing sidecar 是 llm-d 架构中用于**分离式推理（Disaggregated Prefill/Decode, P/D）**的反向代理组件。它作为 sidecar 容器部署在 decode pod 旁边，负责在 prefill worker 和 decode worker 之间协调请求转发和 KV cache 传输。

- **Repo**: https://github.com/llm-d/llm-d-routing-sidecar (已废弃，代码已合并到 [llm-d-inference-scheduler](https://github.com/llm-d/llm-d-inference-scheduler) 的 `cmd/pd_sidecar` 和 `pkg/sidecar` 目录)
- **License**: Apache 2.0

## 核心作用

在 P/D 分离架构中，prefill 和 decode 运行在不同的 vLLM 实例上。当 EPP（Endpoint Picker）决定某个请求需要先发到 prefill worker 处理，再转给 decode worker 时，routing sidecar 负责：

1. **接收请求** — 监听在指定端口（默认 8000）
2. **读取 `x-prefiller-host-port` header** — EPP 在调度时设置这个 header，指明哪个 prefill pod 应该处理这个请求
3. **转发请求到 prefill worker** — 将请求代理到指定的 prefill pod
4. **KV cache 传输** — prefill 完成后，通过 NIXL/LMCache connector 将 KV cache 传给 decode worker
5. **返回结果** — decode worker 利用传来的 KV cache 直接生成 token

## 架构

```
Client → Envoy Gateway → EPP (scheduling) → Routing Sidecar (decode pod)
                                                  ↓
                                            Prefill Worker (KV计算)
                                                  ↓ (NIXL KV transfer)
                                            Decode Worker (token生成)
                                                  ↓
                                              Response
```

## 关键参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-port` | sidecar 监听端口 | `8000` |
| `-vllm-port` | 本地 vLLM decode 端口 | `8001` |
| `-connector` | P/D connector 类型 | `nixl` |
| `-enable-ssrf-protection` | 启用 SSRF 防护（基于 InferencePool allowlist） | `false` |
| `-inference-pool-namespace` | InferencePool 所在 namespace | 环境变量 `INFERENCE_POOL_NAMESPACE` |
| `-inference-pool-name` | InferencePool 名称 | 环境变量 `INFERENCE_POOL_NAME` |

> **注意**: `lmcache` 和 `nixl` connector 已废弃，推荐使用 `nixlv2`。

## Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-decode
spec:
  template:
    spec:
      containers:
      # vLLM decode worker
      - name: vllm
        image: ghcr.io/llm-d/llm-d:0.0.8
        args:
        - --model=Qwen/Qwen3-0.6B
        - --port=8001
        - --enforce-eager
        - --kv-transfer-config={"kv_connector":"NixlConnector","kv_role":"kv_both"}
        env:
        - name: UCX_TLS
          value: "cuda_ipc,cuda_copy,tcp"
        - name: VLLM_NIXL_SIDE_CHANNEL_PORT
          value: "5555"
        - name: VLLM_NIXL_SIDE_CHANNEL_HOST
          value: "localhost"
        ports:
        - containerPort: 8001

      # Routing sidecar
      - name: routing-sidecar
        image: quay.io/llm-d/llm-d-routing-sidecar:latest
        args:
        - -port=8000
        - -vllm-port=8001
        - -connector=nixlv2
        - -enable-ssrf-protection=true
        ports:
        - containerPort: 8000
        env:
        - name: INFERENCE_POOL_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: INFERENCE_POOL_NAME
          value: "my-inference-pool"
```

## SSRF Protection

启用 SSRF 防护后：
- 只允许 InferencePool 内匹配的 pod 作为 prefill 目标（基于 host/IP，不限端口）
- 请求到未授权目标会返回 HTTP 403
- allowlist 会随 pod 变更自动更新

## Local Testing (Quick Start)

```bash
# Terminal 1: Start decode worker (GPU 0)
podman run --network host --device nvidia.com/gpu=0 -v $HOME/models:/models \
  -e UCX_TLS="cuda_ipc,cuda_copy,tcp" \
  -e VLLM_NIXL_SIDE_CHANNEL_PORT=5555 \
  -e VLLM_NIXL_SIDE_CHANNEL_HOST=localhost \
  -e HF_HOME=/models ghcr.io/llm-d/llm-d:0.0.8 --model Qwen/Qwen3-0.6B \
  --enforce-eager --port 8001 \
  --kv-transfer-config='{"kv_connector":"NixlConnector","kv_role":"kv_both"}'

# Terminal 2: Start prefill worker (GPU 1)
podman run --network host --device nvidia.com/gpu=1 -v $HOME/models:/models \
  -e UCX_TLS="cuda_ipc,cuda_copy,tcp" \
  -e VLLM_NIXL_SIDE_CHANNEL_PORT=5556 \
  -e VLLM_NIXL_SIDE_CHANNEL_HOST=localhost \
  -e HF_HOME=/models ghcr.io/llm-d/llm-d:0.0.8 --model Qwen/Qwen3-0.6B \
  --enforce-eager --port 8002 \
  --kv-transfer-config='{"kv_connector":"NixlConnector","kv_role":"kv_both"}'

# Terminal 3: Start routing sidecar
git clone https://github.com/llm-d/llm-d-routing-sidecar.git
cd llm-d-routing-sidecar && make build
./bin/llm-d-routing-sidecar -port=8000 -vllm-port=8001 -connector=nixlv2

# Terminal 4: Send request (x-prefiller-host-port tells sidecar which prefiller to use)
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -H "x-prefiller-host-port: http://localhost:8002" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "prompt": "Explain what disaggregated inference is:"
  }'
```

## 何时需要 Routing Sidecar

- **需要**: P/D 分离部署（prefill 和 decode 在不同 pod/GPU 上）
- **不需要**: 标准推理部署（prefill 和 decode 在同一 vLLM 实例上）

## References

- [llm-d Architecture](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/architecture.md)
- [Disaggregation Doc](https://github.com/llm-d/llm-d-inference-scheduler/blob/main/docs/disaggregation.md)
- [Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/)
