#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).resolve().parent
MERMAID_DIR = ASSET_DIR / "mermaid"
D2_DIR = ASSET_DIR / "d2"
DRAWIO_PATH = ASSET_DIR / "kaito-llm-d-pd-slides.drawio"
PPTX_PATH = REPO_ROOT / "llm" / "kaito-llm-d-pd-slides.pptx"
CANVAS_W = 2200
CANVAS_H = 1000
LOCAL_D2_BIN = REPO_ROOT / ".tmp" / "d2" / "manual" / "d2-v0.9.0" / "bin" / "d2"
D2_BIN = os.environ.get("D2_BIN") or (str(LOCAL_D2_BIN) if LOCAL_D2_BIN.exists() else shutil.which("d2"))
NS_CT = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
NS_REL = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}

SLIDES = {
    4: {"basename": "slide-04-end-to-end-architecture", "source": "d2", "d2": "slide-04-end-to-end-architecture.d2"},
    5: {"basename": "slide-05-multiroleinference-topology", "source": "mermaid", "mmd": "slide-05-multiroleinference-topology.mmd"},
    6: {"basename": "slide-06-kaito-generated-resources", "source": "mermaid", "mmd": "slide-06-kaito-generated-resources.mmd"},
    7: {"basename": "slide-07-request-execution-flow", "source": "d2", "d2": "slide-07-request-execution-flow.d2"},
    8: {"basename": "slide-08-decode-sidecar-placement", "source": "d2", "d2": "slide-08-decode-sidecar-placement.d2"},
    9: {"basename": "slide-09-runtime-contracts", "source": "mermaid", "mmd": "slide-09-runtime-contracts.mmd"},
    10: {"basename": "slide-10-kaito-vs-llmd", "source": "mermaid", "mmd": "slide-10-kaito-vs-llmd.mmd"},
    11: {"basename": "slide-11-ownership-boundary", "source": "mermaid", "mmd": "slide-11-ownership-boundary.mmd"},
}

ET.register_namespace("", NS_CT["ct"])
ET.register_namespace("", NS_REL["rel"])


# ---------------- draw.io parsing/rendering ----------------
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
        spans.append(f'<tspan x="{x_text:.1f}" dy="{dy:.1f}">{html.escape(line)}</tspan>')
    return (
        f'<text x="{x_text:.1f}" y="{start_y:.1f}" text-anchor="{anchor}" '
        f'font-family="Aptos, Arial, sans-serif" font-size="{font_size}" '
        f'font-weight="{weight}" fill="{color}">' + "".join(spans) + "</text>"
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


def parse_drawio_diagrams() -> dict[str, tuple[float, float, list[dict], list[dict]]]:
    root = ET.parse(DRAWIO_PATH).getroot()
    pages: dict[str, tuple[float, float, list[dict], list[dict]]] = {}
    for diagram in root.findall("diagram"):
        name = diagram.attrib.get("name", "diagram")
        model = ET.fromstring(diagram.text or "")
        model_root = model.find("root")
        if model_root is None:
            continue
        width = float(model.attrib.get("pageWidth", str(CANVAS_W)))
        height = float(model.attrib.get("pageHeight", str(CANVAS_H)))
        vertices: list[dict] = []
        edges: list[dict] = []
        for cell in model_root.findall("mxCell"):
            attrs = cell.attrib
            geom = cell.find("mxGeometry")
            if attrs.get("vertex") == "1" and geom is not None:
                vertices.append(
                    {
                        "id": attrs["id"],
                        "text": xml_text_to_plain(attrs.get("value")),
                        "style": parse_style(attrs.get("style", "")),
                        "x": float(geom.attrib.get("x", "0")),
                        "y": float(geom.attrib.get("y", "0")),
                        "w": float(geom.attrib.get("width", "0")),
                        "h": float(geom.attrib.get("height", "0")),
                    }
                )
            elif attrs.get("edge") == "1":
                edges.append(
                    {
                        "id": attrs["id"],
                        "source": attrs.get("source"),
                        "target": attrs.get("target"),
                        "style": parse_style(attrs.get("style", "")),
                    }
                )
        pages[name] = (width, height, vertices, edges)
    return pages


def render_drawio_svg(width: float, height: float, vertices: list[dict], edges: list[dict]) -> str:
    by_id = {v["id"]: v for v in vertices}
    marker_defs: dict[str, str] = {}
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        '<defs>',
    ]
    for edge in edges:
        stroke = edge["style"].get("strokeColor", "#64748B")
        if stroke not in marker_defs:
            mid = f"arrow{len(marker_defs)+1}"
            marker_defs[stroke] = mid
            parts.append(
                f'<marker id="{mid}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">'
                f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{stroke}" /></marker></marker>'
            )
    parts.append('</defs>')
    parts.append(f'<rect x="0" y="0" width="{int(width)}" height="{int(height)}" fill="#FFFFFF"/>')
    # fix accidental double close from above
    parts = [p.replace('</marker></marker>', '</marker>') for p in parts]
    for edge in edges:
        src = by_id.get(edge.get("source", ""))
        dst = by_id.get(edge.get("target", ""))
        if not src or not dst:
            continue
        start, end = choose_anchor((src["x"], src["y"], src["w"], src["h"]), (dst["x"], dst["y"], dst["w"], dst["h"]))
        stroke = edge["style"].get("strokeColor", "#64748B")
        marker = marker_defs[stroke]
        stroke_width = float(edge["style"].get("strokeWidth", "4"))
        parts.append(f'<path d="{orthogonal_path(start, end)}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}" marker-end="url(#{marker})" />')
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
        parts.append(f'<rect x="{v["x"]:.1f}" y="{v["y"]:.1f}" width="{v["w"]:.1f}" height="{v["h"]:.1f}" rx="{rx}" ry="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="3" />')
        if v["text"]:
            parts.append(svg_text_block(v["x"], v["y"], v["w"], v["h"], v["text"], font_size, font_color, align, bold))
    parts.append('</svg>')
    return "\n".join(parts)


