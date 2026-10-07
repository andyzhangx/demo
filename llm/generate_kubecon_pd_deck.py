#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "kubecon-na-2026-pd-disaggregation.md"
OUT_PATH = ROOT / "kubecon-na-2026-pd-disaggregation.pptx"

TITLE = "Prefill Here, Decode There"
SUBTITLE = "Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d"
EVENT = "KubeCon + CloudNativeCon North America 2026"

BG = RGBColor(245, 247, 250)
NAVY = RGBColor(15, 23, 42)
BLUE = RGBColor(37, 99, 235)
LIGHT_BLUE = RGBColor(219, 234, 254)
ORANGE = RGBColor(234, 88, 12)
LIGHT_ORANGE = RGBColor(255, 237, 213)
GREEN = RGBColor(22, 163, 74)
LIGHT_GREEN = RGBColor(220, 252, 231)
GRAY = RGBColor(71, 85, 105)
MID = RGBColor(148, 163, 184)
WHITE = RGBColor(255, 255, 255)
RED = RGBColor(220, 38, 38)
LIGHT_RED = RGBColor(254, 226, 226)


@dataclass
class SlideSection:
    number: int
    title: str
    lead: List[str]
    bullets: List[str]
    visual: str
    speaker: List[str]


def deck_no(section: SlideSection) -> int:
    return getattr(section, "deck_no", section.number)


def set_bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(slide, x, y, w, h, text="", font_size=20, bold=False, color=NAVY,
               align=PP_ALIGN.LEFT, fill=None, line=None, radius=False,
               margin=0.08, name=None):
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    box = slide.shapes.add_shape(shape_type, x, y, w, h)
    if fill is None or fill is False:
        box.fill.background()
    else:
        box.fill.solid()
        box.fill.fore_color.rgb = fill
    if line is None:
        box.line.color.rgb = MID
        box.line.width = Pt(1)
    elif line is False:
        box.line.fill.background()
    else:
        box.line.color.rgb = line
        box.line.width = Pt(1.25)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    font = run.font
    font.size = Pt(font_size)
    font.bold = bold
    font.color.rgb = color
    font.name = "Aptos"
    p.alignment = align
    if name:
        box.name = name
    return box


def add_connector(slide, x1, y1, x2, y2, color=BLUE, width=2):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    return conn


def add_title_banner(slide, title: str, num: int | None = None):
    banner = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.75))
    banner.fill.solid()
    banner.fill.fore_color.rgb = NAVY
    banner.line.fill.background()
    tf = banner.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    if num is not None:
        r = p.add_run()
        r.text = f"{num:02d}  "
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = LIGHT_BLUE
        r.font.name = "Aptos"
    r2 = p.add_run()
    r2.text = title
    r2.font.size = Pt(24)
    r2.font.bold = True
    r2.font.color.rgb = WHITE
    r2.font.name = "Aptos Display"


def add_footer(slide, left="andyzhangx/demo · generated from markdown", right="AKS / KAITO / llm-d"):
    tb = slide.shapes.add_textbox(Inches(0.4), Inches(7.1), Inches(12.5), Inches(0.25))
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = left
    r.font.size = Pt(9)
    r.font.color.rgb = MID
    r.font.name = "Aptos"
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.RIGHT
    r2 = p2.add_run()
    r2.text = right
    r2.font.size = Pt(9)
    r2.font.color.rgb = MID
    r2.font.name = "Aptos"


def clean_bullet(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"\1", text).replace("**", "").strip()


