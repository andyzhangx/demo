#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "kaito-llm-d-pd-slides.pptx"

BG = RGBColor(246, 248, 252)
BG_ALT = RGBColor(240, 244, 248)
NAVY = RGBColor(15, 23, 42)
SLATE = RGBColor(51, 65, 85)
MUTED = RGBColor(100, 116, 139)
MID = RGBColor(203, 213, 225)
WHITE = RGBColor(255, 255, 255)
BLUE = RGBColor(37, 99, 235)
BLUE_SOFT = RGBColor(219, 234, 254)
ORANGE = RGBColor(234, 88, 12)
ORANGE_SOFT = RGBColor(255, 237, 213)
GREEN = RGBColor(22, 163, 74)
GREEN_SOFT = RGBColor(220, 252, 231)
PURPLE = RGBColor(109, 40, 217)
PURPLE_SOFT = RGBColor(237, 233, 254)
RED = RGBColor(220, 38, 38)
RED_SOFT = RGBColor(254, 226, 226)
GRAY_SOFT = RGBColor(241, 245, 249)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def set_bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_shape(slide, kind, x, y, w, h, fill=None, line=None, line_width=1.1):
    s = slide.shapes.add_shape(kind, x, y, w, h)
    if fill is None or fill is False:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.color.rgb = MID
        s.line.width = Pt(line_width)
    elif line is False:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_width)
    return s


def add_textbox(slide, x, y, w, h, text, size=18, bold=False, color=NAVY,
                align=PP_ALIGN.LEFT, fill=None, line=False, radius=False,
                margin=0.08, font="Aptos"):
    kind = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    box = add_shape(slide, kind, x, y, w, h, fill=fill, line=line)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = font
    return box


def add_bullets(slide, x, y, w, h, items, size=16, color=SLATE, bullet_char=True):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(6)
        if bullet_char:
            p.bullet = True
    return tb


def add_numbered(slide, x, y, w, h, items, size=15, color=SLATE):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items, start=1):
        p = tf.paragraphs[0] if i == 1 else tf.add_paragraph()
        p.text = f"{i}. {item}"
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(5)
    return tb


