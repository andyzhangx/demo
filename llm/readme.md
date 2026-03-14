## Backlog

 - multimodal generation support
   - https://github.com/vllm-project/vllm-omni
   - https://github.com/ai-dynamo/dynamo/blob/main/docs/backends/vllm/vllm-omni.md


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
