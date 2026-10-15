# 2026-10-15 live benchmark for `qwen-2-5-0-5b-instruct-cpu-tfs-lpc7d-0`

This note captures a fresh live rerun against the current KAITO pod named:

- pod: `qwen-2-5-0-5b-instruct-cpu-tfs-lpc7d-0`
- served model name: `qwen-2-5-0-5b-instruct-cpu-tfs`
- model root: `Qwen/Qwen2.5-0.5B-Instruct`
- node shape: `Standard_D16s_v5`
- execution mode: **serial**, from **inside the pod**, calling `http://127.0.0.1:5000`
- request set: the same 20 prompts in `short-requests.txt` and the same 20 prompts in `long-requests.txt`

## Important runtime observation

Although the pod name contains `cpu-tfs`, the live container that was actually benchmarked was **not** running a Transformers/TFS serving stack.

Observed runtime signals:

- image:
  - `andyzhangx/kaito-base-vllm-cpu:0.3.0`
- command:
  - `python3 /workspace/vllm/inference_api.py ...`
- `/v1/models` result:
  - `owned_by: "vllm"`

So the results below are a benchmark of the **live pod as deployed**, which at measurement time was effectively another **vLLM CPU** serving pod, even though its name suggested a TFS/transformers path.

## Why this rerun used `/v1/completions`

Like the earlier live CPU preset rerun, the current chat-serving path enables Hermes tool parsing and auto tool choice.

When the same long prompts were sent to `/v1/chat/completions`, the model returned tool-call-shaped output instead of a normal long-form answer, and one sampled long request took about **96s** before returning a `<tool_call>...</tool_call>` payload. That output shape is not comparable to the intended long-generation benchmark.

To keep the request texts the same while forcing a normal generation path, this rerun used:

- endpoint: `/v1/completions`
- `temperature=0`
- short requests: `max_tokens=32`
- long requests: `max_tokens=256`

## Summary

| Request type | Samples | Success rate | Avg latency | P50 | P95 | Min | Max | Avg prompt tokens | Avg completion tokens | Avg total tokens | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short request | 20 | 100% | 1079.87 ms | 1076.75 ms | 1113.78 ms | 1065.59 ms | 1114.54 ms | 22.55 | 32.00 | 54.55 | 29.64 tok/s |
| Long request | 20 | 100% | 7801.13 ms | 7791.47 ms | 7889.30 ms | 7720.94 ms | 7908.21 ms | 42.55 | 256.00 | 298.55 | 32.82 tok/s |

## Request details

### Short request shape

Prompt shape:

```text
Request N: In one short sentence, explain what Kubernetes is. Keep it under 20 words.
```

Parameters:

- `max_tokens=32`
- `temperature=0`

Observed behavior:

- all 20 requests succeeded
- all 20 finished with `finish_reason=length`
- average completion length was exactly `32` tokens

### Long request shape

Prompt shape:

```text
Request N: Explain how Kubernetes handles pod creation from API submission to container start. Use a concise but detailed structure with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.
```

Parameters:

- `max_tokens=256`
- `temperature=0`

Observed behavior:

- all 20 requests succeeded
- all 20 finished with `finish_reason=length`
- average completion length was exactly `256` tokens

## Direct takeaways

- The live pod was **stable** for all **40/40** serial requests on `/v1/completions`.
- Short requests completed in about **1.08s** on average.
- Long requests with **256 generated tokens** completed in about **7.80s** on average.
- Throughput was stable at about:
  - **29.6 tok/s** on the short case
  - **32.8 tok/s** on the long case
- The pod name currently suggests a TFS/transformers path, but the measured runtime was **actually vLLM CPU**, so these numbers should not be used as a true transformers-vs-vLLM comparison point.
