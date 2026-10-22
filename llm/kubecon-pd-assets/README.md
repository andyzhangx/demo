# KubeCon NA 2026 — editable PowerPoint redesign

The deck is [`../kubecon-na-2026-pd-disaggregation.pptx`](../kubecon-na-2026-pd-disaggregation.pptx).
The narrative source remains [`../kubecon-na-2026-pd-disaggregation.md`](../kubecon-na-2026-pd-disaggregation.md).

## Design

- Retains the original narrative and English presentation language; now **56 slides**, with the full nine-slide autoscaling section restored, two KAITO annotation implementation/example slides, two P/D adoption decision slides, a concrete integration roadmap, three attributed public-benchmark interpretations, three expanded P/D-motivation slides, and two introductory prefill/decode explainers.
- Slide 14 compares Dynamo, llm-d, AIBrix, KServe, Ray Serve/KubeRay and vLLM Production Stack, with a separate LWS DisaggregatedSet callout. Slide 15 explains why llm-d fits KAITO’s integration goals.
- Diagrams, tables, labels, arrows and the TTFT/efficiency bars are **native PowerPoint objects**. Slides 7–8 and 43 contain attributed original research figures; there are no flattened slide images.
- Blue = platform/routing; teal = prefill/KV data; purple = decode; amber = constraints or recommendations.
- Architecture, resource graph, request sequence, KV-transfer paths, decode-pod layout, scaling loops, workload matrix, and adoption path are rebuilt as diagrams.
- Speaker notes explain conceptual simplifications, deployment-dependent settings, and implementation references.
- Uses common PowerPoint font families: Arial and Courier New. Fonts are not embedded; substitutions can affect layout on systems without those fonts.
- `overview.png` is a rendered contact sheet **for preview only**; it is not used inside the deck.

## Phase-specific performance metrics

Actual slide **5 — One request. Two different performance targets.** maps prefill to **TTFT** (time to first token) and decode to **ITL / TPOT** (inter-token latency / average time per output token). Lower latency is better. Supporting metrics are prefill latency and input tok/s versus aggregate output tok/s; common compute/bandwidth regimes are qualified as **often**, not universal laws.

