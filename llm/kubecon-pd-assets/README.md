# KubeCon NA 2026 — editable PowerPoint redesign

The deck is [`../kubecon-na-2026-pd-disaggregation.pptx`](../kubecon-na-2026-pd-disaggregation.pptx).
The narrative source remains [`../kubecon-na-2026-pd-disaggregation.md`](../kubecon-na-2026-pd-disaggregation.md).

## Design

- Retains the original narrative and English presentation language; now **48 slides**, with the full nine-slide autoscaling section restored, two KAITO annotation implementation/example slides, two P/D adoption decision slides, and a concrete integration roadmap.
- New slide 9 compares Dynamo, llm-d, AIBrix, KServe, Ray Serve/KubeRay and vLLM Production Stack, with a separate LWS DisaggregatedSet callout. New slide 10 explains why llm-d fits KAITO’s integration goals.
- All diagrams, tables, labels, and arrows are **native PowerPoint objects**. There are no embedded raster/SVG diagrams and no flattened slide images.
- Blue = platform/routing; teal = prefill/KV data; purple = decode; amber = constraints or recommendations.
- Architecture, resource graph, request sequence, KV-transfer paths, decode-pod layout, scaling loops, workload matrix, and adoption path are rebuilt as diagrams.
- Speaker notes explain conceptual simplifications, deployment-dependent settings, and implementation references.
- Uses common PowerPoint font families: Arial and Courier New. Fonts are not embedded; substitutions can affect layout on systems without those fonts.
- `overview.png` is a rendered contact sheet **for preview only**; it is not used inside the deck.

## P/D autoscaling presentation

Slides **22–30** restore the original nine-slide section from commit `b1a2a23`, preserving its content, native shapes and speaker notes (only pagination changes): role saturation, existing KEDA/InferenceSet capability, independent loops, service policy boundary, control architecture, native gauges, policy table, operational safeguards and derived signals.

Two additional slides connect those concepts to the [role-aware autoscaling design](../kaito-llm-d/kaito-role-aware-autoscaling-for-pd.md):

- **31 — KAITO annotation implementation:** proposed `autoscaling.kaito.sh/roles` → validated MRI adapter → each child `InferenceSet.metadata.annotations` → per-role ScaledObject → KEDA/HPA → child scale API. Shows the exact generated prefill annotations and the required MRI-child opt-in.
- **32 — Concrete policy example:** prefill waiting-request thresholds 8/1 and range 1–8; decode running-request thresholds 24/4 and range 2–16. `replicas: null` releases MRI replica enforcement. With waiting=12 and running=12, prefill requests scale-up while decode holds; decode can scale independently when running rises above 24. These are hypothetical decisions, not measured scaling results.

The [full proposed YAML example](../kaito-llm-d/examples/proposed-pd-autoscaling-annotations.yaml) matches the design and slide excerpt. It is **not a currently deployable MRI autoscaling API**: it requires the MRI policy adapter, explicit scaler support for opted-in MRI children, validation, metric wiring, ownership and safe handoff. Existing annotations on MRI alone do not enable this behavior. `AND` combines metrics within a role, not decisions across prefill and decode.

All content remains editable. Source-backed notes preserve implementation and metric-availability caveats without numbered rollout phases. Example thresholds, model and SKUs are not deployment or capacity recommendations.

## When to use P/D—and when not to

Slides **41–42** expand [Slide 34 of the companion Markdown](../kubecon-na-2026-pd-disaggregation.md#slide-34--when-to-use-pd-and-when-not-to):

- **41 — Decision matrix:** role bottleneck/scaling divergence versus KV-transfer cost. Different role needs plus cheap transfer is the strongest candidate; similar roles plus expensive transfer favors aggregated serving. Divergent roles with costly transfer should improve topology first; cheap transfer alone does not justify P/D.
- **42 — Workload/topology scenarios:** keep aggregated serving for simple, similar-role workloads; benchmark P/D for divergent role capacity with a suitable transfer path; improve locality/transport before scaling a transfer-limited design. Single-node trials can simplify the first experiment; cross-node transfer must be measured, not assumed slow.

These are qualitative selection guidelines, not benchmark results. Compare client-visible TTFT/ITL, SLO goodput, KV-transfer tails and total cost using the same model, workload and budget.

## What’s next for KAITO + llm-d

Slide **46** expands [Slide 36 of the companion Markdown](../kubecon-na-2026-pd-disaggregation.md#slide-36--whats-next-for-kaito--llm-d) into three integration directions:

- **Near term:** KV-event-based prefix-cache routing; tiered cache across HBM, CPU RAM and optional filesystem tiers.
- **Next topology:** E/P/D (Encode / Prefill / Decode).
- **Larger-scale systems:** Wide Expert Parallelism and cross-node transport/communication optimization.

Speculative decoding is omitted from future work because it is already implemented, as confirmed by the presenter. Both roadmap mentions in the companion Markdown are updated accordingly. These are KAITO integration directions, not release-date commitments or claims that the underlying llm-d/runtime features are all new.

## Accuracy boundaries

- Slides 33–36 are an **evaluation plan**, not benchmark results. The source does not contain measured data. There are no invented performance percentages, synthetic result curves, or `[X]` / `[Y]` result placeholders.
- Slide 23 covers existing KEDA → InferenceSet scaling; slide 24 illustrates independent role loops. Slides 22–30 explain control and policy **design patterns**. Slides 31–32 explicitly label MRI annotation integration as **proposed**, not a released API. Derived recording rules require aggregation and collection; they are not native vLLM metric outputs.
- Slides 9–10 acknowledge existing declarative APIs, including DynamoGraphDeployment, StormService/RoleSet, LLMInferenceService and DisaggregatedSet. “Best fit” is scoped to extending KAITO, not a claim of universal platform superiority or measured performance. Official references and current alpha/runtime/gateway limitations are included in speaker notes.
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

The generator resolves paths relative to itself and replaces only the PPTX. It does not depend on external images or modify the Markdown. Manual PowerPoint edits are possible, but rerunning the generator overwrites them; update the generator to keep reproducible changes.

## Validation

The redesign was exported with LibreOffice 25.8 and checked for:

- 48 slides and 48 non-empty speaker-note pages;
- all 47 slides from the previous deck preserved, except footer pagination;
- all 43 slides from the pre-condensation baseline preserved, except footer pagination;
- exact equivalence between the YAML example, source design, slide policy and generated prefill projection;
- valid OOXML ZIP/XML and no embedded media;
- slide geometry and text-box overlap;
- rendered text presence and text bounds on every slide (no new layout issues; two pre-existing slide-20 text-box margin overruns remain unchanged);
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
