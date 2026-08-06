"""Generate the Launch Control 'architecture to date' diagram (layered platform view).

Clients on top, then stacked infrastructure layers with nested component boxes and
numbered dependency boundaries underneath. Emits:
  - launch-control-architecture.excalidraw  (editable Excalidraw source)
  - launch-control-architecture.png         (hand-drawn-style preview)

Colors: blue = existing Dataverse-plane pieces, purple = F&O ERP, teal = neutral,
orange = NEW in Episode 10. Red circles = layer dependency boundaries. Text black.
"""
import json, os, random

random.seed(10)
OUT = os.path.dirname(os.path.abspath(__file__))

BLUE   = ("#1864ab", "#a5d8ff")
PURPLE = ("#862e9c", "#f3d9fa")
ORANGE = ("#e67700", "#ffd8a8")
TEAL   = ("#0c8599", "#99e9f2")
GRAY   = ("#495057", "#dee2e6")
RED    = ("#c92a2a", "#ff8787")

# ---- layout model ----
# containers: transparent grouping boxes with a top-left title
containers = [
    dict(x=50,  y=112, w=660, h=180, c=GRAY,   sw=2, title='RUNTIME CLIENTS', tfs=14),
    dict(x=790, y=112, w=660, h=180, c=GRAY,   sw=2, title='ANALYST & BUILD CLIENTS', tfs=14),
    dict(x=50,  y=332, w=1400,h=140, c=BLUE,   sw=2, title='ACCESS & INTELLIGENCE', tfs=15),
    dict(x=50,  y=512, w=680, h=316, c=BLUE,   sw=2, title='SYSTEM OF RECORD - Dataverse + F&O', tfs=14),
    dict(x=770, y=512, w=680, h=316, c=ORANGE, sw=3, title='MICROSOFT FABRIC - analytical layer   (NEW - Ep 10)', tfs=14),
    dict(x=50,  y=858, w=1400,h=120, c=GRAY,   sw=2, title='FOUNDATION - governance & ingestion', tfs=15),
]

# leaf boxes: dict(x,y,w,h,c,fs,t)
boxes = [
    # clients (left cluster)
    dict(x=70,  y=170, w=300, h=110, c=BLUE, fs=15, t='Copilot Studio\nLaunch Control agent\n(Ep 7)'),
    dict(x=390, y=170, w=300, h=110, c=BLUE, fs=13, t='Microsoft 365 Copilot Cowork\n(Ep 6)', vtop=True),
    dict(x=405, y=224, w=270, h=42,  c=ORANGE, fs=12, t='+ Fabric data plugin  (Ep 10)'),
    # clients (right cluster)
    dict(x=810, y=170, w=300, h=110, c=ORANGE, fs=13, t='Power BI report - 3 pages\nLaunch 360 / Vendor List /\nVendor 360   (Ep 10)'),
    dict(x=1130,y=170, w=300, h=110, c=BLUE, fs=13, t='Coding agent / maker\nbuild-time authoring\n(Eps 1-10)'),
    # access & intelligence
    dict(x=70,  y=378, w=320, h=80,  c=BLUE,   fs=13, t='Dataverse MCP Server\n16 tools - search_data  (Ep 7)'),
    dict(x=410, y=378, w=320, h=80,  c=BLUE,   fs=13, t='Custom API + 2 BYO\nMCP connectors  (Ep 5)'),
    dict(x=750, y=378, w=320, h=80,  c=BLUE,   fs=13, t='Business Skills\nreadiness / escalation  (Ep 2)'),
    dict(x=1090,y=378, w=320, h=80,  c=ORANGE, fs=13, t='Power BI / Fabric\nMCP endpoint  (Ep 10)'),
    # system of record (left band)
    dict(x=70,  y=560, w=640, h=96,  c=BLUE,   fs=12, t='Dataverse core tables\nlc_launch / lc_task / lc_milestone / lc_statusupdate /\nlc_teammember / lc_vendorwork  (Eps 1-3)'),
    dict(x=70,  y=668, w=640, h=64,  c=BLUE,   fs=13, t='GitHub-Issues virtual entities + guardrails  (Ep 4)'),
    dict(x=70,  y=744, w=640, h=64,  c=PURPLE, fs=13, t='Dynamics 365 F&O ERP - vendtable / vendtransopen  (Ep 9)'),
    # fabric (right band, NEW) - one box (container) with its analytical components
    dict(x=790, y=560, w=640, h=50,  c=ORANGE, fs=13, t='Fabric Link - near-real-time mirror to OneLake  (~46s median)'),
    dict(x=790, y=620, w=640, h=50,  c=ORANGE, fs=13, t='Lakehouse SQL analytics endpoint - mirror tables lc_*, vend*'),
    dict(x=790, y=680, w=310, h=58,  c=ORANGE, fs=12, t='Semantic views (9)\nenrich + aggregate, incl. historical'),
    dict(x=1120,y=680, w=310, h=58,  c=ORANGE, fs=12, t='Enrichment datasets\nvendor risk + internal delivery perf'),
    dict(x=790, y=748, w=640, h=58,  c=ORANGE, fs=12, t='Direct Lake model "Launch Control 360" - 8 tables + measures (no DAX)'),
    # foundation
    dict(x=70,  y=898, w=650, h=58,  c=BLUE, fs=13, t='Security - 4 roles (Member / Owner / Viewer / Admin) + row & column  (Ep 8)'),
    dict(x=760, y=898, w=650, h=58,  c=BLUE, fs=13, t='Ingestion - staging -> unified (Python + pandas)  (Eps 2-3)'),
]

