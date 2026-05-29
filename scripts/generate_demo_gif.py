import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_gif(output_path: Path):
    # Terminal Dimensions
    width, height = 760, 480
    bg_color = (30, 30, 30)      # Slate gray/dark theme
    text_color = (220, 220, 220)  # Off-white
    prompt_color = (78, 154, 6)   # Terminal Green
    cmd_color = (252, 233, 79)    # Light Yellow
    highlight_color = (114, 159, 207) # Cool Blue
    success_color = (138, 226, 52) # Bright Green

    # Setup standard safe font
    font = ImageFont.load_default()

    frames = []

    # Lines to write step by step
    scripts = [
        # Frame 0: Initial state
        [
            ("operator@host:~$ ", prompt_color),
            ("_", text_color)
        ],
        # Frame 1: Typing docker command
        [
            ("operator@host:~$ ", prompt_color),
            ("docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros", cmd_color)
        ],
        # Frame 2: Daemon boots up inside container
        [
            ("operator@host:~$ ", prompt_color),
            ("docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros\n", cmd_color),
            ("a8f9c1e4d3b6a2b8e8f8... (Container started)\n", text_color),
            ("operator@host:~$ ", prompt_color),
            ("jaros status\n", cmd_color),
            ("  State:          ", text_color), ("PENDING\n", highlight_color),
            ("  Processed Jobs: ", text_color), ("0\n", text_color),
            ("  Failed Jobs:    ", text_color), ("0\n", text_color),
            ("  Active Agents:  ", text_color), ("0\n", text_color),
            ("operator@host:~$ ", prompt_color),
            ("_", text_color)
        ],
        # Frame 3: Submitting job via host CLI
        [
            ("operator@host:~$ ", prompt_color),
            ("docker run -d --name jaros_os -v ${PWD}/.jaros-data:/data jaros\n", cmd_color),
            ("a8f9c1e4d3b6a2b8e8f8... (Container started)\n", text_color),
            ("operator@host:~$ ", prompt_color),
            ("jaros status\n", cmd_color),
            ("  State:          PENDING\n", text_color),
            ("  Processed Jobs: 0\n  Failed Jobs:    0\n  Active Agents:  0\n", text_color),
            ("operator@host:~$ ", prompt_color),
            ("jaros submit advance --input '{\"events\": [\"START\"]}'\n", cmd_color),
            ("Submitted job 69d5ed8c -> .jaros-data/inbox/69d5ed8c.json\n", success_color),
            ("operator@host:~$ ", prompt_color),
            ("_", text_color)
        ],
        # Frame 4: Daemon detects and starts processing (Harness spawns agent thread)
        [
            ("operator@host:~$ ", prompt_color),
            ("jaros submit advance --input '{\"events\": [\"START\"]}'\n", cmd_color),
            ("Submitted job 69d5ed8c -> .jaros-data/inbox/69d5ed8c.json\n", success_color),
            ("operator@host:~$ ", prompt_color),
            ("docker logs -f jaros_os\n", cmd_color),
            ("JAROS_HEARTBEAT tick=1 state=PENDING active=0 processed=0 failed=0\n", text_color),
            ("[ingest] detected job 69d5ed8c (kind: advance)\n", highlight_color),
            ("[harness] spawning agent thread: advance_agent_thread\n", text_color),
            ("[harness] granted capabilities: queue_send, fs_write\n", text_color),
            ("_", text_color)
        ],
        # Frame 5: Decision gate validation and state transitions
        [
            ("operator@host:~$ ", prompt_color),
            ("docker logs -f jaros_os\n", cmd_color),
            ("JAROS_HEARTBEAT tick=1 state=PENDING active=0 processed=0 failed=0\n", text_color),
            ("[ingest] detected job 69d5ed8c (kind: advance)\n", highlight_color),
            ("[harness] spawning agent thread: advance_agent_thread\n", text_color),
            ("[harness] granted capabilities: queue_send, fs_write\n", text_color),
            ("[executor] validating decision... ", text_color), ("ACCEPTED\n", success_color),
            ("[state] transition: PENDING -> RUNNING\n", highlight_color),
            ("[state] transition: RUNNING -> DONE\n", highlight_color),
            ("_", text_color)
        ],
        # Frame 6: Mediatied I/O, writing output, tearing down agent
        [
            ("operator@host:~$ ", prompt_color),
            ("docker logs -f jaros_os\n", cmd_color),
            ("JAROS_HEARTBEAT tick=1 state=PENDING active=0 processed=0 failed=0\n", text_color),
            ("[ingest] detected job 69d5ed8c (kind: advance)\n", highlight_color),
            ("[harness] spawning agent thread: advance_agent_thread\n", text_color),
            ("[harness] granted capabilities: queue_send, fs_write\n", text_color),
            ("[executor] validating decision... ACCEPTED\n", text_color),
            ("[state] transition: PENDING -> RUNNING\n", highlight_color),
            ("[state] transition: RUNNING -> DONE\n", highlight_color),
            ("[harness] writing result atomically to outbox/69d5ed8c.json\n", text_color),
            ("[harness] tearing down agent thread and revoking grants\n", text_color),
            ("JAROS_HEARTBEAT tick=2 state=DONE active=0 processed=1 failed=0\n", text_color),
            ("operator@host:~$ ", prompt_color),
            ("_", text_color)
        ],
        # Frame 7: Inspecting final status
        [
            ("operator@host:~$ ", prompt_color),
            ("docker logs -f jaros_os\n", cmd_color),
            ("JAROS_HEARTBEAT tick=2 state=DONE active=0 processed=1 failed=0\n", text_color),
            ("operator@host:~$ ", prompt_color),
            ("jaros status\n", cmd_color),
            ("  State:          ", text_color), ("DONE\n", success_color),
            ("  Processed Jobs: ", text_color), ("1\n", text_color),
            ("  Failed Jobs:    ", text_color), ("0\n", text_color),
            ("  Active Agents:  ", text_color), ("0\n", text_color),
            ("  Last Result:    ", text_color), ("outbox/69d5ed8c.json\n", success_color),
            ("\n", text_color),
            ("PASS: Jaros OS container execution complete.\n", success_color),
            ("operator@host:~$ ", prompt_color),
            ("_", text_color)
        ]
    ]

    for frame_idx, elements in enumerate(scripts):
        # Create a fresh image frame
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw Terminal Chrome Header
        draw.rectangle([(0, 0), (width, 30)], fill=(45, 45, 45))
        # Draw Window Controls (Fake buttons)
        draw.ellipse([(15, 10), (25, 20)], fill=(255, 95, 86))
        draw.ellipse([(35, 10), (45, 20)], fill=(255, 189, 46))
        draw.ellipse([(55, 10), (65, 20)], fill=(39, 201, 63))
        # Draw Title text
        draw.text((width // 2 - 80, 8), "Jaros OS Terminal - operator@host:~/.jaros-data", fill=(160, 160, 160), font=font)

        # Draw Frame border
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(60, 60, 60), width=1)

        # Write lines
        x_offset = 15
        y_offset = 45
        line_height = 16

        for text, color in elements:
            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    draw.text((x_offset, y_offset), part, fill=color, font=font)
                    # We only advance x_offset if there is more on this physical line
                    if idx < len(parts) - 1:
                        y_offset += line_height
                        x_offset = 15
                    else:
                        x_offset += draw.textlength(part, font=font)
                else:
                    if idx < len(parts) - 1:
                        y_offset += line_height
                        x_offset = 15

        # Duplicate key frames to give the user time to read them
        duration = 1500 if frame_idx in [2, 3, 6, 7] else 800
        frames.append((img, duration))

    # Save animated GIF
    img_list = [f[0] for f in frames]
    durations = [f[1] for f in frames]

    img_list[0].save(
        output_path,
        save_all=True,
        append_images=img_list[1:],
        optimize=True,
        duration=durations,
        loop=0
    )
    print(f"Demo GIF successfully created at: {output_path}")

if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parents[1] / "docs"
    out_dir.mkdir(exist_ok=True)
    generate_gif(out_dir / "demo.gif")
