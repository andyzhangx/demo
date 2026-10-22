#!/usr/bin/env python3
"""Build the KubeCon NA 2026 deck using editable PowerPoint primitives.

Requires python-pptx==1.0.2. Uses editable shapes plus one attributed public
research figure. External results are not KAITO measurements; see speaker notes.
Run from any directory: python llm/generate_kubecon_pd_deck.py
"""
from pathlib import Path
import json
import math
import statistics
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'kubecon-na-2026-pd-disaggregation.pptx'
SOURCE = 'kubecon-na-2026-pd-disaggregation.md'
PD_DOC = 'https://kaito-project.github.io/kaito/docs/prefill-decode-disaggregation'
KEDA_DOC = 'https://kaito-project.github.io/kaito/docs/keda-autoscaler-inference'
AUTOSCALING_DOC = 'https://github.com/andyzhangx/demo/blob/26c3e14a340d4b0aae5c820b43087d71b85d1554/llm/kaito-llm-d/kaito-role-aware-autoscaling-for-pd.md'
VLLM_METRICS = 'https://docs.vllm.ai/en/stable/usage/metrics/'
BENCH_URL = 'https://vllm.ai/blog/2026-04-07-moriio-kv-connector'
BENCH_SHA = 'c4fa4eee56ed2c097a4e078c33955253db123018'
BENCH_RAW = f'https://github.com/vllm-project/vllm-project.github.io/blob/{BENCH_SHA}/assets/figures/2026-04-07-moriio-kv-connector/plotly-figure3.js'
BENCH = json.loads((ROOT / 'kubecon-pd-assets/benchmarks/moriio-source-data.json').read_text())
BENCH_PASSES = {key: sum(t <= 1.0 and i <= .05 for t, i in zip(BENCH[key+'_ttft'], BENCH[key+'_itl'])) for key in ('normal', 'write')}
assert BENCH_PASSES == {'normal': 29, 'write': 73}
W, H = 13.333333, 7.5
C = dict(bg='F6F8FC', ink='172941', muted='586A80', line='D9E2EE', white='FFFFFF',
         blue='2563EB', teal='087F8C', purple='7354B8', amber='AE641A', red='B5464A',
         blue_bg='EAF1FF', teal_bg='E4F4F3', purple_bg='F0EBFA', amber_bg='FFF3E1',
         dark='102039', pale='AFC3DF', green='247952')
FONT = 'Arial'
MONO = 'Courier New'
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
prs.core_properties.title = 'Prefill here, decode there'
prs.core_properties.subject = 'Kubernetes-native LLM inference disaggregation with KAITO and llm-d'
prs.core_properties.author = 'Andy Zhang'
prs.core_properties.keywords = 'KubeCon, KAITO, llm-d, prefill, decode, editable diagrams'


def color(c):
    return RGBColor.from_string(C.get(c, c))


def rect(s, x, y, w, h, fill='white', line=None, radius=False):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = color(fill)
    if line:
        sh.line.color.rgb = color(line); sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    if radius:
        sh.adjustments[0] = 0.10
    return sh


