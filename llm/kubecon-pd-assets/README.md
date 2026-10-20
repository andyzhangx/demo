# KubeCon NA 2026 — editable PowerPoint redesign

The deck is [`../kubecon-na-2026-pd-disaggregation.pptx`](../kubecon-na-2026-pd-disaggregation.pptx).
The narrative source remains [`../kubecon-na-2026-pd-disaggregation.md`](../kubecon-na-2026-pd-disaggregation.md).

## Design

- Retains the 36-slide narrative and English presentation language.
- All diagrams, tables, labels, and arrows are **native PowerPoint objects**. There are no embedded raster/SVG diagrams and no flattened slide images.
- Blue = platform/routing; teal = prefill/KV data; purple = decode; amber = constraints or recommendations.
- Architecture, resource graph, request sequence, KV-transfer paths, decode-pod layout, scaling loops, workload matrix, and adoption path are rebuilt as diagrams.
- Speaker notes explain conceptual simplifications, deployment-dependent settings, and implementation references.
- Uses common PowerPoint font families: Arial and Courier New. Fonts are not embedded; substitutions can affect layout on systems without those fonts.
- `overview.png` is a rendered contact sheet **for preview only**; it is not used inside the deck.

## Accuracy boundaries

- Slides 24–27 are an **evaluation plan**, not benchmark results. The source does not contain measured data. There are no invented performance percentages, synthetic result curves, or `[X]` / `[Y]` result placeholders.
- Slide 21 documents the existing KEDA → InferenceSet integration. Slide 23 explicitly labels MRI-level per-role scaling policy as a **recommendation**, not an available API schema.
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

- 36 slides and 36 non-empty speaker-note pages;
- valid OOXML ZIP/XML and no embedded media;
- slide geometry and text-box overlap;
- rendered text presence and text bounds on every slide;
- explicit distinction between existing capabilities, proposals, and unmeasured results.

This is a LibreOffice rendering check, not a Microsoft PowerPoint application test. Preview the final deck on the presentation machine before the talk, particularly if font substitution occurs.

## Implementation references

- [KAITO prefill/decode disaggregation](https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation)
- [KAITO KEDA autoscaling for InferenceSet](https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference)
