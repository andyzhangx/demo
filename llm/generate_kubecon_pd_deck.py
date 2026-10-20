#!/usr/bin/env python3
"""Build the KubeCon NA 2026 deck using editable PowerPoint primitives.

Requires python-pptx==1.0.2. No images, external assets, or measured benchmark
claims. The companion Markdown is the narrative source; see speaker notes.
Run from any directory: python llm/generate_kubecon_pd_deck.py
"""
from pathlib import Path
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
W, H = 13.333333, 7.5
C = dict(bg='F6F8FC', ink='172941', muted='586A80', line='D9E2EE', white='FFFFFF',
         blue='2563EB', teal='087F8C', purple='7354B8', amber='AE641A', red='B5464A',
         blue_bg='EAF1FF', teal_bg='E4F4F3', purple_bg='F0EBFA', amber_bg='FFF3E1',
         dark='102039', pale='AFC3DF', green='247952')
FONT = 'Arial'
MONO = 'Courier New'
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
prs.core_properties.title = 'Prefill Here, Decode There'
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
    text(s, .5, .27, 11.8, .28, section.upper(), 10, 'pale' if dark else 'blue', True)
    text(s, .5, .83, 12.3, .62, title, 29, 'white' if dark else 'ink', True)
    if sub: text(s, .52, 1.53, 12.2, .53, sub, 17, 'pale' if dark else 'muted')
    if takeaway:
        rect(s, .5, 6.38, 12.33, .53, 'blue_bg')
        text(s, .68, 6.49, 11.97, .31, takeaway, 15, 'ink', True)
    arrow(s, .5, 7.12, 12.83, 7.12, 'muted' if dark else 'line', head=False, width=.7)
    text(s, .5, 7.19, 11.5, .2, 'KUBECON + CLOUDNATIVECON NORTH AMERICA 2026  /  KAITO + llm-d', 8, 'pale' if dark else 'muted')
    text(s, 12.13, 7.17, .7, .24, f'{len(prs.slides):02d} / 36', 9, 'pale' if dark else 'muted', align=PP_ALIGN.RIGHT)
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
s = slide('Prefill Here, Decode There', 'Cloud Native AI + Inference Day / 20-minute talk', dark=True)
text(s, .52, 1.7, 10.9, 1.0, 'Kubernetes-native LLM inference disaggregation\nwith KAITO and llm-d', 25, 'white')
pill(s, .55, 3.15, 2.6, 'ONE DECLARATIVE SERVICE', 'blue', 'blue_bg')
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

# 03
s = slide('One request. Two different GPU workloads.', '01 / The problem',
          'Prefill processes the input; decode repeatedly generates the next token.',
          'P/D is about matching capacity to two very different phases.')
node(s,.55,2.45,2.0,1.08,'Prompt','Input tokens','blue')
node(s,3.0,2.45,3.0,1.08,'PREFILL','Process the prompt once','teal')
node(s,6.5,2.45,2.0,1.08,'KV cache','Attention state','amber')
node(s,9.0,2.45,3.75,1.08,'DECODE','Generate tokens iteratively','purple')
for a,b,ac in [(2.55,3.,'muted'),(6.,6.5,'teal'),(8.5,9.,'purple')]: arrow(s,a,2.99,b,2.99,ac)
card(s,.55,4.03,5.95,1.91,'Prefill: compute-bound','Prompt pressure • time to first token', 'teal',size=18)
card(s,6.78,4.03,5.95,1.91,'Decode: bandwidth-bound','Active KV memory • steady token delivery','purple',size=18)
note(s, 'These are typical workload characteristics, not universal hardware laws. Prefill latency contributes to TTFT; decode performance is also governed by inter-token latency, active KV memory, and concurrency. No timing or token-size ratio is implied by the diagram.')

# 04
s = slide('One shared pool couples two capacity decisions', '01 / The problem',
          'Aggregated serving is simple—but prefill bursts and active decoding share resources.',
          'The compromise is not only performance. It is how you size and scale the service.')
