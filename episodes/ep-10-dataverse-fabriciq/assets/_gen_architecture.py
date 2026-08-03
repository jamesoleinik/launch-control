"""Generate the Launch Control 'architecture to date' diagram.

Emits two artifacts from one shared layout:
  - launch-control-architecture.excalidraw  (editable Excalidraw source)
  - launch-control-architecture.png         (hand-drawn-style preview)

Colors: blue = Dataverse plane, purple = F&O ERP, orange = NEW in Episode 10,
teal = user / surfaces. All text black.
"""
import json, os, random

random.seed(10)
OUT = os.path.dirname(os.path.abspath(__file__))

BLUE   = ("#1864ab", "#a5d8ff")
PURPLE = ("#862e9c", "#f3d9fa")
ORANGE = ("#e67700", "#ffd8a8")
TEAL   = ("#0c8599", "#99e9f2")
GRAY   = ("#495057", "#dee2e6")

# box = dict(x,y,w,h,color,text,fs)
boxes = [
    dict(x=460, y=100, w=580, h=52,  c=TEAL,   fs=17, t='User prompt / click'),
    dict(x=460, y=210, w=580, h=60,  c=BLUE,   fs=16, t='Plane 1 - Copilot Studio "Launch Control" agent  (Ep 7)'),
    dict(x=460, y=290, w=580, h=118, c=BLUE,   fs=15,
         t='Dataverse - system of record\nlc_launch   lc_task   lc_milestone   lc_statusupdate   lc_teammember\n+ GitHub-Issues virtual entities & server-side guardrails  (Eps 1-4)'),
    dict(x=460, y=428, w=580, h=88,  c=PURPLE, fs=15,
         t='Dynamics 365 F&O ERP (virtual tables)\nvendtable   -   vendtransopen   -   lc_vendorwork seam  (Ep 9)'),
    dict(x=460, y=600, w=580, h=60,  c=ORANGE, fs=16, t='Fabric Link - near-real-time mirror to OneLake     (NEW - Ep 10)'),
    dict(x=460, y=690, w=580, h=60,  c=ORANGE, fs=16, t='Lakehouse SQL analytics endpoint - mirror tables lc_*, vend*   (NEW - Ep 10)'),
    dict(x=460, y=780, w=580, h=92,  c=ORANGE, fs=15,
         t='Semantic layer - semantic_views.sql - 9 views\n(incl. enrichment dataset: vw_vendor_enrichment / vw_vendor_risk)   (NEW - Ep 10)'),
    dict(x=460, y=896, w=580, h=78,  c=ORANGE, fs=15,
         t='Power BI Direct Lake model - "Launch Control 360"\n8 tables + relationships + measures, no hand-written DAX   (NEW - Ep 10)'),
    dict(x=460, y=996, w=580, h=60,  c=ORANGE, fs=15, t='Power BI report (3 pages): Launch 360 / Vendor List / Vendor 360   (NEW - Ep 10)'),
    dict(x=460, y=1080,w=580, h=60,  c=ORANGE, fs=15, t='Fabric IQ in Microsoft 365 Copilot Cowork - grounds on the report   (NEW - Ep 10)'),
    # left rail
    dict(x=40,  y=214, w=390, h=66,  c=BLUE, fs=14, t='Dataverse MCP Server\n16 tools - search_data  (Ep 7)'),
    dict(x=40,  y=296, w=390, h=66,  c=BLUE, fs=14, t='Business Skills\nreadiness / escalation / status  (Ep 2)'),
    dict(x=40,  y=378, w=390, h=66,  c=BLUE, fs=14, t='Custom API + 2 BYO MCP connectors  (Ep 5)'),
    dict(x=40,  y=460, w=390, h=66,  c=BLUE, fs=14, t='Ingestion - staging -> unified\n(Python + pandas)  (Eps 2-3)'),
    # right rail
    dict(x=1064,y=214, w=396, h=78,  c=BLUE, fs=14, t='Security - 4 roles\nMember / Owner / Viewer / Admin\n+ row & column security  (Ep 8)'),
    dict(x=1064,y=308, w=396, h=66,  c=TEAL, fs=14, t='Cowork plugin for Dataverse (Teams)  (Ep 6)'),
]

# transparent grouping containers
containers = [
    dict(x=448, y=170, w=604, h=372, c=GRAY,   sw=2),  # plane 1
    dict(x=448, y=560, w=604, h=612, c=ORANGE, sw=3),  # plane 2 (highlight)
]

