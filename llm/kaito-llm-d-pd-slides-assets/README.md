# kaito-llm-d-pd-slides-assets

Mixed-source diagram assets for `../kaito-llm-d-pd-slides.pptx`.

## Source of truth
- `kaito-llm-d-pd-slides.drawio`: main visual / architecture diagrams
  - slide 4: end-to-end architecture
  - slide 7: request execution flow
  - slide 8: decode-side sidecar placement
- `mermaid/*.mmd`: structure / logic diagrams
  - slide 5: MultiRoleInference topology
  - slide 6: KAITO-generated resources
  - slide 9: runtime contracts
  - slide 10: KAITO vs llm-d
  - slide 11: ownership boundary

## Generated outputs
- `slide-04-*.svg` ... `slide-11-*.svg`: vector assets embedded into the PowerPoint deck
- `slide-04-*.png` ... `slide-11-*.png`: legacy raster reference exports

## Regeneration
```bash
cd llm/kaito-llm-d-pd-slides-assets
python3 export_svg_and_patch_pptx.py
```

This regenerates the slide SVG assets from the mixed draw.io + Mermaid sources and patches `../kaito-llm-d-pd-slides.pptx` so slides 4-11 reference the SVG media.
