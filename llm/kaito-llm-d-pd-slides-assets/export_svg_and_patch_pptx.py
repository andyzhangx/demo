#!/usr/bin/env python3
from __future__ import annotations

import html
import math
import shutil
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).resolve().parent
DRAWIO_PATH = ASSET_DIR / "kaito-llm-d-pd-slides.drawio"
PPTX_PATH = REPO_ROOT / "llm" / "kaito-llm-d-pd-slides.pptx"
NS_CT = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
NS_REL = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
SLIDE_TO_BASENAME = {
    4: "slide-04-end-to-end-architecture",
    5: "slide-05-multiroleinference-topology",
    6: "slide-06-kaito-generated-resources",
    7: "slide-07-request-execution-flow",
    8: "slide-08-decode-sidecar-placement",
    9: "slide-09-runtime-contracts",
    10: "slide-10-kaito-vs-llmd",
    11: "slide-11-ownership-boundary",
}
ET.register_namespace("", NS_CT["ct"])
ET.register_namespace("", NS_REL["rel"])


def parse_style(style: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in (style or "").split(";"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def xml_text_to_plain(value: str | None) -> str:
    if not value:
        return ""
    return html.unescape(value).replace("\xa0", " ")


def wrap_text(text: str, width: float, font_size: int) -> list[str]:
    if not text:
        return []
    max_chars = max(8, int(width / max(font_size * 0.58, 1)))
    lines: list[str] = []
    for raw_line in text.splitlines() or [text]:
        words = raw_line.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for word in words[1:]:
            trial = f"{cur} {word}"
            if len(trial) <= max_chars:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def svg_text_block(x: float, y: float, w: float, h: float, text: str, font_size: int, color: str, align: str, bold: bool) -> str:
    lines = wrap_text(text, w - 20, font_size)
    if not lines:
        return ""
    line_height = font_size * 1.25
    total_h = line_height * len(lines)
    start_y = y + (h - total_h) / 2 + font_size
    anchor = {"center": "middle", "right": "end", "left": "start"}.get(align, "middle")
    x_text = {"center": x + w / 2, "right": x + w - 12, "left": x + 12}.get(align, x + w / 2)
    weight = "700" if bold else "400"
    spans = []
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else line_height
        spans.append(
            f'<tspan x="{x_text:.1f}" dy="{dy:.1f}">{html.escape(line)}</tspan>'
        )
    return (
        f'<text x="{x_text:.1f}" y="{start_y:.1f}" text-anchor="{anchor}" '
        f'font-family="Aptos, Arial, sans-serif" font-size="{font_size}" '
        f'font-weight="{weight}" fill="{color}">'
        + "".join(spans)
        + "</text>"
    )


def choose_anchor(src: tuple[float, float, float, float], dst: tuple[float, float, float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    sx, sy, sw, sh = src
    tx, ty, tw, th = dst
    scx, scy = sx + sw / 2, sy + sh / 2
    tcx, tcy = tx + tw / 2, ty + th / 2
    dx, dy = tcx - scx, tcy - scy
    if abs(dx) >= abs(dy):
        start = (sx + sw, scy) if dx >= 0 else (sx, scy)
        end = (tx, tcy) if dx >= 0 else (tx + tw, tcy)
    else:
        start = (scx, sy + sh) if dy >= 0 else (scx, sy)
        end = (tcx, ty) if dy >= 0 else (tcx, ty + th)
    return start, end


def orthogonal_path(start: tuple[float, float], end: tuple[float, float]) -> str:
    sx, sy = start
    ex, ey = end
    if abs(sx - ex) < 1 or abs(sy - ey) < 1:
        return f"M {sx:.1f} {sy:.1f} L {ex:.1f} {ey:.1f}"
    if abs(sx - ex) >= abs(sy - ey):
        mx = (sx + ex) / 2
        return f"M {sx:.1f} {sy:.1f} L {mx:.1f} {sy:.1f} L {mx:.1f} {ey:.1f} L {ex:.1f} {ey:.1f}"
    my = (sy + ey) / 2
    return f"M {sx:.1f} {sy:.1f} L {sx:.1f} {my:.1f} L {ex:.1f} {my:.1f} L {ex:.1f} {ey:.1f}"


def parse_diagrams() -> list[tuple[str, float, float, list[dict], list[dict]]]:
    root = ET.parse(DRAWIO_PATH).getroot()
    pages = []
    for diagram in root.findall("diagram"):
        name = diagram.attrib.get("name", "diagram")
        model = ET.fromstring(diagram.text or "")
        model_root = model.find("root")
        if model_root is None:
            continue
        width = float(model.attrib.get("pageWidth", "2200"))
        height = float(model.attrib.get("pageHeight", "1000"))
        vertices: list[dict] = []
        edges: list[dict] = []
        for cell in model_root.findall("mxCell"):
            attrs = cell.attrib
            geom = cell.find("mxGeometry")
            if attrs.get("vertex") == "1" and geom is not None:
                style = parse_style(attrs.get("style", ""))
                vertices.append(
                    {
                        "id": attrs["id"],
                        "text": xml_text_to_plain(attrs.get("value")),
                        "style": style,
                        "x": float(geom.attrib.get("x", "0")),
                        "y": float(geom.attrib.get("y", "0")),
                        "w": float(geom.attrib.get("width", "0")),
                        "h": float(geom.attrib.get("height", "0")),
                    }
                )
            elif attrs.get("edge") == "1":
                style = parse_style(attrs.get("style", ""))
                points = []
                if geom is not None:
                    for arr in geom.findall("Array"):
                        if arr.attrib.get("as") == "points":
                            for pt in arr.findall("mxPoint"):
                                points.append((float(pt.attrib["x"]), float(pt.attrib["y"])))
                edges.append(
                    {
                        "id": attrs["id"],
                        "source": attrs.get("source"),
                        "target": attrs.get("target"),
                        "style": style,
                        "points": points,
                    }
                )
        pages.append((name, width, height, vertices, edges))
    return pages


def render_svg(name: str, width: float, height: float, vertices: list[dict], edges: list[dict]) -> str:
    by_id = {v["id"]: v for v in vertices}
    marker_defs: dict[str, str] = {}
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        '<defs>',
    ]
    for edge in edges:
        stroke = edge["style"].get("strokeColor", "#64748B")
        mid = marker_defs.get(stroke)
        if mid is None:
            mid = f"arrow{len(marker_defs)+1}"
            marker_defs[stroke] = mid
            parts.append(
                f'<marker id="{mid}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">'
                f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{stroke}" /></marker>'
            )
    parts.append('</defs>')
    parts.append(f'<rect x="0" y="0" width="{int(width)}" height="{int(height)}" fill="#FFFFFF"/>')
    for edge in edges:
        src = by_id.get(edge.get("source", ""))
        dst = by_id.get(edge.get("target", ""))
        if not src or not dst:
            continue
        start, end = choose_anchor((src["x"], src["y"], src["w"], src["h"]), (dst["x"], dst["y"], dst["w"], dst["h"]))
        d = orthogonal_path(start, end)
        stroke = edge["style"].get("strokeColor", "#64748B")
        stroke_width = float(edge["style"].get("strokeWidth", "4"))
        marker = marker_defs[stroke]
        parts.append(
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}" marker-end="url(#{marker})" />'
        )
    for v in vertices:
        style = v["style"]
        fill = style.get("fillColor", "#FFFFFF")
        stroke = style.get("strokeColor", "#CBD5E1")
        font_color = style.get("fontColor", "#111827")
        font_size = int(float(style.get("fontSize", "18")))
        rounded = style.get("rounded") == "1"
        bold = style.get("fontStyle") == "1"
        align = style.get("align", "center")
        rx = 18 if rounded else 0
        parts.append(
            f'<rect x="{v["x"]:.1f}" y="{v["y"]:.1f}" width="{v["w"]:.1f}" height="{v["h"]:.1f}" '
            f'rx="{rx}" ry="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="3" />'
        )
        if v["text"]:
            parts.append(svg_text_block(v["x"], v["y"], v["w"], v["h"], v["text"], font_size, font_color, align, bold))
    parts.append('</svg>')
    return "\n".join(parts)


def export_svgs() -> None:
    diagrams = parse_diagrams()
    for slide_no, basename in SLIDE_TO_BASENAME.items():
        diagram_name = next((name for name, *_ in diagrams if name.startswith(f"Slide {slide_no} ")), None)
        if diagram_name is None:
            raise RuntimeError(f"missing draw.io page for slide {slide_no}")
        for name, width, height, vertices, edges in diagrams:
            if name == diagram_name:
                svg = render_svg(name, width, height, vertices, edges)
                (ASSET_DIR / f"{basename}.svg").write_text(svg)
                break


def patch_pptx_to_svg() -> None:
    with tempfile.TemporaryDirectory() as td:
        tempdir = Path(td)
        with zipfile.ZipFile(PPTX_PATH, "r") as zf:
            zf.extractall(tempdir)
        content_types = tempdir / "[Content_Types].xml"
        ct_tree = ET.parse(content_types)
        ct_root = ct_tree.getroot()
        has_svg = any(el.attrib.get("Extension") == "svg" for el in ct_root.findall("ct:Default", NS_CT))
        if not has_svg:
            ET.SubElement(
                ct_root,
                f'{{{NS_CT["ct"]}}}Default',
                Extension="svg",
                ContentType="image/svg+xml",
            )
            ct_tree.write(content_types, encoding="utf-8", xml_declaration=True)

        for slide_no, basename in SLIDE_TO_BASENAME.items():
            rel_path = tempdir / "ppt" / "slides" / "_rels" / f"slide{slide_no}.xml.rels"
            rel_tree = ET.parse(rel_path)
            rel_root = rel_tree.getroot()
            image_rels = [
                el
                for el in rel_root.findall("rel:Relationship", NS_REL)
                if el.attrib.get("Type") == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
            ]
            if len(image_rels) != 1:
                raise RuntimeError(f"expected exactly one image rel for slide {slide_no}, got {len(image_rels)}")
            target_name = f"{basename}.svg"
            image_rels[0].attrib["Target"] = f"../media/{target_name}"
            rel_tree.write(rel_path, encoding="utf-8", xml_declaration=True)
            shutil.copy2(ASSET_DIR / target_name, tempdir / "ppt" / "media" / target_name)

        rebuilt = tempdir / "rebuilt.pptx"
        with zipfile.ZipFile(rebuilt, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(tempdir.rglob("*")):
                if path.is_dir() or path == rebuilt:
                    continue
                zf.write(path, path.relative_to(tempdir).as_posix())
        shutil.copy2(rebuilt, PPTX_PATH)


def update_readme() -> None:
    readme = ASSET_DIR / "README.md"
    readme.write_text(
        "# kaito-llm-d-pd-slides-assets\n\n"
        "Draw.io source-of-truth assets for the diagram-heavy slides in `../kaito-llm-d-pd-slides.pptx`.\n\n"
        "## Contents\n"
        "- `kaito-llm-d-pd-slides.drawio`: editable diagrams.net source with one page per slide diagram\n"
        "- `slide-04-*.svg` ... `slide-11-*.svg`: vector exports generated from the draw.io pages and embedded into the PowerPoint deck\n"
        "- `slide-04-*.png` ... `slide-11-*.png`: raster fallback/reference exports\n"
        "- `export_svg_and_patch_pptx.py`: exports SVGs from the draw.io XML and rewires the PPTX media relationships to those SVGs\n\n"
        "## Regeneration\n"
        "Run:\n\n"
        "```bash\n"
        "cd llm/kaito-llm-d-pd-slides-assets\n"
        "python3 export_svg_and_patch_pptx.py\n"
        "```\n\n"
        "This regenerates the slide SVG assets and patches `../kaito-llm-d-pd-slides.pptx` so slides 4-11 reference the SVG media instead of the PNG media.\n\n"
        "## Slide mapping\n"
        "- Slide 4: End-to-End Architecture\n"
        "- Slide 5: One MultiRoleInference Object Describes the Topology\n"
        "- Slide 6: What KAITO Automatically Generates for P/D\n"
        "- Slide 7: How a P/D Request Actually Executes\n"
        "- Slide 8: Why the Routing Sidecar Lives on Decode Pods\n"
        "- Slide 9: The Runtime Contracts That Make P/D Actually Work\n"
        "- Slide 10: KAITO Does Not Replace llm-d — It Operationalizes It\n"
        "- Slide 11: What Users Manage vs. What the Platform Manages\n"
    )


def main() -> None:
    export_svgs()
    patch_pptx_to_svg()
    update_readme()
    print(f"updated SVG assets and patched {PPTX_PATH}")


if __name__ == "__main__":
    main()
