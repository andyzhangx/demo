# kaito-cpu-minimal-poc-test

This folder stores the exact prompt content used for the Qwen CPU rerun benchmark documented in `llm/kaito/kaito-cpu-minimal-poc.md`.

## Files
- `short-requests.txt`: the 20 short benchmark prompts
- `long-requests.txt`: the 20 long benchmark prompts

## Notes
- The short and long request shapes were intentionally kept identical between the earlier experimental vLLM CPU benchmark and the later transformers CPU rerun so the results could be compared more directly.
- Both test runs used serial execution, `temperature=0`, and the same token limits described in the benchmark write-up.
