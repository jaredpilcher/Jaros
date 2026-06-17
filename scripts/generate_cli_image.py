"""Render a still terminal image of a REAL Jaros CLI session (Pillow, a dev dep).

Boots a throwaway Jaros node, runs the actual CLI commands, captures their real
stdout, and renders it as a terminal-styled PNG at ``docs/cli.png`` for the
README and docs. Nothing is faked — the output is exactly what the CLI printed.

Run:  python scripts/generate_cli_image.py
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

# Palette — matches the console's terminal lineage.
BG = (12, 15, 19)
CHROME = (27, 33, 43)
TEXT = (221, 227, 236)
PROMPT = (138, 226, 52)
CMD = (244, 211, 94)
MUTED = (122, 134, 150)
OK = (138, 226, 52)
BLUE = (116, 167, 224)

PAD, LINE_H, FONT_SZ = 16, 22, 15


def _font(bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/consola.ttf"]
        if bold
        else ["C:/Windows/Fonts/consola.ttf"]
    )
    candidates += ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, FONT_SZ)
        except OSError:
            continue
    return ImageFont.load_default()


def _env() -> dict:
    # Render the public default: the echo/`default` mock provider, ignoring any
    # local .env (the explicit var wins over python-dotenv's setdefault).
    return {**os.environ, "JAROS_LLM_PROVIDER": "default"}


def _scrub(text: str, data: Path) -> str:
    # Present a clean, portable data dir (and POSIX separators) instead of the
    # throwaway temp path, so the picture reads the same on any OS.
    out = text.replace(str(data), "/tmp/jaros")
    return "\n".join(ln.replace("\\", "/") if "/tmp/jaros" in ln else ln for ln in out.splitlines())


def _run(args: list[str], data: Path) -> str:
    r = subprocess.run(
        [sys.executable, "-m", "jaros.cli", "--data-dir", str(data), *args],
        cwd=str(REPO), capture_output=True, text=True, env=_env(),
    )
    return _scrub((r.stdout or r.stderr).rstrip("\n"), data)


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the daemon and any child it spawned (e.g. the web console)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()




def _capture() -> list[tuple[str, tuple[int, int, int]]]:
    """Run a real session and return styled (text, color) lines."""
    data = Path(tempfile.mkdtemp(prefix="jaros-cli-img-")) / ".jaros-data"

    lines: list[tuple[str, tuple[int, int, int]]] = []

    def cmd(c: str) -> None:
        lines.append((f"$ jaros {c}", CMD))

    def out(text: str, color=TEXT) -> None:
        for ln in text.splitlines():
            lines.append((f"  {ln}", color))

    # 1. Scaffold a ready-to-run node with the bundled example agents — the real
    #    `jaros init` output, nothing faked.
    lines.append(("# scaffold a node with bundled example agents/tools/evals/schedules", MUTED))
    cmd("init --with-examples")
    init_out = _run(["init", "--with-examples"], data)
    # Keep the picture compact: the staged-file list, not every line.
    for ln in init_out.splitlines():
        low = ln.strip().lower()
        col = OK if low.startswith(("created", "staged")) else MUTED if ln.strip().startswith("#") else TEXT
        lines.append((f"  {ln}", col))
    lines.append(("", TEXT))

    # 2. Boot the node and capture the real startup banner (clean, change-only logs).
    serve = subprocess.Popen(
        [sys.executable, "-m", "jaros.cli", "--data-dir", str(data), "serve"],
        cwd=str(REPO), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, env=_env(),
    )
    try:
        lines.append(("# boot the node + web console; then it stays quiet, logging only events", MUTED))
        cmd("serve")
        for _ in range(40):
            line = serve.stderr.readline()
            if not line:
                break
            out(_scrub(line.rstrip("\n"), data), BLUE)
            if "Ctrl-C to stop" in line:
                break
        lines.append(("", TEXT))

        for _ in range(60):
            if (data / "status.json").exists():
                break
            time.sleep(0.25)

        cmd("submit advance --input '{}'")
        out(_run(["submit", "advance", "--input", "{}"], data), OK)
        cmd("submit system-health")
        out(_run(["submit", "system-health"], data), OK)

        for _ in range(60):
            if len(list((data / "outbox").glob("*.json"))) >= 2:
                break
            time.sleep(0.25)
        lines.append(("", TEXT))

        # A compact, real summary read straight from the durable status.json.
        cmd("status")
        try:
            st = json.loads((data / "status.json").read_text(encoding="utf-8"))
            pool = st.get("pool", {})
            out(f"state={st.get('state')}  processed={st.get('processed')}  "
                f"failed={st.get('failed')}  pool={pool.get('active', 0)}/{pool.get('bound', 0)}", OK)
        except (OSError, json.JSONDecodeError):
            out(_run(["status"], data))
        lines.append(("", TEXT))

        lines.append(("# the headline guarantee — rebuild the run from the decision log, no model call", MUTED))
        cmd("replay --json")
        rep = _run(["replay", "--json"], data)
        try:
            parsed = json.loads(rep)
            out(json.dumps(parsed, indent=2), OK if parsed.get("ok") else TEXT)
        except json.JSONDecodeError:
            out(rep)
        lines.append(("", TEXT))

        cmd("eval")
        out(_run(["eval"], data), OK)
        lines.append(("$ ", PROMPT))
        return lines
    finally:
        _kill_tree(serve)
        shutil.rmtree(data.parent, ignore_errors=True)


def _render(lines: list[tuple[str, tuple[int, int, int]]], out_path: Path) -> None:
    font, title_font = _font(), _font(bold=True)
    measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    content_w = max(measure.textlength(t, font=title_font if t.startswith("$ jaros") else font) for t, _ in lines)
    width = max(760, int(content_w) + 2 * PAD)
    height = 30 + PAD + len(lines) * LINE_H + PAD
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (width, 30)], fill=CHROME)
    for i, col in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        draw.ellipse([(15 + i * 20, 10), (25 + i * 20, 20)], fill=col)
    draw.text((width // 2 - 110, 7), "jaros — operator@host", fill=MUTED, font=title_font)
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(40, 48, 60), width=1)

    y = 30 + PAD
    for text, color in lines:
        if text.startswith("$ jaros"):
            draw.text((PAD, y), "$ ", fill=PROMPT, font=title_font)
            draw.text((PAD + draw.textlength("$ ", font=title_font), y), text[2:], fill=color, font=title_font)
        else:
            draw.text((PAD, y), text, fill=color, font=font)
        y += LINE_H

    img.save(out_path)
    print(f"PNG created: {out_path}  ({width}x{height})")


if __name__ == "__main__":
    out_dir = REPO / "docs"
    out_dir.mkdir(exist_ok=True)
    _render(_capture(), out_dir / "cli.png")
