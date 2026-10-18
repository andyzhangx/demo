# kaito-llm-d-pd-slides-assets

Mermaid-first diagram assets for `../kaito-llm-d-pd-slides.pptx`.

## Source of truth
- `mermaid/*.mmd`: Mermaid source files for slides 4-11
- `kaito-llm-d-pd-slides.drawio`: legacy reference copy from the earlier diagram iteration (no longer used by the export pipeline)

## Generated outputs
- `slide-04-*.svg` ... `slide-11-*.svg`: vector assets embedded into the PowerPoint deck
- `slide-04-*.png` ... `slide-11-*.png`: legacy raster reference exports

## Regeneration
```bash
cd llm/kaito-llm-d-pd-slides-assets
python3 export_svg_and_patch_pptx.py
```

This regenerates the slide SVG assets from the Mermaid sources and patches `../kaito-llm-d-pd-slides.pptx` so slides 4-11 reference the SVG media.