# spine arrows (from-box index, to-box index)
spine = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9)]
# rail connectors: (box index, side 'C2'|'C1', from-side)
rails = [
    (10,'C1'),  # MCP -> agent
    (11,'C2'),  # skills -> dataverse
    (12,'C2'),  # custom api -> dataverse
    (13,'C2'),  # ingestion -> dataverse
    (14,'C2'),  # security -> dataverse
    (15,'C1'),  # cowork -> agent
]

# standalone labels: (x,y,text,fontSize,w)
labels = [
    (40,  36,  'Launch Control - architecture to date (through Episode 10)', 30, 1000),
    (40,  84,  'Cumulative build across Episodes 1-10; the Episode 10 Fabric IQ plane is highlighted.', 15, 900),
    (466, 178, 'PLANE 1 - Dataverse system of record + F&O ERP  (Eps 1-9)', 15, 560),
    (466, 568, 'PLANE 2 - Fabric IQ     (NEW in Episode 10)', 16, 560),
    (46,  186, 'ACCESS & INTELLIGENCE  (earlier episodes)', 13, 380),
    (1070,186, 'GOVERNANCE & SURFACES', 13, 380),
]
arrow_labels = [(700, 548, 'replicates to OneLake, ~46s median', 13)]

# legend swatches: (x,y,color,text)
legend = [
    (1070, 40, BLUE,   'Dataverse plane  (Eps 1-8)'),
    (1070, 68, PURPLE, 'F&O ERP  (Ep 9)'),
    (1070, 96, ORANGE, 'NEW in Episode 10  (Fabric IQ)'),
]

# ---------------- Excalidraw emit ----------------
def rid():
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(12))

def nonce():
    return random.randint(1, 2**31)

els = []

def base(el):
    el.setdefault('angle', 0); el.setdefault('strokeWidth', 2)
    el.setdefault('strokeStyle', 'solid'); el.setdefault('roughness', 1)
    el.setdefault('opacity', 100); el.setdefault('groupIds', [])
    el.setdefault('frameId', None); el.setdefault('seed', nonce())
    el.setdefault('version', 1); el.setdefault('versionNonce', nonce())
    el.setdefault('isDeleted', False); el.setdefault('boundElements', None)
    el.setdefault('updated', 1); el.setdefault('link', None); el.setdefault('locked', False)
    return el

def rect(x,y,w,h,stroke,fill,sw=2,style='solid',rounded=True):
    return base(dict(type='rectangle', id=rid(), x=x, y=y, width=w, height=h,
        strokeColor=stroke, backgroundColor=fill, fillStyle='solid',
        strokeWidth=sw, strokeStyle=style,
        roundness=({'type':3} if rounded else None)))

def bound_rect_text(x,y,w,h,stroke,fill,text,fs,sw=2):
    r = rect(x,y,w,h,stroke,fill,sw=sw)
    tid = rid()
    r['boundElements'] = [{'type':'text','id':tid}]
    t = base(dict(type='text', id=tid, x=x+8, y=y+8, width=w-16, height=h-16,
        text=text, fontSize=fs, fontFamily=1, strokeColor='#000000',
        backgroundColor='transparent', textAlign='center', verticalAlign='middle',
        containerId=r['id'], originalText=text, lineHeight=1.25, autoResize=False))
    return r, t

def text(x,y,txt,fs,w,align='left'):
    lines = txt.count('\n')+1
    return base(dict(type='text', id=rid(), x=x, y=y, width=w, height=int(fs*1.7*lines),
        text=txt, fontSize=fs, fontFamily=1, strokeColor='#000000',
        backgroundColor='transparent', textAlign=align, verticalAlign='top',
        originalText=txt, lineHeight=1.25, autoResize=False))

def arrow(x1,y1,x2,y2,stroke='#343a40',sw=2,style='solid'):
    return base(dict(type='arrow', id=rid(), x=x1, y=y1, width=x2-x1, height=y2-y1,
        strokeColor=stroke, backgroundColor='transparent', fillStyle='solid',
        strokeWidth=sw, strokeStyle=style, roundness={'type':2},
        points=[[0,0],[x2-x1,y2-y1]], lastCommittedPoint=None,
        startBinding=None, endBinding=None,
        startArrowhead=None, endArrowhead='arrow'))

# containers first (behind)
for c in containers:
    els.append(rect(c['x'],c['y'],c['w'],c['h'],c['c'][0],'transparent',sw=c['sw']))

# boxes
for b in boxes:
    r,t = bound_rect_text(b['x'],b['y'],b['w'],b['h'],b['c'][0],b['c'][1],b['t'],b['fs'])
    els.append(r); els.append(t)

def cx(b): return b['x']+b['w']/2

