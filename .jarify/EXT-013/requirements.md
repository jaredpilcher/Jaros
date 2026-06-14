---
id: EXT-013
title: Agent Evaluation Framework
status: covered
priority: high
implementation:
  - jaros/eval/runner.py
  - jaros/eval/suite.py
  - jaros/eval/__init__.py
  - jaros/cli.py
---

# Agent Evaluation Framework

Evaluate and test agents the way you test software — reproducibly. Because
reasoning emits only inert `Decision` data and execution is deterministic, an
eval (input → expected decision/result) reproduces exactly, every time. This
gives teams, from startups to enterprise, a built-in way to assert agent behavior
in CI and from the host, serving the Prime Directive's reproducibility purpose
[PRIME-001 / P1] without any model-grading flakiness.

### [REQ-1] Declarative Eval Case Model

An eval case declares the agent to run, its input, and all-optional expectations
about the emitted decision and (optionally) the execution result.

#### Acceptance Criteria
- [x] `EvalCase` carries `name`, `kind`, `input`, and an `Expect` with optional
      `decision_count`, `decision_kind`, `source`, `payload_contains`, `gate`
      ("accept"/"reject"), and `result_contains`.
- [x] `EvalCase.from_dict` validates required fields and rejects a malformed
      `expect`; cases are plain JSON, authorable by hand or tooling.
- [x] The model imports only `jaros` + the standard library (no network/training).

### [REQ-2] Deterministic Eval Runner

A runner resolves the agent, runs `decide()`, and evaluates each expectation,
reporting per-check pass/fail — deterministically.

#### Acceptance Criteria
- [x] `run_case(case, registry)` resolves `case.kind`, runs `decide(input)`, and
      checks decision count/kind/source/payload, the validation gate, and (when
      requested) the executed result via the deterministic executor — no model call.
- [x] A resolution or reasoning exception is a failed eval with a captured error,
      never a crash.
- [x] Each expectation yields a named `EvalCheck` with a human-readable detail;
      the case passes iff every check passes.

### [REQ-3] Suite Loader & Report

Cases load from the shared FS and run as a suite with an aggregate report.

#### Acceptance Criteria
- [x] `load_cases(evals_dir)` reads `evals/*.json` (each file one case or a list),
      skipping malformed files with a logged reason.
- [x] `run_suite(cases, registry)` runs all cases and returns a `SuiteReport` with
      `total`/`passed`/`failed`/`ok` and a JSON-serializable `to_dict()`.
- [x] The suite is a pure function of the cases + registry; identical inputs give
      identical reports.

### [REQ-4] CLI Eval Command

Operators run the eval suite from the host with a single command.

#### Acceptance Criteria
- [x] `jaros eval [--data-dir D]` assembles built-in + plugin agents and the
      read-only/custom tool handlers from the data dir and runs `evals/*.json`.
- [x] It prints a per-case PASS/FAIL report with failing-check details and a
      summary, exiting 0 iff all cases pass (CI-friendly).
- [x] It reads/loads only the shared FS — no socket, no network.
