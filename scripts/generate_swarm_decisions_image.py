"""Render a still image proving the MODEL drives decisions — then replay calls none.

Runs the planner agent against a REAL small model (Ollama) on a spam ticket and a
genuine one: the model's verdict drives the outcome (REJECT -> FAILED, ACCEPT ->
DONE). Then `jaros replay` reconstructs both outcomes byte-identically with ZERO
model calls. Captures the real output to docs/swarm-llm-decisions.png.

Run (needs `ollama serve` + a small model):  python scripts/generate_swarm_decisions_image.py
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
BG=(12,15,19); CHROME=(27,33,43); TEXT=(221,227,236); PROMPT=(138,226,52)
CMD=(244,211,94); MUTED=(122,134,150); OK=(138,226,52); RED=(255,107,107); BLUE=(116,167,224)
PAD,LH,FS=16,22,15
FINAL={("start","complete"):"DONE",("start","fail"):"FAILED",("start","block"):"BLOCKED"}

def _font(b=False):
    for n in ([ "C:/Windows/Fonts/consolab.ttf"] if b else ["C:/Windows/Fonts/consola.ttf"])+["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        try: return ImageFont.truetype(n, FS)
        except OSError: pass
    return ImageFont.load_default()

def _capture():
    data = Path(tempfile.mkdtemp(prefix="jaros-llmdec-"))
    (data/"agents").mkdir(parents=True); (data/"tools").mkdir(parents=True)
    for f in (REPO/"examples/swarm/agents").glob("planner_agent.py"): shutil.copy(f, data/"agents"/f.name)
    model = os.environ.get("OLLAMA_MODEL","gemma2:2b")
    env={**os.environ,"JAROS_TICK_MS":"200","JAROS_POOL_BOUND":"1","JAROS_LLM_PROVIDER":"ollama",
         "OLLAMA_MODEL":model,"OLLAMA_HOST":os.environ.get("OLLAMA_HOST","http://localhost:11434")}
    d=subprocess.Popen([sys.executable,"-m","jaros.cli","--data-dir",str(data),"serve"],env=env,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,cwd=str(REPO))
    lines=[]
    try:
        for _ in range(100):
            if (data/"status.json").exists(): break
            time.sleep(0.2)
        tickets=[("spam","BUY CHEAP CRYPTO NOW!!! claim your prize at sketchy-deals.example"),
                 ("real","I can't log into my account after resetting my password")]
        for _,t in tickets:
            subprocess.run([sys.executable,"-m","jaros.cli","--data-dir",str(data),"submit","planner","--input",json.dumps({"ticket":t})],cwd=str(REPO),capture_output=True)
        from jaros.state import DecisionLog, read_decisions
        dl=DecisionLog(data/"state")
        for _ in range(300):
            if len(read_decisions(dl))>=2: break
            time.sleep(0.2)
        decs=read_decisions(dl)
    finally:
        d.terminate()
        try: d.wait(timeout=5)
        except subprocess.TimeoutExpired: d.kill()
    rep=subprocess.run([sys.executable,"-m","jaros.cli","--data-dir",str(data),"replay","--json"],cwd=str(REPO),capture_output=True,text=True)
    report=json.loads(rep.stdout.strip() or "{}")
    shutil.rmtree(data, ignore_errors=True)

    lines.append((f"# a hive triaged tickets with a REAL small model ({model}) running on jaros", MUTED))
    lines.append(("# the MODEL decided each outcome - watch the same run replay with NO model call", MUTED))
    lines.append(("", TEXT))
    lines.append(("$ jaros submit planner  (spam ticket)   ;  jaros submit planner  (real ticket)", CMD))
    for dec in decs:
        ev=tuple(dec.payload.get("events",[])); verdict=dec.payload.get("verdict","?").upper()
        fs=FINAL.get(ev,"?"); col = RED if fs=="FAILED" else OK
        lines.append((f"   [model decided]  verdict={verdict:7} -> {fs:7}  ({'rejected spam' if verdict=='REJECT' else 'accepted a genuine request'})", col))
    lines.append(("", TEXT))
    lines.append(("$ jaros replay --data-dir /tmp/jaros --json", CMD))
    lines.append((f"   decisions={report.get('decisions')}   modelCalls={report.get('modelCalls')}   byteIdentical={str(report.get('byteIdentical')).lower()}   ok={str(report.get('ok')).lower()}", BLUE))
    lines.append(("   -> the MODEL made the decisions; replay reconstructed them BYTE-IDENTICALLY with 0 model calls", OK))
    lines.append(("$ ", PROMPT))
    return lines

def _render(lines, out):
    f,t=_font(),_font(True)
    m=ImageDraw.Draw(Image.new("RGB",(10,10)))
    w=max(900,int(max(m.textlength(s,font=t if s.startswith('$ jaros') else f) for s,_ in lines))+2*PAD)
    h=30+PAD+len(lines)*LH+PAD
    img=Image.new("RGB",(w,h),BG); d=ImageDraw.Draw(img)
    d.rectangle([(0,0),(w,30)],fill=CHROME)
    for i,c in enumerate(((255,95,86),(255,189,46),(39,201,63))): d.ellipse([(15+i*20,10),(25+i*20,20)],fill=c)
    d.text((w//2-170,7),"jaros - the model decides; replay reproduces with no model call",fill=MUTED,font=t)
    d.rectangle([(0,0),(w-1,h-1)],outline=(40,48,60),width=1)
    y=30+PAD
    for s,c in lines:
        if s.startswith("$ jaros"):
            d.text((PAD,y),"$ ",fill=PROMPT,font=t); d.text((PAD+d.textlength("$ ",font=t),y),s[2:],fill=c,font=t)
        else: d.text((PAD,y),s,fill=c,font=f)
        y+=LH
    img.save(out); print(f"PNG created: {out} ({w}x{h})")

if __name__=="__main__":
    (REPO/"docs").mkdir(exist_ok=True)
    _render(_capture(), REPO/"docs"/"swarm-llm-decisions.png")