# spine arrows
for a,bx in spine:
    ba, bb = boxes[a], boxes[bx]
    els.append(arrow(cx(ba), ba['y']+ba['h'], cx(bb), bb['y'], stroke='#343a40', sw=2))

# rail connectors (dashed)
C1, C2 = boxes[1], boxes[2]
for idx, tgt in rails:
    rb = boxes[idx]
    ry = rb['y']+rb['h']/2
    if rb['x'] < 460:  # left rail -> center left edge
        x1 = rb['x']+rb['w']; 
        dst = C1 if tgt=='C1' else C2
        x2 = dst['x']; y2 = dst['y']+dst['h']/2
    else:  # right rail -> center right edge
        x1 = rb['x']
        dst = C1 if tgt=='C1' else C2
        x2 = dst['x']+dst['w']; y2 = dst['y']+dst['h']/2
    els.append(arrow(x1, ry, x2, y2, stroke='#868e96', sw=1, style='dashed'))

# standalone labels
for x,y,txt,fs,w in labels:
    els.append(text(x,y,txt,fs,w))
for x,y,txt,fs in arrow_labels:
    els.append(text(x,y,txt,fs,320))

# legend swatches + text
for x,y,col,txt in legend:
    els.append(rect(x,y,20,20,col[0],col[1],sw=2,rounded=False))
    els.append(text(x+28,y-1,txt,14,360))

doc = dict(type='excalidraw', version=2, source='copilot-cli',
           elements=els, appState=dict(viewBackgroundColor='#ffffff', gridSize=None),
           files={})
with open(os.path.join(OUT,'launch-control-architecture.excalidraw'),'w',encoding='utf-8') as f:
    json.dump(doc, f, indent=2)
print('excalidraw written:', len(els), 'elements')

# ---------------- PNG preview (hand-drawn style) ----------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

W, H = 1500, 1210
with plt.xkcd():
    fig, ax = plt.subplots(figsize=(15, 12.1), dpi=110)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.invert_yaxis(); ax.axis('off')

    def draw_box(x,y,w,h,stroke,fill,sw=2,ls='-'):
        p = FancyBboxPatch((x, y), w, h,
            boxstyle='round,pad=2,rounding_size=10',
            linewidth=sw, edgecolor=stroke, facecolor=fill, linestyle=ls, zorder=3)
        ax.add_patch(p)

    for c in containers:
        draw_box(c['x'],c['y'],c['w'],c['h'],c['c'][0],'none',sw=c['sw'])
    for b in boxes:
        draw_box(b['x'],b['y'],b['w'],b['h'],b['c'][0],b['c'][1],sw=2)
        ax.text(b['x']+b['w']/2, b['y']+b['h']/2, b['t'], ha='center', va='center',
                fontsize=b['fs']*0.62, color='#000000', zorder=4)

    def draw_arrow(x1,y1,x2,y2,color='#343a40',sw=2,ls='-'):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),
            arrowstyle='-|>', mutation_scale=16, linewidth=sw,
            color=color, linestyle=ls, zorder=2,
            shrinkA=0, shrinkB=0))

    for a,bx in spine:
        ba,bb = boxes[a],boxes[bx]
        draw_arrow(cx(ba),ba['y']+ba['h'],cx(bb),bb['y'])
    for idx,tgt in rails:
        rb = boxes[idx]; ry = rb['y']+rb['h']/2
        if rb['x']<460:
            x1=rb['x']+rb['w']; dst=(C1 if tgt=='C1' else C2); x2=dst['x']; y2=dst['y']+dst['h']/2
        else:
            x1=rb['x']; dst=(C1 if tgt=='C1' else C2); x2=dst['x']+dst['w']; y2=dst['y']+dst['h']/2
        draw_arrow(x1,ry,x2,y2,color='#adb5bd',sw=1.3,ls='--')

    for x,y,txt,fs,w in labels:
        weight = 'bold' if fs>=16 else 'normal'
        ax.text(x, y+fs*0.7, txt, ha='left', va='top', fontsize=fs*0.62,
                color='#000000', weight=weight, zorder=4)
    for x,y,txt,fs in arrow_labels:
        ax.text(x, y, txt, ha='center', va='center', fontsize=fs*0.62,
                color='#495057', style='italic', zorder=4)
    for x,y,col,txt in legend:
        draw_box(x,y,20,20,col[0],col[1],sw=2)
        ax.text(x+30, y+10, txt, ha='left', va='center', fontsize=9, color='#000000', zorder=4)

    fig.tight_layout(pad=0.5)
    fig.savefig(os.path.join(OUT,'launch-control-architecture.png'),
                dpi=110, bbox_inches='tight', facecolor='white')
print('png written')