rect(s,.55,2.3,7.15,3.75,'white','line',True)
text(s,.8,2.56,6.6,.45,'SHARED GPU POOL',17,'blue',True)
for i in range(3):
    x=.86+i*2.2
    rect(s,x,3.34,1.98,1.6,'bg','line',True)
    pill(s,x+.12,3.56,1.73,'PREFILL','teal','teal_bg')
    pill(s,x+.12,4.14,1.73,'DECODE','purple','purple_bg')
text(s,.82,5.26,6.5,.45,'One deployment • one coupled scaling boundary',17,'muted')
card(s,8.05,2.3,4.72,3.75,'The operational tension',
     'Prompt bursts can disrupt token delivery.\n\nScaling adds both phases, even when only one is saturated.', 'amber',size=19)
note(s, 'Do not claim every aggregated deployment performs poorly. Continuous batching and chunked prefill can reduce interference. The point is that a shared resource and scaling boundary still constrains independent capacity shaping.')

# 05
s = slide('Split the phases. Tune the pools independently.', '01 / The problem',
          'P/D introduces a KV-transfer boundary between prompt processing and generation.',
          'The transfer path must be fast enough to justify the split.')
rect(s,.55,2.4,4.5,3.45,'teal_bg',radius=True)
text(s,.8,2.66,4,.48,'PREFILL POOL',23,'teal',True)
node(s,.85,3.4,3.9,1.14,'Prompt processing','Compute + latency','teal')
text(s,.82,4.98,3.9,.78,'Choose replicas and parallelism\nfor prompt pressure.',17,'teal')
rect(s,8.28,2.4,4.5,3.45,'purple_bg',radius=True)
text(s,8.53,2.66,4,.48,'DECODE POOL',23,'purple',True)
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
 ('Long prompts','RAG and retrieval add significant prefill work.','teal','PROMPT PRESSURE'),
 ('Long generations','High concurrency keeps decode busy and KV state resident.','purple','GENERATION PRESSURE'),
 ('Different resources','Each phase needs its own scaling or parallelism choices.','blue','CAPACITY MISMATCH')]):
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
    text(s,x,y+1.73,2.94,.4,['SERVE','SCALE','ROUTE','COMPOSE'][i],12,ac,True,PP_ALIGN.CENTER)
    if i<3: route(s,[(x+2.94,y+.75),(x+3.04,y+.75),(x+3.04,y+.43),(x+3.13,y+.43)],ac)
note(s, 'This is a capability progression, not a strict ownership chain. InferencePool is the Gateway API Inference Extension routing abstraction. KAITO manages the objects and wiring around the runtime.',[PD_DOC])

# 10
s = slide('A continuous API model as serving gets harder', '03 / KAITO + llm-d',
          'Add capabilities without asking users to hand-assemble a new stack.')
rows=[['USER NEED','KUBERNETES OBJECT','PLATFORM RESPONSIBILITY'],
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
note(s, 'The current MRI P/D documentation supports per-role replica, instance-type, preset, and vLLM settings. Do not imply this slide is a literal schema or that the proposed MRI scaling UX on slide 23 is already implemented.',[PD_DOC])

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
pill(s,.55,6.62,12.23,'KAITO RECONCILES THE SERVING TOPOLOGY; THE GATEWAY IS THE API ENTRY POINT','blue','blue_bg')
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
text(s,3.26,2.59,8.9,.4,'DECODE POD  /  SHARED POD NETWORK',16,'purple',True)
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
s = slide('Autoscale the phase that is actually saturated', '04 / Per-role autoscaling',
          'Different bottlenecks deserve different signals and scale decisions.',
          'Independent scaling only helps when the metrics match each role.')
for x,t,body,metric,ac in [
 (.55,'PREFILL','Protect prompt latency\nand time to first token.','Signal: waiting requests / prompt pressure','teal'),
 (6.78,'DECODE','Protect token delivery\nand sustained throughput.','Signal: active KV pressure / decode load','purple')]:
    card(s,x,2.35,5.95,2.7,t,body,ac,size=22)
    pill(s,x,5.35,5.95,metric,ac,'teal_bg' if ac=='teal' else 'purple_bg')
note(s, 'These are role-aware metric recommendations, not a claim that one universal trigger is already built into MRI. Queue length is an existing documented InferenceSet example. Decode signals require the chosen runtime metric and Prometheus query to be validated.',[KEDA_DOC])

# 21 — actual keda capabilities
s = slide('Today: KEDA targets the InferenceSet scale API', '04 / Existing capability',
          'Documented KAITO examples cover both scheduled and metric-based scaling.',
          'The scale target is the InferenceSet—not a manually scaled workload Pod.')
pill(s,.55,2.21,2.4,'DOCUMENTED TODAY','blue','blue_bg')
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
 (2.48,'PREFILL','Waiting requests','Prefill InferenceSet','teal'),
 (4.55,'DECODE','KV / decode load','Decode InferenceSet','purple')]:
    pill(s,.55,y,1.5,role,ac,'teal_bg' if ac=='teal' else 'purple_bg')
    for x,w,t,d in [(2.42,2.85,metric,'Observe'),(6.0,2.6,'KEDA / HPA','Decide'),(9.32,3.46,target,'Reconcile replicas')]:
        node(s,x,y-.08,w,1.19,t,d,ac,17)
    arrow(s,5.27,y+.5,6.,y+.5,ac); arrow(s,8.6,y+.5,9.32,y+.5,ac)
    route(s,[(11.05,y+1.11),(11.05,y+1.49),(3.84,y+1.49),(3.84,y+1.11)],ac,True)
