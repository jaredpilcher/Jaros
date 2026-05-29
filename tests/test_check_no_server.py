"""Tests for the no-server architecture check (EXT-003 / REQ-3).

Covers a positive case (server/listener patterns are flagged), a negative case
(a clean runtime tree passes), and the no-files-present case (graceful, exit 0).
The real ``jaros/runtime`` tree must also be clean.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_no_server.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_no_server", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_no_server"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_runtime(root: Path, contents: str) -> None:
    runtime = root / "jaros" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "evil.py").write_text(contents, encoding="utf-8")


def test_flags_server_patterns(tmp_path):
    mod = _load_module()
    cases = [
        "import socket\ns = socket.socket()\n",
        "import socket\ns.bind(('0.0.0.0', 80))\n",
        "import socket\ns.listen(5)\n",
        "from http.server import HTTPServer\nsrv = HTTPServer(('', 80), None)\n",
        "import socketserver\n",
        "import asyncio\nasyncio.start_server(None, '0.0.0.0', 80)\n",
    ]
    for i, src in enumerate(cases):
        case_root = tmp_path / f"case{i}"
        _write_runtime(case_root, src)
        violations = mod.find_violations(case_root)
        assert violations, f"expected violation for case: {src!r}"


def test_clean_tree_passes(tmp_path):
    mod = _load_module()
    _write_runtime(
        tmp_path,
        "import threading\n\n\ndef body():\n    return None\n\n"
        "t = threading.Thread(target=body)\n",
    )
    assert mod.find_violations(tmp_path) == []


def test_no_files_present_is_graceful(tmp_path):
    mod = _load_module()
    # No jaros/runtime or jaros/agents directory at all.
    assert mod.find_violations(tmp_path) == []


def test_real_runtime_tree_is_clean():
    mod = _load_module()
    assert mod.find_violations(REPO_ROOT) == []
