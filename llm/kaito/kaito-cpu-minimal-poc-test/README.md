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

## What “same requests” means here
- These files are the **same request set used for the Qwen runtime comparison**:
  - experimental `vLLM CPU`
  - later `transformers CPU` rerun
- In that comparison, the request shapes, token limits, and prompt templates were intentionally kept the same so the latency and throughput numbers were more directly comparable.
- The numbered prefixes (`Request 1`, `Request 2`, etc.) are only lightweight sample identifiers. They do **not** change the overall request shape in a meaningful way for this comparison.
- These files do **not** represent the older `microsoft/Phi-3-mini-4k-instruct` CPU POC request set from the earlier section of `kaito-cpu-minimal-poc.md`.
