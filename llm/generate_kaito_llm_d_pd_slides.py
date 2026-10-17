#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "kaito-llm-d-pd-slides.pptx"

NAVY = RGBColor(15, 23, 42)
SLATE = RGBColor(51, 65, 85)
MUTED = RGBColor(100, 116, 139)
WHITE = RGBColor(255, 255, 255)
BG = RGBColor(248, 250, 252)
MID = RGBColor(203, 213, 225)
BLUE = RGBColor(37, 99, 235)
BLUE_SOFT = RGBColor(219, 234, 254)
ORANGE = RGBColor(234, 88, 12)
ORANGE_SOFT = RGBColor(255, 237, 213)
GREEN = RGBColor(22, 163, 74)
GREEN_SOFT = RGBColor(220, 252, 231)
PURPLE = RGBColor(109, 40, 217)
PURPLE_SOFT = RGBColor(237, 233, 254)
GRAY_SOFT = RGBColor(241, 245, 249)
RED = RGBColor(220, 38, 38)
RED_SOFT = RGBColor(254, 226, 226)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def shape(slide, kind, x, y, w, h, fill=None, line=MID, width=1.2):
    s = slide.shapes.add_shape(kind, x, y, w, h)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is False:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(width)
    return s


def textbox(slide, x, y, w, h, text, size=18, bold=False, color=NAVY, align=PP_ALIGN.LEFT,
            fill=None, line=False, radius=False, margin=0.08, font="Aptos"):
    kind = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    box = shape(slide, kind, x, y, w, h, fill=fill, line=line)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
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


def bullets(slide, x, y, w, h, items, size=16, color=SLATE):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(6)
        p.bullet = True
    return tb


def numbered(slide, x, y, w, h, items, size=15):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items, start=1):
        p = tf.paragraphs[0] if i == 1 else tf.add_paragraph()
        p.text = f"{i}. {item}"
        p.font.size = Pt(size)
        p.font.color.rgb = SLATE
        p.space_after = Pt(5)
    return tb


def header(slide, num, title, accent=BLUE):
    shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.84), fill=NAVY, line=False)
    shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, Inches(0.80), Inches(13.333), Inches(0.04), fill=accent, line=False)
    textbox(slide, Inches(0.38), Inches(0.18), Inches(0.60), Inches(0.34), f"{num}", size=14, bold=True,
            color=NAVY, align=PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
    textbox(slide, Inches(1.10), Inches(0.12), Inches(11.5), Inches(0.42), title, size=24, bold=True,
            color=WHITE, fill=None, line=False, font="Aptos Display")


def connector(slide, x1, y1, x2, y2, color=BLUE, width=2.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = color
    c.line.width = Pt(width)
    return c


def note_box(slide, text):
    textbox(slide, Inches(0.65), Inches(6.70), Inches(12.0), Inches(0.42), text, size=13,
            color=NAVY, fill=GRAY_SOFT, line=MID, radius=True)


# Title slide
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide, NAVY)
shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12), fill=ORANGE, line=False)
textbox(slide, Inches(0.75), Inches(0.70), Inches(8.0), Inches(1.0), "KAITO + llm-d", size=30, bold=True, color=WHITE, fill=None, line=False, font="Aptos Display")
textbox(slide, Inches(0.75), Inches(1.55), Inches(10.6), Inches(0.95), "How They Support Prefill/Decode Disaggregation", size=26, bold=True, color=WHITE, fill=None, line=False, font="Aptos Display")
textbox(slide, Inches(0.78), Inches(2.65), Inches(8.6), Inches(0.6), "A slide section generated from llm/kaito-llm-d-pd-slides.md", size=16, color=RGBColor(203,213,225), fill=None, line=False)
textbox(slide, Inches(0.78), Inches(4.05), Inches(5.3), Inches(1.0), "Control plane: KAITO\nRouting contract: GWIE\nScheduling substrate: llm-d Router\nRuntime + KV path: vLLM + NIXL", size=18, color=WHITE, fill=None, line=False)
# mini architecture visual
textbox(slide, Inches(9.00), Inches(1.20), Inches(3.30), Inches(0.45), "P/D platform stack", size=16, bold=True, color=BLUE, align=PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)
textbox(slide, Inches(9.40), Inches(2.00), Inches(2.50), Inches(0.55), "MultiRoleInference", size=20, bold=True, align=PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN)
textbox(slide, Inches(9.40), Inches(3.05), Inches(2.50), Inches(0.55), "InferencePool + GWIE", size=18, bold=True, align=PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE)
textbox(slide, Inches(9.40), Inches(4.10), Inches(2.50), Inches(0.55), "llm-d Router EPP", size=20, bold=True, align=PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE)
textbox(slide, Inches(9.40), Inches(5.15), Inches(2.50), Inches(0.55), "vLLM + NIXL", size=20, bold=True, align=PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE)
connector(slide, Inches(10.65), Inches(2.55), Inches(10.65), Inches(3.05), GREEN, 3)
connector(slide, Inches(10.65), Inches(3.60), Inches(10.65), Inches(4.10), BLUE, 3)
connector(slide, Inches(10.65), Inches(4.65), Inches(10.65), Inches(5.15), ORANGE, 3)