text(s,.57,6.59,12.1,.36,'Add stabilization, warm-up awareness, and safe scale-down behavior to each loop.',16,'muted')
note(s, 'Conceptual two-loop model. One ScaledObject per target InferenceSet is the natural KEDA boundary. Do not install multiple conflicting HPAs for the same scale target. Metric choice, query aggregation, cache headroom, model warm-up, and draining semantics must be validated for the deployment.',[KEDA_DOC])

# 23 — recommendation explicitly marked
s = slide('Recommended UX: one MRI, per-role scaling intent', '04 / Proposed API direction',
          'This is a platform recommendation, not an implemented YAML schema.',
          'Users should express the intent; controllers should generate the scaling plumbing.')
pill(s,.55,2.22,4.3,'RECOMMENDATION / NOT A CURRENT API','amber','amber_bg')
node(s,.55,3.15,3.6,2.22,'MRI role intent','Prefill: prompt-pressure policy\nDecode: sustained-load policy','blue',22)
node(s,5.0,3.53,3.3,1.47,'KAITO controller','Project policy onto child roles','blue',21)
node(s,9.15,2.96,3.63,1.17,'Prefill scale target','Generated policy + target','teal',18)
node(s,9.15,4.63,3.63,1.17,'Decode scale target','Generated policy + target','purple',18)
arrow(s,4.15,4.25,5.,4.25,'blue')
route(s,[(8.3,4.1),(8.7,4.1),(8.7,3.55),(9.15,3.55)],'teal')
route(s,[(8.3,4.42),(8.7,4.42),(8.7,5.22),(9.15,5.22)],'purple')
note(s, 'The companion Markdown recommends a clean MRI API for per-role scaling. It explicitly distinguishes that direction from the current KEDA InferenceSet integration. Do not copy this diagram into a manifest as if it defined supported fields.',[KEDA_DOC])

# 24 — comparison protocol
s = slide('Benchmark the operating point—not only the peak', '05 / Evaluation plan',
          'Compare aggregated and P/D deployments under the same constraints.',
          'No measured results are supplied in the source material.')
node(s,.55,2.37,3.3,1.31,'Workload replay','Same model, traffic, and SLO','blue',21)
node(s,5.05,2.37,3.35,1.31,'Aggregated','Baseline configuration','blue',21)
node(s,9.45,2.37,3.33,1.31,'Disaggregated','Prefill + decode configuration','teal',21)
arrow(s,3.85,2.86,5.05,2.86,'blue')
route(s,[(3.85,3.2),(4.4,3.2),(4.4,4.04),(11.12,4.04),(11.12,3.68)],'teal')
table(s,.55,4.38,[3.2,9.03],[
 ['HOLD CONSTANT','REPORT WITH THE RESULT'],
 ['Model + traffic','Version, quantization, prompt/output lengths, concurrency'],
 ['Cost + SLO','GPU budget, fabric, TTFT/ITL target, warm-up and duration']],.59)
