"""Structural no-server architecture check (EXT-003 / REQ-3).

Agents are lightweight threads, never per-agent services. This check scans the
runtime (``jaros/runtime/**.py``) and any agent code (``jaros/agents/**.py``)
and fails (non-zero exit) if any of them opens a listening socket or HTTP
server. Detected patterns:

- ``socket.socket`` (constructing a raw socket);
- a ``.bind(`` or ``.listen(`` call (binding/listening a socket);
- ``HTTPServer`` (``http.server.HTTPServer`` / ``ThreadingHTTPServer``);
- the ``socketserver`` module;
- ``asyncio.start_server`` (an asyncio listening server).

Exits 0 on a clean tree and when there are no scannable files. Pattern matching
is done on the AST (imports + call expressions), so comments and strings do not
trip it.

Run as: ``python scripts/check_no_server.py``
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# #EXT-003-REQ-3 Start
# Directories whose Python files must be free of server/listener footprints.
SCAN_DIRS = (
    Path("jaros") / "runtime",
    Path("jaros") / "agents",
)

# Module imports that imply a per-agent server footprint.
FORBIDDEN_IMPORT_PREFIXES = ("socketserver",)

# Dotted attribute calls that imply opening a server/listener, e.g.
# ``socket.socket(...)`` or ``asyncio.start_server(...)``.
FORBIDDEN_DOTTED_CALLS = {
    ("socket", "socket"),
    ("asyncio", "start_server"),
}

# Bare names that imply an HTTP server when called or imported, e.g.
# ``HTTPServer(...)`` / ``ThreadingHTTPServer(...)``.
FORBIDDEN_SERVER_NAMES = {"HTTPServer", "ThreadingHTTPServer"}

# Method names that, when called on anything, imply binding/listening a socket.
FORBIDDEN_METHODS = {"bind", "listen"}


def _dotted(node: ast.expr) -> tuple[str, ...]:
    """Return the dotted-name tuple of an attribute/name chain, else ()."""
    parts: list[str] = []
    cur: ast.expr | None = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        parts.reverse()
        return tuple(parts)
    return ()


def _check_call(node: ast.Call, path: Path) -> list[str]:
    violations: list[str] = []
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in FORBIDDEN_METHODS:
            violations.append(
                f"{path.as_posix()}:{node.lineno}: forbidden socket "
                f"'.{func.attr}(' call"
            )
        dotted = _dotted(func)
        if len(dotted) >= 2 and (dotted[-2], dotted[-1]) in FORBIDDEN_DOTTED_CALLS:
            violations.append(
                f"{path.as_posix()}:{node.lineno}: forbidden server call "
                f"{'.'.join(dotted[-2:])!r}"
            )
    elif isinstance(func, ast.Name) and func.id in FORBIDDEN_SERVER_NAMES:
        violations.append(
            f"{path.as_posix()}:{node.lineno}: forbidden server "
            f"construction {func.id!r}"
        )
    return violations


def _check_import(name: str | None, path: Path, lineno: int) -> list[str]:
    if not name:
        return []
    if any(name == p or name.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
        return [f"{path.as_posix()}:{lineno}: forbidden server import {name!r}"]
    return []


def find_violations(repo_root: Path) -> list[str]:
    """Return human-readable server-footprint violations (empty if clean)."""
    violations: list[str] = []
    for rel_dir in SCAN_DIRS:
        scan_dir = repo_root / rel_dir
        if not scan_dir.is_dir():
            continue
        for path in sorted(scan_dir.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    violations.extend(_check_call(node, path))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        violations.extend(
                            _check_import(alias.name, path, node.lineno)
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0:
                        violations.extend(
                            _check_import(node.module, path, node.lineno)
                        )
                    for alias in node.names:
                        if alias.name in FORBIDDEN_SERVER_NAMES:
                            violations.append(
                                f"{path.as_posix()}:{node.lineno}: forbidden "
                                f"server import {alias.name!r}"
                            )
    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    violations = find_violations(repo_root)
    if violations:
        print("No-server check FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("No-server check passed: no per-agent server/listener footprint.")
    return 0
# #EXT-003-REQ-3 End


if __name__ == "__main__":
    sys.exit(main())
