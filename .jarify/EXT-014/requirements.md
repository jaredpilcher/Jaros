---
id: EXT-014
title: Agent Kit — Authoring Onboarding for AI Coding Agents
status: covered
priority: medium
implementation:
  - file: agent-kit/templates/agent.py
    ranges:
      - - 1
        - 51
  - file: agent-kit/templates/tool.py
    ranges:
      - - 1
        - 46
---

# Agent Kit

Jaros is meant to be extended. A developer should be able to point any AI coding
agent at a single folder and have it learn the whole project and author correct
Jaros agents, tools, evals, and schedules — with no other context. This
specification defines that folder, `agent-kit/`, and the root `AGENTS.md` entry
point that leads to it.

This spec serves the Prime Directive: it lowers the cost of safely extending the
runtime while keeping every authored artifact faithful to the directive's rules
(inert decisions, deterministic execution, capability-safety, zero-infrastructure).

### [REQ-1] Discoverable Entry Point

A coding agent pointed at the repository can find, in one hop, an authoritative
description of the whole project and how to extend it.

#### Acceptance Criteria
- [x] A root `AGENTS.md` (the cross-tool convention) states what Jaros is, the
      non-negotiable rules an author must honor, and points to `agent-kit/`.
- [x] `agent-kit/README.md` orients an agent: the mental model, an index of the
      skills, reference docs, and templates, and how to verify authored work.
- [x] The entry point is tool-agnostic — it works for any AI coding agent and
      assumes no specific one.

### [REQ-2] Authoring Skills

The kit ships task-focused skill guides, in the portable `SKILL.md` format, for
each kind of artifact an author creates.

#### Acceptance Criteria
- [x] There is one skill each for: building an agent, building a custom tool,
      writing an eval, and scheduling an agent.
- [x] Each `SKILL.md` has YAML frontmatter (`name`, `description`) and a body with
      the contract, a worked example, and a verification step.
- [x] Each skill links to the matching template and the relevant reference doc.

### [REQ-3] Accurate Reference Material

The kit documents the real, current public surface an author uses — so generated
code compiles against the actual APIs.

#### Acceptance Criteria
- [x] Reference docs cover the architecture (Decision/Plane model, reproducibility,
      capability-safety, zero-infra), the public API signatures, and the CLI
      workflow.
- [x] Every signature and JSON shape shown matches the real `jaros` package and the
      working `examples/`.

### [REQ-4] Runnable Templates

The kit provides a matched, copy-pasteable starter set that works as-is.

#### Acceptance Criteria
- [x] Templates exist for an agent, a custom tool, an eval case, and a schedule,
      forming one coherent example (`word-count`).
- [x] Staging the agent + tool + eval into a data dir and running `jaros eval`
      passes (exit 0) with no edits.
- [x] Each template carries inline guidance on what to change for a real artifact.