# dependency arrows (x1, y1, x2, y2, label); horizontal when y1==y2
arrows = [
    (380, 292, 380, 332, None),   # left clients -> access
    (1120,292, 1120,332, None),   # right clients -> access
    (390, 472, 390, 512, None),   # access -> system of record
    (1110,472, 1110,512, None),   # access -> fabric
    (710, 600, 790, 600, 'Fabric Link mirror ~46s (Ep 10)'),  # system of record -> fabric (side by side)
    (390, 828, 390, 858, None),   # system of record -> foundation
    (1110,828, 1110,858, None),   # fabric -> foundation
]
# numbered boundary circles (cx, cy, label)
circles = [
    (750, 312, '1'),   # clients -> access
    (390, 492, '2'),   # access -> data band
    (750, 600, '3'),   # system of record -> fabric mirror
    (750, 843, '4'),   # data band -> foundation
]

labels = [
    (50,  36,  'Launch Control - architecture to date (through Episode 10)', 30, 1100),
    (50,  84,  'Platform view: clients on top, infrastructure beneath. Fabric sits side by side with the system of record, fed by Fabric Link. Episode 10 additions highlighted. (1-4) mark boundaries.', 14, 1050),
]
legend = [
    (1120, 34, BLUE,   'Dataverse plane  (Eps 1-8)'),
    (1120, 60, PURPLE, 'F&O ERP  (Ep 9)'),
    (1120, 86, ORANGE, 'NEW in Episode 10  (Fabric)'),
]

# ---------------- Excalidraw emit ----------------
def rid():
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(12))
def nonce():
    return random.randint(1, 2**31)
els = []
def base(el):
    el.setdefault('angle',0); el.setdefault('strokeWidth',2); el.setdefault('strokeStyle','solid')
    el.setdefault('roughness',1); el.setdefault('opacity',100); el.setdefault('groupIds',[])
    el.setdefault('frameId',None); el.setdefault('seed',nonce()); el.setdefault('version',1)
    el.setdefault('versionNonce',nonce()); el.setdefault('isDeleted',False)
    el.setdefault('boundElements',None); el.setdefault('updated',1); el.setdefault('link',None)
    el.setdefault('locked',False); return el
def rect(x,y,w,h,stroke,fill,sw=2,style='solid',rounded=True):
    return base(dict(type='rectangle',id=rid(),x=x,y=y,width=w,height=h,strokeColor=stroke,
        backgroundColor=fill,fillStyle='solid',strokeWidth=sw,strokeStyle=style,
        roundness=({'type':3} if rounded else None)))
def bound_box(x,y,w,h,stroke,fill,text,fs,sw=2,vtop=False):
    r=rect(x,y,w,h,stroke,fill,sw=sw); tid=rid()
    r['boundElements']=[{'type':'text','id':tid}]
    t=base(dict(type='text',id=tid,x=x+8,y=y+8,width=w-16,height=h-16,text=text,fontSize=fs,
        fontFamily=1,strokeColor='#000000',backgroundColor='transparent',textAlign='center',
        verticalAlign=('top' if vtop else 'middle'),containerId=r['id'],originalText=text,
        lineHeight=1.25,autoResize=False))
    return r,t
def text(x,y,txt,fs,w,align='left',bold=False):
    lines=txt.count('\n')+1
    return base(dict(type='text',id=rid(),x=x,y=y,width=w,height=int(fs*1.7*lines),text=txt,
        fontSize=fs,fontFamily=1,strokeColor='#000000',backgroundColor='transparent',
        textAlign=align,verticalAlign='top',originalText=txt,lineHeight=1.25,autoResize=False))
def arrow(x1,y1,x2,y2,stroke='#343a40',sw=2,style='solid'):
    return base(dict(type='arrow',id=rid(),x=x1,y=y1,width=x2-x1,height=y2-y1,strokeColor=stroke,
        backgroundColor='transparent',fillStyle='solid',strokeWidth=sw,strokeStyle=style,
        roundness={'type':2},points=[[0,0],[x2-x1,y2-y1]],lastCommittedPoint=None,
        startBinding=None,endBinding=None,startArrowhead=None,endArrowhead='arrow'))