def add_bullets_content(slide, lead: List[str], bullets: List[str], visual: str | None = None):
    x = Inches(0.6)
    y = Inches(1.05)
    w = Inches(12.15)
    h = Inches(5.7)
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)

    first = True
    for para in lead:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = clean_bullet(para)
        p.font.size = Pt(20)
        p.font.color.rgb = NAVY
        p.font.bold = True
        p.space_after = Pt(8)
    for b in bullets:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = clean_bullet(b)
        p.level = 0
        p.bullet = True
        p.font.size = Pt(22)
        p.font.color.rgb = NAVY
        p.space_after = Pt(6)
    if visual:
        box = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(8.4), Inches(5.8), Inches(4.3), Inches(0.8))
        box.fill.solid()
        box.fill.fore_color.rgb = WHITE
        box.line.color.rgb = MID
        tfv = box.text_frame
        tfv.clear()
        p = tfv.paragraphs[0]
        p.text = f"Visual cue: {visual}"
        p.font.size = Pt(11)
        p.font.color.rgb = GRAY
        p.alignment = PP_ALIGN.CENTER


def parse_sections(md_text: str) -> List[SlideSection]:
    pattern = re.compile(r"^### Slide (\d+) — (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(md_text))
    sections: List[SlideSection] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[start:end].strip()
        title = m.group(2).strip()
        number = int(m.group(1))
        visual = ""
        speaker: List[str] = []
        if "**Suggested visual:**" in body:
            pre, rest = body.split("**Suggested visual:**", 1)
            visual = rest.split("**Speaker note:**", 1)[0].strip().replace("\n", " ")
        else:
            pre = body
        if "**Speaker note:**" in body:
            sp = body.split("**Speaker note:**", 1)[1].strip()
            speaker = [clean_bullet(line[2:]) for line in sp.splitlines() if line.strip().startswith("- ")]
        lead: List[str] = []
        bullets: List[str] = []
        for raw in pre.splitlines():
            line = raw.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("- "):
                bullets.append(line[2:].strip())
            else:
                lead.append(line)
        sections.append(SlideSection(number, title, lead, bullets, visual, speaker))
    return sections


def add_title_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, NAVY)
    accent = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.18))
    accent.fill.solid(); accent.fill.fore_color.rgb = ORANGE; accent.line.fill.background()
    add_textbox(slide, Inches(0.8), Inches(1.0), Inches(11.8), Inches(1.1), TITLE, 28, True, WHITE, radius=False, line=False)
    add_textbox(slide, Inches(0.82), Inches(2.0), Inches(11.5), Inches(0.9), SUBTITLE, 22, False, LIGHT_BLUE, radius=False, line=False)
    add_textbox(slide, Inches(0.82), Inches(3.1), Inches(5.8), Inches(2.2),
                "KubeCon + CloudNativeCon North America 2026\n\nGenerated from llm/kubecon-na-2026-pd-disaggregation.md\n\nFocus: KAITO + llm-d + P/D + KEDA autoscaling", 18, False, WHITE, fill=False, line=False)
    add_textbox(slide, Inches(7.5), Inches(2.8), Inches(4.8), Inches(2.4), "prefill\n⬇\nKV handoff\n⬇\ndecode", 24, True, WHITE, align=PP_ALIGN.CENTER, fill=BLUE, line=False, radius=True)
    add_footer(slide, left=EVENT, right="generated deck")


def add_core_question_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(0.9), Inches(1.4), Inches(11.5), Inches(1.3),
                "Why does one LLM request turn into two different systems problems?", 28, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(1.1), Inches(3.0), Inches(4.8), Inches(2.2), "Prefill\ncompute-heavy\nTTFT-sensitive", 24, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_ORANGE, line=ORANGE, radius=True)
    add_textbox(slide, Inches(7.4), Inches(3.0), Inches(4.8), Inches(2.2), "Decode\nmemory/KV heavy\nthroughput-sensitive", 24, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_BLUE, line=BLUE, radius=True)
    add_connector(slide, Inches(5.95), Inches(4.1), Inches(7.35), Inches(4.1), ORANGE, 3)
    add_footer(slide)


