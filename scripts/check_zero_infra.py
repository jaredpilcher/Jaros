"""Structural zero-infrastructure architecture check (EXT-007 / REQ-6, EXT-006 / REQ-6).

Jaros runs with no external server, database, or message broker — only the
local/shared file system and in-process threads (Prime Directive P3). This check
scans the whole package (``jaros/**.py``) and fails (non-zero exit) if runtime
code imports a database driver, a message broker / queue service, or an external
server / web framework. It complements:

- ``check_no_server.py`` — no listening socket / HTTP server footprint;
- ``check_comms.py``     — no agent-to-agent RPC / network channel.

Detection is on the AST (imports only), so comments and strings do not trip it.

Run as: ``python scripts/check_zero_infra.py``
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# #EXT-007-REQ-6 Start
#: The package whose Python files must require no external infrastructure.
SCAN_DIR = Path("jaros")

#: Module import prefixes that imply an external infrastructure dependency.
FORBIDDEN_IMPORT_PREFIXES = (
    # Databases / ORMs used as a system-of-record store.
    "sqlite3", "psycopg", "psycopg2", "pymysql", "MySQLdb", "asyncpg",
    "sqlalchemy", "pymongo", "cx_Oracle",
    # Message brokers / queue services.
    "redis", "pika", "kafka", "confluent_kafka", "nats", "aio_pika",
    "kombu", "celery", "zmq", "stomp",
    # External server / web frameworks (listeners).
    "flask", "fastapi", "uvicorn", "gunicorn", "tornado", "bottle",
    "django", "aiohttp", "starlette", "sanic", "wsgiref",
    "http.server", "socketserver", "xmlrpc.server",
)


def _is_forbidden(name: str | None) -> bool:
    if not name:
        return False
    return any(name == p or name.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES)


def find_violations(repo_root: Path) -> list[str]:
    """Return human-readable zero-infrastructure violations (empty if clean)."""
    violations: list[str] = []
    scan_dir = repo_root / SCAN_DIR
    if not scan_dir.is_dir():
        return violations
    for path in sorted(scan_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden(alias.name):
                        violations.append(
                            f"{path.as_posix()}:{node.lineno}: forbidden "
                            f"infrastructure import {alias.name!r}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and _is_forbidden(node.module):
                    violations.append(
                        f"{path.as_posix()}:{node.lineno}: forbidden "
                        f"infrastructure import {node.module!r}"
                    )
    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    violations = find_violations(repo_root)
    if violations:
        print("Zero-infrastructure check FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("Zero-infrastructure check passed: no server, database, or broker dependency.")
    return 0
# #EXT-007-REQ-6 End


if __name__ == "__main__":
    sys.exit(main())