Both phases affect total response latency, capacity and SLO goodput (requests/s meeting latency targets). Notes distinguish aggregate throughput from per-request speed, vLLM streamed-event ITL from request-level TPOT, frontend/engine from client timing, and latency to the last token from request-close time. They cover queueing, input processing, delivery, P/D transfer, cross-phase interference and KV pressure without inventing performance numbers. See [vLLM metric definitions](https://docs.vllm.ai/en/latest/design/metrics/) and the [companion metric mapping](../kubecon-na-2026-pd-disaggregation.md#slide-3--one-request-two-phases).

This update changes only slide 5 and its notes against baseline `4a6e810856b22ade7025e9d303c99868a531a64b`; the other 55 native slide XML/notes and all three embedded research images are unchanged. All 56 pages were rendered again, the full overview regenerated, and slide 5 visually checked. No new layout issues; the two pre-existing slide-25 text-box margin overruns remain unchanged.

## P/D autoscaling presentation

Slides **27–35** restore the original nine-slide section from commit `b1a2a23`, preserving its content, native shapes and speaker notes (only pagination changes): role saturation, existing KEDA/InferenceSet capability, independent loops, service policy boundary, control architecture, native gauges, policy table, operational safeguards and derived signals.

Two additional slides connect those concepts to the [role-aware autoscaling design](../kaito-llm-d/kaito-role-aware-autoscaling-for-pd.md):

- **36 — KAITO annotation implementation:** proposed `autoscaling.kaito.sh/roles` → validated MRI adapter → each child `InferenceSet.metadata.annotations` → per-role ScaledObject → KEDA/HPA → child scale API. Shows the exact generated prefill annotations and the required MRI-child opt-in.
- **37 — Concrete policy example:** prefill waiting-request thresholds 8/1 and range 1–8; decode running-request thresholds 24/4 and range 2–16. `replicas: null` releases MRI replica enforcement. With waiting=12 and running=12, prefill requests scale-up while decode holds; decode can scale independently when running rises above 24. These are hypothetical decisions, not measured scaling results.

The [full proposed YAML example](../kaito-llm-d/examples/proposed-pd-autoscaling-annotations.yaml) matches the design and slide excerpt. It is **not a currently deployable MRI autoscaling API**: it requires the MRI policy adapter, explicit scaler support for opted-in MRI children, validation, metric wiring, ownership and safe handoff. Existing annotations on MRI alone do not enable this behavior. `AND` combines metrics within a role, not decisions across prefill and decode.

The autoscaling content remains editable. Source-backed notes preserve implementation and metric-availability caveats without numbered rollout phases. Example thresholds, model and SKUs are not deployment or capacity recommendations.

## When to use P/D—and when not to

Slides **49–50** expand [Slide 34 of the companion Markdown](../kubecon-na-2026-pd-disaggregation.md#slide-34--when-to-use-pd-and-when-not-to):

- **49 — Decision matrix:** role bottleneck/scaling divergence versus KV-transfer cost. Different role needs plus cheap transfer is the strongest candidate; similar roles plus expensive transfer favors aggregated serving. Divergent roles with costly transfer should improve topology first; cheap transfer alone does not justify P/D.
- **50 — Workload/topology scenarios:** keep aggregated serving for simple, similar-role workloads; benchmark P/D for divergent role capacity with a suitable transfer path; improve locality/transport before scaling a transfer-limited design. Single-node trials can simplify the first experiment; cross-node transfer must be measured, not assumed slow.

These are qualitative selection guidelines, not benchmark results. Compare client-visible TTFT/ITL, SLO goodput, KV-transfer tails and total cost using the same model, workload and budget.

## What’s next for KAITO + llm-d

Slide **54** expands [Slide 36 of the companion Markdown](../kubecon-na-2026-pd-disaggregation.md#slide-36--whats-next-for-kaito--llm-d) into three integration directions:

- **Near term:** KV-event-based prefix-cache routing; tiered cache across HBM, CPU RAM and optional filesystem tiers.
- **Next topology:** E/P/D (Encode / Prefill / Decode).
- **Larger-scale systems:** Wide Expert Parallelism and cross-node transport/communication optimization.

Speculative decoding is omitted from future work because it is already implemented, as confirmed by the presenter. Both roadmap mentions in the companion Markdown are updated accordingly. These are KAITO integration directions, not release-date commitments or claims that the underlying llm-d/runtime features are all new.

## Public benchmark results

Slides **42–44** interpret one external [vLLM / AMD MORI-IO study](https://vllm.ai/blog/2026-04-07-moriio-kv-connector), using Qwen3-235B-A22B-FP8 on eight MI300X GPUs with fixed 2K-input/1K-output requests:

- **42 — TTFT:** native bars computed from published Figure 3 observations. P/D is slower in this setup; the slide does not fabricate a prompt-length-dependent TTFT gain.
- **43 — Useful throughput under load:** original Figure 4 SLO-attainment curve, with the 8 req/s region highlighted. This is SLO attainment, not an absolute token-throughput axis; fixed-length concurrent phases are not a heterogeneous mixed-traffic benchmark.
- **44 — Efficiency proxy:** native bars for normalized SLO passes/GPU, at the same eight-GPU budget. No GPU busy-utilization, asymmetric-traffic or fewer-GPU result is claimed.

[Benchmark sources, literal data, formulas, scope and source-data discrepancy](benchmarks/README.md) are included. Derived values consistently use the pinned Figure 3 arrays (29/100 vs 73/100 passes), not the differing static Table 3 values (28/100 vs 70/100). These are three views of one external study, **not KAITO measurements** or three independent experiments.

## Accuracy boundaries

- Slides 38–41 are a **local KAITO evaluation plan**, not benchmark results. Slides 42–44 separately identify external public results; no local KAITO measurements are available. There are no invented performance percentages, synthetic result curves, or `[X]` / `[Y]` result placeholders.
- Slide 28 covers existing KEDA → InferenceSet scaling; slide 29 illustrates independent role loops. Slides 27–35 explain control and policy **design patterns**. Slides 36–37 explicitly label MRI annotation integration as **proposed**, not a released API. Derived recording rules require aggregation and collection; they are not native vLLM metric outputs.
- Slides 14–15 acknowledge existing declarative APIs, including DynamoGraphDeployment, StormService/RoleSet, LLMInferenceService and DisaggregatedSet. “Best fit” is scoped to extending KAITO, not a claim of universal platform superiority or measured performance. Official references and current alpha/runtime/gateway limitations are included in speaker notes.
- Request/control messages and KV-tensor payloads are separate. The KV payload moves from prefill to decode even when the transport operation is a decode-initiated read.
- Diagram arrows illustrate logical paths, not exact timings, port values, or strict Kubernetes owner references unless identified as such.
- Readiness is a logical serving contract, not a claim that all processes must start serially.

## Rebuild

Requires Python 3 and `python-pptx==1.0.2`:

```bash
python -m venv .venv-slides
. .venv-slides/bin/activate
pip install python-pptx==1.0.2
python llm/generate_kubecon_pd_deck.py
```

The generator resolves paths relative to itself and replaces only the PPTX. It reads the checked-in benchmark JSON and source figures under `benchmarks/` and `motivation/`, requires no network access, and does not modify the Markdown. Foundation word sequences are constants in the generator; the archival `tokenization/` files are not used. Manual PowerPoint edits are possible, but rerunning the generator overwrites them; update the generator to keep reproducible changes.

## Validation

The redesign was exported with LibreOffice 25.8 and checked for:

- 56 slides and 56 non-empty speaker-note pages;
- the other 54 slides and their notes preserved byte-for-byte in native XML when updating foundation slides 3–4;
- exact equivalence between the YAML example, source design, slide policy and generated prefill projection;
- valid OOXML ZIP/XML and exactly three embedded pictures: the existing public Figure 4 plus two mechanical DistServe SVG renders;
- exact source-array equivalence and reproducible TTFT percentiles, SLO-pass counts and normalized proxy;
- visual review of the two foundation pages and updated phase-metrics slide 5;
- slide geometry and text-box overlap;
- rendered text presence and text bounds on every slide (no new layout issues; two pre-existing slide-25 text-box margin overruns remain unchanged);
- explicit distinction between existing capabilities, proposals, and unmeasured results.

This is a LibreOffice rendering check, not a Microsoft PowerPoint application test. Preview the final deck on the presentation machine before the talk, particularly if font substitution occurs.

## Implementation references

- [KAITO prefill/decode disaggregation](https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation)
- [KAITO KEDA autoscaling for InferenceSet](https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference)
- [Role-aware P/D autoscaling design](../kaito-llm-d/kaito-role-aware-autoscaling-for-pd.md)
- [vLLM native production metrics](https://docs.vllm.ai/en/stable/usage/metrics/)
- [llm-d architecture](https://llm-d.ai/docs/architecture)
- [Dynamo Kubernetes deployment](https://docs.nvidia.com/dynamo/v1.1.0/getting-started/kubernetes-deployment)
- [AIBrix P/D routing](https://aibrix.readthedocs.io/latest/features/gateway-routing/pd-disaggregation.html) and [StormService](https://aibrix.readthedocs.io/latest/designs/aibrix-stormservice.html)
- [KServe LLMInferenceService](https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview)
- [Ray Serve P/D](https://docs.ray.io/en/latest/serve/llm/user-guides/prefill-decode.html)
- [vLLM Production Stack P/D](https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/disaggregated-prefill.html)
- [LWS DisaggregatedSet](https://lws.sigs.k8s.io/docs/concepts/disaggregatedset/)

## Prefill and decode foundations

Actual slides **3–4** explain a standard cached decoder-only Transformer before discussing disaggregation. All diagrams, table cells, arrows and labels remain native editable PowerPoint objects.

**Exact prompt:** `What does Kubernetes do?`

**Exact illustrative output:** `Kubernetes helps teams deploy and scale applications.`

#### Simple word-level teaching example

**Illustrative word-level tokens; not a real model tokenizer.** Assume one complete English word per token for this explanation; punctuation occupies a separate position. Spaces separate the displayed words and are not extra positions. This keeps “Kubernetes” intact so the audience can focus on prefill and decode rather than tokenization.

- Prompt positions: `What | does | Kubernetes | do | ?` (four words plus punctuation).
- Output positions: `Kubernetes | helps | teams | deploy | and | scale | applications | .` (seven words plus punctuation).

These are schematic tokens, **not actual Qwen tokens or a claim that typical production LLMs use word-level tokenization**. Real tokenizers can split words into subwords and handle whitespace/punctuation differently. The sentence is authored for teaching; **no tokenizer or model inference was run** for this example. The generator defines these word sequences directly and does not load a tokenizer manifest.

#### Phase and cache semantics

1. **Prefill:** process the 5 uncached prompt positions with a causal mask, build per-layer attention keys and values, then use final-position logits to select y1 = `Kubernetes` along this illustrative path. Immediately after selection, the cache contains prompt KV, **not** K/V for y1.
2. **Decode:** consume a selected token with past KV, append K/V for that consumed token, and select the next:

   | Step | Consume | Append to per-layer KV | Select next |
   | --- | --- | --- | --- |
   | 1 | y1 = Kubernetes | K/V for y1 | y2 = helps |
   | 2 | y2 = helps | K/V for y2 | y3 = teams |
   | 3 | y3 = teams | K/V for y3 | y4 = deploy |
   | 4 | y4 = deploy | K/V for y4 | y5 = and |
   | 5 | y5 = and | K/V for y5 | y6 = scale |
   | 6 | y6 = scale | K/V for y6 | y7 = applications |

   After row 6, output KV covers y1–y6; y7 is selected but not consumed/cached. The omitted final step consumes y7 = `applications` and selects y8 = `.`. If generation continued, consuming the period could select EOS. EOS normally is hidden and need not be consumed into KV when stopping; output limits and stop strings are alternatives. No EOS ID or actual model decision is asserted.
3. **Client timing:** the first six word arrivals illustrate request → first token (**TTFT**, the first word in this schematic) and five successive **ITL** gaps. Later arrivals are omitted; the timeline is not to scale. In real systems the first token need not be a complete word. Queueing, transport, detokenization and buffering affect observed timing, and stream chunks can group multiple tokens.

KV reuse avoids recomputing old K/V, but full-context attention still reads cached history. Notes qualify chunked prefill, prefix caching, static/sliding-window caches, ordinary autoregressive versus speculative decoding, and worker boundaries. These phase definitions do not assign first-token selection or delivery to a particular worker.

Reference: [Hugging Face Transformers — How caching works](https://huggingface.co/docs/transformers/en/cache_explanation).

### Archival tokenizer reference (not used by these slides)

The prior real-Qwen [`manifest.json`](tokenization/manifest.json) and [`reproduce.py`](tokenization/reproduce.py) are retained unchanged as an optional historical reference. Their subword pieces, token IDs and cache-step mapping describe the previous slides, **not the current word-level illustration**. See the [archive README](tokenization/README.md) for provenance and optional reproduction instructions. No tokenizer dependency is needed to build the deck.

Only actual slides 3–4 were updated against baseline `93bf4b0e9e8ce88e36ec87f11e7e8f23ab27d348`. The other 54 native slide XML and speaker-note parts remain unchanged. The overview was regenerated from all 56 rendered slides. Existing motivation slides remain **7–9**.