def add_two_phase_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(0.9), Inches(2.2), Inches(5.2), Inches(1.8), "Prefill", 30, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_ORANGE, line=ORANGE, radius=True)
    add_textbox(slide, Inches(7.2), Inches(2.2), Inches(5.2), Inches(1.8), "Decode", 30, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_BLUE, line=BLUE, radius=True)
    add_connector(slide, Inches(6.1), Inches(3.1), Inches(7.15), Inches(3.1), BLUE, 4)
    add_textbox(slide, Inches(2.35), Inches(4.5), Inches(8.4), Inches(1.0), "One request. Two phases. Two very different bottlenecks.", 24, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_footer(slide)


def add_object_ladder_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    items = [
        ("Workspace", "run a model workload", LIGHT_BLUE, BLUE),
        ("InferenceSet", "replicas + autoscaling", LIGHT_GREEN, GREEN),
        ("InferencePool", "inference-aware routing", LIGHT_ORANGE, ORANGE),
        ("MultiRoleInference", "distributed topology", WHITE, NAVY),
    ]
    x = Inches(0.8)
    y = Inches(2.0)
    box_w = Inches(2.75)
    gap = Inches(0.35)
    prev_right = None
    for i, (name, desc, fill, line) in enumerate(items):
        bx = x + i * (box_w + gap)
        add_textbox(slide, bx, y, box_w, Inches(1.8), f"{name}\n{desc}", 22 if i < 3 else 20, True, NAVY, PP_ALIGN.CENTER, fill=fill, line=line, radius=True)
        if prev_right is not None:
            add_connector(slide, prev_right, y + Inches(0.9), bx, y + Inches(0.9), BLUE, 3)
        prev_right = bx + box_w
    add_textbox(slide, Inches(1.0), Inches(4.7), Inches(11.2), Inches(1.2),
                "KAITO adds higher-level Kubernetes objects as the serving problem gets harder.", 22, True, NAVY, PP_ALIGN.CENTER, fill=False, line=False)
    add_footer(slide)


def add_division_of_labor_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(0.9), Inches(2.1), Inches(3.2), Inches(2.2), "KAITO\ncontrol-plane abstraction\norchestration", 24, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_BLUE, line=BLUE, radius=True)
    add_textbox(slide, Inches(5.0), Inches(2.1), Inches(3.2), Inches(2.2), "GWIE\ninference routing contract", 24, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_GREEN, line=GREEN, radius=True)
    add_textbox(slide, Inches(9.1), Inches(2.1), Inches(3.2), Inches(2.2), "llm-d Router\nrouting + scheduling\nEPP", 24, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_ORANGE, line=ORANGE, radius=True)
    add_connector(slide, Inches(4.1), Inches(3.2), Inches(4.95), Inches(3.2), BLUE, 3)
    add_connector(slide, Inches(8.2), Inches(3.2), Inches(9.05), Inches(3.2), BLUE, 3)
    add_footer(slide)


def add_architecture_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(0.5), Inches(2.9), Inches(1.3), Inches(1.0), "Client", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(2.0), Inches(2.9), Inches(1.6), Inches(1.0), "Gateway", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(3.9), Inches(2.7), Inches(2.1), Inches(1.4), "InferencePool\n+ EPP", 20, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_GREEN, line=GREEN, radius=True)
    add_textbox(slide, Inches(6.5), Inches(1.7), Inches(2.5), Inches(1.5), "Prefill\nchild InferenceSet", 20, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_ORANGE, line=ORANGE, radius=True)
    add_textbox(slide, Inches(6.5), Inches(4.0), Inches(2.5), Inches(1.5), "Decode\nchild InferenceSet", 20, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_BLUE, line=BLUE, radius=True)
    add_textbox(slide, Inches(10.0), Inches(2.7), Inches(2.5), Inches(1.4), "KV path\nNIXL / sidecar", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_connector(slide, Inches(1.8), Inches(3.4), Inches(2.0), Inches(3.4), BLUE, 3)
    add_connector(slide, Inches(3.6), Inches(3.4), Inches(3.9), Inches(3.4), BLUE, 3)
    add_connector(slide, Inches(6.0), Inches(3.2), Inches(6.5), Inches(2.45), ORANGE, 2)
    add_connector(slide, Inches(6.0), Inches(3.6), Inches(6.5), Inches(4.75), BLUE, 2)
    add_connector(slide, Inches(9.0), Inches(2.45), Inches(10.0), Inches(3.0), GRAY, 2)
    add_connector(slide, Inches(9.0), Inches(4.75), Inches(10.0), Inches(3.8), GRAY, 2)
    add_footer(slide)


def add_compare_signals_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(0.8), Inches(1.6), Inches(5.5), Inches(0.7), "Classic CPU-era autoscaling", 22, True, WHITE, PP_ALIGN.CENTER, fill=GRAY, line=False, radius=True)
    add_textbox(slide, Inches(7.0), Inches(1.6), Inches(5.5), Inches(0.7), "LLM inference autoscaling", 22, True, WHITE, PP_ALIGN.CENTER, fill=NAVY, line=False, radius=True)
    add_textbox(slide, Inches(0.8), Inches(2.5), Inches(5.5), Inches(3.1),
                "• CPU utilization\n• memory utilization\n• request-per-pod as a rough proxy\n\nWorks well for stateless web workloads.", 18, False, NAVY, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(7.0), Inches(2.5), Inches(5.5), Inches(3.1),
                "• waiting requests\n• token generation pressure\n• active KV memory\n• prompt / generation mix\n\nCPU can look fine while TTFT is already bad.", 18, False, NAVY, fill=WHITE, line=BLUE, radius=True)
    add_footer(slide)


