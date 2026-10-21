# Why separate prefill and decode? — slides 5–7

These pages expand the introductory motivation using two original external research figures and one conceptual summary. They are **not KAITO/llm-d measurements**, not a new reproduction, and not a benchmark of current vLLM scheduling.

## Source and license

Yinmin Zhong et al., **DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving**, arXiv:2401.09670v2, March 19, 2024.

- [Versioned paper](https://arxiv.org/html/2401.09670v2).
- [Figure 2 and interference discussion](https://arxiv.org/html/2401.09670v2#S2.F2).
- [Figure 3 and phase-specific tuning discussion](https://arxiv.org/html/2401.09670v2#S3.F3).
- [Resource and parallelism coupling, section 2.3](https://arxiv.org/html/2401.09670v2#S2.SS3).
- Paper/figures license: **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**, as declared by the versioned arXiv page. Attribution is preserved on the slides and in speaker notes. This license applies to the reproduced source SVGs and their PNG rasterizations; no ownership or different license is asserted over these figures.

The SVG files here are downloaded verbatim from the versioned paper. PNGs are mechanical rasterizations using PyMuPDF at 3× scale, with original axes, legends, annotations and data intact. No values were visually estimated, digitized or redrawn. Added presentation labels sit outside the original figures. See `source-manifest.json` for URLs and SHA-256 hashes.

## Slide 5 — A prefill can interfere with existing decode work

`distserve-fig2-interference.svg` / `.png` reproduce [the Figure 2 SVG](https://arxiv.org/html/2401.09670v2/prefill-decoding-interference.svg).

- Model is described as a **13B LLM** in the figure caption.
- Left: 128-token prefill. Right: 1,024-token prefill.
- Orange: decoding-only batch. Blue: decoding plus one prefill.
- The plotted quantity is **batch execution latency**, not client-visible TTFT or end-to-end request latency.
- **Panel scales differ.** Compare the within-panel mixed/decode-only gap, not apparent slopes or heights across panels.
- The blue horizontal line and slowdown arrows are original source annotations.
- Interpretation: a long prefill can delay other requests' token streams. Chunked prefill, continuous batching and scheduling can mitigate this; do not infer the same penalty in every modern colocated setup.

## Slide 6 — Different batching curves justify separate tuning

`distserve-fig3-throughput.svg` / `.png` reproduce [the Figure 3 SVG](https://arxiv.org/html/2401.09670v2/prefill_decode_throughput.svg).

- 13B LLM, input lengths 128/256/512/1,024; phase-only throughput versus batch size.
- Left panel: prefill. Right panel: decode.
- Read the curve shapes within each panel. Prefill throughput plateaus earlier; decode benefits more from batching in this setup.
- **Input-token and output-token throughput are not interchangeable units of useful work.** Do not compare absolute heights as equivalent serving productivity.
- Compute-dominant prefill and bandwidth-dominant decode are common operating regimes, not universal truths independent of model, batch size, context length and hardware.
- The paper analyzes A100 behavior in sections 2–3, but the captions do not enumerate every kernel, software version or exact model identifier. No current-AKS numeric capacity threshold is inferred.

## Slide 7 — Independent capacity avoids a forced compromise

This page is a native, editable conceptual summary, not measured data. The two demand patterns indicate where to investigate first, not a deterministic scaling rule. Longer prompts can also increase decode KV state and KV-transfer cost, so always check both roles and end-to-end SLOs.

Separate execution pools permit different replica, parallelism, batching and resource choices where supported. The gain must exceed KV transfer, duplicated model-weight residency and added operational costs. No fixed P:D ratio, GPU-saving claim or new KAITO autoscaling availability is implied.

## NVIDIA Dynamo cross-reference

The user-provided [NVIDIA Dynamo disaggregated-serving overview](https://docs.nvidia.com/dynamo/dev/kubernetes/disaggregated-serving/overview) corroborates phase-specific resource bottlenecks, independent worker pools, batching, parallelism and hardware choices. Accessed 2026-10-21; `/dev/` is a moving documentation version. The overview page is text-only, so the two reproduced empirical figures come from the explicitly licensed DistServe paper instead. No NVIDIA performance numbers or imagery are reproduced.

Slide 7 links NVIDIA in its speaker notes and cites it visibly. Compute-bound prefill / bandwidth-bound decode are common regimes, not universal laws. Dynamo's decode-first orchestration, etcd/NATS discovery and NIXL configuration are not presented as KAITO/llm-d implementation behavior.