# ---------------- Mermaid parsing/rendering ----------------
EDGE_RE = re.compile(r'^(?P<src>[A-Za-z0-9_]+)\s+(?P<arrow>-\.->|-->)\s+(?P<dst>[A-Za-z0-9_]+)$')
CLASSDEF_RE = re.compile(r'^classDef\s+(?P<name>[A-Za-z0-9_-]+)\s+(?P<body>.+)$')
POS_RE = re.compile(r'^%%\s+pos\s+(?P<id>[A-Za-z0-9_]+)\s+(?P<x>\d+)\s+(?P<y>\d+)\s+(?P<w>\d+)\s+(?P<h>\d+)$')
FLOW_RE = re.compile(r'^(flowchart|graph)\s+(?P<dir>LR|TB)$')


def parse_mermaid_style(body: str) -> dict[str, str]:
    style: dict[str, str] = {}
    for part in body.split(','):
        piece = part.strip()
        if not piece or ':' not in piece:
            continue
        key, value = piece.split(':', 1)
        key = key.strip()
        value = value.strip().rstrip(';')
        if key == 'fill':
            style['fill'] = value
        elif key == 'stroke':
            style['stroke'] = value
        elif key == 'color':
            style['color'] = value
        elif key == 'font-size':
            style['font-size'] = value.replace('px', '')
        elif key == 'font-weight':
            style['font-weight'] = value
    return style


def parse_mermaid_node(line: str) -> dict | None:
    if '["' not in line or '"]' not in line:
        return None
    node_id, rest = line.split('["', 1)
    if not re.fullmatch(r'[A-Za-z0-9_]+', node_id):
        return None
    label, tail = rest.split('"]', 1)
    class_name = 'default'
    tail = tail.strip()
    if tail.startswith(':::'):
        class_name = tail[3:].strip()
    return {'id': node_id, 'label': label.replace('<br/>', '\n').replace('<br>', '\n'), 'class': class_name}


def parse_mermaid(path: Path) -> dict:
    direction = 'LR'
    classdefs: dict[str, dict[str, str]] = {}
    positions: dict[str, tuple[float, float, float, float]] = {}
    nodes: list[dict] = []
    edges: list[dict] = []
    order = 0
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        m = FLOW_RE.match(line)
        if m:
            direction = m.group('dir')
            continue
        m = POS_RE.match(line)
        if m:
            positions[m.group('id')] = tuple(float(m.group(k)) for k in ('x', 'y', 'w', 'h'))
            continue
        if line.startswith('%%'):
            continue
        m = CLASSDEF_RE.match(line)
        if m:
            classdefs[m.group('name')] = parse_mermaid_style(m.group('body'))
            continue
        node = parse_mermaid_node(line)
        if node is not None:
            node['order'] = order
            nodes.append(node)
            order += 1
            continue
        m = EDGE_RE.match(line)
        if m:
            edges.append({'src': m.group('src'), 'dst': m.group('dst'), 'dashed': m.group('arrow') == '-.->'})
            continue
        raise RuntimeError(f'unhandled Mermaid line in {path.name}: {line}')
    return {'direction': direction, 'classdefs': classdefs, 'positions': positions, 'nodes': nodes, 'edges': edges}


