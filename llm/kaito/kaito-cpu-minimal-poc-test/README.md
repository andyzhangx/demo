# kaito-cpu-minimal-poc-test

This folder stores the exact prompt content used for the Qwen CPU rerun benchmark documented in `llm/kaito/kaito-cpu-minimal-poc.md`.

## Files
- `short-requests.txt`: the 20 short benchmark prompts
- `long-requests.txt`: the 20 long benchmark prompts
- `2026-10-15-live-vllm-cpu-benchmark.md`: a fresh live rerun report for the current KAITO CPU vLLM pod using this exact request set
- `2026-10-15-live-cpu-tfs-pod-benchmark.md`: a fresh live rerun report for the pod named `cpu-tfs`, including the observed runtime mismatch (the live container was still serving via vLLM CPU at measurement time)

## Notes
- The short and long request shapes were intentionally kept identical between the earlier experimental vLLM CPU benchmark and the later transformers CPU rerun so the results could be compared more directly.
- Both test runs used serial execution, `temperature=0`, and the same token limits described in the benchmark write-up.
- The two main live comparison reports in this folder are:
  - `2026-10-15-live-vllm-cpu-benchmark.md`
  - `2026-10-15-live-cpu-tfs-pod-benchmark.md`

## Latest live TFS benchmark (2026-10-28)

- [Full report (Chinese)](2026-10-28-live-cpu-tfs-pod-benchmark.md) · [Per-sample statistics and provenance](2026-10-28-live-cpu-tfs-pod-benchmark-summary.json)
- Target: `qwen-2-5-0-5b-instruct-cpu-tfs-pmfmn-0`, actual Transformers/TFS runtime, `Standard_D16s_v6`.
- Same 20 short + 20 long prompts, serial chat requests, `temperature=0`, `max_tokens=32/256`.
- Mean latency: **2,504.37 ms short / 28,671.93 ms long**; end-to-end output throughput: **8.39 / 8.93 tokens/s**.
- **49 client attempts total**: 40 original attempts (31 successes, 9 transport failures), followed by 9 explicit recovery retries (all successful). Final results contain 20 unique successful samples per group across two measurement windows, not an uninterrupted 40/40 run.
- Pod remained healthy with zero restarts. Compared with historical TFS, mean latency was 39.3% / 24.1% lower, but node generation and image/runtime differ; this is not a controlled code-performance comparison.

## Historical runtime comparison summary (2026-10-16)
- Both reports benchmark the same `Qwen/Qwen2.5-0.5B-Instruct` request family on `Standard_D16s_v5` with 20 short + 20 long serial requests.
- The **vLLM CPU** run was much faster than the **transformers/TFS CPU** run.
- Headline numbers:
  - short latency: TFS `4123.78 ms` vs vLLM `859.20 ms` → TFS was **4.80x slower**
  - long latency: TFS `37772.32 ms` vs vLLM `6083.30 ms` → TFS was **6.21x slower**
  - short throughput: TFS `5.09 tok/s` vs vLLM `37.25 tok/s`
  - long throughput: TFS `6.78 tok/s` vs vLLM `42.09 tok/s`
- The **long case** is the cleaner apples-to-apples comparison because both runtimes generated `256` completion tokens.
- One caveat on the short case: the TFS run used `/v1/chat/completions` and averaged `21` completion tokens, while the vLLM run used `/v1/completions` and averaged `32` completion tokens.

## What “same requests” means here
- These files are the **same request set used for the Qwen runtime comparison**:
  - experimental `vLLM CPU`
  - later `transformers CPU` rerun
- In that comparison, the request shapes, token limits, and prompt templates were intentionally kept the same so the latency and throughput numbers were more directly comparable.
- The numbered prefixes (`Request 1`, `Request 2`, etc.) are only lightweight sample identifiers. They do **not** change the overall request shape in a meaningful way for this comparison.
- These files do **not** represent the older `microsoft/Phi-3-mini-4k-instruct` CPU POC request set from the earlier section of `kaito-cpu-minimal-poc.md`.
