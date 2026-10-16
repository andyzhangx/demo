# 2026-10-16 live benchmark for `qwen-2-5-0-5b-instruct-cpu-tfs-25z7m-0`

This note captures a fresh live rerun against the current KAITO pod named:

- pod: `qwen-2-5-0-5b-instruct-cpu-tfs-25z7m-0`
- service: `qwen-2-5-0-5b-instruct-cpu-tfs-25z7m`
- workspace: `qwen-2-5-0-5b-instruct-cpu-tfs-25z7m`
- served model name: `qwen2.5-0.5b-instruct`
- model root: `qwen/qwen2.5-0.5b-instruct`
- node shape: `Standard_D16s_v5`
- actual node: `aks-ws8fbcbc958-30541760-vmss000000`
- execution mode: **serial**, via `kubectl port-forward`, calling `http://127.0.0.1:18080`
- request set: the same 20 prompts in `short-requests.txt` and the same 20 prompts in `long-requests.txt`
- measurement window: `2026-10-16T05:22:04Z` to `2026-10-16T05:36:06Z`

## Runtime observation

This live pod is running the expected transformers/TFS CPU runtime rather than the earlier mislabeled vLLM CPU path.

Observed runtime signals:

- image:
  - `andyzhangx/kaito-base-tfs-cpu:0.3.0`
- container command:
  - `accelerate launch --num_processes=1 --num_machines=1 --machine_rank=0 --gpu_ids=all /workspace/tfs/inference_api.py --torch_dtype=bfloat16 --pipeline=text-generation --served_model_name=qwen2.5-0.5b-instruct --pretrained_model_name_or_path=qwen/qwen2.5-0.5b-instruct --allow_remote_files`
- `/health` result:
  - `{"status":"Healthy"}`
- `/v1/models` result:
  - `owned_by: "kaito"`

## Important API observation

The earlier live CPU report used `/v1/completions` to avoid chat-path behavior differences.

For this pod, that same endpoint is **not implemented**:

- `POST /v1/completions` → `404 Not Found`

The runtime OpenAPI only exposed:

- `/v1/chat/completions`
- `/v1/responses`
- `/v1/models`

So this rerun kept the **same request files**, **same serial execution pattern**, and **same token limits**, but used:

- endpoint: `/v1/chat/completions`
- `temperature=0`
- short requests: `max_tokens=32`
- long requests: `max_tokens=256`

One runtime nuance from the server logs:

- transformers logged that generation flags such as `temperature`, `top_p`, and `top_k` may be ignored by this serving path

## Summary

| Request type | Samples | Success rate | Avg latency | P50 | P95 | Min | Max | Avg prompt tokens | Avg completion tokens | Avg total tokens | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short request | 20 | 100% | 4123.78 ms | 4126.86 ms | 4170.51 ms | 4045.24 ms | 4184.06 ms | 51.55 | 21.00 | 72.55 | 5.09 tok/s |
| Long request | 20 | 100% | 37772.32 ms | 37757.92 ms | 38275.52 ms | 37347.27 ms | 38349.31 ms | 71.55 | 256.00 | 327.55 | 6.78 tok/s |

## Request details

### Short request shape

Prompt shape:

```text
Request N: In one short sentence, explain what Kubernetes is. Keep it under 20 words.
```

Parameters:

- `max_tokens=32`
- `temperature=0`
- endpoint: `/v1/chat/completions`

Observed behavior:

- all 20 requests succeeded
- all 20 finished with `finish_reason=stop`
- average completion length was exactly `21` tokens
- prompt token count was `51` for requests `1-9` and `52` for requests `10-20`

### Long request shape

Prompt shape:

```text
Request N: Explain how Kubernetes handles pod creation from API submission to container start. Use a concise but detailed structure with sections for API server, scheduler, kubelet, container runtime, and networking/storage considerations.
```

Parameters:

- `max_tokens=256`
- `temperature=0`
- endpoint: `/v1/chat/completions`

Observed behavior:

- all 20 requests succeeded
- all 20 finished with `finish_reason=length`
- average completion length was exactly `256` tokens
- prompt token count was `71` for requests `1-9` and `72` for requests `10-20`

## Direct takeaways

- The live pod was **stable** for all **40/40** serial requests.
- This pod is a **real transformers/TFS CPU runtime** benchmark, not the earlier mislabeled vLLM CPU path.
- Short requests completed in about **4.12s** on average.
- Long requests with **256 generated tokens** completed in about **37.77s** on average.
- Throughput was stable at about:
  - **5.09 tok/s** on the short case
  - **6.78 tok/s** on the long case
- Compared with the earlier mislabeled vLLM CPU measurement, this transformers/TFS runtime is substantially slower on both short and long requests, but it was stable across the full 40-request run.

## Comparison vs `2026-10-15-live-vllm-cpu-benchmark.md`

The closest comparison point is:

- `llm/kaito/kaito-cpu-minimal-poc-test/2026-10-15-live-vllm-cpu-benchmark.md`

That vLLM run used the **same short/long request files**, the same serial execution pattern, the same model family, and the same node shape (`Standard_D16s_v5`).

There are still two important caveats:

- the vLLM report used `/v1/completions`, while this TFS run had to use `/v1/chat/completions` because `/v1/completions` returned `404`
- the short case did **not** generate the same output length on both runtimes:
  - vLLM short case averaged `32` completion tokens
  - TFS short case averaged `21` completion tokens

So the **long case** is the cleaner apples-to-apples comparison because both runs generated `256` completion tokens.

| Metric | TFS CPU (this run) | vLLM CPU (prior run) | Relative difference |
| --- | ---: | ---: | ---: |
| Short avg latency | 4123.78 ms | 859.20 ms | TFS is **4.80x slower** |
| Short throughput | 5.09 tok/s | 37.25 tok/s | TFS is **86.3% lower** |
| Long avg latency | 37772.32 ms | 6083.30 ms | TFS is **6.21x slower** |
| Long throughput | 6.78 tok/s | 42.09 tok/s | TFS is **83.9% lower** |

### Comparison takeaways

- On the **short case**, TFS was much slower, but that result is also affected by a different response shape (`stop` at ~21 tokens vs `length` at 32 tokens on vLLM).
- On the **long case**, where both runtimes generated the same `256` completion tokens, the comparison is much cleaner:
  - TFS latency was about **37.77s** vs **6.08s** for vLLM
  - TFS throughput was about **6.78 tok/s** vs **42.09 tok/s** for vLLM
- For this live cluster state and request family, **vLLM CPU clearly outperformed transformers/TFS CPU** on both latency and throughput.
- The TFS runtime was still **functionally stable** across all `40/40` requests, so the tradeoff here is mainly **performance**, not correctness or stability.

## Artifacts

Raw benchmark output for this rerun was captured in:

- `/home/vibe/.openclaw/workspace/qwen_cpu_tfs_live_benchmark_results.json`
