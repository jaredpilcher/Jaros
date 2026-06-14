# Implementation Tasks — Agent Evaluation Framework

### [TASK-1] Implement the eval case model and runner

Define declarative cases and a deterministic per-case runner.

#### Steps
1. Create `jaros/eval/runner.py` with `Expect` (optional `decision_count`/`decision_kind`/`source`/`payload_contains`/`gate`/`result_contains`), `EvalCase` (+ `from_dict` validation), `EvalCheck`, and `EvalResult`.
2. Implement `run_case(case, registry, *, execute=True)` that resolves the kind, runs `decide()`, evaluates each expectation (decision fields, gate via `validate_decision`, result via `executor.apply`), captures exceptions as a failed eval, and returns per-check results.

#### Implements
- [REQ-1] Declarative Eval Case Model
- [REQ-2] Deterministic Eval Runner

### [TASK-2] Implement the suite loader and report

Load cases from the shared FS and aggregate results.

#### Steps
1. Create `jaros/eval/suite.py` with `load_cases(evals_dir)` reading `*.json` (single case or list), skipping malformed files with a logged reason.
2. Add a `SuiteReport` dataclass (`total`/`passed`/`failed`/`ok`/`to_dict`) and `run_suite(cases, registry)`; export the public API from `jaros/eval/__init__.py`.

#### Implements
- [REQ-3] Suite Loader & Report

### [TASK-3] Add the `jaros eval` CLI command

Run the eval suite from the host, CI-friendly.

#### Steps
1. In `jaros/cli.py`, add `cmd_eval(data_dir)` that builds the LLM + `AgentRegistry` (`register_builtins` + `load_agents`) and loads custom tool handlers, then runs `load_cases`/`run_suite` over `evals/`.
2. Print a per-case PASS/FAIL report with failing-check details and a summary; register the `eval` subcommand and dispatch it; return 0 iff all cases pass.

#### Implements
- [REQ-4] CLI Eval Command

### [TASK-4] Add example cases and tests

Ship eval cases for the read-only agents and test the framework.

#### Steps
1. Create `examples/readonly/evals/readonly.json` with cases for `system-health`, `disk-monitor`, `inventory`, and `text-metrics` asserting decision kind/payload/gate and (where path-independent) `result_contains`.
2. Create `tests/test_eval.py` covering decision-level checks, gate, result execution, error capture, malformed-skip loading, and that the shipped read-only suite passes via `run_suite`.

#### Implements
- [REQ-1] Declarative Eval Case Model
- [REQ-3] Suite Loader & Report
- [REQ-4] CLI Eval Command
