# 2026-10-15 live vLLM CPU benchmark

This note captures a fresh live rerun against the current KAITO CPU preset pod for:

- model: `Qwen/Qwen2.5-0.5B-Instruct`
- served model name: `qwen-2-5-0-5b-instruct-cpu-vllm`
- pod: `qwen-2-5-0-5b-instruct-cpu-vllm-rlcdh-0`
- node shape: `Standard_D16s_v5`
- execution mode: **serial**, from **inside the pod**, calling `http://127.0.0.1:5000`
- request set: the 20 prompts in `short-requests.txt` and the 20 prompts in `long-requests.txt`

## Why this rerun used `/v1/completions`

The current live preset enables Hermes tool parsing and auto tool choice. When the same long prompts were sent to `/v1/chat/completions`, the model frequently emitted `<tool_call>...</tool_call>` content instead of a normal long-form answer, which reduced the output length and made the latency numbers no longer comparable to the earlier long-output benchmark shape.

To keep the request set the same **and** force a normal generation shape for the long requests, this rerun used:

- endpoint: `/v1/completions`
- `temperature=0`
- short requests: `max_tokens=32`
- long requests: `max_tokens=256`

## Summary

| Request type | Samples | Success rate | Avg latency | P50 | P95 | Min | Max | Avg prompt tokens | Avg completion tokens | Avg total tokens | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short request | 20 | 100% | 859.20 ms | 857.10 ms | 866.52 ms | 847.98 ms | 901.69 ms | 22.55 | 32.00 | 54.55 | 37.25 tok/s |
| Long request | 20 | 100% | 6083.30 ms | 6065.78 ms | 6180.71 ms | 6019.12 ms | 6355.48 ms | 42.55 | 256.00 | 298.55 | 42.09 tok/s |

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

## Additional observation about the current chat endpoint

A separate inspection of the current `/v1/chat/completions` path showed that the live preset is now optimized for tool-calling behavior rather than this benchmark's plain long-answer shape.

With the same long prompt family, the chat endpoint often produced tool-call-like output such as:

```text
<tool_call>
{...}
</tool_call>
```

That behavior made the long case look artificially short and fast, so those numbers were intentionally **not** used as the primary performance report here.

## Takeaways

- The current live vLLM CPU pod was **stable** for all 40 serial requests.
- Short requests completed in about **0.86s** on average.
- Long requests with 256 generated tokens completed in about **6.08s** on average.
- Output throughput remained strong and stable, especially on the long case at about **42.1 tok/s**.
- For this exact live pod and request set, the current CPU vLLM path is functionally healthy and benchmarkable, but the default chat-serving behavior now needs to be interpreted carefully because tool-calling changes the output shape.
