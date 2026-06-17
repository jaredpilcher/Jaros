"""Render the README terminal-cast GIFs with Pillow (a dev dependency).

Produces two animated GIFs under ``docs/``:

- ``demo.gif``   — boot the OS and run a built-in + two example agents.
- ``replay.gif`` — the headline differentiator: reproduce a run byte-for-byte by
  replaying the recorded decision log, with no model call.

Run:  python scripts/generate_demo_gif.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 760, 480
BG = (30, 30, 30)
TEXT = (220, 220, 220)
PROMPT = (78, 154, 6)       # terminal green
CMD = (252, 233, 79)        # light yellow
HILITE = (114, 159, 207)    # cool blue
OK = (138, 226, 52)         # bright green
MUTED = (150, 150, 150)

FONT = ImageFont.load_default()


def _render(scripts: list[list[tuple[str, tuple[int, int, int]]]],
            output_path: Path,
            title: str,
            slow_frames: set[int]) -> None:
    frames: list[tuple[Image.Image, int]] = []
    for frame_idx, elements in enumerate(scripts):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        # Terminal chrome.
        draw.rectangle([(0, 0), (WIDTH, 30)], fill=(45, 45, 45))
        draw.ellipse([(15, 10), (25, 20)], fill=(255, 95, 86))
        draw.ellipse([(35, 10), (45, 20)], fill=(255, 189, 46))
        draw.ellipse([(55, 10), (65, 20)], fill=(39, 201, 63))
        draw.text((WIDTH // 2 - 120, 8), title, fill=MUTED, font=FONT)
        draw.rectangle([(0, 0), (WIDTH - 1, HEIGHT - 1)], outline=(60, 60, 60), width=1)

        x_offset, y_offset, line_height = 15, 45, 16
        for text, color in elements:
            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    draw.text((x_offset, y_offset), part, fill=color, font=FONT)
                    if idx < len(parts) - 1:
                        y_offset += line_height
                        x_offset = 15
                    else:
                        x_offset += draw.textlength(part, font=FONT)
                elif idx < len(parts) - 1:
                    y_offset += line_height
                    x_offset = 15

        frames.append((img, 1700 if frame_idx in slow_frames else 850))

    imgs = [f[0] for f in frames]
    durations = [f[1] for f in frames]
    imgs[0].save(
        output_path, save_all=True, append_images=imgs[1:],
        optimize=True, duration=durations, loop=0,
    )
    print(f"GIF created: {output_path}")


def demo_script() -> list:
    return [
        [("operator@host:~$ ", PROMPT), ("_", TEXT)],
        [
            ("operator@host:~$ ", PROMPT),
            ("docker run -d --name jaros_os -v ${PWD}/data:/data jaros\n", CMD),
            ("# no database, no broker, no server  -  just files + threads\n", MUTED),
            ("_", TEXT),
        ],
        [
            ("operator@host:~$ ", PROMPT),
            ("jaros submit advance --input '{}'\n", CMD),
            ("jaros submit echo    --input '{\"msg\": \"hi\"}'\n", CMD),
            ("jaros submit greeter --input '{\"name\": \"Jaros\"}'\n", CMD),
            ("submitted 3 jobs -> data/inbox/\n", OK),
            ("_", TEXT),
        ],
        [
            ("operator@host:~$ ", PROMPT),
            ("docker logs -f jaros_os\n", CMD),
            ("[ingest] advance  -> agent thread  (capabilities: fs_write)\n", HILITE),
            ("[ingest] echo     -> agent  (loaded at runtime)\n", HILITE),
            ("[ingest] greeter  -> agent  -> custom tool demo.greet\n", HILITE),
            ("[gate]   3 decisions ACCEPTED (inert data)\n", TEXT),
            ("[log]    recorded 3 decisions -> state/decisions.log\n", OK),
            ("_", TEXT),
        ],
        [
            ("operator@host:~$ ", PROMPT),
            ("jaros status\n", CMD),
            ("  State:          ", TEXT), ("DONE\n", OK),
            ("  Processed Jobs: ", TEXT), ("3\n", TEXT),
            ("  Failed Jobs:    ", TEXT), ("0\n", TEXT),
            ("  Active Agents:  ", TEXT), ("0\n", TEXT),
            ("\n", TEXT),
            ("PASS: built-in + 2 agents + a custom tool, zero infra.\n", OK),
            ("operator@host:~$ ", PROMPT), ("_", TEXT),
        ],
    ]


def replay_script() -> list:
    return [
        [("operator@host:~$ ", PROMPT), ("_", TEXT)],
        [
            ("operator@host:~$ ", PROMPT),
            ("# An agent run misbehaved in prod. Reproduce it byte-for-byte.\n", MUTED),
            ("cat data/state/decisions.log\n", CMD),
            ("_", TEXT),
        ],
        [
            ("operator@host:~$ ", PROMPT),
            ("cat data/state/decisions.log\n", CMD),
            ("{\"index\":1,\"decision\":{\"type\":\"advance\",\"payload\":{...}}}\n", TEXT),
            ("{\"index\":2,\"decision\":{\"type\":\"demo.greet\",\"payload\":{...}}}\n", TEXT),
            ("# the model's outputs, captured as inert data\n", MUTED),
            ("_", TEXT),
        ],
        [
            ("operator@host:~$ ", PROMPT),
            ("python -m replay data/state/decisions.log\n", CMD),
            (">>> replay(decisions, executor.apply, log=fresh)\n", HILITE),
            ("[replay] re-executing recorded decisions  (no model call)\n", TEXT),
            ("[state]  PENDING -> RUNNING -> DONE\n", HILITE),
            ("_", TEXT),
        ],
        [
            ("operator@host:~$ ", PROMPT),
            (">>> recover(fresh) == recover(original)\n", HILITE),
            ("True\n", OK),
            (">>> fresh.read_bytes() == original.read_bytes()\n", HILITE),
            ("True\n", OK),
            ("\n", TEXT),
            ("Reproducible by replay: same decisions -> byte-identical state.\n", OK),
            ("No model call. Deterministic. Debuggable like any program.\n", OK),
            ("operator@host:~$ ", PROMPT), ("_", TEXT),
        ],
    ]


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parents[1] / "docs"
    out_dir.mkdir(exist_ok=True)
    _render(demo_script(), out_dir / "demo.gif",
            "Jaros OS  -  operator@host", slow_frames={1, 3, 4})
    _render(replay_script(), out_dir / "replay.gif",
            "Jaros OS  -  reproducibility by replay", slow_frames={1, 2, 4})
