# kaito-llm-d-pd-slides-assets

Draw.io source-of-truth assets for the diagram-heavy slides in `../kaito-llm-d-pd-slides.pptx`.

## Contents
- `kaito-llm-d-pd-slides.drawio`: editable diagrams.net source with one page per slide diagram
- `slide-04-*.svg` ... `slide-11-*.svg`: vector exports generated from the draw.io pages and embedded into the PowerPoint deck
- `slide-04-*.png` ... `slide-11-*.png`: raster fallback/reference exports
- `export_svg_and_patch_pptx.py`: exports SVGs from the draw.io XML and rewires the PPTX media relationships to those SVGs

## Regeneration
Run:

```bash
cd llm/kaito-llm-d-pd-slides-assets
python3 export_svg_and_patch_pptx.py
```

This regenerates the slide SVG assets and patches `../kaito-llm-d-pd-slides.pptx` so slides 4-11 reference the SVG media instead of the PNG media.

## Slide mapping
- Slide 4: End-to-End Architecture
- Slide 5: One MultiRoleInference Object Describes the Topology
- Slide 6: What KAITO Automatically Generates for P/D
- Slide 7: How a P/D Request Actually Executes
- Slide 8: Why the Routing Sidecar Lives on Decode Pods
- Slide 9: The Runtime Contracts That Make P/D Actually Work
- Slide 10: KAITO Does Not Replace llm-d — It Operationalizes It
- Slide 11: What Users Manage vs. What the Platform Manages
