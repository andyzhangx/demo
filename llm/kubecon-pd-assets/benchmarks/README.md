# Public P/D benchmark used on slides 37–39

These are **external vLLM / AMD MORI-IO results**, not KAITO/llm-d measurements, not a local reproduction and not a claim that every workload benefits.

## Primary source and attribution

- AMD and Embedded LLM, **“Next-Level Inference: Why Your Single-Node vLLM Setup Needs Prefill-Decode Disaggregation”**, vLLM blog, April 7, 2026.
- [Published article](https://vllm.ai/blog/2026-04-07-moriio-kv-connector).
- Source repository snapshot: `c4fa4eee56ed2c097a4e078c33955253db123018`.
- [Figure 3 JavaScript, including published per-request arrays](https://github.com/vllm-project/vllm-project.github.io/blob/c4fa4eee56ed2c097a4e078c33955253db123018/assets/figures/2026-04-07-moriio-kv-connector/plotly-figure3.js).
- [Figure 4 image](https://github.com/vllm-project/vllm-project.github.io/blob/c4fa4eee56ed2c097a4e078c33955253db123018/assets/figures/2026-04-07-moriio-kv-connector/SLO-attainment.png), reproduced unmodified with attribution; the slide adds an editable outline around the 8 req/s region. The source figure is the only raster object in this otherwise editable deck. No ownership or blanket relicensing of the source figure is asserted.

`moriio-source-data.json` is the literal `DATA` object extracted from the Figure 3 JavaScript. It includes 100 paired TTFT and per-request ITL observations for each of four configurations, in seconds. Slides 37 and 39 calculate their native, editable bars directly from these arrays. No plotted values were visually estimated or digitized.

## Experimental boundary

- **Model:** `Qwen/Qwen3-235B-A22B-FP8`.
- **Hardware:** one node, eight AMD MI300X GPUs.
- **Compared configurations:** standard two colocated TP4 instances vs MORI-IO write-mode disaggregation, prefill TP4 + decode TP4. Both use all eight GPUs.
- **Workload:** synthetic random inputs, fixed 2,000 input / 1,000 output tokens, 100 requests at 8 offered requests/s for Figure 3; Figure 4 sweeps offered request rate.
- **Joint SLO predicate:** `ttft <= 1.0 and itl <= 0.05` per exported request, reproducing the source JavaScript. This is **not** a p99-per-token ITL predicate; the export does not document how the per-request ITL value aggregates individual tokens.
- **Software:** vLLM source build (exact vLLM commit not stated), ROCm 7.0.3, MORI 0.1.0. Reported settings include `gpu_memory_utilization=0.9`, `max_model_len=4096`, `max_num_seqs=256`, `enable_expert_parallel=True`.
- These concurrent requests mix prefill and decode activity, but there is **no heterogeneous prompt-length, asymmetric-traffic, or independent-autoscaling sweep**.
- Small 100-request sample; no repeated-run uncertainty or error bars.

## Derivations and an inconsistency in the original article

| From pinned Figure 3 arrays | Colocated 2× TP4 | P/D write TP4 + TP4 |
|---|---:|---:|
| Median TTFT | 227.9635 ms | 645.135 ms |
| Nearest-rank p95 TTFT | 490.613 ms | 1325.584 ms |
| Joint SLO passes | 29 / 100 | 73 / 100 |
| Total GPUs | 8 | 8 |
| SLO passes / GPU **in this 100-request trace** | 3.625 | 9.125 |
| Normalized SLO-pass/GPU proxy | 1.00× | 2.52× |

Median is the average of the middle two ordered observations. Nearest-rank p95 is the 95th observation out of 100. Displayed TTFT bars are rounded to integer milliseconds. The normalized proxy is `(73/8)/(29/8) = 73/29 = 2.517241379...`.

**The post's static Table 3 instead reports 28 and 70 joint passes for these configurations.** The pinned interactive Figure 3 data produce 29 and 73. The deck consistently uses the latter exact arrays for every derived value and calls out the discrepancy in notes. It does not silently merge snapshots. The unmodified Figure 4 remains the original author-produced load curve; other rates are not digitized. We do not repeat the source caption's overly broad claim of improvement at *every* rate: at the lowest rate, standard TP4 also reaches 100%.

## What the three slides actually establish

1. **TTFT trade-off:** this experiment has *higher*, not lower, TTFT with disaggregation. Long prompts plus concurrency are a reason to investigate decode interference, not evidence of a TTFT gain by prompt length; this report contains no prompt-length sweep.
2. **Useful-throughput interpretation:** joint SLO attainment under offered load improves at 8 req/s. The chart's y-axis stays SLO attainment; it is not relabeled as measured tokens/s or completed requests/s. A heterogeneous mixed-traffic throughput benchmark remains future validation.
3. **Efficiency proxy:** the fixed-budget run produces more SLO passes per GPU. This is not time-normalized capacity, measured GPU utilization, dollar/energy efficiency, or proof that GPU count can be reduced. Do **not** divide the required GPU budget by 2.52. No asymmetric-traffic efficiency sweep is available in this source.

The three pages interpret one experiment; they are not three independent confirmations. Use them as public evidence of the trade-off, then measure the actual KAITO deployment and workload.