# Slide 18
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 18, "KAITO + llm-d + GWIE: Division of Labor")
textbox(slide, Inches(0.75), Inches(1.05), Inches(5.0), Inches(0.45), "Three layers, three responsibilities, one usable P/D platform.", size=16, color=MUTED, fill=None, line=False)
bullets(slide, Inches(0.80), Inches(1.65), Inches(5.1), Inches(3.4), [
    "KAITO = declarative API and Kubernetes orchestration for P/D topology",
    "GWIE = inference-aware routing contract between gateway and model backends",
    "llm-d Router = EPP-based endpoint selection and P/D-aware scheduling logic",
    "InferencePool = binds gateway-facing traffic to the serving backends",
], size=17)
# layered diagram
textbox(slide, Inches(7.0), Inches(1.30), Inches(5.3), Inches(0.45), "Suggested architecture view", size=16, bold=True, color=SLATE, align=PP_ALIGN.CENTER, fill=None, line=False)
textbox(slide, Inches(7.35), Inches(1.95), Inches(4.6), Inches(0.75), "User API layer\nMultiRoleInference", size=20, bold=True, align=PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
textbox(slide, Inches(7.15), Inches(3.10), Inches(5.0), Inches(0.95), "Kubernetes routing contract\nInferencePool + Gateway API Inference Extension", size=18, bold=True, align=PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
textbox(slide, Inches(6.85), Inches(4.45), Inches(5.6), Inches(1.15), "Execution and scheduling\nllm-d Router EPP + prefill workers + decode workers + KV transfer", size=17, bold=True, align=PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
connector(slide, Inches(9.65), Inches(2.70), Inches(9.65), Inches(3.10), GREEN, 3)
connector(slide, Inches(9.65), Inches(4.05), Inches(9.65), Inches(4.45), BLUE, 3)
note_box(slide, "KAITO makes P/D operable. llm-d makes it routable. GWIE makes it Kubernetes-native.")

# Slide 19
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 19, "One MultiRoleInference Object Describes the Topology", accent=GREEN)
textbox(slide, Inches(0.75), Inches(1.05), Inches(6.0), Inches(0.4), "Users declare intent once; the platform expands it into a runnable P/D system.", size=16, color=MUTED, fill=None, line=False)
# yaml panel
shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(1.6), Inches(5.25), Inches(4.65), fill=NAVY, line=False)
textbox(slide, Inches(0.98), Inches(1.90), Inches(4.8), Inches(3.9), "apiVersion: kaito.sh/v1alpha1\nkind: MultiRoleInference\nmetadata:\n  name: phi-4-mini\nspec:\n  model:\n    name: phi-4-mini-instruct\n  roles:\n    - type: prefill\n      replicas: 1\n      instanceType: Standard_NC24ads_A100_v4\n    - type: decode\n      replicas: 1\n      instanceType: Standard_NC24ads_A100_v4", size=15, color=WHITE, fill=None, line=False, font="Consolas")
# arrow and topology
connector(slide, Inches(6.15), Inches(3.9), Inches(7.1), Inches(3.9), GREEN, 4)
textbox(slide, Inches(7.35), Inches(2.0), Inches(2.0), Inches(0.6), "prefill", size=20, bold=True, align=PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
textbox(slide, Inches(9.85), Inches(2.0), Inches(2.0), Inches(0.6), "decode", size=20, bold=True, align=PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
textbox(slide, Inches(8.60), Inches(3.25), Inches(2.0), Inches(0.6), "InferencePool", size=18, bold=True, align=PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
connector(slide, Inches(9.55), Inches(2.60), Inches(9.55), Inches(3.25), PURPLE, 3)
connector(slide, Inches(10.85), Inches(3.55), Inches(10.85), Inches(2.60), PURPLE, 3)
bullets(slide, Inches(7.15), Inches(4.55), Inches(5.0), Inches(1.5), [
    "One logical service with role-specific backends",
    "Role-specific scaling intent for prefill and decode",
    "Users describe what they want, not how to wire the stack",
], size=15)
note_box(slide, "The CRD is the product surface. Users express topology intent; controllers own the plumbing.")

# Slide 20
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 20, "What KAITO Automatically Generates for P/D", accent=ORANGE)
textbox(slide, Inches(0.75), Inches(1.05), Inches(5.6), Inches(0.4), "KAITO acts like the control-plane compiler for the topology.", size=16, color=MUTED, fill=None, line=False)
textbox(slide, Inches(4.95), Inches(3.20), Inches(3.2), Inches(0.7), "MultiRoleInference", size=22, bold=True, align=PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
boxes = [
    (Inches(1.0), Inches(1.95), "InferenceSet\n(prefill)", ORANGE_SOFT, ORANGE),
    (Inches(1.0), Inches(4.55), "InferenceSet\n(decode)", BLUE_SOFT, BLUE),
    (Inches(8.8), Inches(1.95), "InferencePool", GREEN_SOFT, GREEN),
    (Inches(8.6), Inches(3.25), "llm-d Router\nEPP", ORANGE_SOFT, ORANGE),
    (Inches(8.35), Inches(4.55), "sidecar injection", PURPLE_SOFT, PURPLE),
    (Inches(4.95), Inches(5.0), "NIXL env wiring", BLUE_SOFT, BLUE),
]
for x, y, label, fillc, linec in boxes:
    textbox(slide, x, y, Inches(2.4), Inches(0.78), label, size=18, bold=True, align=PP_ALIGN.CENTER, fill=fillc, line=linec, radius=True)
# connectors
for x, y, *_ in boxes:
    connector(slide, Inches(6.55), Inches(3.55), x + Inches(1.2), y + Inches(0.39), GREEN if x < Inches(6) else BLUE, 2.3)
note_box(slide, "KAITO does not replace llm-d. It generates, owns, and keeps the llm-d-facing resources consistent.")

# Slide 21
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 21, "How a P/D Request Actually Executes", accent=PURPLE)
textbox(slide, Inches(0.75), Inches(1.05), Inches(5.7), Inches(0.4), "One endpoint for the user; multiple coordinated steps underneath.", size=16, color=MUTED, fill=None, line=False)
# request flow diagram top
labels = [
    ("Client", Inches(0.75), Inches(1.75), GREEN_SOFT, GREEN),
    ("Gateway", Inches(2.15), Inches(1.75), BLUE_SOFT, BLUE),
    ("InferencePool", Inches(3.65), Inches(1.75), GREEN_SOFT, GREEN),
    ("llm-d Router EPP", Inches(5.45), Inches(1.75), ORANGE_SOFT, ORANGE),
    ("Decode sidecar", Inches(7.65), Inches(1.75), PURPLE_SOFT, PURPLE),
    ("Decode vLLM", Inches(10.00), Inches(1.75), BLUE_SOFT, BLUE),
]
for t, x, y, fillc, linec in labels:
    textbox(slide, x, y, Inches(1.35), Inches(0.58), t, size=15, bold=True, align=PP_ALIGN.CENTER, fill=fillc, line=linec, radius=True)
for i in range(len(labels)-1):
    _, x1, y1, *_ = labels[i]
    _, x2, y2, *_ = labels[i+1]
    connector(slide, x1 + Inches(1.35), y1 + Inches(0.29), x2, y2 + Inches(0.29), BLUE, 2.4)
textbox(slide, Inches(7.65), Inches(3.05), Inches(1.35), Inches(0.58), "Prefill", size=15, bold=True, align=PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
connector(slide, Inches(8.30), Inches(2.33), Inches(8.30), Inches(3.05), PURPLE, 2.4)
connector(slide, Inches(9.00), Inches(3.34), Inches(10.00), Inches(2.33), PURPLE, 2.4)
textbox(slide, Inches(9.05), Inches(3.15), Inches(1.2), Inches(0.38), "NIXL KV", size=13, bold=True, align=PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)
numbered(slide, Inches(0.75), Inches(4.05), Inches(8.4), Inches(2.3), [
    "Gateway / HTTPRoute forwards to the InferencePool for the model",
    "llm-d Router EPP decides whether prefill work is needed and selects the role-specific backends",
    "The request lands on a decode pod, whose sidecar coordinates prefill on the selected prefill pod",
    "KV cache is transferred directly to decode via NIXL, and local decode vLLM continues generation",
], size=15)
textbox(slide, Inches(9.45), Inches(4.15), Inches(2.9), Inches(1.55), "• Decode is the coordination point\n• Prefill is selected only when it helps\n• KV transfer bridges the two phases", size=15, color=SLATE, fill=WHITE, line=MID, radius=True)
note_box(slide, "The user sees one endpoint. The platform coordinates routing, prefill placement, KV movement, and decode execution across multiple pods.")

# Slide 22
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 22, "Why the Routing Sidecar Lives on Decode Pods", accent=BLUE)
textbox(slide, Inches(0.75), Inches(1.05), Inches(6.5), Inches(0.4), "Sidecar placement is an execution design choice, not an incidental implementation detail.", size=16, color=MUTED, fill=None, line=False)
# pod cutaway
shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(7.35), Inches(1.65), Inches(4.8), Inches(4.7), fill=WHITE, line=BLUE, width=2)
textbox(slide, Inches(8.65), Inches(1.85), Inches(2.2), Inches(0.4), "Decode Pod", size=22, bold=True, align=PP_ALIGN.CENTER, fill=None, line=False)
textbox(slide, Inches(7.85), Inches(2.65), Inches(3.75), Inches(0.82), "Routing sidecar\nport 5000", size=20, bold=True, align=PP_ALIGN.CENTER, fill=PURPLE_SOFT, line=PURPLE, radius=True)
textbox(slide, Inches(7.85), Inches(4.15), Inches(3.75), Inches(0.82), "Local decode vLLM\nport 5001", size=20, bold=True, align=PP_ALIGN.CENTER, fill=BLUE_SOFT, line=BLUE, radius=True)
connector(slide, Inches(9.72), Inches(3.47), Inches(9.72), Inches(4.15), PURPLE, 3)
textbox(slide, Inches(6.25), Inches(2.82), Inches(1.1), Inches(0.42), "from EPP", size=13, bold=True, align=PP_ALIGN.CENTER, fill=GREEN_SOFT, line=GREEN, radius=True)
connector(slide, Inches(7.35), Inches(3.05), Inches(6.95), Inches(3.05), GREEN, 2.6)
textbox(slide, Inches(11.9), Inches(3.42), Inches(1.0), Inches(0.42), "NIXL KV", size=13, bold=True, align=PP_ALIGN.CENTER, fill=ORANGE_SOFT, line=ORANGE, radius=True)
connector(slide, Inches(11.60), Inches(3.63), Inches(11.95), Inches(4.56), ORANGE, 2.6)
bullets(slide, Inches(0.78), Inches(1.80), Inches(5.8), Inches(3.8), [
    "Decode pods are the final response point for user traffic",
    "The routing sidecar receives the EPP decision, coordinates prefill, waits for KV handoff, then forwards to local vLLM",
    "This keeps the external routing contract cleaner: sidecar on 5000, local decode vLLM on 5001",
    "Prefill pods stay simpler and focus only on prompt processing",
], size=16)
note_box(slide, "Decode-side sidecar placement turns the decode pod into the coordination point for P/D execution.")

# Slide 23
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 23, "The Runtime Contracts That Make P/D Actually Work", accent=RED)
textbox(slide, Inches(0.75), Inches(1.05), Inches(5.8), Inches(0.4), "Most real failures here are contract bugs, not model bugs.", size=16, color=MUTED, fill=None, line=False)
rows = [
    ("Routing sidecar", "No", "Yes", "Decode is the coordination point"),
    ("vLLM port", "5000", "5001", "Avoid sidecar ↔ local vLLM collision"),
    ("Sidecar ingress port", "N/A", "5000", "Gives decode a stable external entry point"),
    ("Role label", "prefill", "decode", "EPP filters workers by role"),
    ("NIXL side-channel host", "Pod IP", "Pod IP", "KV handoff must advertise a reachable address"),
    ("InferencePool targetPort", "Shared", "Shared", "Gateway/EPP expect consistent routing semantics"),
]
# simple grid using boxes
x0 = Inches(0.75)
y0 = Inches(1.75)
widths = [Inches(2.4), Inches(1.2), Inches(1.2), Inches(4.7)]
headers = ["Contract", "Prefill", "Decode", "Why it matters"]
x = x0
for w, head in zip(widths, headers):
    textbox(slide, x, y0, w, Inches(0.48), head, size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER, fill=NAVY, line=False)
    x += w
for r, row in enumerate(rows, start=1):
    x = x0
    fill = WHITE if r % 2 else GRAY_SOFT
    for idx, (w, cell) in enumerate(zip(widths, row)):
        textbox(slide, x, y0 + Inches(0.48 * r), w, Inches(0.48), cell, size=13, bold=(idx==0), align=PP_ALIGN.CENTER if idx < 3 else PP_ALIGN.LEFT, fill=fill, line=MID)
        x += w
bullets(slide, Inches(0.85), Inches(5.10), Inches(11.6), Inches(1.3), [
    "Contracts must be controller-enforced",
    "Labels are functional metadata, not decoration",
    "TargetPort is part of the serving contract",
    "Pod IP / env wiring must be automatic",
], size=14)
note_box(slide, "If these contracts are not enforced by the controller, users debug infrastructure wiring as if it were model behavior.")

# Slide 24
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 24, "KAITO Does Not Replace llm-d — It Operationalizes It", accent=ORANGE)
textbox(slide, Inches(0.75), Inches(1.05), Inches(6.3), Inches(0.4), "The two projects solve different layers of the same problem.", size=16, color=MUTED, fill=None, line=False)
# two columns
textbox(slide, Inches(1.05), Inches(1.8), Inches(4.55), Inches(0.52), "llm-d Router", size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER, fill=ORANGE, line=False, radius=True)
textbox(slide, Inches(7.75), Inches(1.8), Inches(4.55), Inches(0.52), "KAITO", size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER, fill=BLUE, line=False, radius=True)
left_items = ["EPP implementation", "endpoint picking", "scheduling profiles", "P/D-aware plugins", "routing execution", "future scheduling surface"]
right_items = ["CRD abstraction", "child resource generation", "lifecycle orchestration", "Kubernetes-native UX", "integration with InferenceSet / autoscaling", "future topology APIs"]
for i, (l, r) in enumerate(zip(left_items, right_items)):
    y = Inches(2.55 + i * 0.58)
    textbox(slide, Inches(1.0), y, Inches(4.65), Inches(0.45), l, size=15, fill=ORANGE_SOFT if i % 2 == 0 else WHITE, line=MID, radius=True)
    textbox(slide, Inches(7.70), y, Inches(4.65), Inches(0.45), r, size=15, fill=BLUE_SOFT if i % 2 == 0 else WHITE, line=MID, radius=True)
    connector(slide, Inches(5.80), y + Inches(0.225), Inches(7.55), y + Inches(0.225), PURPLE, 2.2)