def auto_layout(nodes: list[dict], edges: list[dict], direction: str) -> dict[str, tuple[float, float, float, float]]:
    level = {n['id']: 0 for n in nodes}
    changed = True
    for _ in range(len(nodes)):
        if not changed:
            break
        changed = False
        for edge in edges:
            if level[edge['dst']] < level[edge['src']] + 1:
                level[edge['dst']] = level[edge['src']] + 1
                changed = True
    groups: dict[int, list[dict]] = {}
    for n in sorted(nodes, key=lambda x: (level[x['id']], x['order'])):
        groups.setdefault(level[n['id']], []).append(n)
    positions: dict[str, tuple[float, float, float, float]] = {}
    if direction == 'TB':
        y = 80.0
        for lvl in sorted(groups):
            x = 80.0
            row = groups[lvl]
            max_h = 0.0
            for node in row:
                lines = node['label'].splitlines() or ['']
                w = max(260.0, min(560.0, max(len(line) for line in lines) * 13 + 80))
                h = max(90.0, 46.0 * len(lines) + 36)
                positions[node['id']] = (x, y, w, h)
                x += w + 80.0
                max_h = max(max_h, h)
            y += max_h + 80.0
    else:
        x = 80.0
        for lvl in sorted(groups):
            y = 80.0
            col = groups[lvl]
            max_w = 0.0
            for node in col:
                lines = node['label'].splitlines() or ['']
                w = max(260.0, min(640.0, max(len(line) for line in lines) * 13 + 80))
                h = max(90.0, 46.0 * len(lines) + 36)
                positions[node['id']] = (x, y, w, h)
                y += h + 60.0
                max_w = max(max_w, w)
            x += max_w + 120.0
    return positions


def render_mermaid_svg(model: dict) -> str:
    classdefs = model['classdefs']
    nodes = model['nodes']
    edges = model['edges']
    positions = auto_layout(nodes, edges, model['direction'])
    positions.update(model['positions'])
    by_id = {n['id']: n for n in nodes}
    marker_solid: dict[str, str] = {}
    marker_dashed: dict[str, str] = {}
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">',
        '<defs>',
    ]
    for edge in edges:
        src_cls = by_id[edge['src']]['class']
        stroke = classdefs.get(src_cls, {}).get('stroke', '#64748B')
        target = marker_dashed if edge['dashed'] else marker_solid
        if stroke not in target:
            mid = f"{'dash' if edge['dashed'] else 'solid'}{len(marker_solid)+len(marker_dashed)+1}"
            target[stroke] = mid
            parts.append(
                f'<marker id="{mid}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">'
                f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{stroke}" /></marker>'
            )
    parts.append('</defs>')
    parts.append(f'<rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" fill="#FFFFFF"/>')

    # edges first
    for edge in edges:
        src_box = positions[edge['src']]
        dst_box = positions[edge['dst']]
        stroke = classdefs.get(by_id[edge['src']]['class'], {}).get('stroke', '#64748B')
        start, end = choose_anchor(src_box, dst_box)
        dash = ' stroke-dasharray="10 8"' if edge['dashed'] else ''
        marker = (marker_dashed if edge['dashed'] else marker_solid)[stroke]
        parts.append(f'<path d="{orthogonal_path(start, end)}" fill="none" stroke="{stroke}" stroke-width="4"{dash} marker-end="url(#{marker})" />')

    # nodes
    for node in nodes:
        x, y, w, h = positions[node['id']]
        style = classdefs.get(node['class'], {})
        fill = style.get('fill', '#FFFFFF')
        stroke = style.get('stroke', '#CBD5E1')
        color = style.get('color', '#111827')
        font_size = int(float(style.get('font-size', '20')))
        bold = style.get('font-weight', '').lower() in {'bold', '700'}
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="18" ry="18" fill="{fill}" stroke="{stroke}" stroke-width="3" />')
        parts.append(svg_text_block(x, y, w, h, node['label'], font_size, color, 'center', bold))
    parts.append('</svg>')
    return '\n'.join(parts)