def text(s, x, y, w, h, value, size=20, ink='ink', bold=False, align=None, mono=False):
    sh = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.clear(); tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(.015)
    tf.margin_top = tf.margin_bottom = Inches(.015)
    for i, line in enumerate(value.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = MONO if mono else FONT
        p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = color(ink)
        p.space_after = Pt(5); p.space_before = Pt(0)
        if align is not None: p.alignment = align
    return sh


def arrow(s, x1, y1, x2, y2, ink='muted', dashed=False, head=True, width=2):
    sh = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    sh.line.color.rgb = color(ink); sh.line.width = Pt(width)
    ln = sh._element.spPr.get_or_add_ln()
    if dashed:
        d = OxmlElement('a:prstDash'); d.set('val', 'dash'); ln.append(d)
    if head:
        e = OxmlElement('a:tailEnd'); e.set('type', 'triangle'); e.set('w', 'med'); e.set('len', 'med'); ln.append(e)
    return sh


def route(s, pts, ink='muted', dashed=False):
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        arrow(s, *a, *b, ink, dashed, i == len(pts)-2)


def pill(s, x, y, w, value, ink='blue', fill='blue_bg'):
    rect(s, x, y, w, .34, fill, radius=True)
    text(s, x+.07, y+.035, w-.14, .26, value, 10, ink, True, PP_ALIGN.CENTER)


def node(s, x, y, w, h, title, detail='', accent='blue', size=19):
    rect(s, x, y, w, h, 'white', 'line', True)
    rect(s, x, y+.1, .055, h-.2, accent)
    th = .72 if '\n' in title else .43
    text(s, x+.15, y+.13, w-.3, th, title, size, accent, True, PP_ALIGN.CENTER)
    if detail:
        text(s, x+.16, y+.18+th, w-.32, h-th-.28, detail, 14, 'muted', align=PP_ALIGN.CENTER)


def card(s, x, y, w, h, title, body, accent='blue', tag=None, size=19):
    rect(s, x, y, w, h, 'white', 'line', True)
    rect(s, x+.18, y+.2, .38, .065, accent)
    dy = .4
    if tag:
        text(s, x+.2, y+.37, w-.4, .28, tag, 11, accent, True); dy = .78
    text(s, x+.2, y+dy, w-.4, .8 if '\n' in title else .46, title, 20, accent, True)
    by = dy + (.92 if '\n' in title else .66)
    text(s, x+.2, y+by, w-.4, h-by-.16, body, size)


def note(s, value, refs=()):
    s.notes_slide.notes_text_frame.text = (value + '\n\nNarrative source: ' + SOURCE +
        ('\nReferences:\n' + '\n'.join(refs) if refs else '') +
        '\nDesign: all diagrams, labels, tables and arrows are native editable PowerPoint objects.')


def slide(title, section, sub='', takeaway=None, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid(); s.background.fill.fore_color.rgb = color('dark' if dark else 'bg')
    text(s, .5, .27, 11.8, .28, section, 10, 'pale' if dark else 'blue', True)
    text(s, .5, .83, 12.3, .62, title, 29, 'white' if dark else 'ink', True)
    if sub: text(s, .52, 1.53, 12.2, .53, sub, 17, 'pale' if dark else 'muted')
    if takeaway:
        rect(s, .5, 6.38, 12.33, .53, 'blue_bg')
        text(s, .68, 6.49, 11.97, .31, takeaway, 15, 'ink', True)
    arrow(s, .5, 7.12, 12.83, 7.12, 'muted' if dark else 'line', head=False, width=.7)
    text(s, .5, 7.19, 11.5, .2, 'KubeCon + CloudNativeCon North America 2026  /  KAITO + llm-d', 8, 'pale' if dark else 'muted')
    text(s, 12.13, 7.17, .7, .24, f'{len(prs.slides):02d} / 56', 9, 'pale' if dark else 'muted', align=PP_ALIGN.RIGHT)
    return s


def table(s, x, y, widths, rows, row_h=.65, header=True):
    """Editable cells, with predictable sizing across PowerPoint and LibreOffice."""
    for r, row in enumerate(rows):
        xx = x
        for c, (w, val) in enumerate(zip(widths, row)):
            fill = 'dark' if header and r == 0 else ('white' if r % 2 else 'blue_bg')
            rect(s, xx, y+r*row_h, w-.025, row_h-.025, fill)
            text(s, xx+.12, y+r*row_h+.13, w-.24, row_h-.2, val,
                 14 if header and r == 0 else 15,
                 'white' if header and r == 0 else ('blue' if c == 0 else 'ink'), header and r == 0)
            xx += w


# 01 — opening visual
s = slide('Prefill here, decode there', 'Cloud Native AI + Inference Day / 20-minute talk', dark=True)
text(s, .52, 1.7, 10.9, 1.0, 'Kubernetes-native LLM inference disaggregation\nwith KAITO and llm-d', 25, 'white')
pill(s, .55, 3.15, 2.6, 'One declarative service', 'blue', 'blue_bg')
node(s, .55, 3.9, 3.25, 1.55, 'KAITO', 'Declare the serving topology', 'blue', 25)
node(s, 5.0, 3.9, 3.0, 1.55, 'Prefill', 'Prompt → KV cache', 'teal', 25)
node(s, 9.25, 3.9, 3.5, 1.55, 'Decode', 'KV cache → token stream', 'purple', 25)
arrow(s, 3.8, 4.65, 5.0, 4.65, 'pale'); arrow(s, 8.0, 4.65, 9.25, 4.65, 'teal')
text(s, 8.1, 4.11, 1.05, .37, 'KV data', 12, 'pale', align=PP_ALIGN.CENTER)
text(s, .55, 6.17, 11.8, .5, 'Separate the phases. Keep a Kubernetes-native operating model.', 21, 'pale')
note(s, 'Open on the operating model, not a benchmark claim. Prefill computes the prompt state; decode consumes that state to generate tokens. This is a conceptual title diagram, not the full request path.')

# 02
s = slide('The route from idea to production', 'Agenda', 'Four questions connect the architecture to the operating tradeoffs.')
for i,(title,body,ac) in enumerate([
    ('Why split?', 'Two phases\nTwo bottlenecks', 'teal'),
    ('Why hard?', 'Routing, KV transfer\nKubernetes contracts', 'amber'),
    ('The solution', 'KAITO + llm-d\nOne declared topology', 'blue'),
    ('When to split?', 'Role-aware scaling\nMeasured tradeoffs', 'purple')]):
    x=.5+i*3.12
    card(s,x,2.48,2.96,2.95,title,body,ac,f'0{i+1}',18)
    if i<3: arrow(s,x+2.96,3.93,x+3.12,3.93,ac,width=1.4)
note(s, 'Keep this agenda brief. Spend the time on the problem, the orchestration abstraction, and production tradeoffs. Preserve the advanced diagrams for a faster walkthrough or questions if needed.')

# Foundations — schematic word-level tokens; authored sentence, not model inference.
CACHE_DOC = 'https://huggingface.co/docs/transformers/en/cache_explanation'
FOUNDATION_PROMPT = 'What does Kubernetes do?'
FOUNDATION_PROMPT_TOKENS = ['What', 'does', 'Kubernetes', 'do', '?']
FOUNDATION_SENTENCE = 'Kubernetes helps teams deploy and scale applications.'
FOUNDATION_OUTPUT = ['Kubernetes', 'helps', 'teams', 'deploy', 'and', 'scale', 'applications', '.']
FOUNDATION_SCOPE = ('Illustrative word-level tokens; not a real model tokenizer. For teaching only, assume each complete English word is one token and each punctuation mark is a separate token. Spaces are presentation separators, not extra positions. The prompt has four words plus a question mark (five positions); the output has seven words plus a period (eight positions). This is not BPE and does not describe Qwen or typical production tokenization: real tokenizers can split words into subwords and handle whitespace and punctuation differently. No tokenizer or model inference was run; the completion is authored, not a captured model response or evidence of a KAITO model deployment. ')
s = slide('Prefill: read the prompt, select the first output token', '01 / Foundations — prefill',
          'Prompt: “What does Kubernetes do?”',
          'Prefill caches the prompt, then selects “Kubernetes”. Its K/V is not cached until it is consumed.')
text(s,.65,2.17,11.9,.28,'Teaching example  /  One word per token',12,'blue',True)
# Complete words stay intact; punctuation occupies its own schematic position.
xs = [.65, 3.06, 5.47, 7.88, 10.29]
for x,piece in zip(xs, FOUNDATION_PROMPT_TOKENS):
    rect(s,x,2.61,2.38,.70,'blue_bg',radius=True)
    text(s,x+.08,2.75,2.22,.42,piece,22,'blue',True,PP_ALIGN.CENTER)
text(s,.65,3.54,12.02,.32,'Process the prompt positions together, with attention only to earlier or current positions.',17,'ink')
node(s,.65,4.17,3.0,1.22,'5 prompt positions','4 words + punctuation','blue',20)
node(s,4.15,4.17,4.16,1.22,'Causal prefill','No attention to future positions','teal',20)
node(s,9.0,4.17,3.67,1.22,'Select “Kubernetes”','Final prompt-position logits','purple',20)
arrow(s,3.65,4.77,4.15,4.77,'teal'); arrow(s,8.31,4.77,9.0,4.77,'purple')
arrow(s,6.23,5.39,6.23,5.58,'teal')
rect(s,.65,5.60,12.02,.43,'teal_bg',radius=True)
text(s,.85,5.68,11.62,.29,'Prompt KV = per-layer attention keys + values for the 5 processed prompt positions.',16,'teal')
text(s,.65,6.12,12.02,.22,'Illustrative word-level tokens; not a real model tokenizer.',11,'muted')
note(s, FOUNDATION_SCOPE + 'Exact prompt: What does Kubernetes do? Exact output: Kubernetes helps teams deploy and scale applications. Scope: a standard decoder-only autoregressive Transformer with KV caching and no speculative decoding. Tokenization precedes model execution. Prefill processes all uncached prompt positions; operations across positions can be batched within a layer while a causal mask prevents attention to future positions. Layers still follow model dependencies. Every attention layer builds K/V for the positions it processes. KV tensors are model state, not prompt text, weights or cached answers. Final prompt-position logits select y1, illustrated as the complete word Kubernetes. This authored selection is a hypothetical model path, not a measured probability. Immediately after selection, only prompt KV is cached. The next forward pass consumes y1 and appends its K/V. Chunked prefill splits uncached positions into scheduled chunks; prefix caching can reuse cached prompt positions. Prefill is not necessarily one physical kernel or uninterrupted scheduler iteration. Phase semantics do not assign first-token selection or delivery to a particular worker or specify the KAITO/llm-d transfer protocol. Client TTFT also includes queueing, tokenization, orchestration, transfer and delivery.', [CACHE_DOC,'https://docs.nvidia.com/dynamo/dev/kubernetes/disaggregated-serving/overview'])

s = slide('Decode: consume one token, select the next, repeat', '01 / Foundations — decode',
          'Illustrative output: “Kubernetes helps teams deploy and scale applications.”',
          'Append KV for the consumed token—not the newly selected token. Read past KV; do not recompute it.')
text(s,.65,2.10,12.02,.24,'Illustrative word-level tokens; not a real model tokenizer.',11,'muted')
for x,w,label in [(.65,.73,'Step'),(1.4,3.1,'Consume + read past KV'),(4.55,4.02,'Append to per-layer KV'),(8.62,4.05,'Select next output')]:
    rect(s,x,2.43,w,.34,'dark')
    text(s,x+.08,2.48,w-.16,.24,label,10,'white',True)
for row,(consumed,selected) in enumerate(zip(FOUNDATION_OUTPUT[:6],FOUNDATION_OUTPUT[1:7])):
    i=row+1
    y=2.83+row*.32
    rect(s,.65,y,12.02,.30,'white' if row%2==0 else 'purple_bg')
    for x,w,value,ac in [(.73,.55,str(i),'muted'),(1.49,2.9,consumed,'purple'),
                          (4.64,3.82,f'K/V for “{consumed}”','teal'),
                          (8.71,3.85,selected,'purple')]:
        text(s,x,y+.035,w,.26,value,14,ac,True)
text(s,.65,4.84,12.02,.25,'Repeat until the answer is complete. Each selected token becomes the next input.',14,'muted')
text(s,.65,5.18,11.9,.24,'Client arrivals  /  First 6 words shown  /  Schematic, not to scale',10,'blue',True)
xs=[.65,4.05,5.95,7.3,8.65,10.0,11.35]
labels=['Request']+FOUNDATION_OUTPUT[:6]
widths=[1.45,1.72]+[1.17]*5
for idx,(x,label,w) in enumerate(zip(xs,labels,widths)):
    rect(s,x,5.78,w,.39,'blue_bg' if idx==0 else ('teal_bg' if idx==1 else 'purple_bg'),radius=True)
    text(s,x+.025,5.85,w-.05,.25,label,12,'blue' if idx==0 else ('teal' if idx==1 else 'purple'),True,PP_ALIGN.CENTER)
    if idx:
        prev=xs[idx-1]+widths[idx-1]
        arrow(s,prev,5.975,x,5.975,'teal' if idx==1 else 'purple',width=1.4)
        text(s,xs[idx-1],5.52,x-xs[idx-1],.22,'TTFT → first word' if idx==1 else f'ITL {idx-1}',11,'teal' if idx==1 else 'purple',True,PP_ALIGN.CENTER)
note(s, FOUNDATION_SCOPE + 'Continue slide 3. Exact output: Kubernetes helps teams deploy and scale applications. Prefill selected y1 = Kubernetes with only prompt KV cached. Decode step i consumes yi with cache for prompt plus y1 through y(i-1), appends per-layer K/V for yi, then selects y(i+1) from the new position logits. Six rows: Kubernetes -> helps; helps -> teams; teams -> deploy; deploy -> and; and -> scale; scale -> applications. After row 6, cached output positions are y1-y6 and y7 (applications) is selected but not consumed or cached. The omitted final step consumes y7 (applications) and selects y8 (period). If generation continues, consuming the period could select EOS; EOS is normally hidden and need not be consumed into KV on stopping. No EOS ID or actual model decision is asserted. A token limit or stop string can also stop generation. With full-context attention each new query still reads cached history; caching avoids recomputing old K/V, not all attention work or history reads. Cache memory behavior depends on static allocation, sliding windows and eviction. Ordinary autoregressive decode is sequential within one request; cross-request batching is possible, and speculative decoding may accept multiple tokens per physical iteration. Client timeline shows the first six words under the one-word-per-token teaching assumption; the later word applications and punctuation are omitted. TTFT means time to first token: request submission to first received token, which is a whole word only in this schematic. Each ITL is the gap between successive received tokens. Five gaps are shown, not timing measurements; durations are not to scale. In real systems the first token need not be a complete word. Queueing, orchestration, transport, detokenization and stream buffering may change client-observed arrival grouping and latency. A real stream chunk may contain multiple tokens. Average time per output token is not each ITL sample or percentile. These phase semantics cover colocated and disaggregated serving and do not mandate a worker boundary; colocated serving needs no inter-worker KV transfer.', [CACHE_DOC,VLLM_METRICS])

# Actual slide 05 — phase-specific performance metrics
s = slide('One request. Two different performance targets.', '01 / The problem',
          'Prefill mainly shapes the wait for the first token; decode shapes the pace after it.',
          'Both affect total response latency and SLO goodput: requests/s meeting the latency targets.')
node(s,.55,2.16,2.0,1.08,'Prompt','Input tokens','blue')
node(s,3.0,2.16,3.0,1.08,'Prefill','Process uncached input','teal')
node(s,6.5,2.16,2.0,1.08,'KV cache','Attention state','amber')
node(s,9.0,2.16,3.75,1.08,'Decode','Generate tokens iteratively','purple')
for a,b,ac in [(2.55,3.,'muted'),(6.,6.5,'teal'),(8.5,9.,'purple')]: arrow(s,a,2.70,b,2.70,ac)
# Parallel native cards: latency targets first, role throughput second.
for x,ac in [(.55,'teal'),(6.78,'purple')]:
    rect(s,x,3.51,5.95,2.45,'white','line',True)
    rect(s,x+.18,3.72,.38,.065,ac)
text(s,.76,3.90,5.50,.43,'Prefill → TTFT',23,'teal',True)
text(s,.76,4.39,5.50,.33,'Time to first token • lower is better',18,'ink',True)
text(s,.76,4.92,5.50,.65,'Track prefill latency + input tok/s\nOften compute-bound',17,'muted')
text(s,6.99,3.90,5.50,.43,'Decode → ITL / TPOT',23,'purple',True)
text(s,6.99,4.39,5.50,.43,'Inter-token latency / avg. time per output token',16,'ink',True)
text(s,6.99,4.92,5.50,.82,'Lower is better • track aggregate output tok/s\nOften memory-bandwidth-bound',17,'muted')
text(s,.65,6.07,12.02,.23,'Not exclusive: queueing / delivery also affect TTFT; shared prefill can stall decode. Sources: vLLM metrics; NVIDIA Dynamo.',11,'muted')
note(s, 'Primary mapping, not exclusive causation: prefill latency mainly shapes TTFT (time to first token), while decode mainly shapes ITL (inter-token latency) and per-request TPOT (average time per output token after the first). Lower latency is better at matched workload and quality. TTFT is not pure prefill compute: request queueing, routing, input processing/tokenization, scheduling, and delivery contribute; disaggregated serving can also add KV-transfer and coordination time on the first-token critical path, depending on the protocol. No worker ordering or first-token delivery worker is mandated.\n\nAt a client measurement boundary, TTFT is request submission to receipt of the first output token. ITL describes gaps between successive output tokens in a one-token-per-event stream. The cited vLLM inter_token_latency_seconds histogram actually records consecutive streamed output events, which can contain multiple tokens; request_time_per_output_token_seconds records one TPOT sample per finished request. For Nout > 1, TPOT = (end-to-end latency - TTFT)/(Nout - 1) at the source metric boundaries. ITL and TPOT distributions, means and percentiles are not interchangeable: multi-token events and different request/event weighting change them. With consistent client boundaries and TPOT measured from first to last received token, total response latency to the last token is approximately TTFT + (Nout - 1) × TPOT. This is not an exact claim about HTTP request-close time. For no more than one generated token, vLLM server records TPOT as zero whereas its benchmark excludes the request from TPOT statistics.\n\nvLLM frontend/engine timing is not identical to client timing: the documented frontend arrival_time starts at tokenization, and engine prefill time runs from the most recent SCHEDULED to first NEW_TOKENS. Client timing additionally observes network and delivery overhead. ITL/TPOT can include scheduling gaps, preemption, contention, detokenization, transport and stream buffering rather than only GPU decode compute. Colocated prefill bursts can stall existing decode streams; chunked prefill and scheduling can mitigate this.\n\nSupporting role metrics: prefill latency and input-token processing throughput (input tok/s); decode output-token throughput (output tok/s). State the aggregation scope, time window, prompt/output lengths and prefix-cache accounting. Aggregate output tok/s is across concurrent requests and is not the speed experienced by one request. After the first token, a single request has approximately 1/TPOT output tok/s at matching boundaries; larger decode batches may raise aggregate throughput while worsening per-request ITL/TPOT. Input and output tok/s measure different work and must not be compared as equivalent productivity.\n\nBoth phases affect end-to-end latency and system capacity. SLO goodput here means requests/s meeting both TTFT and token-delivery latency targets, not all completed requests or raw token throughput. The word often qualifies compute-bound prefill and memory-bandwidth-bound decode: bottlenecks depend on model, batch size, context, hardware and scheduling. Prefill populates the KV cache; longer prompts also increase decode attention/KV cost. HBM KV occupancy is a resource-capacity pressure indicator, not memory bandwidth or a primary latency metric. Conceptual mapping only: no measured speedups or performance data.', ['https://docs.vllm.ai/en/latest/design/metrics/','https://docs.vllm.ai/en/latest/benchmarking/cli/#understanding-the-latency-metrics','https://docs.nvidia.com/dynamo/dev/kubernetes/disaggregated-serving/overview'])

# 04
s = slide('One shared pool couples two capacity decisions', '01 / The problem',
          'Aggregated serving is simple—but prefill bursts and active decoding share resources.',
          'The compromise is not only performance. It is how you size and scale the service.')
rect(s,.55,2.3,7.15,3.75,'white','line',True)
text(s,.8,2.56,6.6,.45,'Shared GPU pool',17,'blue',True)
for i in range(3):
    x=.86+i*2.2
    rect(s,x,3.34,1.98,1.6,'bg','line',True)
    pill(s,x+.12,3.56,1.73,'Prefill','teal','teal_bg')
    pill(s,x+.12,4.14,1.73,'Decode','purple','purple_bg')
text(s,.82,5.26,6.5,.45,'One deployment • one coupled scaling boundary',17,'muted')
card(s,8.05,2.3,4.72,3.75,'The operational tension',
     'Prompt bursts can disrupt token delivery.\n\nScaling adds both phases, even when only one is saturated.', 'amber',size=19)
note(s, 'Do not claim every aggregated deployment performs poorly. Continuous batching and chunked prefill can reduce interference. The point is that a shared resource and scaling boundary still constrains independent capacity shaping.')

# Motivation additions — slides 05–07 (external evidence + conceptual consequence)
DYNAMO_PD = 'https://docs.nvidia.com/dynamo/dev/kubernetes/disaggregated-serving/overview'
DISTSERVE = 'https://arxiv.org/html/2401.09670v2'
# Original editable schematics grounded in NVIDIA's 2025 explanation and current docs.
# No quantitative data, copied vendor graphics, or measured performance implied.
DYNAMO_DISAGG = 'https://docs.nvidia.com/dynamo/kubernetes/disaggregated-serving/overview'
VLLM_DISAGG = 'https://docs.vllm.ai/en/latest/features/disagg_prefill/'
VLLM_2025 = 'https://vllm.ai/blog/2025-09-05-anatomy-of-vllm'
DYNAMO_2025 = 'https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/'
s = slide('Long prefills can interrupt token delivery', '01 / Why split — execution interference',
          'A is already decoding. B arrives with a new prompt. Where should B run?',
          'Separate GPUs remove direct prefill execution from the decode GPU—not every source of latency.')
text(s,.65,2.12,12.0,.28,'Conceptual schedule · Not a benchmark · Block widths and gaps are not timings',12,'amber',True)
rect(s,.55,2.58,12.23,1.27,'white','line',True)
text(s,.76,2.80,2.65,.36,'Shared GPU',21,'ink',True)
text(s,.76,3.29,2.65,.28,'One worker does both',14,'muted')
for x,w,label,ac in [(3.75,1.10,'A','purple'),(5.05,1.10,'A','purple'),(6.35,3.00,'Prefill B','teal'),(9.55,1.10,'A','purple'),(10.85,1.10,'A','purple')]:
    rect(s,x,3.09,w,.49,ac+'_bg',radius=True)
    text(s,x+.03,3.18,w-.06,.30,label,16,ac,True,PP_ALIGN.CENTER)
text(s,6.23,2.68,3.25,.30,'A waits while B runs prefill',15,'amber',True,PP_ALIGN.CENTER)
rect(s,.55,4.06,12.23,1.79,'white','line',True)
text(s,.76,4.30,2.65,.41,'Separate GPUs',21,'ink',True)
text(s,.76,4.85,2.65,.26,'Prefill worker',14,'teal',True)
text(s,.76,5.36,2.65,.26,'Decode worker',14,'purple',True)
rect(s,6.35,4.75,3.00,.43,'teal_bg',radius=True)
text(s,6.38,4.81,2.94,.29,'Prefill B',16,'teal',True,PP_ALIGN.CENTER)
text(s,9.57,4.81,2.80,.29,'B still needs KV handoff',13,'amber')
for x in [3.75,5.05,6.35,7.65,8.95,10.25,11.55]:
    rect(s,x,5.28,.80,.39,'purple_bg',radius=True)
    text(s,x+.02,5.33,.76,.28,'A',15,'purple',True,PP_ALIGN.CENTER)
text(s,3.75,4.23,8.65,.28,'A can continue decoding while B runs prefill elsewhere',16,'purple',True)
text(s,.65,5.97,11.95,.23,'A = ongoing decode; B = new request. Chunked prefill can mitigate the shared-worker pause.',11,'muted')
text(s,.65,6.22,11.95,.15,'Original conceptual illustration; sources: NVIDIA and vLLM (2025) + current documentation.',8,'muted')
note(s, 'Original author-created conceptual schedule, not a reproduced research figure, trace or benchmark. Source basis: NVIDIA Dynamo introduction, published 18 March 2025 (page metadata), and current disaggregated-serving overview, accessed 22 October 2026. A is one ongoing request; B is a different newly arriving request. Each purple A block represents some decode execution, not a measured token duration or count. The shared-GPU example chooses a simple non-chunked prefill scheduling interval to explain how prompt processing can delay ongoing decode. Real schedulers can chunk or interleave prefill, use decode-priority policies or mixed batches, and mitigate interference; not all colocated serving has a contiguous pause. Separate GPUs let A continue without executing B prefill on its decode GPU. Equally spaced symbols are for readability only, not a promise of constant ITL or a measured improvement. B still requires KV transfer before its own decode; that transfer and B decode are omitted from this schedule, not assumed free. Queueing, KV movement, memory contention, batching and shared infrastructure can still affect either stream. The split uses an additional worker in this structural sketch; it is not an equal-budget performance comparison. No latency numbers, speedup, throughput, model or GPU recommendation is inferred.', [DYNAMO_2025,VLLM_2025,DYNAMO_DISAGG,VLLM_DISAGG])

s = slide('Prefill and decode batch different work', '01 / Why split — different batching units',
          'Prefill processes many prompt positions; ordinary decode advances many independent requests.',
          'Prefill finds parallel work in prompt length; decode finds it across active sequences.')
text(s,.65,2.12,12.0,.28,'Conceptual illustration · Not a benchmark · Tokens and request counts are schematic',12,'amber',True)
for x,title,sub,ac in [(.55,'Prefill','Many input positions in one forward pass','teal'),
                       (6.79,'Decode','One newest input position per active request','purple')]:
    rect(s,x,2.58,5.99,3.27,'white','line',True)
    rect(s,x+.18,2.81,.07,.40,ac)
    text(s,x+.37,2.76,5.37,.46,title,24,ac,True)
    text(s,x+.22,3.31,5.55,.32,sub,16,'ink')
for row,(name,tokens) in enumerate([('Request A',['p1','p2','p3','p4']),('Request B',['q1','q2','q3'])]):
    y=3.94+row*.58
    text(s,.78,y+.06,1.34,.31,name,15,'muted',True)
    for j,token in enumerate(tokens):
        x=2.29+j*.80
        rect(s,x,y,.65,.43,'teal_bg',radius=True)
        text(s,x+.015,y+.075,.62,.29,token,16,'teal',True,PP_ALIGN.CENTER)
text(s,.79,5.28,5.44,.32,'Batch prompt positions from one or more requests.',14,'teal',True)
text(s,7.02,3.76,1.37,.23,'Request',11,'muted',True)
text(s,8.42,3.76,1.31,.23,'Read history',11,'muted',True)
text(s,10.11,3.76,2.35,.23,'Consume newest input',11,'muted',True)
for row,name in enumerate(['A','B','C']):
    y=4.10+row*.48
    text(s,7.02,y+.04,1.21,.27,name,16,'purple',True)
    rect(s,8.40,y,1.22,.35,'teal_bg',radius=True)
    text(s,8.43,y+.035,1.16,.25,'Prior KV',13,'teal',True,PP_ALIGN.CENTER)
    text(s,9.72,y+.02,.28,.27,'+',15,'muted',True,PP_ALIGN.CENTER)
    rect(s,10.13,y,1.98,.35,'purple_bg',radius=True)
    text(s,10.16,y+.035,1.92,.25,'One token',13,'purple',True,PP_ALIGN.CENTER)
text(s,7.02,5.59,5.45,.23,'Then select a next output token for each request.',12,'purple',True)
text(s,.65,5.99,11.95,.25,'More decode concurrency can increase ITL. Batch within latency and KV-memory budgets.',13,'amber',True)
text(s,.65,6.22,11.95,.15,'Original conceptual illustration; sources: NVIDIA and vLLM (2025) + current documentation.',8,'muted')
note(s, 'Original author-created conceptual batching illustration, not measured curves or reproduced vendor artwork. Dated sources: NVIDIA Dynamo introduction, 18 March 2025; Anatomy of vLLM, article dated 5 September 2025 (published repository 8 September; analyzes an August 9 snapshot). Also current vLLM disaggregated-prefill and Dynamo disaggregated-serving documentation, accessed 22 October 2026. Prefill has many prompt input positions from one or more requests in a forward pass; their p/q labels are schematic positions, not words, actual tokenizer IDs or optimal batch counts. Causal attention still applies: parallel processing does not let a position attend to future positions. Uncached prompt positions may be split across multiple chunks/passes, and prefix reuse can skip cached positions. Ordinary autoregressive decode consumes one newest input position per active sequence, attends to the sequence’s previous KV history, appends that position’s per-layer KV, then selects the next output token. The consumed token is not the newly selected output token of that same step. Independent requests can share a decode batch, but generation remains sequential within each request. The diagram represents three independent sequences, not three successive tokens from one sequence. Speculative decoding and multi-token methods are outside this ordinary-decode illustration. vLLM V1 can mix decode with chunked prefill in one scheduled step, so these conceptual units do not mandate separate physical passes or workers. Longer prompts provide within-request parallel work for prefill; more active sequences provide cross-request decode batching. Larger decode batches can amortize work but increase iteration time, ITL and KV-memory demand; no monotonic throughput improvement, ideal batch size, fixed worker count or latency number is claimed. Both phases use memory and compute. Independent phase tuning may help but remains workload-dependent. P/D additionally requires KV transfer and coordination; see slide7 and slide9 for that tradeoff. This slide deliberately explains batching units, not the independent capacity allocation shown on slide9.', [DYNAMO_2025,VLLM_2025,DYNAMO_DISAGG,VLLM_DISAGG])

s = slide('Independent pools remove a forced compromise', '01 / Why split — capacity control',
          'The payoff is a separate capacity decision for each phase—not separation for its own sake.',
          'Split only when phase-specific gains outweigh KV transfer, duplicated weights and operational cost.')
card(s,.55,2.35,5.96,2.42,'Prompt-heavy demand',
     'Usually compute-bound; target TTFT.\nTune prefill capacity / parallelism first.','teal','Input side',18)
card(s,6.78,2.35,5.96,2.42,'Generation-heavy demand',
     'Often bandwidth-bound; target ITL.\nTune decode capacity / batching first.','purple','Output side',18)
node(s,.65,4.92,3.85,1.11,'Different latency targets','TTFT versus token delivery','blue',18)
node(s,4.74,4.92,3.85,1.11,'Different resource needs','Compute, bandwidth, active KV','teal',18)
node(s,8.83,4.92,3.85,1.11,'Different capacity knobs','Replicas, TP, batching policy','purple',18)
text(s,.65,6.17,11.8,.14,'Sources: NVIDIA Dynamo disaggregated-serving overview + DistServe §2.3 • Conceptual; bottlenecks depend on workload',8,'muted')
note(s, 'NVIDIA Dynamo disaggregated-serving overview describes compute-bound prefill and memory-bandwidth-bound decode, with independent pools, batching, hardware and parallelism choices. These are common regimes rather than universal laws: model, context length, batch size and hardware change the limiting resource. Dynamo-specific worker orchestration and NIXL setup are not presented as KAITO architecture. Conceptual synthesis, not measured performance data. DistServe section 2.3 identifies resource and parallelism coupling as distinct from prefill/decode execution interference: a colocated deployment shares devices, resource allocation and a parallelism plan even when the two phases have different bottlenecks and latency constraints. Separate pools permit different hardware, tensor-parallel degrees, batching policies and replica counts, subject to runtime/connector compatibility; they do not imply every choice is supported by current KAITO. The two demand cards are first investigation directions, not a deterministic scaler: longer prompts also increase decode KV state and transfer bytes, so inspect both roles and the end-to-end SLO before changing capacity. Likewise larger decode batches must respect ITL and KV limits. Shared pools can still benefit from chunked prefill, continuous batching and scheduling improvements. P/D becomes worthwhile only when independent capacity tuning or interference isolation creates a measured gain larger than transfer, duplicated model residency and operational overhead. No fixed P:D ratio, GPU savings or current autoscaler implementation is claimed.', [DYNAMO_PD,DISTSERVE+'#S2.SS3',PD_DOC])

# 05
s = slide('Split the phases. Tune the pools independently.', '01 / The problem',
          'P/D introduces a KV-transfer boundary between prompt processing and generation.',
          'The transfer path must be fast enough to justify the split.')
rect(s,.55,2.4,4.5,3.45,'teal_bg',radius=True)
text(s,.8,2.66,4,.48,'Prefill pool',23,'teal',True)
node(s,.85,3.4,3.9,1.14,'Prompt processing','Compute + latency','teal')
text(s,.82,4.98,3.9,.78,'Choose replicas and parallelism\nfor prompt pressure.',17,'teal')
rect(s,8.28,2.4,4.5,3.45,'purple_bg',radius=True)
text(s,8.53,2.66,4,.48,'Decode pool',23,'purple',True)
node(s,8.58,3.4,3.9,1.14,'Token generation','Bandwidth + active KV memory','purple')
text(s,8.55,4.98,3.9,.78,'Choose replicas and parallelism\nfor sustained generation.',17,'purple')
arrow(s,5.05,3.98,8.28,3.98,'teal',width=3)
text(s,5.22,3.08,2.9,.65,'KV cache transfer',20,'teal',True,PP_ALIGN.CENTER)
text(s,5.18,4.35,2.95,1.1,'New cost:\ntransfer + coordination',17,'muted',align=PP_ALIGN.CENTER)
note(s, 'Conceptual data direction is prefill to decode. The low-level transfer can be a decode-initiated pull. Network and transport support depend on the deployment. Separate pools allow different instance types, replica counts, and tensor-parallel settings.', [PD_DOC])

# 06
s = slide('P/D fits when the phases need different shapes', '01 / The problem',
          'Start with the traffic profile, not the architecture trend.')
for i,(title,body,ac,tag) in enumerate([
 ('Long prompts','RAG and retrieval add significant prefill work.','teal','Prompt pressure'),
 ('Long generations','High concurrency keeps decode busy and KV state resident.','purple','Generation pressure'),
 ('Different resources','Each phase needs its own scaling or parallelism choices.','blue','Capacity mismatch')]):
    card(s,.55+i*4.14,2.35,3.95,3.45,title,body,ac,tag,20)
note(s, 'The real value is independent capacity shaping. Long prompts alone do not prove P/D wins; combine workload measurements with transfer-fabric and operational constraints. A fast GPU-to-GPU path lowers the barrier; cross-node P/D requires closer attention to the transfer path.')

# 07
s = slide('Keep aggregated serving when simplicity wins', '01 / The problem',
          'P/D is an option, not a default.', 'Small workload + slow transfer fabric is a strong reason not to split.')
card(s,.55,2.38,5.95,3.55,'When aggregated fits',
     'Small models or short prompts\n\nLow request concurrency\n\nSimple, stable capacity needs','blue',size=20)
card(s,6.78,2.38,5.95,3.55,'The split adds real costs',
     'KV transfer across the fabric\n\nMore routing and runtime wiring\n\nAdditional failure boundaries','amber',size=20)
note(s, 'Avoid blanket promises. The break-even point is empirical and model-, traffic-, and fabric-dependent. Aggregated serving can be simpler and faster for the wrong P/D workload.')

# 08
s = slide('The hard part is the Kubernetes wiring', '02 / The orchestration gap',
          'The two-pool idea expands into a network of runtime contracts.',
          'Correct routing, transfer settings, labels, ports, and readiness must agree.')
node(s,4.82,3.43,3.7,1.05,'One model service','Two role-specific backends','blue')
items=[(.55,2.3,'Routing topology','EPP + endpoint selection','blue'),
       (.55,4.58,'KV-transfer contract','Connector + transport settings','teal'),
       (9.03,2.3,'Decode-side proxy','Request orchestration','purple'),
       (9.03,4.58,'Lifecycle + scaling','Ports, labels, probes, replicas','amber')]
for x,y,t,d,ac in items:
    node(s,x,y,3.75,1.25,t,d,ac,18)
route(s,[(4.3,2.93),(4.55,2.93),(4.55,3.75),(4.82,3.75)],'blue')
route(s,[(4.3,5.2),(4.55,5.2),(4.55,4.17),(4.82,4.17)],'teal')
route(s,[(8.52,3.75),(8.77,3.75),(8.77,2.93),(9.03,2.93)],'purple')
route(s,[(8.52,4.17),(8.77,4.17),(8.77,5.2),(9.03,5.2)],'amber')
note(s, 'This is an operational dependency map, not a request-flow diagram. Explain why assembling correct components by hand still leaves brittle contracts between them.',[PD_DOC])

# Ecosystem addition — slides 09–10 (original slide markers below remain stable)
ECOSYSTEM_REFS = [
    'https://docs.nvidia.com/dynamo/v1.1.0/getting-started/kubernetes-deployment',
    'https://llm-d.ai/docs/architecture',
    'https://aibrix.readthedocs.io/latest/features/gateway-routing/pd-disaggregation.html',
    'https://aibrix.readthedocs.io/latest/designs/aibrix-stormservice.html',
    'https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview',
    'https://docs.ray.io/en/latest/serve/llm/user-guides/prefill-decode.html',
    'https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/disaggregated-prefill.html',
    'https://lws.sigs.k8s.io/docs/concepts/disaggregatedset/',
]
s = slide('Open-source P/D: several paths, different abstractions', '02 / Ecosystem landscape',
          'Representative approaches—not an adoption ranking or mutually exclusive stacks.',
          'Declarative APIs already exist. The opportunity is simpler integration—not the first CRD.')
rows = [
    ['Approach', 'Serving / routing path', 'Kubernetes packaging'],
    ['NVIDIA Dynamo', 'Integrated inference stack', 'Operator + DynamoGraphDeployment'],
    ['llm-d', 'P/D-aware EPP + routing sidecar', 'Gateway API / InferencePool'],
    ['AIBrix', 'P/D-aware gateway + engines', 'StormService / RoleSet'],
    ['KServe + llm-d', 'llm-d serving integration', 'LLMInferenceService'],
    ['Ray Serve + KubeRay', 'P/D app + vLLM KV connectors', 'RayService + Serve configuration'],
    ['vLLM Production Stack', 'vLLM + LMCache / NIXL + router', 'Helm-managed P/D deployment'],
]
for r, row in enumerate(rows):
    x = .55
    y = 2.12 + r * .47
    for c, (w, val) in enumerate(zip([3.15, 4.33, 4.75], row)):
        rect(s, x, y, w-.025, .445, 'dark' if r == 0 else ('white' if r % 2 else 'blue_bg'))
        text(s, x+.11, y+.085, w-.22, .32, val, 13 if r == 0 else 14,
             'white' if r == 0 else ('blue' if c == 0 else 'ink'), r == 0 or c == 0)
        x += w
rect(s, .55, 5.55, 12.23, .57, 'teal_bg', radius=True)
text(s, .72, 5.68, 11.9, .32,
     'Also: LWS DisaggregatedSet orchestrates roles; engines and KV transport remain separate.', 15, 'teal')
note(s, 'Sources checked 2026-10-20. This is a capability and abstraction map, not a maturity, performance, or market-share ranking. '
     'The Kubernetes packaging column highlights a representative API; it is not an exhaustive feature inventory. '
     'Dynamo has a Kubernetes Operator and DynamoGraphDeployment: do not characterize it as lacking declarative orchestration. '
     'AIBrix StormService/RoleSet manages multi-role workloads. KServe LLMInferenceService explicitly wraps llm-d architecture, '
     'so it is not a separate underlying P/D engine. Ray Serve models P/D as application deployments; KubeRay supplies Kubernetes lifecycle management. '
     'The vLLM Production Stack tutorial supplies a Helm-based P/D deployment using LMCache/NIXL and a router; its sample versions are not a recommendation. '
     'LWS DisaggregatedSet is a workload controller, not a complete serving data plane. SGLang, vLLM and TensorRT-LLM are engines; '
     'NIXL, LMCache and Mooncake are transfer/cache building blocks, not standalone Kubernetes serving platforms. '
     'Latest documentation can describe newer or alpha capabilities: validate release compatibility and production maturity separately. '
     'Replace the old claim that the ecosystem lacks a declarative Kubernetes abstraction.', ECOSYSTEM_REFS)

s = slide('Why llm-d is the best fit for KAITO’s P/D integration', '03 / Integration rationale',
          'For teams choosing KAITO’s Kubernetes operating model—not a universal best-platform claim.',
          'KAITO owns deployment intent and lifecycle; llm-d supplies reusable inference routing.')
node(s, .55, 2.16, 3.62, 1.22, 'KAITO', 'MRI → child InferenceSets', 'blue', 21)
node(s, 4.86, 2.16, 3.62, 1.22, 'llm-d', 'EPP + decode routing sidecar', 'teal', 21)
node(s, 9.17, 2.16, 3.61, 1.22, 'vLLM + NIXL', 'Execute phases + move KV', 'purple', 21)
text(s, 4.24, 2.52, .54, .5, '+', 26, 'muted', True, PP_ALIGN.CENTER)
text(s, 8.55, 2.52, .54, .5, '+', 26, 'muted', True, PP_ALIGN.CENTER)
for i, (title, body, accent) in enumerate([
    ('Reuse the API model', 'Keep Workspace / InferenceSet.\nAdd role-specific replicas, GPU\ninstance types and runtime settings.', 'blue'),
    ('Integrate, do not rebuild', 'Reuse P/D-aware endpoint selection\nand request orchestration. KAITO\nwires sidecars, ports and the pool.', 'teal'),
    ('Clear ownership', 'Use Gateway API / InferencePool.\nKeep routing plugins upstream;\navoid adding a second serving API.', 'purple'),
]):
    card(s, .55+i*4.14, 3.58, 3.95, 2.12, title, body, accent, size=14)
text(s, .58, 5.78, 12.15, .4,
     'Current scope: alpha MRI • vLLM + Istio • GPU connectivity for KV transfer • scaling policy still needs design',
     13, 'muted')
note(s, 'Best fit is an architecture recommendation relative to the goal of extending KAITO, not evidence that KAITO beats every serving platform. '
     'KAITO users already have Workspace/InferenceSet APIs, model presets and infrastructure lifecycle workflows. MRI reuses that model through role-specific child InferenceSets. '
     'The documented controller creates an InferencePool and llm-d EPP, injects the decode routing sidecar, and sets vLLM NIXL side-channel configuration. '
     'llm-d contributes P/D endpoint-selection plugins and request orchestration; vLLM and NIXL execute inference and transfer KV directly between pods. '
     'The three boxes are a composition diagram, not a sequential request path. Gateway/HTTPRoute, certificates, GPU capacity and fabric setup remain platform prerequisites; '
     'do not claim MRI provisions every cluster dependency automatically. '
     'Compared with introducing another serving platform API alongside KAITO, reusing llm-d components preserves KAITO as the user-facing orchestration entry point. '
     'KServe and AIBrix are legitimate alternative orchestration platforms; Dynamo offers an integrated stack; Ray Serve fits Ray-centric applications. '
     'Existing users of those platforms need not migrate solely to obtain P/D. '
     'Documented KAITO limitations: MRI is alpha, currently vLLM-only and requires Istio plus suitable GPU-to-GPU connectivity. '
     'Independent role replica settings do not imply an automatic MRI-level autoscaling policy. The existing KEDA-InferenceSet capability and proposed MRI policy UX are discussed later. '
     'No throughput, latency, cost, hardware-portability or superiority claim is made. Sources checked 2026-10-20.',
     [PD_DOC, KEDA_DOC, 'https://llm-d.ai/docs/architecture',
      'https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview'])

# 09
s = slide('KAITO turns inference topology into Kubernetes APIs', '03 / KAITO + llm-d',
          'A control-plane progression from model serving to distributed inference.',
          'KAITO is the abstraction and orchestration layer—not the model server.')
for i,(title,desc,ac) in enumerate([
 ('Workspace','Run a serving\nor tuning workload','blue'),
 ('InferenceSet','Scale serving\nreplicas','teal'),
 ('InferencePool','Expose routing-facing\nbackend groups','purple'),
 ('MultiRoleInference','Describe role-specific\nserving topology','amber')]):
    x=.55+i*3.13; y=3.4-i*.32
    node(s,x,y,2.94,1.53,title,desc,ac,16)
    text(s,x,y+1.73,2.94,.4,['Serve','Scale','Route','Compose'][i],12,ac,True,PP_ALIGN.CENTER)
    if i<3: route(s,[(x+2.94,y+.75),(x+3.04,y+.75),(x+3.04,y+.43),(x+3.13,y+.43)],ac)
note(s, 'This is a capability progression, not a strict ownership chain. InferencePool is the Gateway API Inference Extension routing abstraction. KAITO manages the objects and wiring around the runtime.',[PD_DOC])

# 10
s = slide('A continuous API model as serving gets harder', '03 / KAITO + llm-d',
          'Add capabilities without asking users to hand-assemble a new stack.')
rows=[['User need','Kubernetes object','Platform responsibility'],
      ['Run one model','Workspace','Provision and run the workload'],
      ['Add replicas','InferenceSet','Manage the replica set'],
      ['Route intelligently','InferencePool','Integrate inference-aware routing'],
      ['Split roles','MultiRoleInference','Reconcile a multi-role topology']]
table(s,.55,2.42,[3.1,3.7,5.48],rows,.66)
note(s, 'The same mental model persists: declare intent, observe status, and let controllers reconcile. InferencePool belongs to GWIE rather than being a KAITO-defined CRD. These objects have distinct jobs and should not be presented as interchangeable.',[PD_DOC])

# 11
s = slide('Clear responsibilities across the stack', '03 / KAITO + llm-d',
          'The stack works because each layer has a different job.',
          'KAITO composes the platform; llm-d routes; the runtime executes.')
for y,t,b,ac in [
 (2.33,'KAITO','Declarative APIs • child resources • lifecycle orchestration','blue'),
 (3.56,'llm-d Router / EPP','Inference-aware endpoint selection and scheduling','teal'),
 (4.79,'Runtime + KV transport','Prefill computation • KV movement • token generation','purple')]:
    rect(s,.55,y,12.23,1.03,'white','line',True)
    text(s,.8,y+.29,3.82,.42,t,18,ac,True)
    text(s,4.8,y+.29,7.7,.5,b,17)
    if y<4.7: arrow(s,6.67,y+1.03,6.67,y+1.23,ac,width=1.5)
note(s, 'Avoid calling KAITO the scheduler or vLLM the orchestrator. The EPP participates in the Gateway request-routing decision; the decode-side routing proxy orchestrates the P/D request lifecycle.',[PD_DOC])

# 12
s = slide('The stack is composable—not a custom monolith', '03 / KAITO + llm-d',
          'Kubernetes resources connect routing, execution, transfer, and scaling.')
for x,y,w,t,d,ac in [
 (.55,2.38,3.95,'Gateway API + GWIE','Gateway • HTTPRoute • InferencePool','blue'),
 (4.69,2.38,3.95,'llm-d','EPP + routing sidecar','teal'),
 (8.83,2.38,3.95,'vLLM','Serving runtime','purple'),
 (.55,4.35,3.95,'NIXL','KV-transfer integration','teal'),
 (4.69,4.35,3.95,'KEDA','InferenceSet autoscaling','amber'),
 (8.83,4.35,3.95,'KAITO','Reconcile the declared topology','blue')]:
    node(s,x,y,w,1.5,t,d,ac,22)
note(s, 'These are ecosystem building blocks, not all resources owned by the same controller. KEDA ScaledObjects target the InferenceSet scale subresource; KEDA and HPA implement the scaling loop. Runtime and transport versions matter.',[PD_DOC,KEDA_DOC])

# 13
s = slide('Declare roles once with MultiRoleInference', '03 / KAITO + llm-d',
          'One logical service, two independently configurable child InferenceSets.',
          'Role settings describe capacity; controller reconciliation supplies the wiring.')
node(s,4.45,2.25,4.43,.95,'MultiRoleInference','One desired topology','blue',20)
node(s,.8,3.89,5.5,1.83,'prefill InferenceSet','Replica count • instance type\nTensor parallelism • vLLM configuration','teal',21)
node(s,7.03,3.89,5.5,1.83,'decode InferenceSet','Replica count • instance type\nTensor parallelism • vLLM configuration','purple',21)
route(s,[(6.66,3.2),(6.66,3.52),(3.55,3.52),(3.55,3.89)],'teal')
route(s,[(6.66,3.52),(9.78,3.52),(9.78,3.89)],'purple')
note(s, 'The current MRI P/D documentation supports per-role replica, instance-type, preset, and vLLM settings. Do not imply this slide is a literal schema or that the proposed MRI scaling UX on slide 25 is already implemented.',[PD_DOC])

# 14 — full architecture
s = slide('One API endpoint, a role-aware serving path', '03 / Architecture',
          'Solid arrows: request/data flow. Dashed arrows: scheduling or reconciliation.')
node(s,.55,2.57,1.35,1.1,'Client','API call','blue',17)
node(s,2.36,2.57,2.08,1.1,'Gateway','HTTPRoute','blue',19)
node(s,2.36,4.5,2.08,1.1,'llm-d EPP','Pick P + D','teal',18)
node(s,5.07,2.57,2.54,1.1,'Decode proxy','Orchestrate request','purple',18)
node(s,9.45,2.38,3.28,1.25,'Prefill workers','Compute prompt KV','teal',20)
node(s,9.45,4.5,3.28,1.25,'Decode workers','Generate token stream','purple',20)
arrow(s,1.9,3.12,2.36,3.12,'blue')
arrow(s,4.44,3.12,5.07,3.12,'blue')
arrow(s,3.15,3.67,3.15,4.5,'teal',True)
arrow(s,3.7,4.5,3.7,3.67,'teal',True)
text(s,.55,4.68,1.6,.7,'Scheduling\nselection',12,'muted',align=PP_ALIGN.CENTER)
route(s,[(7.61,2.92),(8.35,2.92),(8.35,2.99),(9.45,2.99)],'blue')
text(s,7.75,2.26,1.5,.42,'Prompt',13,'blue',True)
route(s,[(6.34,3.67),(6.34,5.13),(9.45,5.13)],'blue')
text(s,6.48,4.43,2.7,.55,'Decode + KV metadata',12,'blue',True)
arrow(s,11.11,3.63,11.11,4.5,'teal',width=3)
text(s,11.33,3.83,1.34,.4,'KV data',12,'teal',True)
route(s,[(9.45,5.53),(8.8,5.53),(8.8,6.04),(.97,6.04),(.97,3.67)],'purple')
text(s,4.55,6.12,5.4,.28,'Token stream returns through proxy + Gateway',12,'purple')
pill(s,.55,6.62,12.23,'KAITO reconciles the serving topology; the Gateway is the API entry point','blue','blue_bg')
note(s, 'Conceptual topology, not a port-level deployment diagram. The Gateway consults the EPP, then sends the request to the selected decode pod routing sidecar. That sidecar calls prefill, forwards metadata to local decode, and streams the response back through the Gateway. The return line is a summarized path. KV data moves from prefill memory to decode; transport initiation may be a decode-side read. Gateway installation/lifecycle is separate from MRI.',[PD_DOC])

# 15 — resource graph
s = slide('From one MRI to a reconciled resource graph', '03 / Resource ownership',
          'Solid connectors: generated resources. Dashed connector: routing configuration.')
node(s,4.44,2.18,4.46,.88,'MultiRoleInference',accent='blue',size=21)
node(s,.55,3.7,3.7,1.0,'Prefill InferenceSet','Role-specific serving template','teal',17)
node(s,4.81,3.7,3.7,1.0,'Decode InferenceSet','Runtime + routing sidecar','purple',17)
node(s,9.07,3.7,3.7,1.0,'InferencePool','Routing-facing backend group','blue',18)
for x,ac in [(2.4,'teal'),(6.66,'purple'),(10.92,'blue')]:
    route(s,[(6.66,3.06),(6.66,3.37),(x,3.37),(x,3.7)],ac)
node(s,.55,5.26,3.7,.9,'Workspaces → Pods',accent='teal',size=18)
node(s,4.81,5.26,3.7,.9,'Workspaces → Pods',accent='purple',size=18)
node(s,9.07,5.26,3.7,.9,'EPP config + HTTPRoute',accent='blue',size=17)
arrow(s,2.4,4.7,2.4,5.26,'teal'); arrow(s,6.66,4.7,6.66,5.26,'purple')
arrow(s,10.92,4.7,10.92,5.26,'blue',True)
text(s,.57,6.48,12.1,.4,'Less hand-maintained glue: role labels, ports, sidecar configuration, and routing bindings.',17,'muted')
note(s, 'MRI creates child InferenceSets and a routing pool; InferenceSets reconcile Workspaces. The diagram deliberately distinguishes generated resource relationships from routing configuration. HTTPRoute requires a parent Gateway; it is not owned by the pool in a strict Kubernetes owner-reference sense.',[PD_DOC])

# 16 — swimlane sequence
s = slide('A request crosses four distinct boundaries', '03 / Request lifecycle',
          'Request orchestration and KV-data movement are separate paths.')
xs=[1.45,4.45,7.47,10.8]
for x,t,ac in zip(xs,['Gateway + EPP','Decode proxy','Prefill worker','Decode runtime'],['blue','purple','teal','purple']):
    node(s,x-1.25,2.18,2.5,.65,t,accent=ac,size=14)
    arrow(s,x,2.84,x,6.45,'line',True,False,1)
steps=[(3.12,0,1,'1  Route to selected decode','blue',False),
 (3.73,1,2,'2  Execute prefill','blue',False),
 (4.34,2,1,'3  Return KV-transfer metadata','muted',True),
 (4.95,1,3,'4  Start decode with metadata','blue',False),
 (5.56,2,3,'5  KV data (prefill → decode)','teal',False),
 (6.17,3,1,'6  Token stream → proxy → Gateway','purple',False)]
for y,a,b,label,ac,dash in steps:
    arrow(s,xs[a],y,xs[b],y,ac,dash)
    text(s,min(xs[a],xs[b])+.09,y-.32,abs(xs[b]-xs[a])-.15,.29,label,11,ac,True)
text(s,.55,6.69,12.2,.29,'KV-transfer metadata identifies remote state; it is not the KV tensor payload.',14,'muted')
note(s, 'Conceptual sequence, not a timing chart. Gateway and EPP are combined into one lane for space; the EPP makes the endpoint decision. Prefill returns metadata to the decode proxy. The decode runtime then obtains the KV tensors and generates tokens. The NIXL path can be decode-initiated; arrow 5 shows payload direction only. The stream travels via the proxy and Gateway. No duration is implied.',[PD_DOC])

# 17 — protocol distinction
s = slide('Metadata is not the KV payload', '03 / KV transfer',
          'Keep control messages and the high-volume data path distinct.',
          'Do not read a request arrow as a KV-transfer arrow.')
node(s,.55,2.4,3.4,1.24,'Decode proxy','HTTP orchestration','purple',21)
node(s,9.38,2.4,3.4,1.24,'Prefill worker','Owns newly computed KV','teal',21)
arrow(s,3.95,2.81,9.38,2.81,'blue')
text(s,4.07,2.24,5.17,.4,'Prompt request',16,'blue',True,PP_ALIGN.CENTER)
arrow(s,9.38,3.34,3.95,3.34,'muted',True)
text(s,4.05,3.43,5.2,.43,'Response: KV-transfer metadata',15,'muted',align=PP_ALIGN.CENTER)
node(s,.55,4.69,3.4,1.24,'Decode runtime','Uses KV to generate tokens','purple',21)
node(s,9.38,4.69,3.4,1.24,'Prefill KV memory','Remote transfer source','teal',21)
arrow(s,2.25,3.64,2.25,4.69,'purple')
text(s,.57,3.98,1.45,.5,'Metadata',12,'purple')
arrow(s,9.38,5.29,3.95,5.29,'teal',width=3)
text(s,4.05,4.73,5.2,.42,'KV tensor data: prefill → decode',16,'teal',True,PP_ALIGN.CENTER)
text(s,4.08,5.52,5.16,.56,'A decode-initiated read can drive the transfer.',14,'muted',align=PP_ALIGN.CENTER)
note(s, 'The NIXL connector is configured at the serving runtime. Exact transport, ports, and handshake fields depend on runtime versions. Do not label one transfer protocol or port number as a universal invariant.',[PD_DOC])

# 18 — pod detail
s = slide('The decode pod contains two different roles', '03 / Runtime boundary',
          'The routing sidecar coordinates the request; vLLM executes decode.',
          'Generated Service targetPorts, probes, and runtime arguments must agree.')
rect(s,3.0,2.36,9.78,3.67,'purple_bg','line',True)
text(s,3.26,2.59,8.9,.4,'Decode pod  /  Shared pod network',16,'purple',True)
node(s,3.3,3.47,3.25,1.75,'llm-d routing\nsidecar','Receives inference requests','purple',20)
node(s,9.05,3.47,3.4,1.75,'vLLM decode\nruntime','Local backend listener','purple',20)
node(s,.55,3.67,1.93,1.28,'Gateway','Via Service','blue',18)
arrow(s,2.48,4.3,3.3,4.3,'blue')
arrow(s,6.55,4.33,9.05,4.33,'purple')
text(s,6.7,3.72,2.2,.48,'Local forwarding',14,'purple',True,PP_ALIGN.CENTER)
text(s,6.7,4.62,2.2,.55,'Distinct listeners',14,'muted',align=PP_ALIGN.CENTER)
text(s,3.34,5.52,8.9,.33,'Illustrative topology; use the generated manifest for actual port numbers.',13,'muted')
note(s, 'Do not hard-code example listener ports as a universal contract. The external serving Service must target the routing sidecar, while local forwarding reaches the decode runtime. Health probes must hit the correct process. The exact port mapping and command flags depend on installed KAITO, llm-d, and vLLM versions.',[PD_DOC])

# 19
s = slide('The abstraction removes assembly—not visibility', '03 / Operator value',
          'One declared topology replaces repetitive runtime wiring.')
card(s,.55,2.35,5.35,3.75,'Before: manual assembly',
     'Pair role deployments and Services\n\nAlign labels, ports, env vars, probes\n\nWire sidecars and routing config','amber',size=18)
arrow(s,6.08,4.15,7.15,4.15,'blue',width=3)
card(s,7.43,2.35,5.35,3.75,'After: declared intent',
     'Describe roles in MultiRoleInference\n\nInspect generated child resources\n\nOperate through Kubernetes APIs','blue',size=18)
note(s, 'The value is reduced configuration drift, not the removal of all operational complexity. Operators still need observability, fabric validation, failure testing, and version-aware troubleshooting.',[PD_DOC])

# 20
s = slide('Autoscale the role that is actually saturated', '04 / Per-role autoscaling',
          'Different bottlenecks deserve different signals and scale decisions.',
          'Independent scaling only helps when the metrics match each role.')
for x,t,body,metric,ac in [
 (.55,'Prefill','Protect prompt latency\nand time to first token.','Primary signal: vLLM waiting requests','teal'),
 (6.78,'Decode','Protect token delivery\nand sustained throughput.','Primary signal: vLLM running requests','purple')]:
    card(s,x,2.35,5.95,2.7,t,body,ac,size=22)
    pill(s,x,5.35,5.95,metric,ac,'teal_bg' if ac=='teal' else 'purple_bg')
note(s, 'Use native vllm:num_requests_waiting for prefill and vllm:num_requests_running for decode as primary role-specific signals. Verify availability and aggregation on the actual runtime. KV utilization and latency add diagnostic context; a derived signal becomes a control input only after its semantics and safety policy are validated. This is a control-pattern recommendation, not a claim about an automatically available MRI feature.',[AUTOSCALING_DOC,KEDA_DOC])

# 21 — actual keda capabilities
s = slide('Today: KEDA targets the InferenceSet scale API', '04 / Existing capability',
          'Documented KAITO examples cover both scheduled and metric-based scaling.',
          'The scale target is the InferenceSet—not a manually scaled workload Pod.')
pill(s,.55,2.21,2.4,'Documented today','blue','blue_bg')
node(s,.55,3.12,3.5,1.37,'Trigger','Cron or Prometheus query','amber',22)
node(s,4.92,3.12,3.5,1.37,'KEDA / HPA','ScaledObject target','blue',22)
node(s,9.28,3.12,3.5,1.37,'InferenceSet','Scale subresource','teal',22)
arrow(s,4.05,3.8,4.92,3.8,'blue'); arrow(s,8.42,3.8,9.28,3.8,'teal')
rect(s,.55,5.05,12.23,.92,'white','line',True)
text(s,.78,5.31,3.6,.36,'Documented queue signal',17,'muted',True)
text(s,4.7,5.31,7.7,.37,'vllm:num_requests_waiting',19,'teal',mono=True)
note(s, 'KEDA is installed separately. The KAITO documentation shows Cron and Prometheus triggers with a ScaledObject scaleTargetRef pointing to a kaito.sh InferenceSet. The controller reconciles the desired replicas into serving resources. The queue metric example is real; it does not establish native per-role MRI autoscaling policy.',[KEDA_DOC])

# 22 — loops
s = slide('Two independent control loops, one logical service', '04 / Per-role autoscaling',
          'Conceptual design: validate signals and thresholds for the actual workload.')
for y,role,metric,target,ac in [
 (2.48,'Prefill','Waiting requests','Prefill InferenceSet','teal'),
 (4.55,'Decode','Running requests','Decode InferenceSet','purple')]:
    pill(s,.55,y,1.5,role,ac,'teal_bg' if ac=='teal' else 'purple_bg')
    for x,w,t,d in [(2.42,2.85,metric,'Observe'),(6.0,2.6,'KEDA / HPA','Decide'),(9.32,3.46,target,'Reconcile replicas')]:
        node(s,x,y-.08,w,1.19,t,d,ac,17)
    arrow(s,5.27,y+.5,6.,y+.5,ac); arrow(s,8.6,y+.5,9.32,y+.5,ac)
    route(s,[(11.05,y+1.11),(11.05,y+1.49),(3.84,y+1.49),(3.84,y+1.11)],ac,True)
text(s,.57,6.59,12.1,.36,'Add stabilization, warm-up awareness, and safe scale-down behavior to each loop.',16,'muted')
note(s, 'Conceptual two-loop design. A KEDA deployment can use one ScaledObject per target InferenceSet. Native vLLM waiting and running request gauges supply role-specific signals. Do not install conflicting autoscalers for one target. Metric aggregation, freshness, model warm-up and safe scale-down require verification. The following slides explain policy and signal choices independently of the configuration API.',[AUTOSCALING_DOC,KEDA_DOC])

# 23 — recommendation explicitly marked
s = slide('One service, independently managed role capacity', '04 / Policy boundary',
          'Coordinate P/D at the service level; make capacity decisions separately for each role.',
          'Scale a complete serving replica—not an individual tensor-parallel worker.')
pill(s,.55,2.22,4.3,'Design pattern / Per-role control','amber','amber_bg')
node(s,.55,3.15,3.6,2.22,'Service-level intent','Prefill: latency objective\nDecode: delivery objective','blue',22)
node(s,5.0,3.53,3.3,1.47,'Policy reconciliation','Independent role targets','blue',21)
node(s,9.15,2.96,3.63,1.17,'Prefill scale target','Generated policy + target','teal',18)
node(s,9.15,4.63,3.63,1.17,'Decode scale target','Generated policy + target','purple',18)
arrow(s,4.15,4.25,5.,4.25,'blue')
route(s,[(8.3,4.1),(8.7,4.1),(8.7,3.55),(9.15,3.55)],'teal')
route(s,[(8.3,4.42),(8.7,4.42),(8.7,5.22),(9.15,5.22)],'purple')
note(s, 'Public-facing design pattern: express service objectives, reconcile independent role policies, and scale each role as a complete serving replica. Policy representation and controller-specific wiring are implementation details and intentionally omitted here. Existing KEDA/InferenceSet capability is described on the earlier slide; this diagram is not a claim that automatic service-level policy projection is already available. Keep one authoritative autoscaler per target.',[AUTOSCALING_DOC,KEDA_DOC])

# Autoscaling detail A — policy ownership and independent actuators
s = slide('Observe each role. Act on its own capacity.', '04 / Control-loop design',
          'Independent feedback loops connect role-specific load to role-specific serving capacity.',
          'Routing chooses where requests go; autoscaling changes how much capacity is available.')
node(s,.55,2.23,3.5,1.16,'Role-specific policies','Signals, thresholds and bounds','blue',21)
node(s,4.92,2.23,3.5,1.16,'Independent decisions','One controller per target','blue',21)
node(s,9.28,2.23,3.5,1.16,'Serving capacity','Count model-ready replicas','blue',21)
arrow(s,4.05,2.81,4.92,2.81,'blue'); arrow(s,8.42,2.81,9.28,2.81,'blue')
for y,role,metric,ac in [(3.89,'Prefill','Waiting requests','teal'),(5.07,'Decode','Running requests','purple')]:
    node(s,.55,y,3.5,1.0,role+' vLLM /metrics',metric,ac,18)
    node(s,4.92,y,3.5,1.0,role+' autoscaler','Evaluate this role independently',ac,18)
    node(s,9.28,y,3.5,1.0,role+' replicas','Reconcile serving capacity',ac,18)
    arrow(s,4.05,y+.5,4.92,y+.5,ac); arrow(s,8.42,y+.5,9.28,y+.5,ac)
note(s, 'Architectural control pattern, independent of how policies are encoded. Each role has its own signals, controller decision and serving-replica target. KEDA/HPA targeting an InferenceSet is one implementation. Scope samples to the actual role and deduplicate engine/worker series. Scale complete serving replicas and account for model loading before counting new capacity as ready. Arrows show conceptual policy and metric flow, not strict ownership references or push-based scraping. The serving topology still coordinates P/D requests while the capacity loops act independently. Implementation-specific automatic policy projection is outside this talk slide.', [AUTOSCALING_DOC,KEDA_DOC])

# Autoscaling detail B — explicit native signals and illustrative actions
s = slide('Two native gauges, two scaling decisions', '04 / vLLM-native metrics',
          'Use per-replica role aggregation; tune thresholds against the deployed model and workload.',
          'Illustrative thresholds only. Verify actual /metrics output before enabling either policy.')
for x,role,metric,body,low,high,bounds,ac,bg in [
 (.55,'Prefill','vllm:num_requests_waiting','Queue inside the prefill engine.\nProtect prompt admission latency.','< 1','> 8','Example bounds: 1–8 role replicas','teal','teal_bg'),
 (6.78,'Decode','vllm:num_requests_running','Requests in decode execution batches.\nProtect token delivery under load.','< 4','> 24','Example bounds: 2–16 role replicas','purple','purple_bg')]:
    rect(s,x,2.28,5.95,3.8,'white','line',True)
    pill(s,x+.2,2.48,1.6,role,ac,bg)
    text(s,x+.2,3.06,5.55,.44,metric,20,ac,True,mono=True)
    text(s,x+.2,3.66,5.55,.77,body,18)
    for k,(t,d) in enumerate([(low,'Scale down'),('Between','Hold'),(high,'Scale up')]):
        xx=x+.2+k*1.86
        rect(s,xx,4.65,1.72,.83,bg,radius=True)
        text(s,xx+.06,4.74,1.6,.28,t,16,ac,True,PP_ALIGN.CENTER)
        text(s,xx+.06,5.11,1.6,.25,d,13,ac,align=PP_ALIGN.CENTER)
    text(s,x+.2,5.69,5.55,.3,bounds,15,'muted')
note(s, 'Native vllm:num_requests_waiting and vllm:num_requests_running are the primary signals for the respective roles. Verify metric presence, type and units on the actual runtime. Engine-local queues exclude requests still waiting in the router/EPP. Thresholds and bounds are illustrative, not capacity recommendations. The design example uses bounded incremental adjustments; behavior still depends on readiness, stabilization, cooldown and the chosen controller. Equal-to-threshold values hold under the stated strict comparisons. KV utilization and latency support diagnosis; integrating them into automated decisions needs an explicit tested policy. Missing/stale/non-finite data must not become zero; hold/report semantics require implementation and validation.', [AUTOSCALING_DOC,VLLM_METRICS])

# Autoscaling detail C — policy behavior rather than implementation syntax
s = slide('Different roles need different scaling policies', '04 / Role-specific decisions',
          'Use the same safety contract, but tune each role against its own workload and objective.',
          'Illustrative policy—not universal tuning. Validate thresholds, cooldown and model warm-up.')
table(s,.55,2.25,[3.2,4.51,4.51],[
 ['Policy','Prefill','Decode'],
 ['Primary signal','Waiting requests','Running requests'],
 ['Example replica range','1–8','2–16'],
 ['Example scale-up','Signal > 8','Signal > 24'],
 ['Example scale-down','Signal < 1','Signal < 4'],
 ['Shared guardrails','Readiness + fresh metrics','Readiness + fresh metrics']],.64)
note(s, 'The slide explains policy semantics without exposing configuration syntax. Values are illustrative and match the source design: waiting-request thresholds 8/1 and bounds 1–8 for prefill; running-request thresholds 24/4 and bounds 2–16 for decode. Evaluate role-scoped per-replica aggregation, not a whole-service sum. Apply strict above/below comparisons, hold between/equal to thresholds, and enforce bounds, fresh-data checks, readiness, stabilization and cooldown for both roles. Scale-down also requires safe treatment of in-flight work. Policy ownership must be unambiguous. The underlying representation is intentionally outside the external presentation.', [AUTOSCALING_DOC,VLLM_METRICS])

# Autoscaling detail D — safe lifecycle and unavailable data
s = slide('Safe autoscaling starts with ownership and valid data', '04 / Operational safeguards',
          'The happy path is small. Correct handoff and failure behavior make it operable.',
          'Avoid competing controllers, count only ready capacity, and protect in-flight requests.')
for i,(title,body,ac,tag) in enumerate([
 ('Choose one writer','One policy owns replica count\nSeparate targets for P and D\nNo competing autoscalers','blue','01 / Replica ownership'),
 ('Verify real signals','Inspect actual /metrics\nScope samples per role\nMissing is not zero\nOn failure: hold + report','teal','02 / Metric availability'),
 ('Make handoff explicit','Stop the old writer first\nDelete only owned scalers\nAllow model warm-up\nTest safe scale-down','purple','03 / Lifecycle')]):
    card(s,.55+i*4.14,2.35,3.95,3.35,title,body,ac,tag,17)
text(s,.57,5.97,12.1,.33,'On missing or invalid signals: hold decisions and report the problem. Missing is not zero.',16,'muted')
note(s, 'Safety contract: do not let a fixed-replica reconciler and an autoscaler compete for the same target. Stop the old writer before handing over control, and never silently adopt/delete user-managed autoscalers. Missing, stale, unreachable or non-finite metric samples should prevent activation or hold active decisions and surface a condition/event. This is the required behavior, not an assertion that all controller/HPA fallback paths implement it today; verify end to end. Partial scrape coverage must not look like zero load. Readiness includes model loading and actual serving eligibility. Protect in-flight requests and KV state during scale-down.', [AUTOSCALING_DOC])

# Autoscaling detail E — derived signals and their interpretation
s = slide('Derived signals add context to scaling decisions', '04 / Signal interpretation',
          'Aggregate native vLLM metrics to understand KV utilization, latency and throughput.',
          'KV occupancy is not demand. High or low throughput alone should not change replica counts.')
table(s,.55,2.25,[4.43,3.4,4.4],[
 ['Native input (vllm: prefix)','Derivation','Decision support'],
 ['kv_cache_usage_perc','max(role samples)','Candidate downscale guard'],
 ['kv_cache_usage_perc','1 - max(role samples)','Minimum free fraction;\nnot effective request capacity'],
 ['time_to_first_token_seconds\n(histogram buckets)','p95 over bucket rates','Latency tail; tune prefill policy'],
 ['generation_tokens_total','sum(rate(counter[5m]))','Output throughput;\nobserve and benchmark']],.78)
note(s, 'These are derived-signal design examples, not metrics natively emitted by vLLM or a claim of current MRI integration support. All table input names have the vllm: prefix. Proposed recording-rule names: kaito:decode_kv_cache_usage_max = max valid role-scoped vllm:kv_cache_usage_perc; kaito:decode_kv_cache_free_fraction_min = 1 - that maximum; kaito:prefill_ttft_p95_seconds = histogram_quantile(0.95, summed per-series 5m bucket rates preserving workload/role and le); kaito:decode_generation_tokens_per_second = sum of reset-aware rate(vllm:generation_tokens_total[5m]). Generation tokens is a native Counter exposed with the _total suffix. KV usage is a fraction 0–1; 0.8 is 80%. Maximum usage and minimum free fraction are complements, not independent evidence, bytes or effective request capacity. A fleet maximum does not identify a safe removal target. Histogram quantiles need sufficient observations and are engine-local, not client P/D latency. Apply rate before summing counters, account for resets, deduplicate engines and require fresh/full role coverage. Recording-rule outputs do not appear on vLLM /metrics; a verified adapter/query integration is required. The desired guard allows high running load to scale up independently of KV occupancy, while low load permits scale-down only with safe KV utilization. Simply appending KV to the existing conservative AND list can suppress needed scale-up and is not this policy. Start with observation; promote a signal to control only after failure and workload tests.', [AUTOSCALING_DOC,VLLM_METRICS])


# Annotation addition — 31: concrete implementation boundary, not a shipped MRI API
s = slide('KAITO annotations wire each role to its own scaler', '04 / KAITO implementation design',
          'Reuse existing InferenceSet scaling; add an explicit MRI-to-role policy adapter.',
          'Proposed MRI integration—not enabled today by adding annotations alone.')
node(s,.55,2.24,3.25,1.08,'MultiRoleInference','autoscaling.kaito.sh/roles','blue',19)
node(s,4.24,2.24,3.28,1.08,'MRI adapter (new)','Validate + project by role','amber',19)
node(s,8.0,2.24,4.78,1.08,'Role InferenceSet metadata','scaledobject.kaito.sh/*','teal',19)
arrow(s,3.8,2.78,4.24,2.78,'blue'); arrow(s,7.52,2.78,8.0,2.78,'teal')
rect(s,.55,3.56,6.08,2.56,'white','line',True)
text(s,.75,3.72,5.68,.3,'Generated prefill child annotations',12,'teal',True)
code = '''scaledobject.kaito.sh/auto-provision: "true"
scaledobject.kaito.sh/min-replicas: "1"
scaledobject.kaito.sh/max-replicas: "8"
scaledobject.kaito.sh/combinepolicy: AND
scaledobject.kaito.sh/metrics: |
  - name: vllm:num_requests_waiting
    type: gauge
    upthreshold: 8
    downthreshold: 1'''
sh=text(s,.75,4.19,5.68,1.76,code,11.6,'ink',mono=True)
for p in sh.text_frame.paragraphs: p.space_after=Pt(0)
text(s,7.0,3.59,5.65,.33,'One path per role',12,'blue',True)
text(s,7.0,4.02,5.65,.78,'Scaler provisions ScaledObject\nKEDA / HPA writes InferenceSet /scale',18,'ink')
text(s,7.0,4.97,5.65,1.13,'Required: opt in MRI-owned children\nWrite metadata, not template annotations\nreplicas: null releases MRI enforcement',15,'amber')
note(s, 'This is the proposed annotation-first integration, not an existing deployable MRI API. Existing scaler source consumes InferenceSet.metadata.annotations and provisions an owned ScaledObject. It currently rejects MRI-owned children in create/update predicates; deliberately support only adapter-managed opt-in children, including cleanup events. MRI currently copies annotations to child spec.template.annotations; that placement does not configure this scaler. A new adapter must validate/version autoscaling.kaito.sh/roles, match entries by role type, project only allowed scalar/metrics keys into the matching child metadata, keep the policy blob out of workload templates, watch annotation-only changes, and remove stale owned output. One child InferenceSet and one ScaledObject per enabled role; KEDA/HPA targets that child scale subresource, not MRI or an individual Pod. A null role replicas value stops MRI steady-state replica enforcement but does not create an autoscaler. Reject fixed replicas plus policy and conflicting manually managed autoscalers; preserve unrelated annotations and perform ordered cleanup/handoff. KEDA, the scaler and metrics collection must be installed/configured separately. Sources are pinned in the design document: KAITO 3c831cad and scaler ba1f2340. The annotation block shown is generated output inside child metadata.annotations. Decode receives the analogous 2..16 / running / 24 / 4 policy.', [AUTOSCALING_DOC,KEDA_DOC])

# Annotation addition — 32: input and observable per-role behavior
s = slide('Example: one MRI policy, independent P/D decisions', '04 / KAITO annotation example',
          'Illustrative policy excerpts. Full proposed manifest is linked in the speaker notes.',
          'Requires the MRI adapter + child opt-in above. Thresholds are examples, not production tuning.')
rect(s,.55,2.22,6.2,4.03,'white','line',True)
text(s,.75,2.3,5.8,.25,'MRI metadata.annotations',12,'blue',True,mono=True)
code = '''autoscaling.kaito.sh/roles: |
  version: v1alpha1
  roles:
    prefill:
      min-replicas: "1"
      max-replicas: "8"
      combinepolicy: AND
      metrics:
      - name: vllm:num_requests_waiting
        type: gauge
        upthreshold: 8
        downthreshold: 1
    decode:
      min-replicas: "2"
      max-replicas: "16"
      combinepolicy: AND
      metrics:
      - name: vllm:num_requests_running
        type: gauge
        upthreshold: 24
        downthreshold: 4'''
sh=text(s,.75,2.65,5.8,3.59,code,10.7,'ink',mono=True)
for p in sh.text_frame.paragraphs:
    p.space_after=Pt(0)
    p.line_spacing=Pt(12.2)
rect(s,7.02,2.22,5.76,1.55,'blue_bg',radius=True)
text(s,7.22,2.36,5.36,.3,'MRI spec.roles (excerpt)',13,'blue',True,mono=True)
sh=text(s,7.22,2.83,5.36,.79,'- type: prefill\n  replicas: null\n- type: decode\n  replicas: null',12,'ink',mono=True)
for p in sh.text_frame.paragraphs: p.space_after=Pt(0)
text(s,7.04,3.98,5.69,.31,'Role averages / Start at P=1, D=2',12,'blue',True)
text(s,7.04,4.49,5.69,.7,'Waiting=12; running=12\nPrefill scales up; decode holds.',17,'teal')
text(s,7.04,5.4,5.69,.68,'Running later rises above 24:\ndecode can scale up independently.',16,'purple')
note(s, 'The left panel is a literal excerpt under MRI metadata.annotations; the right is a spec.roles excerpt, not the entire deployable resource. Full YAML: llm/kaito-llm-d/examples/proposed-pd-autoscaling-annotations.yaml in this repository. Model and instanceType values in that file are illustrative and not deployment-validated. Annotation policy is a proposal and needs the integration work on the preceding slide. Role replicas are null to stop MRI enforcement; the adapter must reject non-null replicas with an enabled policy and bootstrap minima safely. The modelpod source discovers Workspaces owned by the target InferenceSet and scrapes their Workspace Service /metrics endpoints, not every GPU worker individually. The gauge default is service-avg: sum matching label series within each service, then average across successfully scraped services. Treat this as a per-serving-replica signal only after verifying the runtime/service topology; do not use an MRI-wide total or include router/EPP queues. Current source skips failed services and can treat a partially absent metric as zero, so complete-coverage missing-is-not-zero hardening is still required, not an existing guarantee. Example: with P=1 and D=2, prefill waiting=12 is above 8, so prefill has an up decision while decode running=12 lies between 4 and 24, so decode holds. Later running above 24 can independently request decode scale-up. These are illustrative decision outcomes, not observed tests or guaranteed instantaneous replica counts: readiness, cooldown, stabilization, data availability and bounds still apply. Strict comparisons mean equality holds. The generated expression produces 2.0 when ready and above up-threshold, 0.5 below down-threshold, otherwise 1.0; raw desired replicas are ceil(current replicas times that result). The generated HPA behavior limits each directional change to at most one replica per configured cooldown period, subject to stabilization and bounds. The formula is not itself N+1/N-1 and an evaluation does not guarantee immediate scaling. Values below 1 for prefill or below 4 for decode can request scale-down only after safeguards and within minima. Each role has only one metric, so AND is trivial within a role; it does NOT mean prefill and decode must both be busy. Do not claim an asymmetric KV guard is implemented by appending KV to AND. Require deployed vLLM /metrics verification and full-role sample coverage before activation.', [AUTOSCALING_DOC,VLLM_METRICS,'https://github.com/andyzhangx/demo/blob/master/llm/kaito-llm-d/examples/proposed-pd-autoscaling-annotations.yaml'])

# 24 — comparison protocol
s = slide('Benchmark the operating point—not only the peak', '05 / Evaluation plan',
          'Compare aggregated and P/D deployments under the same constraints.',
          'Local KAITO evaluation plan; external reference results follow.')
node(s,.55,2.37,3.3,1.31,'Workload replay','Same model, traffic, and SLO','blue',21)
node(s,5.05,2.37,3.35,1.31,'Aggregated','Baseline configuration','blue',21)
node(s,9.45,2.37,3.33,1.31,'Disaggregated','Prefill + decode configuration','teal',21)
arrow(s,3.85,2.86,5.05,2.86,'blue')
route(s,[(3.85,3.2),(4.4,3.2),(4.4,4.04),(11.12,4.04),(11.12,3.68)],'teal')
table(s,.55,4.38,[3.2,9.03],[
 ['Hold constant','Report with the result'],
 ['Model + traffic','Version, quantization, prompt/output lengths, concurrency'],
 ['Cost + SLO','GPU budget, fabric, TTFT/ITL target, warm-up and duration']],.59)
note(s, 'This slide is an evaluation protocol, not a result. Match GPU budget or cost budget and state the comparison basis. Report latency percentiles and achieved throughput at matched load. Include transport and hardware topology, model and runtime versions, warm-up, run duration, and sampling method. No synthetic performance curves should be mistaken for measurements.')

# 25 — no fake chart
s = slide('TTFT: measure the tail under prompt pressure', '05 / Benchmark scorecard',
          'Local measurement plan. External benchmark results are separate—not KAITO data.')
pill(s,.55,2.18,2.9,'Awaiting measured results','amber','amber_bg')
table(s,.55,2.87,[3.52,4.35,4.36],[
 ['TTFT metric','Aggregated','P/D'],
 ['p50 / median','Not measured','Not measured'],
 ['p95 / tail','Not measured','Not measured'],
 ['p99 / extreme tail','Not measured','Not measured']],.64)
rect(s,.55,5.7,12.23,1.08,'teal_bg',radius=True)
text(s,.78,5.88,11.7,.35,'Question to answer',19,'teal',True)
text(s,.78,6.33,11.7,.3,'Does P/D reduce tail TTFT at the same offered load and cost budget?',16,'ink')
note(s, 'Replaces the original [X]% / [Y]% placeholders. There is no numeric claim or implied performance curve. Collect TTFT percentiles under prompt-heavy traffic and report the request rate, concurrency, prompt/output distributions, model, hardware, and cost comparison. Include the effect of KV-transfer overhead.')

# 26
s = slide('Throughput: count useful work inside the SLO', '05 / Benchmark scorecard',
          'Local measurement plan. Report useful throughput and its cost together.')
pill(s,.55,2.18,2.9,'Awaiting measured results','amber','amber_bg')
table(s,.55,2.87,[3.52,4.35,4.36],[
 ['Measure','Aggregated','P/D'],
 ['Output tokens / second','Not measured','Not measured'],
 ['Requests meeting SLO','Not measured','Not measured'],
 ['Cost / useful output','Not measured','Not measured']],.64)
rect(s,.55,5.7,12.23,1.08,'purple_bg',radius=True)
text(s,.78,5.88,11.7,.35,'Utilization is context—not the success metric.',19,'purple',True)
text(s,.78,6.33,11.7,.3,'Compare steady token delivery, SLO goodput, active KV usage, and GPU-hours.',16,'ink')
note(s, 'No benchmark results are supplied. High utilization alone does not prove better efficiency. Record achieved output throughput and successful requests under agreed TTFT and inter-token-latency limits; report total GPU-hours or cost for both phases and associated infrastructure.')

# 27
s = slide('The break-even boundary is a measurement problem', '05 / Workload decision map',
          'Qualitative candidates only—not a measured heatmap or a performance guarantee.')
table(s,.55,2.48,[3.35,4.44,4.44],[
 ['Workload','Short output','Long output'],
 ['Short prompt','Start with aggregated','Evaluate decode pressure'],
 ['Long prompt','Evaluate prefill isolation','Strong P/D candidate to test']],.88)
rect(s,.55,5.5,12.23,.88,'amber_bg',radius=True)
text(s,.8,5.71,11.72,.47,'Concurrency, GPU budget, and transfer fabric can change the result in every cell.',17,'amber',True)
note(s, 'A decision aid, not experimental data. Prompt and output lengths interact with concurrency, model size, parallelism, and hardware. Validate both latency and cost. Even the strongest candidate cell is not a guaranteed P/D win.')

# Public benchmark additions — 37–39; external results, not KAITO tests
bench_context = 'External vLLM / MORI-IO study • Qwen3-235B-A22B-FP8 • one 8× MI300X node • 2K input / 1K output'
bench_notes = ('External benchmark by AMD and Embedded LLM, published on the vLLM blog on 2026-04-07; not a KAITO or llm-d measurement and not a reproduction performed for this deck. Hardware: one node, 8 AMD MI300X GPUs. Model: Qwen/Qwen3-235B-A22B-FP8. Compare standard two independent TP4 instances with MORI-IO write-mode 1P+1D, TP4 per role; all eight GPUs used in either case. Synthetic random workload, fixed 2000-token input and 1000-token output, 100 requests at 8 offered requests/s for the per-request data. Concurrent prefill/decode phases, NOT a heterogeneous prompt-length or asymmetric-traffic sweep. Source software is a vLLM source build (no exact vLLM commit stated), ROCm 7.0.3, MORI 0.1.0; gpu_memory_utilization=0.9, max_model_len=4096, max_num_seqs=256, enable_expert_parallel=True.\n'
               'Provenance: the pinned Figure 3 JavaScript DATA arrays contain 100 paired TTFT/ITL values per configuration, in seconds. Joint pass criterion is TTFT <=1 second and the published per-request ITL value <=0.05 seconds. This reproduces the JavaScript predicate. It is NOT a p99-per-token ITL test and ITL aggregation inside each request is not documented by the exported arrays. Figure 3 arrays produce 29 standard TP4 passes and 73 write-mode passes. The post’s static Table 3 instead says 28 and 70; use the pinned arrays consistently and do not silently combine those snapshots. Figure 4 is reproduced as published; rates other than 8 are not digitized.\n'
               'No sustained tokens/s, completed requests/s, GPU busy utilization, energy, dollar cost, or fewer-GPU result is measured by this deck. The small 100-request trace has no error bars or repeated-run uncertainty. Results are evidence of a tradeoff in this setup, not a universal P/D win. All raw values and derivations are documented in kubecon-pd-assets/benchmarks/README.md.\n')
s = slide('Evaluation results: TTFT is a trade-off', '05 / Public benchmark — TTFT',
          bench_context,
          'No TTFT win in this setup: measure first-token latency separately from streaming quality.')
text(s,.65,2.16,6.7,.31,'TTFT (ms) • lower is better • 8 offered req/s',14,'blue',True)
# Native, editable grouped bars. Median and nearest-rank p95 from published arrays.
base_y, top_y, chart_x0, chart_x1 = 5.65, 2.78, 1.15, 7.15
for val in (0,500,1000,1500):
    y=base_y-(base_y-top_y)*val/1500
    arrow(s,chart_x0,y,chart_x1,y,'line',1,False)
    text(s,.56,y-.12,.49,.24,str(val),10,'muted',align=PP_ALIGN.RIGHT)
for center,percentile in ((2.68,'p50'),(5.65,'p95')):
    for dx,key,ac in ((-.79,'normal','blue'),(.12,'write','teal')):
        values=BENCH[key+'_ttft']
        value=1000*(statistics.median(values) if percentile=='p50' else sorted(values)[math.ceil(.95*len(values))-1])
        height=(base_y-top_y)*value/1500
        rect(s,center+dx,base_y-height,.66,height,ac)
        text(s,center+dx-.13,base_y-height-.3,.92,.27,str(round(value)),13,ac,True,PP_ALIGN.CENTER)
    text(s,center-.72,5.76,1.57,.27,percentile,13,'ink',True,PP_ALIGN.CENTER)
rect(s,1.05,2.58,.15,.12,'blue');text(s,1.28,2.49,2.3,.25,'Colocated: 2× TP4',11,'ink')
rect(s,4.04,2.58,.15,.12,'teal');text(s,4.27,2.49,2.8,.25,'P/D: write, TP4 + TP4',11,'ink')
text(s,7.78,2.62,4.93,.7,'First token is slower here.',23,'amber',True)
text(s,7.78,3.56,4.85,1.08,'Long prompts + concurrency can\nmake decode isolation valuable.\nThat does not imply lower TTFT.',17,'ink')
text(s,7.78,5.09,4.85,.84,'No prompt-length sweep was published.\nDo not infer which prompts gain most.',15,'muted')
text(s,.65,6.09,11.9,.18,'Source: vLLM blog (Apr 7, 2026), Figure 3 data. Median / nearest-rank p95 computed from 100 requests; see notes.',9,'muted')
note(s, bench_notes+'One chart, one interpretation: this comparison trades a higher TTFT for more stable decoding, rather than proving a TTFT improvement. Values: standard median 227.9635 ms, p95 490.613 ms; write-mode median 645.135 ms, p95 1325.584 ms. Median is the mean of the middle two ordered observations; p95 is nearest-rank (95th of 100). Rounded to integer milliseconds on the slide. No SLO line is implied by the 1000 ms grid tick. The source recommends investigating P/D for high concurrency and long prompts because prefill interference is stronger, but has no prompt-length sweep supporting a quantified TTFT gain by workload. Do not narrate a fabricated long-prompt TTFT win.', [BENCH_URL,BENCH_RAW])

s = slide('Evaluation results: useful throughput under load', '05 / Public benchmark — SLO attainment',
          bench_context,
          'Two phases, one pool: removing decode interference improves SLO attainment—not every latency metric.')
s.shapes.add_picture(str(ROOT/'kubecon-pd-assets/benchmarks/moriio-slo-attainment.png'),Inches(.55),Inches(2.13),width=Inches(6.66))
# Outline a narrow region around 8 req/s without modifying the original chart pixels.
highlight = rect(s,5.57,2.35,.61,2.81,'white','amber',True)
highlight.fill.background()
text(s,7.68,2.38,4.96,.43,'Focus: 8 offered req/s',14,'amber',True)
text(s,7.68,3.04,4.96,.68,'29% → 73%',32,'teal',True)
text(s,7.68,3.91,4.96,.96,'Joint SLO passes at this load\nColocated 2× TP4 → P/D write\nTTFT ≤1 s and ITL ≤50 ms',16,'ink')
text(s,7.68,5.18,4.96,.89,'Concurrent P/D phases; fixed 2K/1K.\nNot a heterogeneous traffic benchmark\nor an absolute tokens/s result.',14,'muted')
text(s,.65,6.09,11.9,.18,'Source: vLLM blog Figure 4, reproduced with attribution; highlighted region at 8 req/s. Callout uses pinned Figure 3 arrays.',9,'muted')
note(s, bench_notes+'Keep narration high signal. Original Figure 4 shows request SLO attainment versus offered request rate, not measured token throughput. The source calls the joint-SLO benefit higher goodput; this slide retains the original y-axis instead of relabeling it as throughput. The orange outline focuses attention on about 8 req/s. The 29% and 73% callout comes from the exact Figure 3 arrays for standard TP4 and MORI-IO write, not visual digitization. Other configurations are retained as source context; do not narrate every curve. At this load the colocated configuration’s per-request ITL values account for failed joint SLOs; the P/D write configuration’s TTFT values account for its failures. This supports phase-interference interpretation, not an unqualified peak-throughput claim. Prompt/output lengths are fixed, so mixed-length traffic remains a validation gap. The source caption overstates improvement across all rates: at the lowest rate standard TP4 also reaches 100%, so this slide only highlights the loaded regime.', [BENCH_URL,BENCH_RAW])

s = slide('Evaluation results: more SLO passes per GPU', '05 / Public benchmark — efficiency proxy',
          bench_context,
          'More useful work on the same eight GPUs—not measured GPU utilization or proof that fewer GPUs suffice.')
text(s,.66,2.25,6.51,.38,'Normalized SLO passes / GPU',14,'blue',True)
ratio=BENCH_PASSES['write']/BENCH_PASSES['normal']
for y,name,value,ac in ((3.16,'Colocated',1.0,'blue'),(4.37,'P/D write',ratio,'teal')):
    text(s,.66,y-.02,1.75,.37,name,16,'ink',True)
    rect(s,2.54,y,4.02*value/ratio,.49,ac)
    text(s,2.54+4.02*value/ratio+.13,y-.01,.91,.47,f'{value:.2f}×',18,ac,True)
text(s,.66,5.4,6.51,.56,'Same 100-request workload and 8-GPU budget.\nA comparison-specific efficiency proxy, not sustained capacity.',13,'muted')
table(s,7.79,2.37,[2.17,1.2,1.08],[
 ['Measure','2× TP4','P/D'],
 ['Total GPUs','8','8'],
 ['Joint SLO passes','29 / 100','73 / 100'],
 ['SLO passes / GPU','3.625','9.125'],
 ],row_h=.82)
text(s,7.79,5.72,4.72,.37,'No GPU savings or utilization claim.',12,'amber')
text(s,.65,6.09,11.9,.18,'Source: pinned vLLM Figure 3 arrays. Derived proxy = (SLO passes / 8 GPUs), normalized to colocated; not req/s/GPU.',9,'muted')
note(s, bench_notes+'Reinforce why separate pools: isolate prefill and decode, then judge useful service delivered at a fixed resource budget. The source configuration uses all 8 GPUs in both cases: standard 2×TP4 versus prefill TP4 + decode TP4. Derivation: 29/8=3.625 and 73/8=9.125 SLO passes per GPU in each 100-request trace; normalized ratio = (73/8)/(29/8) = 73/29 = 2.517241379, displayed 2.52×. This is a sample-specific SLO-pass efficiency proxy, NOT a time-normalized throughput-per-GPU metric, GPU busy percentage, independent capacity study, cost/energy result, or justification for dividing the GPU budget by 2.52. Do not claim fewer GPUs. There is no asymmetric traffic experiment or dynamic P/D autoscaling in this source; that business case still needs a controlled local benchmark. The same trace supports the preceding slide, so these are three interpretations of one study, not three independent confirmations.', [BENCH_URL,BENCH_RAW])

# 28
s = slide('Production lesson #1: KV transfer is a dependency', '06 / Production lessons',
          'A healthy inference API does not prove the KV-data path is healthy.',
          'Measure the transfer path end to end, including cross-node deployments.')
node(s,.55,2.5,3.35,1.3,'Prefill memory','KV source','teal',23)
node(s,4.98,2.5,3.35,1.3,'Transfer fabric','Bandwidth + latency + topology','amber',21)
node(s,9.43,2.5,3.35,1.3,'Decode memory','KV destination','purple',23)
arrow(s,3.9,3.15,4.98,3.15,'teal',width=3); arrow(s,8.33,3.15,9.43,3.15,'teal',width=3)
for i,(t,d,ac) in enumerate([
 ('Observe','Transfer duration\nErrors and retries','teal'),
 ('Validate','Node / GPU placement\nTransport configuration','amber'),
 ('Compare','Same-node vs cross-node\nLatency and cost impact','purple')]):
    node(s,.55+i*4.14,4.52,3.95,1.48,t,d,ac,20)
note(s, 'A conceptual dependency diagram. Actual transport support is version- and hardware-dependent. Do not assert a specific RDMA or non-RDMA configuration without validating the deployment. Include fabric contention and failure cases in production testing.',[PD_DOC])

# 29
s = slide('Production lesson #2: readiness is a chain', '06 / Production lessons',
          'A Running pod is only one part of a usable serving path.',
          'Make routing eligibility depend on the right readiness contracts.')
for i,(title,body,ac) in enumerate([
 ('Model ready','Weights loaded\nRuntime responsive','teal'),
 ('Proxy ready','Correct local backend\nHealthy listeners','purple'),
 ('Route ready','Labels and endpoints\nPorts and pool wiring','blue')]):
    x=.55+i*4.14
    node(s,x,2.65,3.95,1.77,title,body,ac,23)
    if i<2: arrow(s,x+3.95,3.54,x+4.14,3.54,ac,width=1.5)
rect(s,.55,5.02,12.23,.95,'white','line',True)
text(s,.8,5.3,11.73,.45,'Test startup, partial failure, replacement, and rollout—not only the steady state.',19,'muted')
note(s, 'The chain represents logical serving readiness, not a mandatory serial process startup order. Probe the correct process and listener. Test whether unready backends are excluded, how endpoints appear in the EPP, and how sidecars behave while the model warms up.',[PD_DOC])

# 30
s = slide('Production lesson #3: use role-appropriate signals', '06 / Production lessons',
          'One dashboard can show both phases; one scaling signal should not govern both.')
table(s,.55,2.45,[2.24,4.15,5.84],[
 ['Role','Useful signals','Watch out for'],
 ['Prefill','Queue / prompt pressure','Averages that hide burst and tail latency'],
 ['Decode','Running load; observe KV usage','Evicting active work during scale-down'],
 ['Both','Warm-up + SLO + capacity','Oscillation, slow model load, fabric limits']],.85)
note(s, 'Native vllm:num_requests_waiting and vllm:num_requests_running are the primary role-specific signals. KV utilization can inform a safety guard only with explicit tested semantics. Validate availability, role scope, units and freshness. Derived metrics require aggregation and collection; their names are not native vLLM outputs.',[AUTOSCALING_DOC,KEDA_DOC])

# 31
s = slide('A production decision has four gates', '06 / Tradeoffs',
          'The benchmark is one gate; the operating model is another.')
for i,(t,b,ac,tag) in enumerate([
 ('Workload fit','Do prompt and generation pressure diverge enough?','teal','01'),
 ('Transfer path','Can KV movement stay inside the latency budget?','amber','02'),
 ('Operational fit','Can the team observe, scale, and debug both roles?','blue','03'),
 ('Measured win','Does SLO goodput improve at acceptable total cost?','purple','04')]):
    card(s,.55+i*3.13,2.4,2.94,3.62,t,b,ac,tag,18)
note(s, 'Use these gates to decide whether to keep, tune, or reject P/D. Do not infer a generic performance percentage. Operators still own resource placement, network policy, observability, failure recovery, and upgrades.')

# P/D adoption addition — source Markdown Slide 34, actual slides 41–42
s = slide('When should you use P/D—and when not?', '06 / P/D decision matrix',
          'Two axes matter: how different the roles are, and what the KV-transfer path costs.',
          'Use P/D when the roles want different capacity and KV transfer does not erase the gain.')
text(s,2.38,2.17,4.85,.32,'Expensive / weak KV transfer',13,'amber',True,PP_ALIGN.CENTER)
text(s,7.69,2.17,4.85,.32,'Cheap / fast enough KV transfer',13,'teal',True,PP_ALIGN.CENTER)
text(s,.55,2.9,1.55,.92,'Different\nbottlenecks /\nscaling needs',14,'ink',True)
text(s,.55,4.74,1.55,.8,'Similar\nbottlenecks /\nscaling needs',14,'muted',True)
for x,y,w,title,body,fill,ink in [
 (2.3,2.68,5.05,'Improve topology first','Independent capacity may help.\nTransfer overhead may erase the gain.','amber_bg','amber'),
 (7.62,2.68,5.16,'Strong P/D candidate','Different role capacity or parallelism.\nValidate the gain at matched SLO + cost.','teal_bg','green'),
 (2.3,4.39,5.05,'Stay aggregated','Little role separation benefit,\nplus an expensive transfer path.','line','muted'),
 (7.62,4.39,5.16,'Usually stay aggregated','Fast fabric alone is not a reason to split.\nOperational gains may be limited.','white','blue')]:
    rect(s,x,y,w,1.48,fill,radius=True)
    text(s,x+.18,y+.16,w-.36,.31,title,16,ink,True)
    text(s,x+.18,y+.67,w-.36,.67,body,15,'ink')
note(s, 'Source: companion Markdown, Slide 34 — When to use P/D, and when not to. This is a qualitative decision matrix, not measured results or a performance guarantee. The horizontal axis increases from costly/weak transfer to cheap/fast-enough transfer; the vertical axis increases from similar role bottlenecks at the bottom to meaningfully different scaling, bottlenecks or parallelism at the top. Top-right is the strongest candidate; bottom-left stays aggregated. Top-left should first improve locality/transport or investigate same-node placement. Bottom-right usually remains aggregated because cheap transfer does not by itself create a reason for role separation. Cross-node placement is a risk factor to measure, not proof that fabric is weak: fast cross-node links can satisfy the right-hand condition. Likewise single-node transfer is not automatically free. Compare actual KV payload transfer cost, contention, tail latency, reliability and operational complexity. A strong candidate still requires a matched workload/cost/SLO benchmark.', [SOURCE+'#slide-34--when-to-use-pd-and-when-not-to'])

s = slide('Apply the matrix to your workload and topology', '06 / P/D adoption examples',
          'Workload shape suggests a candidate. Measurement decides whether to keep it.',
          'A long prompt or a fast interconnect alone is not enough—both axes must justify separation.')
for i,(title,body,ac,tag) in enumerate([
 ('Keep it simple','Small model, short prompts\nLow concurrency\nSimilar P/D scaling needs\n\nStart with aggregated.','blue','Similar roles'),
 ('Benchmark P/D','Different role bottlenecks\nDifferent scaling or TP needs\nCheap, reliable KV transfer\n\nTest independent role capacity.','teal','Strong candidate'),
 ('Fix the path first','Different role bottlenecks\nCostly or unstable KV path\n\nImprove locality or transport.\nThen reassess P/D.','amber','Transfer-limited')]):
    card(s,.55+i*4.14,2.3,3.95,3.43,title,body,ac,tag,15)
text(s,.57,5.94,12.1,.35,'Start with a simple topology; measure client TTFT / ITL, KV-transfer tails, SLO goodput and total cost.',14,'muted')
note(s, 'Expands companion Markdown Slide 34 into concrete but unmeasured adoption scenarios. Small models, short prompts, low concurrency and simple traffic often favor aggregated serving, but those attributes are heuristics rather than hard cutoffs. Long prompts, retrieval-heavy traffic, long generation or high concurrency are reasons to investigate divergent P/D pressure, not sufficient conditions for a win. Use P/D when separate capacity/parallelism can address a demonstrated bottleneck and KV-transfer overhead does not eliminate that benefit. A single-node multi-GPU experiment can simplify the initial topology if the model and role placement fit; it is not a universal fastest or feasible configuration. Cross-node P/D raises the validation bar: test transfer payload sizes, sustained/tail latency, contention, reliability, network policy and failure recovery. Improve locality or transport before adding scale if KV transfer is already the bottleneck. Compare aggregated and P/D at the same model, request distribution, offered load and GPU/cost budget, measuring client-visible TTFT/ITL, SLO goodput, transfer tails and total GPU cost. Retain a reversible aggregated baseline; do not claim measured savings here.', [SOURCE+'#slide-34--when-to-use-pd-and-when-not-to'])

# 32
s = slide('Adopt P/D in reversible steps', '06 / Adoption path',
          'Start with the simplest serving model that meets the workload.')
for i,(title,body,ac) in enumerate([
 ('Baseline','Run aggregated.\nMeasure traffic + SLO.','blue'),
 ('Separate','Declare roles.\nValidate KV + routing.','teal'),
 ('Tune','Set role capacity.\nBenchmark at fixed cost.','purple'),
 ('Operate','Add scale policies.\nTest failure + rollback.','amber')]):
    x=.55+i*3.13
    card(s,x,2.55,2.94,3.38,title,body,ac,f'Step {i+1}',18)
    if i<3: arrow(s,x+2.94,4.16,x+3.13,4.16,ac,width=1.4)
note(s, 'Begin with a measurable aggregated baseline. Keep an operationally viable rollback path and compare like-for-like cost and SLO. Per-role autoscaling should follow validated signals; avoid changing topology, parallelism, transport, and autoscaling all at once.')

# 33
s = slide('Demo: follow the intent into the running system', '07 / Demo path',
          'Show the same service at the API, controller, and traffic layers.')
for i,(title,body,ac) in enumerate([
 ('1  Declare','Inspect the MRI\nand its role settings.','blue'),
 ('2  Reconcile','Inspect child InferenceSets,\nWorkspaces, and routing.','teal'),
 ('3  Verify','Send one request.\nObserve both roles.','purple')]):
    card(s,.55+i*4.14,2.45,3.95,3.03,title,body,ac,size=20)
text(s,.57,5.96,12.1,.43,'Optional: apply a verified KEDA policy to one child InferenceSet and observe scaling.',17,'muted')
note(s, 'Demo outline, not evidence of a demo run. Before presenting: verify installed CRD versions, Gateway, supported model/preset, fabric connectivity, and metric availability. Use docs appropriate to that version. Do not present the proposed MRI autoscaling UX as an available manifest.',[PD_DOC,KEDA_DOC])

# 34
s = slide('Next: make multi-role serving easier to operate', '07 / Direction',
          'Recommended areas of work—not release commitments.')
for i,(title,body,ac) in enumerate([
 ('Scaling UX','Express per-role policy\nwithout repetitive plumbing.','teal'),
 ('Observability','Connect request latency,\nrole load, and KV transfer.','blue'),
 ('Topology UX','Keep richer serving layouts\ninside the same API model.','purple')]):
    card(s,.55+i*4.14,2.45,3.95,3.43,title,body,ac,'Direction',20)
note(s, 'These are talk recommendations derived from the source outline, not a published project delivery timeline. Keep the distinction between current capability and proposed user experience explicit.')

# Roadmap addition — source Markdown Slide 36, actual slide 46
s = slide('What’s next for KAITO + llm-d', '07 / Integration roadmap',
          'Build on P/D with better cache reuse, richer role layouts and larger-scale execution.',
          'Integration directions—not release dates or claims that every upstream capability is new.')
for i,(title,body,ac,tag) in enumerate([
 ('Cache-aware serving','KV-event-based\nprefix-cache routing\n\nTiered cache: HBM + CPU RAM\n+ optional filesystem tiers','teal','Near term'),
 ('E/P/D','Encode / Prefill / Decode\n\nExtend role-based serving\nto richer inference topologies.','blue','Next topology'),
 ('Larger-scale systems','Wide Expert Parallelism\n\nCross-node transport\nand communication\noptimization','purple','At larger scale')]):
    card(s,.55+i*4.14,2.35,3.95,3.72,title,body,ac,tag,17)
note(s, 'Based on companion Markdown Slide 36 — What’s next for KAITO + llm-d. Near-term integration directions are precise prefix-cache routing driven by KV events and tiered prefix cache across GPU HBM, CPU RAM, and optional filesystem tiers. The next topology item is E/P/D: Encode, Prefill, Decode. Larger-scale work includes Wide Expert Parallelism and cross-node transport/communication optimization. These are presentation-level KAITO integration directions, not a dated release commitment or a claim that llm-d and its runtimes lack these capabilities today. Speculative decoding was removed from future work because the presenter confirms it is already implemented; this slide does not attempt to revalidate its support matrix or claim universal runtime support. Keep feature availability tied to the deployed KAITO/llm-d/runtime versions.', [SOURCE+'#slide-36--whats-next-for-kaito--llm-d'])

# 35
s = slide('Three things to remember', '08 / Takeaways',
          'Independent capacity is the opportunity. Reconciled topology is the enabler.')
for i,(title,body,ac) in enumerate([
 ('Split for a reason','Prefill and decode have different bottlenecks.','teal'),
 ('Declare the topology','KAITO composes the resources; llm-d routes the work.','blue'),
 ('Prove the tradeoff','Use role-aware metrics and measure against a baseline.','purple')]):
    y=2.38+i*1.19
    pill(s,.55,y+.24,.6,f'0{i+1}',ac,{'teal':'teal_bg','blue':'blue_bg','purple':'purple_bg'}[ac])
    text(s,1.42,y+.08,4.15,.48,title,24,ac,True)
    text(s,5.72,y+.13,6.95,.78,body,19)
note(s, 'Restate the thesis without claiming unmeasured speedups. P/D is useful when the workload and infrastructure justify independent capacity shaping. KAITO aims to make that topology a normal Kubernetes operating model.')

# 36
s = slide('Questions? Start with your workload.', '08 / Q&A', dark=True)
text(s,.55,1.77,11.8,1.05,'Which phase limits you today—\nprompt processing, token delivery, or the KV path?',26,'white',True)
for i,(title,body,ac) in enumerate([
 ('Workload','Prompt + output lengths','teal'),('Infrastructure','GPU topology + fabric','blue'),('Operations','SLO + scaling signals','purple')]):
    node(s,.55+i*4.14,3.28,3.95,1.4,title,body,ac,22)
text(s,.55,5.26,12.2,.36,'Continue with the implementation guides',18,'pale',True)
for y,label,url in [(5.87,'KAITO: prefill/decode disaggregation',PD_DOC),(6.32,'KAITO: KEDA autoscaling for InferenceSet',KEDA_DOC)]:
    sh=text(s,.55,y,12.0,.34,label,15,'white')
    sh.text_frame.paragraphs[0].runs[0].hyperlink.address=url
note(s, 'Use workload, fabric, and operational constraints to guide questions. Both links are clickable in PowerPoint. Full URLs are retained here for export formats that do not preserve hyperlinks.',[PD_DOC,KEDA_DOC])

assert len(prs.slides) == 56
prs.save(OUT)
print(f'Saved {OUT} ({len(prs.slides)} slides; editable shapes plus one attributed public figure)')
