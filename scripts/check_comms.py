"""Structural exclusive-channels check (EXT-006 / REQ-3, REQ-5).

Inter-agent communication must occur ONLY through the rigid queues
(``jaros.comms.queue``) and the shared file system (``jaros.comms.fs``). This
check scans agent / plugin / runtime code and fails (non-zero exit) on any
direct agent-to-agent path:

- network / RPC imports (``socket``, ``http.client``, ``urllib.request``,
  ``requests``, ``grpc``) and ``asyncio.open_connection`` calls;
- direct imports of another agent's package (``jaros.agents.*`` /
  ``jaros.plugins.*``) by sibling agent/plugin code.

The only inter-agent dependencies that pass are ``jaros.comms.queue`` and
``jaros.comms.fs``. Exits 0 on a clean tree and when no scannable files exist.

Run as: ``python scripts/check_comms.py``
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# #EXT-006-REQ-3 Start
# #EXT-006-REQ-5 Start
# Network / RPC modules that imply a direct (non-sanctioned) channel.
FORBIDDEN_NETWORK_PREFIXES = (
    "socket",
    "http.client",
    "urllib.request",
    "requests",
    "grpc",
)

# Agent / plugin package prefixes; one of these importing another is a direct
# agent-to-agent reference.
AGENT_PACKAGE_PREFIXES = (
    "jaros.agents",
    "jaros.plugins",
)

# The only cross-agent dependencies that are allowed.
ALLOWED_COMMS_PREFIXES = (
    "jaros.comms.queue",
    "jaros.comms.fs",
)

# Directories scanned for violations: runtime + any agent / plugin code.
SCAN_DIRS = (
    Path("jaros") / "runtime",
    Path("jaros") / "agents",
    Path("jaros") / "plugins",
)


def _matches(module: str | None, prefixes: tuple[str, ...]) -> bool:
    if not module:
        return False
    return any(module == p or module.startswith(p + ".") for p in prefixes)


def _own_agent_package(path: Path, repo_root: Path) -> str | None:
    """Return the specific agent/plugin package ``path`` belongs to.

    For ``jaros/agents/foo/x.py`` this is ``jaros.agents.foo`` — one level below
    the umbrella ``jaros.agents`` — so that imports between *different* agents
    are recognised as cross-agent.
    """
    try:
        rel = path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return None
    dotted = rel.replace("/", ".")
    for prefix in AGENT_PACKAGE_PREFIXES:
        if dotted.startswith(prefix + "."):
            remainder = dotted[len(prefix) + 1 :]
            head = remainder.split(".", 1)[0]
            return f"{prefix}.{head}"
    return None


def _agent_of_module(module: str) -> str | None:
    """Return the specific agent/plugin package a ``module`` refers to, if any."""
    for prefix in AGENT_PACKAGE_PREFIXES:
        if module.startswith(prefix + "."):
            head = module[len(prefix) + 1 :].split(".", 1)[0]
            return f"{prefix}.{head}"
    return None


def _check_module(module: str | None, path: Path, lineno: int, repo_root: Path) -> str | None:
    """Return a violation message for an imported ``module`` or None if allowed."""
    if module is None:
        return None
    if _matches(module, ALLOWED_COMMS_PREFIXES):
        return None  # explicitly sanctioned channel
    if _matches(module, FORBIDDEN_NETWORK_PREFIXES):
        return f"{path.as_posix()}:{lineno}: forbidden network/RPC import of {module!r}"
    # Direct agent-to-agent import: this file lives in an agent/plugin package
    # and imports a *different* agent/plugin package.
    target_agent = _agent_of_module(module)
    if target_agent is not None:
        own = _own_agent_package(path, repo_root)
        if own is None or target_agent != own:
            return f"{path.as_posix()}:{lineno}: direct agent-to-agent import of {module!r}"
    return None


def find_violations(repo_root: Path) -> list[str]:
    """Return human-readable violation messages (empty if the tree is clean)."""
    violations: list[str] = []
    for rel_dir in SCAN_DIRS:
        scan_dir = repo_root / rel_dir
        if not scan_dir.is_dir():
            continue
        for path in sorted(scan_dir.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        msg = _check_module(alias.name, path, node.lineno, repo_root)
                        if msg:
                            violations.append(msg)
                elif isinstance(node, ast.ImportFrom):
                    # `from X import ...` (level 0); relative imports stay intra-package.
                    if node.level == 0:
                        msg = _check_module(node.module, path, node.lineno, repo_root)
                        if msg:
                            violations.append(msg)
                elif isinstance(node, ast.Call):
                    # asyncio.open_connection(...) — a direct network channel.
                    func = node.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr == "open_connection"
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "asyncio"
                    ):
                        violations.append(
                            f"{path.as_posix()}:{node.lineno}: forbidden network call "
                            "'asyncio.open_connection'"
                        )
    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    violations = find_violations(repo_root)
    if violations:
        print("Communication-fabric check FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("Communication-fabric check passed: no direct agent-to-agent channels.")
    return 0


# #EXT-006-REQ-3 End
# #EXT-006-REQ-5 End


if __name__ == "__main__":
    sys.exit(main())