# ---------------- export + patch ----------------
def export_d2_svg(d2_path: Path, out_path: Path) -> None:
    if not D2_BIN:
        raise RuntimeError(
            "D2 binary not found. Set D2_BIN or install d2, e.g. repo-local .tmp/d2/manual/d2-v0.9.0/bin/d2"
        )
    subprocess.run([D2_BIN, str(d2_path), str(out_path)], check=True, cwd=REPO_ROOT)



def export_svgs() -> None:
    for _slide_no, meta in SLIDES.items():
        out = ASSET_DIR / f"{meta['basename']}.svg"
        if meta['source'] == 'd2':
            export_d2_svg(D2_DIR / meta['d2'], out)
        else:
            mmd_path = MERMAID_DIR / meta['mmd']
            out.write_text(render_mermaid_svg(parse_mermaid(mmd_path)))


def patch_pptx_to_svg() -> None:
    with tempfile.TemporaryDirectory() as td:
        tempdir = Path(td)
        with zipfile.ZipFile(PPTX_PATH, 'r') as zf:
            zf.extractall(tempdir)
        content_types = tempdir / '[Content_Types].xml'
        ct_tree = ET.parse(content_types)
        ct_root = ct_tree.getroot()
        has_svg = any(el.attrib.get('Extension') == 'svg' for el in ct_root.findall('ct:Default', NS_CT))
        if not has_svg:
            ET.SubElement(ct_root, f'{{{NS_CT["ct"]}}}Default', Extension='svg', ContentType='image/svg+xml')
            ct_tree.write(content_types, encoding='utf-8', xml_declaration=True)
        for slide_no, meta in SLIDES.items():
            rel_path = tempdir / 'ppt' / 'slides' / '_rels' / f'slide{slide_no}.xml.rels'
            rel_tree = ET.parse(rel_path)
            rel_root = rel_tree.getroot()
            image_rels = [
                el for el in rel_root.findall('rel:Relationship', NS_REL)
                if el.attrib.get('Type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'
            ]
            if len(image_rels) != 1:
                raise RuntimeError(f'expected exactly one image rel for slide {slide_no}, got {len(image_rels)}')
            target_name = f"{meta['basename']}.svg"
            image_rels[0].attrib['Target'] = f'../media/{target_name}'
            rel_tree.write(rel_path, encoding='utf-8', xml_declaration=True)
            shutil.copy2(ASSET_DIR / target_name, tempdir / 'ppt' / 'media' / target_name)
        rebuilt = tempdir / 'rebuilt.pptx'
        with zipfile.ZipFile(rebuilt, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(tempdir.rglob('*')):
                if path.is_dir() or path == rebuilt:
                    continue
                zf.write(path, path.relative_to(tempdir).as_posix())
        shutil.copy2(rebuilt, PPTX_PATH)


def update_readme() -> None:
    (ASSET_DIR / 'README.md').write_text(
        "# kaito-llm-d-pd-slides-assets\n\n"
        "Mixed D2 + Mermaid diagram assets for `../kaito-llm-d-pd-slides.pptx`.\n\n"
        "## Source of truth\n"
        "- `d2/*.d2`: D2 source files for key visual slides (currently 4 / 7 / 8)\n"
        "- `mermaid/*.mmd`: Mermaid source files for the structure / logic slides\n"
        "- `kaito-llm-d-pd-slides.drawio`: legacy reference copy from an earlier iteration (not used by the active export pipeline)\n\n"
        "## Generated outputs\n"
        "- `slide-04-*.svg` ... `slide-11-*.svg`: vector assets embedded into the PowerPoint deck\n"
        "- `slide-04-*.png` ... `slide-11-*.png`: legacy raster reference exports\n\n"
        "## Regeneration\n"
        "```bash\n"
        "cd llm/kaito-llm-d-pd-slides-assets\n"
        "python3 export_svg_and_patch_pptx.py\n"
        "```\n\n"
        "This regenerates the slide SVG assets from the mixed D2 + Mermaid sources and patches `../kaito-llm-d-pd-slides.pptx` so slides 4-11 reference the SVG media.\n"
    )


def main() -> None:
    export_svgs()
    patch_pptx_to_svg()
    update_readme()
    print(f'updated D2 + Mermaid SVG assets and patched {PPTX_PATH}')


if __name__ == '__main__':
    main()