def add_connector(slide, x1, y1, x2, y2, color=BLUE, width=2.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = color
    c.line.width = Pt(width)
    return c


def add_header(slide, num, title, accent=BLUE):
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.84), fill=NAVY, line=False)
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, Inches(0.80), Inches(13.333), Inches(0.04), fill=accent, line=False)
    add_textbox(slide, Inches(0.40), Inches(0.18), Inches(0.62), Inches(0.34), str(num), 14, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_textbox(slide, Inches(1.12), Inches(0.12), Inches(11.4), Inches(0.42), title, 24, True,
                WHITE, fill=None, line=False, font="Aptos Display")


def add_note(slide, text):
    add_textbox(slide, Inches(0.65), Inches(6.72), Inches(12.0), Inches(0.40), text, 13, False,
                NAVY, PP_ALIGN.CENTER, fill=GRAY_SOFT, line=MID, radius=True)


def add_card(slide, x, y, w, h, title, lines, fill=WHITE, line=MID, title_color=NAVY):
    add_textbox(slide, x, y, w, h, "", fill=fill, line=line, radius=True)
    add_textbox(slide, x + Inches(0.16), y + Inches(0.12), w - Inches(0.32), Inches(0.36), title,
                18, True, title_color, fill=None, line=False)
    tb = slide.shapes.add_textbox(x + Inches(0.18), y + Inches(0.56), w - Inches(0.36), h - Inches(0.68))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.font.size = Pt(14)
        p.font.color.rgb = SLATE
        p.space_after = Pt(5)
    return tb


def title_slide():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, NAVY)
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.14), fill=ORANGE, line=False)
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(8.9), Inches(0.14), Inches(4.45), Inches(7.36), fill=RGBColor(22, 32, 58), line=False)
    add_textbox(slide, Inches(0.82), Inches(0.92), Inches(0.98), Inches(0.42), "KubeCon '26", 12, True, NAVY,
                PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_textbox(slide, Inches(0.82), Inches(1.45), Inches(7.7), Inches(0.70), "KAITO + llm-d", 30, True,
                WHITE, fill=None, line=False, font="Aptos Display")
    add_textbox(slide, Inches(0.84), Inches(2.08), Inches(8.0), Inches(1.05),
                "How They Support Prefill/Decode\nDisaggregation", 25, True,
                WHITE, fill=None, line=False, font="Aptos Display")
    add_textbox(slide, Inches(0.86), Inches(3.35), Inches(7.8), Inches(0.82),
                "A Kubernetes-native story about declarative topology,\nrole-aware routing, and direct KV-cache handoff.",
                18, False, RGBColor(201, 214, 255), fill=None, line=False)
    add_textbox(slide, Inches(0.86), Inches(5.10), Inches(5.6), Inches(1.05),
                "Control plane: KAITO\nRouting contract: GWIE\nScheduling substrate: llm-d Router\nRuntime + KV path: vLLM + NIXL",
                17, False, WHITE, fill=None, line=False)
    chips = [("KAITO", BLUE_SOFT, BLUE), ("llm-d", ORANGE_SOFT, ORANGE), ("GWIE", GREEN_SOFT, GREEN), ("NIXL", PURPLE_SOFT, PURPLE)]
    cx = Inches(0.88)
    for label, fillc, linec in chips:
        add_textbox(slide, cx, Inches(6.25), Inches(1.18), Inches(0.44), label, 13, True, NAVY,
                    PP_ALIGN.CENTER, fill=fillc, line=linec, radius=True)
        cx += Inches(1.35)
    add_textbox(slide, Inches(9.22), Inches(1.00), Inches(3.2), Inches(0.45), "P/D platform stack", 15, True,
                BLUE, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_textbox(slide, Inches(9.46), Inches(1.88), Inches(2.72), Inches(0.62), "MultiRoleInference", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
    add_textbox(slide, Inches(9.46), Inches(2.98), Inches(2.72), Inches(0.62), "InferencePool + GWIE", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
    add_textbox(slide, Inches(9.46), Inches(4.08), Inches(2.72), Inches(0.62), "llm-d Router EPP", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
    add_textbox(slide, Inches(9.46), Inches(5.18), Inches(2.72), Inches(0.62), "vLLM + NIXL", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)
    add_connector(slide, Inches(10.82), Inches(2.50), Inches(10.82), Inches(2.98), GREEN, 3)
    add_connector(slide, Inches(10.82), Inches(3.60), Inches(10.82), Inches(4.08), BLUE, 3)
    add_connector(slide, Inches(10.82), Inches(4.70), Inches(10.82), Inches(5.18), ORANGE, 3)


def slide_18_division_of_labor():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_header(slide, 18, "KAITO + llm-d + GWIE: Division of Labor", accent=GREEN)
    add_textbox(slide, Inches(0.85), Inches(1.18), Inches(11.7), Inches(0.62),
                "Three layers, three responsibilities, one usable P/D platform.", 21, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_card(slide, Inches(0.9), Inches(2.2), Inches(3.2), Inches(2.55), "KAITO",
             ["declarative abstraction", "Kubernetes orchestration", "child resource ownership", "platform-facing UX"],
             fill=BLUE_SOFT, line=BLUE)
    add_card(slide, Inches(5.05), Inches(2.2), Inches(3.2), Inches(2.55), "GWIE",
             ["inference routing contract", "InferencePool model", "gateway integration pattern", "Kubernetes-native interface"],
             fill=GREEN_SOFT, line=GREEN)
    add_card(slide, Inches(9.2), Inches(2.2), Inches(3.2), Inches(2.55), "llm-d Router",
             ["EPP implementation", "endpoint selection", "P/D-aware scheduling", "routing execution substrate"],
             fill=ORANGE_SOFT, line=ORANGE)
    add_connector(slide, Inches(4.10), Inches(3.47), Inches(5.00), Inches(3.47), PURPLE, 3)
    add_connector(slide, Inches(8.25), Inches(3.47), Inches(9.15), Inches(3.47), PURPLE, 3)
    add_note(slide, "KAITO makes P/D operable. llm-d makes it routable. GWIE makes it Kubernetes-native.")


def slide_19_anchor_architecture():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_ALT)
    add_header(slide, 19, "End-to-End Architecture", accent=ORANGE)
    add_textbox(slide, Inches(0.86), Inches(1.10), Inches(11.65), Inches(0.55),
                "This is the anchor architecture slide: one user endpoint, one routing surface, two role-specific backends, and a direct KV path.",
                18, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)

    # Cluster canvas
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.78), Inches(1.85), Inches(11.9), Inches(4.7), fill=WHITE, line=False)
    add_textbox(slide, Inches(0.98), Inches(2.00), Inches(2.0), Inches(0.28), "AKS / Kubernetes cluster", 12, True, MUTED, fill=None, line=False)

    # Control plane band
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(1.05), Inches(2.22), Inches(10.95), Inches(0.78), fill=GRAY_SOFT, line=False)
    add_textbox(slide, Inches(1.20), Inches(2.40), Inches(1.55), Inches(0.20), "control plane", 12, True, BLUE, fill=None, line=False)
    add_textbox(slide, Inches(2.15), Inches(2.32), Inches(2.45), Inches(0.44), "KAITO\nMultiRoleInference controller", 16, True, NAVY, PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
    add_textbox(slide, Inches(4.95), Inches(2.32), Inches(1.90), Inches(0.44), "InferencePool", 16, True, NAVY, PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
    add_textbox(slide, Inches(7.20), Inches(2.32), Inches(2.65), Inches(0.44), "Gateway API Inference Extension", 15, True, NAVY, PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
    add_textbox(slide, Inches(10.15), Inches(2.32), Inches(1.40), Inches(0.44), "KEDA", 16, True, NAVY, PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)

    # Data plane band labels
    add_textbox(slide, Inches(1.15), Inches(3.18), Inches(1.25), Inches(0.20), "request path", 12, True, BLUE, fill=None, line=False)
    add_textbox(slide, Inches(1.15), Inches(5.78), Inches(1.10), Inches(0.20), "KV path", 12, True, PURPLE, fill=None, line=False)

    # Request/data plane components
    add_textbox(slide, Inches(1.15), Inches(3.45), Inches(1.10), Inches(0.74), "Client", 18, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(2.55), Inches(3.45), Inches(1.40), Inches(0.74), "Gateway", 18, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(4.25), Inches(3.28), Inches(2.05), Inches(1.06), "llm-d Router\nEPP", 18, True, NAVY, PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
    add_textbox(slide, Inches(6.80), Inches(3.02), Inches(2.15), Inches(0.84), "Prefill\nInferenceSet", 18, True, NAVY, PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
    add_textbox(slide, Inches(6.80), Inches(4.58), Inches(2.15), Inches(0.84), "Decode\nInferenceSet", 18, True, NAVY, PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
    add_textbox(slide, Inches(9.35), Inches(4.32), Inches(2.10), Inches(1.05), "Decode pod\nsidecar + local vLLM", 16, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=PURPLE, radius=True)

    # Request path connectors
    add_connector(slide, Inches(2.25), Inches(3.82), Inches(2.55), Inches(3.82), BLUE, 3)
    add_connector(slide, Inches(3.95), Inches(3.82), Inches(4.25), Inches(3.82), BLUE, 3)
    add_connector(slide, Inches(6.30), Inches(3.82), Inches(6.80), Inches(5.00), BLUE, 2.8)
    add_connector(slide, Inches(8.95), Inches(5.00), Inches(9.35), Inches(4.85), BLUE, 2.8)

    # Optional prefill decision branch
    add_connector(slide, Inches(6.30), Inches(3.68), Inches(6.80), Inches(3.42), BLUE, 2.2)
    add_textbox(slide, Inches(5.55), Inches(3.00), Inches(0.95), Inches(0.30), "selects", 11, True, MUTED, PP_ALIGN.CENTER, fill=None, line=False)

    # KV path
    add_connector(slide, Inches(8.95), Inches(3.44), Inches(9.35), Inches(4.70), PURPLE, 2.8)
    add_textbox(slide, Inches(8.82), Inches(3.68), Inches(0.90), Inches(0.28), "NIXL KV", 11, True, PURPLE, PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)

    # Callouts
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(1.10), Inches(6.02), Inches(4.55), Inches(0.42), fill=GRAY_SOFT, line=False)
    add_textbox(slide, Inches(1.18), Inches(6.09), Inches(4.40), Inches(0.24),
                "Request routing and KV transfer are separate paths.", 13, True, MUTED,
                PP_ALIGN.CENTER, fill=None, line=False)
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(6.15), Inches(6.02), Inches(5.70), Inches(0.42), fill=GRAY_SOFT, line=False)
    add_textbox(slide, Inches(6.28), Inches(6.09), Inches(5.42), Inches(0.24),
                "KAITO owns topology + wiring; llm-d owns EPP decisions; vLLM/NIXL own execution + handoff.",
                13, True, MUTED, PP_ALIGN.CENTER, fill=None, line=False)


def slide_20_mri_object():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_header(slide, 20, "One MultiRoleInference Object Describes the Topology", accent=GREEN)
    add_textbox(slide, Inches(0.84), Inches(1.12), Inches(11.7), Inches(0.55),
                "Users declare intent once; the platform expands it into a runnable P/D system.", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.80), Inches(1.92), Inches(5.18), Inches(4.65), fill=NAVY, line=False)
    add_textbox(slide, Inches(1.02), Inches(2.18), Inches(4.8), Inches(3.9),
                "apiVersion: kaito.sh/v1alpha1\nkind: MultiRoleInference\nmetadata:\n  name: phi-4-mini\nspec:\n  model:\n    name: phi-4-mini-instruct\n  roles:\n    - type: prefill\n      replicas: 1\n      instanceType: Standard_NC24ads_A100_v4\n    - type: decode\n      replicas: 1\n      instanceType: Standard_NC24ads_A100_v4",
                15, False, WHITE, fill=None, line=False, font="Consolas")
    add_connector(slide, Inches(6.10), Inches(4.05), Inches(7.05), Inches(4.05), GREEN, 4)
    add_textbox(slide, Inches(7.30), Inches(2.10), Inches(2.0), Inches(0.60), "prefill", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
    add_textbox(slide, Inches(9.85), Inches(2.10), Inches(2.0), Inches(0.60), "decode", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
    add_textbox(slide, Inches(8.58), Inches(3.36), Inches(2.0), Inches(0.60), "InferencePool", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
    add_connector(slide, Inches(9.55), Inches(2.70), Inches(9.55), Inches(3.36), PURPLE, 3)
    add_connector(slide, Inches(10.85), Inches(3.96), Inches(10.85), Inches(2.70), PURPLE, 3)
    add_bullets(slide, Inches(7.08), Inches(4.65), Inches(5.1), Inches(1.35), [
        "One logical service with role-specific backends",
        "Role-specific scaling intent for prefill and decode",
        "Users describe what they want, not how to wire the stack",
    ], size=15)
    add_note(slide, "The CRD is the product surface. Users express topology intent; controllers own the plumbing.")


def slide_21_kaito_generates():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_ALT)
    add_header(slide, 21, "What KAITO Automatically Generates for P/D", accent=ORANGE)
    add_textbox(slide, Inches(0.88), Inches(1.12), Inches(11.6), Inches(0.55),
                "KAITO acts like the control-plane compiler for the topology.", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_textbox(slide, Inches(4.95), Inches(3.18), Inches(3.15), Inches(0.70), "MultiRoleInference", 22, True,
                NAVY, PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
    boxes = [
        (Inches(1.05), Inches(1.95), "InferenceSet\n(prefill)", ORANGE_SOFT, ORANGE),
        (Inches(1.05), Inches(4.58), "InferenceSet\n(decode)", BLUE_SOFT, BLUE),
        (Inches(8.85), Inches(1.95), "InferencePool", GREEN_SOFT, GREEN),
        (Inches(8.62), Inches(3.25), "llm-d Router\nEPP", ORANGE_SOFT, ORANGE),
        (Inches(8.35), Inches(4.58), "sidecar\ninjection", PURPLE_SOFT, PURPLE),
        (Inches(4.95), Inches(5.05), "NIXL env wiring", BLUE_SOFT, BLUE),
    ]
    for x, y, label, fillc, linec in boxes:
        add_textbox(slide, x, y, Inches(2.45), Inches(0.82), label, 18, True, NAVY,
                    PP_ALIGN.CENTER, fill=fillc, line=linec, radius=True)
    for x, y, *_ in boxes:
        add_connector(slide, Inches(6.52), Inches(3.53), x + Inches(1.22), y + Inches(0.41),
                      GREEN if x < Inches(6.1) else BLUE, 2.2)
    add_note(slide, "KAITO does not replace llm-d. It generates, owns, and keeps the llm-d-facing resources consistent.")


def slide_22_request_flow():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_header(slide, 22, "How a P/D Request Actually Executes", accent=PURPLE)
    add_textbox(slide, Inches(0.84), Inches(1.12), Inches(11.7), Inches(0.55),
                "One endpoint for the user; multiple coordinated steps underneath.", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    labels = [
        ("Client", Inches(0.72), Inches(1.95), GREEN_SOFT, GREEN),
        ("Gateway", Inches(2.10), Inches(1.95), BLUE_SOFT, BLUE),
        ("InferencePool", Inches(3.60), Inches(1.95), GREEN_SOFT, GREEN),
        ("llm-d Router EPP", Inches(5.38), Inches(1.95), ORANGE_SOFT, ORANGE),
        ("Decode sidecar", Inches(7.60), Inches(1.95), PURPLE_SOFT, PURPLE),
        ("Decode vLLM", Inches(10.00), Inches(1.95), BLUE_SOFT, BLUE),
    ]
    for t, x, y, fillc, linec in labels:
        add_textbox(slide, x, y, Inches(1.40), Inches(0.62), t, 15, True, NAVY,
                    PP_ALIGN.CENTER, fill=fillc, line=linec, radius=True)
    for i in range(len(labels) - 1):
        _, x1, y1, *_ = labels[i]
        _, x2, y2, *_ = labels[i + 1]
        add_connector(slide, x1 + Inches(1.40), y1 + Inches(0.31), x2, y2 + Inches(0.31), BLUE, 2.4)
    add_textbox(slide, Inches(7.60), Inches(3.18), Inches(1.40), Inches(0.62), "Prefill", 15, True,
                NAVY, PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
    add_connector(slide, Inches(8.30), Inches(2.57), Inches(8.30), Inches(3.18), PURPLE, 2.4)
    add_connector(slide, Inches(9.00), Inches(3.49), Inches(10.00), Inches(2.57), PURPLE, 2.4)
    add_textbox(slide, Inches(9.00), Inches(3.25), Inches(1.22), Inches(0.36), "NIXL KV", 12, True,
                PURPLE, PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)
    add_numbered(slide, Inches(0.82), Inches(4.10), Inches(8.25), Inches(2.05), [
        "Gateway / HTTPRoute forwards to the InferencePool for the model",
        "llm-d Router EPP decides whether prefill work is needed and selects the role-specific backends",
        "The request lands on a decode pod, whose sidecar coordinates prefill on the selected prefill pod",
        "KV cache is transferred directly to decode via NIXL, and local decode vLLM continues generation",
    ], size=15)
    add_textbox(slide, Inches(9.35), Inches(4.08), Inches(3.0), Inches(1.62),
                "• Decode is the coordination point\n• Prefill is selected only when it helps\n• KV transfer bridges the two phases",
                15, False, SLATE, fill=WHITE, line=MID, radius=True)
    add_note(slide, "The user sees one endpoint. The platform coordinates routing, prefill placement, KV movement, and decode execution across multiple pods.")


def slide_23_sidecar():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_header(slide, 23, "Why the Routing Sidecar Lives on Decode Pods", accent=BLUE)
    add_textbox(slide, Inches(0.84), Inches(1.12), Inches(11.7), Inches(0.55),
                "Sidecar placement is an execution design choice, not an incidental implementation detail.",
                18, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_bullets(slide, Inches(0.85), Inches(2.05), Inches(5.55), Inches(3.8), [
        "Decode pods are the final response point for user traffic",
        "The routing sidecar receives the EPP decision, coordinates prefill, waits for KV handoff, then forwards to local vLLM",
        "This keeps the external routing contract cleaner: sidecar on 5000, local decode vLLM on 5001",
        "Prefill pods stay simpler and focus only on prompt processing",
    ], size=16)
    add_shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(7.25), Inches(1.85), Inches(4.95), Inches(4.65), fill=WHITE, line=BLUE, line_width=1.8)
    add_textbox(slide, Inches(8.72), Inches(2.00), Inches(2.0), Inches(0.35), "Decode Pod", 21, True,
                NAVY, PP_ALIGN.CENTER, fill=None, line=False)
    add_textbox(slide, Inches(7.80), Inches(2.80), Inches(3.85), Inches(0.82), "Routing sidecar\nport 5000", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)
    add_textbox(slide, Inches(7.80), Inches(4.25), Inches(3.85), Inches(0.82), "Local decode vLLM\nport 5001", 20, True,
                NAVY, PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
    add_connector(slide, Inches(9.72), Inches(3.62), Inches(9.72), Inches(4.25), PURPLE, 3)
    add_textbox(slide, Inches(6.15), Inches(2.95), Inches(1.10), Inches(0.40), "from EPP", 12, True,
                NAVY, PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
    add_connector(slide, Inches(7.25), Inches(3.21), Inches(6.85), Inches(3.21), GREEN, 2.6)
    add_textbox(slide, Inches(11.82), Inches(3.62), Inches(0.98), Inches(0.40), "NIXL KV", 12, True,
                NAVY, PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
    add_connector(slide, Inches(11.55), Inches(3.82), Inches(11.82), Inches(4.66), ORANGE, 2.6)
    add_note(slide, "Decode-side sidecar placement turns the decode pod into the coordination point for P/D execution.")


def slide_24_runtime_contracts():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_ALT)
    add_header(slide, 24, "The Runtime Contracts That Make P/D Actually Work", accent=RED)
    add_textbox(slide, Inches(0.84), Inches(1.12), Inches(11.7), Inches(0.55),
                "Most real failures here are contract bugs, not model bugs.", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    rows = [
        ("Routing sidecar", "No", "Yes", "Decode is the coordination point"),
        ("vLLM port", "5000", "5001", "Avoid sidecar ↔ local vLLM collision"),
        ("Sidecar ingress port", "N/A", "5000", "Gives decode a stable external entry point"),
        ("Role label", "prefill", "decode", "EPP filters workers by role"),
        ("NIXL side-channel host", "Pod IP", "Pod IP", "KV handoff must advertise a reachable address"),
        ("InferencePool targetPort", "Shared", "Shared", "Gateway/EPP expect consistent routing semantics"),
    ]
    x0 = Inches(0.80)
    y0 = Inches(1.92)
    widths = [Inches(2.35), Inches(1.20), Inches(1.20), Inches(4.85)]
    headers = ["Contract", "Prefill", "Decode", "Why it matters"]
    x = x0
    for w, head in zip(widths, headers):
        add_textbox(slide, x, y0, w, Inches(0.48), head, 15, True, WHITE,
                    PP_ALIGN.CENTER, fill=NAVY, line=False)
        x += w
    for r, row in enumerate(rows, start=1):
        x = x0
        fill = WHITE if r % 2 else GRAY_SOFT
        for idx, (w, cell) in enumerate(zip(widths, row)):
            add_textbox(slide, x, y0 + Inches(0.48 * r), w, Inches(0.48), cell, 13,
                        idx == 0, NAVY if idx == 0 else SLATE,
                        PP_ALIGN.CENTER if idx < 3 else PP_ALIGN.LEFT, fill=fill, line=MID)
            x += w
    add_bullets(slide, Inches(0.92), Inches(5.18), Inches(11.3), Inches(1.0), [
        "Contracts must be controller-enforced",
        "Labels are functional metadata, not decoration",
        "TargetPort is part of the serving contract",
        "Pod IP / env wiring must be automatic",
    ], size=14)
    add_note(slide, "If these contracts are not enforced by the controller, users debug infrastructure wiring as if it were model behavior.")


def slide_25_operationalizes():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_header(slide, 25, "KAITO Does Not Replace llm-d — It Operationalizes It", accent=ORANGE)
    add_textbox(slide, Inches(0.84), Inches(1.12), Inches(11.7), Inches(0.55),
                "The two projects solve different layers of the same problem.", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_textbox(slide, Inches(1.05), Inches(1.95), Inches(4.55), Inches(0.50), "llm-d Router", 20, True,
                WHITE, PP_ALIGN.CENTER, fill=ORANGE, line=False, radius=True)
    add_textbox(slide, Inches(7.75), Inches(1.95), Inches(4.55), Inches(0.50), "KAITO", 20, True,
                WHITE, PP_ALIGN.CENTER, fill=BLUE, line=False, radius=True)
    left_items = ["EPP implementation", "endpoint picking", "scheduling profiles", "P/D-aware plugins", "routing execution", "future scheduling surface"]
    right_items = ["CRD abstraction", "child resource generation", "lifecycle orchestration", "Kubernetes-native UX", "integration with InferenceSet / autoscaling", "future topology APIs"]
    for i, (l, r) in enumerate(zip(left_items, right_items)):
        y = Inches(2.70 + i * 0.57)
        add_textbox(slide, Inches(1.0), y, Inches(4.65), Inches(0.44), l, 15, False, SLATE,
                    fill=ORANGE_SOFT if i % 2 == 0 else WHITE, line=MID, radius=True)
        add_textbox(slide, Inches(7.70), y, Inches(4.65), Inches(0.44), r, 15, False, SLATE,
                    fill=BLUE_SOFT if i % 2 == 0 else WHITE, line=MID, radius=True)
        add_connector(slide, Inches(5.80), y + Inches(0.22), Inches(7.55), y + Inches(0.22), PURPLE, 2.2)
    add_note(slide, "This is not KAITO vs. llm-d. KAITO builds on llm-d and turns it into a cleaner Kubernetes workflow.")


def slide_26_users_vs_platform():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_ALT)
    add_header(slide, 26, "What Users Manage vs. What the Platform Manages", accent=GREEN)
    add_textbox(slide, Inches(0.84), Inches(1.12), Inches(11.7), Inches(0.55),
                "P/D becomes usable when the ownership boundary is clean.", 18, True,
                NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    add_textbox(slide, Inches(0.96), Inches(1.95), Inches(5.0), Inches(0.50), "User intent", 20, True,
                WHITE, PP_ALIGN.CENTER, fill=GREEN, line=False, radius=True)
    add_textbox(slide, Inches(7.35), Inches(1.95), Inches(5.0), Inches(0.50), "Platform-managed plumbing", 20, True,
                WHITE, PP_ALIGN.CENTER, fill=BLUE, line=False, radius=True)
    add_bullets(slide, Inches(1.02), Inches(2.62), Inches(4.86), Inches(3.45), [
        "model choice",
        "prefill/decode role definitions",
        "replica intent",
        "instance types",
        "autoscaling intent",
        "policy-level topology decisions",
    ], size=16)
    add_bullets(slide, Inches(7.45), Inches(2.62), Inches(4.80), Inches(3.75), [
        "child InferenceSets",
        "InferencePool",
        "llm-d Router EPP resources",
        "sidecar injection",
        "labels / services / targetPorts",
        "env wiring for NIXL",
        "ownership references",
        "request path correctness",
        "per-role wiring consistency",
    ], size=15)
    add_connector(slide, Inches(6.12), Inches(4.02), Inches(7.10), Inches(4.02), GREEN, 4)
    add_note(slide, "The platform value is not fewer YAML files. The platform value is a cleaner operational ownership boundary.")


def closing_slide():
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, NAVY)
    add_textbox(slide, Inches(1.0), Inches(1.12), Inches(11.3), Inches(0.82), "Why This Matters Operationally", 30, True,
                WHITE, PP_ALIGN.CENTER, fill=None, line=False, font="Aptos Display")
    add_textbox(slide, Inches(1.35), Inches(2.20), Inches(10.65), Inches(2.75),
                "• P/D is useful because prefill and decode have different resource profiles.\n\n• llm-d is useful because routing and scheduling need role awareness.\n\n• KAITO is useful because platform teams need a Kubernetes-native control-plane abstraction.\n\n• Together they turn P/D from a manual stack into a repeatable platform workflow.",
                21, False, WHITE, fill=None, line=False)
    add_textbox(slide, Inches(1.48), Inches(5.65), Inches(10.35), Inches(0.68),
                "KAITO turns llm-d-style prefill/decode disaggregation from a manual routing stack into a declarative Kubernetes workflow.",
                20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)


def main():
    title_slide()
    slide_18_division_of_labor()
    slide_19_anchor_architecture()
    slide_20_mri_object()
    slide_21_kaito_generates()
    slide_22_request_flow()
    slide_23_sidecar()
    slide_24_runtime_contracts()
    slide_25_operationalizes()
    slide_26_users_vs_platform()
    closing_slide()
    prs.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