def add_keda_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(4.8), Inches(2.5), Inches(3.7), Inches(1.4), "KEDA", 28, True, WHITE, PP_ALIGN.CENTER, fill=BLUE, line=False, radius=True)
    add_textbox(slide, Inches(0.8), Inches(1.3), Inches(2.8), Inches(1.1), "external metrics", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(0.8), Inches(4.3), Inches(2.8), Inches(1.1), "cron triggers", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(9.7), Inches(1.3), Inches(2.8), Inches(1.1), "scale decisions", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_textbox(slide, Inches(9.7), Inches(4.3), Inches(2.8), Inches(1.1), "inference workloads", 20, True, NAVY, PP_ALIGN.CENTER, fill=WHITE, line=MID, radius=True)
    add_connector(slide, Inches(3.6), Inches(1.85), Inches(4.8), Inches(3.0), GREEN, 2)
    add_connector(slide, Inches(3.6), Inches(4.85), Inches(4.8), Inches(3.4), GREEN, 2)
    add_connector(slide, Inches(8.5), Inches(3.0), Inches(9.7), Inches(1.85), GREEN, 2)
    add_connector(slide, Inches(8.5), Inches(3.4), Inches(9.7), Inches(4.85), GREEN, 2)
    add_footer(slide)


def add_kaito_keda_flow(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    labels = [
        ("InferenceSet", LIGHT_BLUE, BLUE),
        ("annotations\nscaledobject.kaito.sh/*", WHITE, MID),
        ("KEDA KAITO\nscaler", LIGHT_GREEN, GREEN),
        ("ScaledObject\n+ HPA", LIGHT_ORANGE, ORANGE),
        ("replicas", WHITE, MID),
    ]
    x = Inches(0.5)
    for i, (label, fill, line) in enumerate(labels):
        bx = x + Inches(2.45) * i
        add_textbox(slide, bx, Inches(2.7), Inches(2.1), Inches(1.4), label, 18, True, NAVY, PP_ALIGN.CENTER, fill=fill, line=line, radius=True)
        if i < len(labels) - 1:
            add_connector(slide, bx + Inches(2.1), Inches(3.4), bx + Inches(2.45), Inches(3.4), BLUE, 3)
    add_textbox(slide, Inches(1.2), Inches(4.7), Inches(11.0), Inches(0.8),
                "Directly scrapes inference metrics from vLLM pods — no separate Prometheus dependency required for this flow.", 18, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_footer(slide)


def add_role_scaling_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(0.9), Inches(1.8), Inches(5.4), Inches(3.8),
                "Prefill\n\nScale on prompt pressure\n\nExample signal:\nvllm:num_requests_waiting\n\nGoal: protect TTFT", 22, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_ORANGE, line=ORANGE, radius=True)
    add_textbox(slide, Inches(7.0), Inches(1.8), Inches(5.4), Inches(3.8),
                "Decode\n\nScale on sustained generation pressure\n\nExample signals:\nKV/cache pressure\nsteady decode saturation\n\nGoal: protect throughput", 22, True, NAVY, PP_ALIGN.CENTER, fill=LIGHT_BLUE, line=BLUE, radius=True)
    add_textbox(slide, Inches(2.7), Inches(6.0), Inches(8.0), Inches(0.8),
                "Once prefill and decode are separate backends, they should scale like separate backends.", 18, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_footer(slide)


def add_matrix_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_textbox(slide, Inches(4.0), Inches(1.0), Inches(5.3), Inches(0.6), "KV transfer cost / fabric quality", 18, True, NAVY, PP_ALIGN.CENTER, line=False)
    add_textbox(slide, Inches(0.2), Inches(3.0), Inches(1.0), Inches(1.7), "Prefill / decode difference", 16, True, NAVY, PP_ALIGN.CENTER, line=False)
    # matrix cells
    cells = [
        (Inches(1.3), Inches(1.8), Inches(5.2), Inches(2.0), LIGHT_RED, RED, "Stay aggregated", "Small models, short prompts, low concurrency, simple traffic."),
        (Inches(6.7), Inches(1.8), Inches(5.2), Inches(2.0), WHITE, MID, "Usually stay aggregated", "You can try P/D, but the operational gain is often limited."),
        (Inches(1.3), Inches(4.1), Inches(5.2), Inches(2.0), LIGHT_ORANGE, ORANGE, "Maybe later", "Value may exist, but weak transfer paths will erase it."),
        (Inches(6.7), Inches(4.1), Inches(5.2), Inches(2.0), LIGHT_GREEN, GREEN, "Strong candidate for P/D", "Long prompts, retrieval-heavy traffic, long generations, high concurrency, or different scaling / parallelism needs."),
    ]
    for x, y, w, h, fill, line, head, body in cells:
        add_textbox(slide, x, y, w, h, f"{head}\n\n{body}", 18, True, NAVY, PP_ALIGN.CENTER, fill=fill, line=line, radius=True)
    add_textbox(slide, Inches(1.3), Inches(1.25), Inches(5.2), Inches(0.4), "transfer expensive / weak", 14, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_textbox(slide, Inches(6.7), Inches(1.25), Inches(5.2), Inches(0.4), "transfer cheap / strong", 14, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_textbox(slide, Inches(0.15), Inches(2.25), Inches(1.0), Inches(1.2), "similar", 14, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_textbox(slide, Inches(0.12), Inches(4.65), Inches(1.05), Inches(1.0), "meaningfully\ndifferent", 14, True, GRAY, PP_ALIGN.CENTER, line=False)
    add_footer(slide)


def add_generic_slide(prs: Presentation, section: SlideSection):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_title_banner(slide, section.title, deck_no(section))
    add_bullets_content(slide, section.lead, section.bullets, section.visual)
    add_footer(slide)


def build_presentation(sections: List[SlideSection]) -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    add_title_slide(prs)

    custom = {
        2: add_core_question_slide,
        3: add_two_phase_slide,
        11: add_object_ladder_slide,
        12: add_object_ladder_slide,
        18: add_division_of_labor_slide,
        19: add_architecture_slide,
        26: add_compare_signals_slide,
        27: add_keda_slide,
        28: add_kaito_keda_flow,
        29: add_role_scaling_slide,
        34: add_matrix_slide,
    }
    filtered = [sec for sec in sections if sec.number != 1]
    for idx, sec in enumerate(filtered, 1):
        sec.deck_no = idx
        fn = custom.get(sec.number, add_generic_slide)
        fn(prs, sec)
    return prs


def main():
    md_text = MD_PATH.read_text(encoding="utf-8")
    sections = parse_sections(md_text)
    prs = build_presentation(sections)
    prs.save(str(OUT_PATH))
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
