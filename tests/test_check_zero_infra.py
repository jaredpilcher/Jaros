"""Tests for the zero-infrastructure architecture check (EXT-007 / REQ-6, EXT-006 / REQ-6).

Covers a positive case (DB/broker/server-framework imports are flagged), a
negative case (a stdlib-only tree passes), the no-files case (graceful), and the
real ``jaros`` package (must be clean — including ``jaros/comms``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_zero_infra.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_zero_infra", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_zero_infra"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_pkg(root: Path, contents: str, name: str = "evil.py") -> None:
    pkg = root / "jaros" / "comms"
    pkg.mkdir(parents=True)
    (pkg / name).write_text(contents, encoding="utf-8")


def test_flags_infrastructure_imports(tmp_path):
    mod = _load_module()
    cases = [
        "import redis\n",
        "import psycopg\n",
        "from kafka import KafkaProducer\n",
        "import pika\n",
        "import sqlite3\n",
        "from flask import Flask\n",
        "import fastapi\n",
        "import http.server\n",
    ]
    for i, src in enumerate(cases):
        case_root = tmp_path / f"case{i}"
        _write_pkg(case_root, src)
        violations = mod.find_violations(case_root)
        assert violations, f"expected violation for: {src!r}"


def test_clean_tree_passes(tmp_path):
    mod = _load_module()
    _write_pkg(
        tmp_path,
        "import json\nimport os\nfrom pathlib import Path\n\n\ndef f():\n    return Path('.')\n",
    )
    assert mod.find_violations(tmp_path) == []


def test_no_files_present_is_graceful(tmp_path):
    mod = _load_module()
    assert mod.find_violations(tmp_path) == []


def test_real_package_is_clean():
    mod = _load_module()
    assert mod.find_violations(REPO_ROOT) == []
