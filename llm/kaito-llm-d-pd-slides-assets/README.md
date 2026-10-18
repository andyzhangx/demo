# kaito-llm-d-pd-slides-assets

Mixed D2 + Mermaid diagram assets for `../kaito-llm-d-pd-slides.pptx`.

## Source of truth
- `d2/*.d2`: D2 source files for key visual slides (currently 4 / 7 / 8)
- `mermaid/*.mmd`: Mermaid source files for the structure / logic slides
- `kaito-llm-d-pd-slides.drawio`: legacy reference copy from an earlier iteration (not used by the active export pipeline)

## Generated outputs
- `slide-04-*.svg` ... `slide-11-*.svg`: vector assets embedded into the PowerPoint deck
- `slide-04-*.png` ... `slide-11-*.png`: legacy raster reference exports

## Regeneration
```bash
cd llm/kaito-llm-d-pd-slides-assets
python3 export_svg_and_patch_pptx.py
```

This regenerates the slide SVG assets from the mixed D2 + Mermaid sources and patches `../kaito-llm-d-pd-slides.pptx` so slides 4-11 reference the SVG media.
