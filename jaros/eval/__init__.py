"""Agent Evaluation Framework (EXT-013).

Reproducible, declarative evaluation of agents. Because reasoning emits only
inert ``Decision`` data and execution is deterministic, evals reproduce exactly.

- :mod:`jaros.eval.runner` — EvalCase / Expect model + ``run_case``.
- :mod:`jaros.eval.suite` — load cases from ``evals/*.json`` + ``run_suite``.
"""

from __future__ import annotations

from jaros.eval.runner import EvalCase, EvalCheck, EvalResult, Expect, run_case
from jaros.eval.suite import SuiteReport, load_cases, run_suite

__all__ = [
    "EvalCase",
    "EvalCheck",
    "EvalResult",
    "Expect",
    "run_case",
    "SuiteReport",
    "load_cases",
    "run_suite",
]