note_box(slide, "This is not KAITO vs. llm-d. KAITO builds on llm-d and turns it into a cleaner Kubernetes workflow.")

# Slide 25
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide)
header(slide, 25, "What Users Manage vs. What the Platform Manages", accent=GREEN)
textbox(slide, Inches(0.75), Inches(1.05), Inches(6.4), Inches(0.4), "P/D becomes usable when the ownership boundary is clean.", size=16, color=MUTED, fill=None, line=False)
textbox(slide, Inches(0.95), Inches(1.75), Inches(5.0), Inches(0.52), "User intent", size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER, fill=GREEN, line=False, radius=True)
textbox(slide, Inches(7.35), Inches(1.75), Inches(5.0), Inches(0.52), "Platform-managed plumbing", size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER, fill=BLUE, line=False, radius=True)
bullets(slide, Inches(1.0), Inches(2.45), Inches(4.9), Inches(3.5), [
    "model choice",
    "prefill/decode role definitions",
    "replica intent",
    "instance types",
    "autoscaling intent",
    "policy-level topology decisions",
], size=16)
bullets(slide, Inches(7.40), Inches(2.45), Inches(4.85), Inches(3.8), [
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
connector(slide, Inches(6.15), Inches(3.95), Inches(7.10), Inches(3.95), GREEN, 4)
note_box(slide, "The platform value is not fewer YAML files. The platform value is a cleaner operational ownership boundary.")

# Closing transition
slide = prs.slides.add_slide(prs.slide_layouts[6])
bg(slide, NAVY)
textbox(slide, Inches(1.0), Inches(1.15), Inches(11.3), Inches(0.9), "Why This Matters Operationally", size=30, bold=True, color=WHITE, align=PP_ALIGN.CENTER, fill=None, line=False, font="Aptos Display")
textbox(slide, Inches(1.4), Inches(2.25), Inches(10.5), Inches(2.4), "• P/D is useful because prefill and decode have different resource profiles.\n\n• llm-d is useful because routing and scheduling need role awareness.\n\n• KAITO is useful because platform teams need a Kubernetes-native control-plane abstraction.\n\n• Together they turn P/D from a manual stack into a repeatable platform workflow.", size=21, color=WHITE, fill=None, line=False)
textbox(slide, Inches(1.55), Inches(5.55), Inches(10.2), Inches(0.7), "KAITO turns llm-d-style prefill/decode disaggregation from a manual routing stack into a declarative Kubernetes workflow.", size=20, bold=True, color=NAVY, align=PP_ALIGN.CENTER, fill=WHITE, line=False, radius=True)

prs.save(OUT)
print(f"wrote {OUT}")
