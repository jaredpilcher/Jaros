"""Refresh the bundled console SPA shipped inside the wheel.

The TypeScript console under ``console/`` is built with Vite into
``console/dist/`` (gitignored). For a plain ``pip install jaros`` to ship a
working console with no Node toolchain, that prebuilt bundle is vendored into
``jaros_console/_dist/`` (tracked, declared as package-data). Run this after any
change to the console UI:

    python scripts/sync_console_dist.py            # build + copy
    python scripts/sync_console_dist.py --no-build # copy existing console/dist

It shells out to ``npm run build`` (unless ``--no-build``), then mirrors
``console/dist/`` into ``jaros_console/_dist/``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONSOLE = REPO / "console"
SRC = CONSOLE / "dist"
DST = REPO / "jaros_console" / "_dist"


def main(argv: list[str]) -> int:
    if "--no-build" not in argv:
        npm = shutil.which("npm")
        if npm is None:
            print("npm not found; install Node or pass --no-build to copy an "
                  "existing console/dist/", file=sys.stderr)
            return 2
        print("building console (npm run build)…")
        subprocess.run([npm, "run", "build"], cwd=str(CONSOLE), check=True)

    if not (SRC / "index.html").is_file():
        print(f"no build at {SRC} — run `npm run build` in console/ first",
              file=sys.stderr)
        return 1

    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    files = sorted(p.relative_to(DST).as_posix() for p in DST.rglob("*") if p.is_file())
    print(f"synced {len(files)} file(s) -> jaros_console/_dist/")
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
