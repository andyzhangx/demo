# P/D motivation: original editable conceptual diagrams

Current slides **7–8** contain only native PowerPoint text, rectangles and arrows, authored in `../../generate_kubecon_pd_deck.py`. No source image is reproduced and no numerical data is plotted. Both visibly say **Conceptual / Not a benchmark**, use sentence-case prose labels, and cite the dated source. These are simpler updated explanations, **not recent measured performance charts**.

## Source basis

1. NVIDIA Developer Blog, **“NVIDIA Dynamo, A Low-Latency Distributed Inference Framework for Scaling Reasoning AI Models”**, [published 18 March 2025](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/). Page `datePublished` is `2025-03-18T17:50:00+00:00`; `dateModified` is `2025-08-08T17:30:03+00:00`. Sections on disaggregated serving and the Planner explain different phase resource requirements, independent parallelism, and transfer/queueing tradeoffs. None of the article’s performance multipliers is used.
2. NVIDIA Dynamo, [Disaggregated Serving overview](https://docs.nvidia.com/dynamo/kubernetes/disaggregated-serving/overview), **current documentation accessed 22 October 2026** (not represented as a dated 2025 document). Describes independent pools, prefill pressure from input length/reuse/context, decode pressure from concurrency/output length/active KV, and KV transport overhead. The URL is mutable; these conceptual claims are the source basis, not a guarantee of a specific API version.

3. vLLM, [Disaggregated Prefill](https://docs.vllm.ai/en/latest/features/disagg_prefill/), current documentation accessed 22 October 2026. Explains how prefill inserted into decoding can increase tail ITL, how chunked prefill can mitigate it, and why disaggregation does not itself guarantee throughput improvement.

4. vLLM, [Anatomy of vLLM](https://vllm.ai/blog/2025-09-05-anatomy-of-vllm), article dated **5 September 2025** (published in the repository 8 September; discusses an August 9 snapshot). Scheduler and chunked-prefill sections explain prompt-position batching, ordinary decode’s newest-token positions, and mixed prefill/decode scheduling. No article benchmarks are reused.

## What the diagrams mean

- **Slide 7:** request A is decoding while another request B needs prefill. A simplified shared-GPU schedule illustrates possible interference; separate GPUs remove B’s direct prefill execution from A’s decode GPU. Widths, gaps, counts and lane lengths are schematic, not latency or throughput. This is not an equal-GPU-budget comparison. Chunked prefill, interleaving and scheduler policies may mitigate a shared-worker pause. Equal spacing is not a promise of constant ITL. B’s KV handoff/start is omitted from the lane view but explicitly required; queueing, shared-fabric/memory contention and transfer can still cause jitter.
- **Slide 8:** prefill batches many prompt-token input positions from one or more requests. Ordinary decode consumes one newest input position per active sequence, reads prior KV, and then selects its next output token. This is cross-request batching, not simultaneous generation of multiple successive tokens within one request. Prefill still respects causal attention; chunking and prefix reuse alter processed positions. Speculative decoding is outside this basic example. Both phases use memory and compute. Larger decode batches are not unconditionally better; iteration time, ITL and KV-memory limits still apply. Token/request counts are schematic, not optimal sizes. KV-transfer cost remains explicit on slide7 and discussed on slide9; slide8 focuses on batching rather than independent capacity.

The author-created diagrams are not copies/adaptations of NVIDIA artwork. NVIDIA is cited as the conceptual source, not as the author of the shapes. Full sources and caveats are also in speaker notes. No external measurement was performed.

## Historical assets — not embedded in the current deck

The following files are retained for provenance and reproducibility of the prior version. They are **not** the new diagrams, and their 2024 results have not been relabeled as newer data. DistServe remains a conceptual reference in the unchanged slide 9 notes.

## Archived version: Why separate prefill and decode? — former slides 7–9

The previous version expanded the introductory motivation using two original external research figures and one conceptual summary. They are **not KAITO/llm-d measurements**, not a new reproduction, and not a benchmark of current vLLM scheduling.

## Source and license

Yinmin Zhong et al., **DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving**, arXiv:2401.09670v2, March 19, 2024.

- [Versioned paper](https://arxiv.org/html/2401.09670v2).
- [Figure 2 and interference discussion](https://arxiv.org/html/2401.09670v2#S2.F2).
- [Figure 3 and phase-specific tuning discussion](https://arxiv.org/html/2401.09670v2#S3.F3).
- [Resource and parallelism coupling, section 2.3](https://arxiv.org/html/2401.09670v2#S2.SS3).
- Paper/figures license: **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**, as declared by the versioned arXiv page. Attribution is preserved on the slides and in speaker notes. This license applies to the reproduced source SVGs and their PNG rasterizations; no ownership or different license is asserted over these figures.

The SVG files here are downloaded verbatim from the versioned paper. PNGs are mechanical rasterizations using PyMuPDF at 3× scale, with original axes, legends, annotations and data intact. No values were visually estimated, digitized or redrawn. Added presentation labels sit outside the original figures. See `source-manifest.json` for URLs and SHA-256 hashes.

## Slide 7 — A prefill can interfere with existing decode work

`distserve-fig2-interference.svg` / `.png` reproduce [the Figure 2 SVG](https://arxiv.org/html/2401.09670v2/prefill-decoding-interference.svg).

- Model is described as a **13B LLM** in the figure caption.
- Left: 128-token prefill. Right: 1,024-token prefill.
- Orange: decoding-only batch. Blue: decoding plus one prefill.
- The plotted quantity is **batch execution latency**, not client-visible TTFT or end-to-end request latency.
- **Panel scales differ.** Compare the within-panel mixed/decode-only gap, not apparent slopes or heights across panels.
- The blue horizontal line and slowdown arrows are original source annotations.
- Interpretation: a long prefill can delay other requests' token streams. Chunked prefill, continuous batching and scheduling can mitigate this; do not infer the same penalty in every modern colocated setup.

## Slide 8 — Different batching curves justify separate tuning

`distserve-fig3-throughput.svg` / `.png` reproduce [the Figure 3 SVG](https://arxiv.org/html/2401.09670v2/prefill_decode_throughput.svg).

- 13B LLM, input lengths 128/256/512/1,024; phase-only throughput versus batch size.
- Left panel: prefill. Right panel: decode.
- Read the curve shapes within each panel. Prefill throughput plateaus earlier; decode benefits more from batching in this setup.
- **Input-token and output-token throughput are not interchangeable units of useful work.** Do not compare absolute heights as equivalent serving productivity.
- Compute-dominant prefill and bandwidth-dominant decode are common operating regimes, not universal truths independent of model, batch size, context length and hardware.
- The paper analyzes A100 behavior in sections 2–3, but the captions do not enumerate every kernel, software version or exact model identifier. No current-AKS numeric capacity threshold is inferred.

## Slide 9 — Independent capacity avoids a forced compromise

This page is a native, editable conceptual summary, not measured data. The two demand patterns indicate where to investigate first, not a deterministic scaling rule. Longer prompts can also increase decode KV state and KV-transfer cost, so always check both roles and end-to-end SLOs.

Separate execution pools permit different replica, parallelism, batching and resource choices where supported. The gain must exceed KV transfer, duplicated model-weight residency and added operational costs. No fixed P:D ratio, GPU-saving claim or new KAITO autoscaling availability is implied.

## NVIDIA Dynamo cross-reference

The user-provided [NVIDIA Dynamo disaggregated-serving overview](https://docs.nvidia.com/dynamo/kubernetes/disaggregated-serving/overview) corroborates phase-specific resource bottlenecks, independent worker pools, batching, parallelism and hardware choices. Accessed 2026-10-21; `/dev/` is a moving documentation version. The overview page is text-only, so the two reproduced empirical figures come from the explicitly licensed DistServe paper instead. No NVIDIA performance numbers or imagery are reproduced.

Slide 9 links NVIDIA in its speaker notes and cites it visibly. Compute-bound prefill / bandwidth-bound decode are common regimes, not universal laws. Dynamo's decode-first orchestration, etcd/NATS discovery and NIXL configuration are not presented as KAITO/llm-d implementation behavior.
