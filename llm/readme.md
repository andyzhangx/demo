## Knowledge
 - [vLLM Router: A High-Performance and Prefill/Decode Aware Load Balancer for Large-scale Serving](https://vllm.ai/blog/vllm-router-release)

## Backlog

 - multimodal generation support
   - https://github.com/vllm-project/vllm-omni
   - https://github.com/ai-dynamo/dynamo/blob/main/docs/backends/vllm/vllm-omni.md
 - Quantization support
 - https://vllm.ai/blog/kv-offloading-connector
 - [Dynamo ModelExpress: Model weight management for LLM inference — cache, transfer, and serve weights at scale with GPU-to-GPU RDMA and multi-node coordination](https://github.com/ai-dynamo/modelexpress)

### issues
 - how to disable think during vllm startup for https://huggingface.co/tencent/Hunyuan-A13B-Instruct?
```yaml
kind: ConfigMap
metadata:
  name: pd-params
data:
  inference_config.yaml: |
    max_probe_steps: 6
    vllm:
      tensor-parallel-size: 1
      max_model_len: 1024
      gpu-memory-utilization: 0.95
      default-chat-template-kwargs: "{\"enable_thinking\":false}"
```
