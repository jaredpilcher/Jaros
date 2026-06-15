"""Render a still terminal image of a REAL swarm replay (Pillow, a dev dep).

Stands up a support-triage swarm (planner -> worker -> reviewer) on a throwaway
node with the deterministic mock LLM, seeds one bad handoff, then captures the
actual `jaros replay` output — byte-identical swarm reconstruction + the culprit
attributed to the exact agent — and renders it as a terminal-styled PNG at
``docs/swarm-replay.png`` for the README/launch. Nothing is faked.

Run:  python scripts/generate_swarm_image.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]

BG = (12, 15, 19)
CHROME = (27, 33, 43)
TEXT = (221, 227, 236)
PROMPT = (138, 226, 52)
CMD = (244, 211, 94)
MUTED = (122, 134, 150)
OK = (138, 226, 52)
RED = (255, 107, 107)
BLUE = (116, 167, 224)
PAD, LINE_H, FONT_SZ = 16, 22, 15


def _font(bold: bool = False):
    names = (["C:/Windows/Fonts/consolab.ttf"] if bold else ["C:/Windows/Fonts/consola.ttf"])
    names += ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, FONT_SZ)
        except OSError:
            continue
    return ImageFont.load_default()


def _capture() -> list[tuple[str, tuple[int, int, int]]]:
    data = Path(tempfile.mkdtemp(prefix="jaros-swarm-img-"))
    for area, src in (("plugins", "examples/swarm/plugins"), ("tools", "examples/swarm/tools")):
        (data / area).mkdir(parents=True, exist_ok=True)
        for f in (REPO / src).glob("*.py"):
            shutil.copy(f, data / area / f.name)
    env = {**os.environ, "JAROS_TICK_MS": "100", "JAROS_LLM_PROVIDER": "default"}
    daemon = subprocess.Popen(
        [sys.executable, "-m", "jaros.cli", "--data-dir", str(data), "serve"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(REPO),
    )
    lines: list[tuple[str, tuple[int, int, int]]] = []
    try:
        for _ in range(80):
            if (data / "status.json").exists():
                break
            time.sleep(0.2)

        def submit(kind, payload):
            subprocess.run(
                [sys.executable, "-m", "jaros.cli", "--data-dir", str(data),
                 "submit", kind, "--input", json.dumps(payload)],
                cwd=str(REPO), capture_output=True, text=True,
            )

        for ticket in ("login keeps failing", "double-charged on billing"):
            submit("planner", {"ticket": ticket})
            submit("worker", {"ticket": ticket})
            submit("reviewer", {"ticket": ticket})
        submit("worker", {"ticket": "refund please", "bad": True})  # the culprit

        from jaros.state import DecisionLog, read_decisions
        for _ in range(100):
            if len(read_decisions(DecisionLog(data / "state"))) >= 7:
                break
            time.sleep(0.2)
    finally:
        daemon.terminate()
        try:
            daemon.wait(timeout=5)
        except subprocess.TimeoutExpired:
            daemon.kill()

    replay = subprocess.run(
        [sys.executable, "-m", "jaros.cli", "--data-dir", str(data), "replay"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    out = replay.stdout.rstrip("\n").replace(str(data), "/tmp/jaros")
    shutil.rmtree(data, ignore_errors=True)

    lines.append(("# a hive of agents triaged tickets in a container; one passed a bad handoff", MUTED))
    lines.append(("# replay the whole swarm from the recorded log - no model call - and find the culprit", MUTED))
    lines.append(("$ jaros replay --data-dir /tmp/jaros", CMD))
    for ln in out.splitlines():
        s = ln.strip()
        if s.startswith("replayed"):
            color = TEXT
        elif "decision(s)" in ln:
            color = BLUE
        elif "yes" in ln or "intact" in ln:
            color = OK
        elif "attribution" in ln or "reason:" in ln or "FAILURE" in ln:
            color = RED
        elif ln.startswith("repro"):
            color = OK
        else:
            color = TEXT
        lines.append(("  " + ln, color))
    lines.append(("$ ", PROMPT))
    return lines


def _render(lines, out_path: Path) -> None:
    font, title = _font(), _font(bold=True)
    measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    width = max(820, int(max(measure.textlength(t, font=title if t.startswith("$ jaros") else font) for t, _ in lines)) + 2 * PAD)
    height = 30 + PAD + len(lines) * LINE_H + PAD
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 0), (width, 30)], fill=CHROME)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([(15 + i * 20, 10), (25 + i * 20, 20)], fill=c)
    d.text((width // 2 - 150, 7), "jaros - swarm replay & attribution", fill=MUTED, font=title)
    d.rectangle([(0, 0), (width - 1, height - 1)], outline=(40, 48, 60), width=1)
    y = 30 + PAD
    for text, color in lines:
        if text.startswith("$ jaros"):
            d.text((PAD, y), "$ ", fill=PROMPT, font=title)
            d.text((PAD + d.textlength("$ ", font=title), y), text[2:], fill=color, font=title)
        else:
            d.text((PAD, y), text, fill=color, font=font)
        y += LINE_H
    img.save(out_path)
    print(f"PNG created: {out_path}  ({width}x{height})")


if __name__ == "__main__":
    (REPO / "docs").mkdir(exist_ok=True)
    _render(_capture(), REPO / "docs" / "swarm-replay.png")
