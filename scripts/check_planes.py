"""Structural plane-separation check (EXT-001 / REQ-4).

Scans every ``jaros/execution/**.py`` module and fails (non-zero exit) if any of
them imports the Reasoning Plane — i.e. ``jaros.llm`` or ``reasoning_boundary``.
This is the build-time enforcement that no execution module reaches up into
reasoning. Exits 0 on a clean tree.

Run as: ``python scripts/check_planes.py``
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Reasoning-plane modules that the Execution Plane must never import.
FORBIDDEN_PREFIXES = ("jaros.llm", "reasoning_boundary", "jaros.core.reasoning_boundary")


def _is_forbidden(module: str | None) -> bool:
    if not module:
        return False
    return any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in FORBIDDEN_PREFIXES
    )


def find_violations(execution_dir: Path) -> list[str]:
    """Return a list of human-readable violation messages (empty if clean)."""
    violations: list[str] = []
    for path in sorted(execution_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            # Covers `import X` and `import X as Y` (bare imports).
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden(alias.name):
                        violations.append(
                            f"{path}:{node.lineno}: forbidden import of {alias.name!r}"
                        )
            # Covers `from X import ...`.
            elif isinstance(node, ast.ImportFrom):
                if _is_forbidden(node.module):
                    violations.append(
                        f"{path}:{node.lineno}: forbidden import from {node.module!r}"
                    )
    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    execution_dir = repo_root / "jaros" / "execution"
    if not execution_dir.is_dir():
        print(f"check_planes: execution dir not found: {execution_dir}", file=sys.stderr)
        return 0
    violations = find_violations(execution_dir)
    if violations:
        print("Plane-separation check FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("Plane-separation check passed: execution plane is clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
