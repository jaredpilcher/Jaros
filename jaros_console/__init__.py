"""Jaros Console — a host-side companion server, bundled for pip installs.

This package lives *beside* the ``jaros`` package, not inside it, on purpose:
``jaros`` itself must import no server framework (the zero-infrastructure
guarantee, enforced by ``scripts/check_zero_infra.py``). The console is an
admin tool — like the CLI — that opens a localhost port to serve the prebuilt
React SPA and a small REST + SSE API over the shared data directory. The Jaros
node stays serverless; nothing here is part of it.

It is the Python twin of the TypeScript bridge under ``console/`` (same routes,
same data-dir reads/writes), so a plain ``pip install jaros`` ships a working
console with no Node toolchain required.
"""

from __future__ import annotations

__all__ = ["serve_console", "make_server"]

from .server import make_server, serve_console
