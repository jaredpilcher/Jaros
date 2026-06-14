"""Eval suite loader + report (EXT-013 / REQ-3).

Loads declarative eval cases from ``evals/*.json`` (each file is one case or a
list of cases) and runs them, producing a pass/fail report.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jaros.eval.runner import EvalCase, EvalResult, run_case

logger = logging.getLogger(__name__)


# #EXT-013-REQ-3 Start
def load_cases(evals_dir: str | Path) -> list[EvalCase]:
    """Load and validate eval cases from ``*.json``, skipping malformed files."""
    directory = Path(evals_dir)
    cases: list[EvalCase] = []
    if not directory.is_dir():
        return cases
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else [data]
            for item in items:
                cases.append(EvalCase.from_dict(item))
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            logger.warning("skipping malformed eval %s: %s", path.name, exc)
    return cases


@dataclass
class SuiteReport:
    """Aggregate result of running an eval suite."""

    results: list[EvalResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.total > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "ok": self.ok,
            "results": [
                {
                    "case": r.case,
                    "passed": r.passed,
                    "error": r.error,
                    "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in r.checks],
                }
                for r in self.results
            ],
        }


def run_suite(cases: list[EvalCase], registry: Any, *, execute: bool = True) -> SuiteReport:
    """Run every case against the registry and collect the results."""
    return SuiteReport([run_case(c, registry, execute=execute) for c in cases])
# #EXT-013-REQ-3 End