note(s, 'This slide is an evaluation protocol, not a result. Match GPU budget or cost budget and state the comparison basis. Report latency percentiles and achieved throughput at matched load. Include transport and hardware topology, model and runtime versions, warm-up, run duration, and sampling method. No synthetic performance curves should be mistaken for measurements.')

# 25 — no fake chart
s = slide('TTFT: measure the tail under prompt pressure', '05 / Benchmark scorecard',
          'Measurement plan only. No performance numbers are available in the source.')
pill(s,.55,2.18,2.9,'AWAITING MEASURED RESULTS','amber','amber_bg')
table(s,.55,2.87,[3.52,4.35,4.36],[
 ['TTFT METRIC','AGGREGATED','P/D'],
 ['p50 / median','Not measured','Not measured'],
 ['p95 / tail','Not measured','Not measured'],
 ['p99 / extreme tail','Not measured','Not measured']],.64)
rect(s,.55,5.7,12.23,1.08,'teal_bg',radius=True)
text(s,.78,5.88,11.7,.35,'Question to answer',19,'teal',True)
text(s,.78,6.33,11.7,.3,'Does P/D reduce tail TTFT at the same offered load and cost budget?',16,'ink')
note(s, 'Replaces the original [X]% / [Y]% placeholders. There is no numeric claim or implied performance curve. Collect TTFT percentiles under prompt-heavy traffic and report the request rate, concurrency, prompt/output distributions, model, hardware, and cost comparison. Include the effect of KV-transfer overhead.')

# 26
s = slide('Throughput: count useful work inside the SLO', '05 / Benchmark scorecard',
          'Measurement plan only. Report useful throughput and its cost together.')
pill(s,.55,2.18,2.9,'AWAITING MEASURED RESULTS','amber','amber_bg')
table(s,.55,2.87,[3.52,4.35,4.36],[
 ['MEASURE','AGGREGATED','P/D'],
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
 ['WORKLOAD','SHORT OUTPUT','LONG OUTPUT'],
 ['Short prompt','Start with aggregated','Evaluate decode pressure'],
 ['Long prompt','Evaluate prefill isolation','Strong P/D candidate to test']],.88)
rect(s,.55,5.5,12.23,.88,'amber_bg',radius=True)
text(s,.8,5.71,11.72,.47,'Concurrency, GPU budget, and transfer fabric can change the result in every cell.',17,'amber',True)
note(s, 'A decision aid, not experimental data. Prompt and output lengths interact with concurrency, model size, parallelism, and hardware. Validate both latency and cost. Even the strongest candidate cell is not a guaranteed P/D win.')

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
 ['ROLE','USEFUL SIGNALS','WATCH OUT FOR'],
 ['Prefill','Queue / prompt pressure','Averages that hide burst and tail latency'],
 ['Decode','KV pressure / steady load','Evicting active work during scale-down'],
 ['Both','Warm-up + SLO + capacity','Oscillation, slow model load, fabric limits']],.85)
note(s, 'Signal examples are recommendations. Validate exporter names, units, and label scoping. Choose thresholds and stabilization behavior from the workload. The source documentation provides a queue-based InferenceSet example; decode trigger selection remains deployment-specific.',[KEDA_DOC])

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

# 32
s = slide('Adopt P/D in reversible steps', '06 / Adoption path',
          'Start with the simplest serving model that meets the workload.')
for i,(title,body,ac) in enumerate([
 ('Baseline','Run aggregated.\nMeasure traffic + SLO.','blue'),
 ('Separate','Declare roles.\nValidate KV + routing.','teal'),
 ('Tune','Set role capacity.\nBenchmark at fixed cost.','purple'),
 ('Operate','Add scale policies.\nTest failure + rollback.','amber')]):
    x=.55+i*3.13
    card(s,x,2.55,2.94,3.38,title,body,ac,f'STEP {i+1}',18)
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
    card(s,.55+i*4.14,2.45,3.95,3.43,title,body,ac,'DIRECTION',20)
note(s, 'These are talk recommendations derived from the source outline, not a published project delivery timeline. Keep the distinction between current capability and proposed user experience explicit.')

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

assert len(prs.slides) == 36
prs.save(OUT)
print(f'Saved {OUT} ({len(prs.slides)} slides; native editable shapes, no embedded images)')