def ellipse(x,y,w,h,stroke,fill,sw=2):
    return base(dict(type='ellipse',id=rid(),x=x,y=y,width=w,height=h,strokeColor=stroke,
        backgroundColor=fill,fillStyle='solid',strokeWidth=sw))

# containers first
for c in containers:
    els.append(rect(c['x'],c['y'],c['w'],c['h'],c['c'][0],'transparent',sw=c['sw']))
    els.append(text(c['x']+15,c['y']+8,c['title'],c['tfs'],c['w']-30,bold=True))
# leaf boxes
for b in boxes:
    r,t=bound_box(b['x'],b['y'],b['w'],b['h'],b['c'][0],b['c'][1],b['t'],b['fs'],vtop=b.get('vtop',False))
    els.append(r); els.append(t)
# arrows + labels
for x1,y1,x2,y2,lab in arrows:
    els.append(arrow(x1,y1,x2,y2,stroke='#343a40',sw=2))
    if lab:
        if x1==x2:
            els.append(text(x1+18,(y1+y2)//2-8,lab,12,340))
        else:
            els.append(text((x1+x2)//2-110,y1-30,lab,12,240,align='center'))
# circles
for cxp,cyp,lab in circles:
    r=15
    els.append(ellipse(cxp-r,cyp-r,2*r,2*r,RED[0],RED[1],sw=2))
    els.append(text(cxp-5,cyp-9,lab,15,10,align='center'))
# title + legend
for x,y,txt,fs,w in labels:
    els.append(text(x,y,txt,fs,w))
for x,y,col,txt in legend:
    els.append(rect(x,y,20,20,col[0],col[1],sw=2,rounded=False))
    els.append(text(x+28,y-1,txt,13,320))

doc=dict(type='excalidraw',version=2,source='copilot-cli',elements=els,
    appState=dict(viewBackgroundColor='#ffffff',gridSize=None),files={})
with open(os.path.join(OUT,'launch-control-architecture.excalidraw'),'w',encoding='utf-8') as f:
    json.dump(doc,f,indent=2)
print('excalidraw written:',len(els),'elements')

# ---------------- PNG preview ----------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
W,H=1500,1000
with plt.xkcd():
    fig,ax=plt.subplots(figsize=(15,10),dpi=110)
    ax.set_xlim(0,W); ax.set_ylim(0,H); ax.invert_yaxis(); ax.axis('off')
    def dbox(x,y,w,h,stroke,fill,sw=2):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=2,rounding_size=9',
            linewidth=sw,edgecolor=stroke,facecolor=fill,zorder=3))
    for c in containers:
        dbox(c['x'],c['y'],c['w'],c['h'],c['c'][0],'none',sw=c['sw'])
        ax.text(c['x']+16,c['y']+20,c['title'],ha='left',va='center',fontsize=c['tfs']*0.62,
                color='#000000',weight='bold',zorder=4)
    for b in boxes:
        dbox(b['x'],b['y'],b['w'],b['h'],b['c'][0],b['c'][1],sw=2)
        va='top' if b.get('vtop') else 'center'
        ty=b['y']+12 if b.get('vtop') else b['y']+b['h']/2
        ax.text(b['x']+b['w']/2,ty,b['t'],ha='center',va=va,fontsize=b['fs']*0.62,
                color='#000000',zorder=4)
    def darrow(x1,y1,x2,y2,color='#343a40',sw=2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=16,
            linewidth=sw,color=color,zorder=2,shrinkA=0,shrinkB=0))
    for x1,y1,x2,y2,lab in arrows:
        darrow(x1,y1,x2,y2)
        if lab:
            if x1==x2:
                ax.text(x1+16,(y1+y2)/2,lab,ha='left',va='center',fontsize=12*0.62,
                        color='#495057',style='italic',zorder=4)
            else:
                ax.text((x1+x2)/2,y1-16,lab,ha='center',va='center',fontsize=12*0.62,
                        color='#495057',style='italic',zorder=4)
    for cxp,cyp,lab in circles:
        ax.add_patch(Circle((cxp,cyp),15,edgecolor=RED[0],facecolor=RED[1],linewidth=2,zorder=5))
        ax.text(cxp,cyp,lab,ha='center',va='center',fontsize=11,weight='bold',color='#000000',zorder=6)
    for x,y,txt,fs,w in labels:
        ax.text(x,y+fs*0.7,txt,ha='left',va='top',fontsize=fs*0.62,color='#000000',
                weight=('bold' if fs>=20 else 'normal'),zorder=4)
    for x,y,col,txt in legend:
        dbox(x,y,20,20,col[0],col[1],sw=2)
        ax.text(x+30,y+10,txt,ha='left',va='center',fontsize=8.5,color='#000000',zorder=4)
    fig.tight_layout(pad=0.4)
    fig.savefig(os.path.join(OUT,'launch-control-architecture.png'),dpi=110,
                bbox_inches='tight',facecolor='white')
print('png written')
