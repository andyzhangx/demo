# KubeCon NA 2026 — editable PowerPoint redesign

The deck is [`../kubecon-na-2026-pd-disaggregation.pptx`](../kubecon-na-2026-pd-disaggregation.pptx).
The narrative source remains [`../kubecon-na-2026-pd-disaggregation.md`](../kubecon-na-2026-pd-disaggregation.md).

## Design

- Retains the original narrative and English presentation language; now **38 slides**, with two ecosystem/integration slides after original slide 8 and a concise four-slide autoscaling section.
- New slide 9 compares Dynamo, llm-d, AIBrix, KServe, Ray Serve/KubeRay and vLLM Production Stack, with a separate LWS DisaggregatedSet callout. New slide 10 explains why llm-d fits KAITO’s integration goals.
- All diagrams, tables, labels, and arrows are **native PowerPoint objects**. There are no embedded raster/SVG diagrams and no flattened slide images.
- Blue = platform/routing; teal = prefill/KV data; purple = decode; amber = constraints or recommendations.
- Architecture, resource graph, request sequence, KV-transfer paths, decode-pod layout, scaling loops, workload matrix, and adoption path are rebuilt as diagrams.
- Speaker notes explain conceptual simplifications, deployment-dependent settings, and implementation references.
- Uses common PowerPoint font families: Arial and Courier New. Fonts are not embedded; substitutions can affect layout on systems without those fonts.
- `overview.png` is a rendered contact sheet **for preview only**; it is not used inside the deck.

## P/D autoscaling presentation

Slides **22–25** condense autoscaling into four ideas based on the [role-aware autoscaling design](../kaito-llm-d/kaito-role-aware-autoscaling-for-pd.md):

1. Native vLLM waiting/running gauges and illustrative scaling decisions.
2. Two independent control loops for one logical P/D service.
3. Single-writer ownership, valid metric data, and safe scale-down/handoff.
4. Derived KV, latency and throughput signals and their decision-support limits.

Repeated architecture, API and policy-table slides have been removed; essential details remain in speaker notes.

The slides focus on external concepts rather than rollout phases or KAITO-specific policy encoding. All content remains editable, with source-backed speaker notes preserving implementation and metric-availability caveats. The underlying design document retains its implementation plan; the talk does not present that plan as a released capability. Example thresholds are not production recommendations.

## Accuracy boundaries

- Slides 26–29 are an **evaluation plan**, not benchmark results. The source does not contain measured data. There are no invented performance percentages, synthetic result curves, or `[X]` / `[Y]` result placeholders.
- Slide 23 uses the existing KEDA → InferenceSet integration to illustrate two role-specific loops. Slides 22–25 explain control and policy **design patterns**, not a new available MRI API schema. Derived recording rules require aggregation and collection; they are not native vLLM metric outputs.
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

- 38 slides and 38 non-empty speaker-note pages;
- valid OOXML ZIP/XML and no embedded media;
- slide geometry and text-box overlap;
- rendered text presence and text bounds on every slide;
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
