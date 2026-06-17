# Implementation Tasks

### [TASK-1] Create the runnable template set

Provide a matched, copy-pasteable `word-count` example that passes `jaros eval`
unmodified, as the executable backbone of the kit.

#### Steps
1. Add `agent-kit/templates/agent.py` — a `WordCountBoundary` with `NAME` and
   `build(llm)`, emitting a `text.wordcount` decision with a `{path}` payload.
2. Add `agent-kit/templates/tool.py` — a `WordCountTool` (`NAME = "text.wordcount"`)
   with `validate()` and a deterministic `execute()` that counts words in the file.
3. Add `agent-kit/templates/eval.json` and `schedule.json` for the same `word-count`
   agent.
4. Verify: stage agent + tool + eval into a throwaway data dir and confirm
   `jaros eval` exits 0.

#### Implements
- [REQ-4] Runnable Templates

### [TASK-2] Write the authoring skills

Add one `SKILL.md` per artifact type so an agent has a task-focused recipe.

#### Steps
1. Create `agent-kit/skills/jaros-build-agent/SKILL.md` with frontmatter, the
   `ReasoningBoundary` contract, a worked example, and the verification step.
2. Create `jaros-build-tool/SKILL.md`, `jaros-write-eval/SKILL.md`, and
   `jaros-schedule-agent/SKILL.md` in the same shape.
3. Cross-link each skill to its template and the relevant reference doc.

#### Implements
- [REQ-2] Authoring Skills

### [TASK-3] Write the reference docs

Document the real, current surface an author needs.

#### Steps
1. Add `agent-kit/reference/architecture.md` (Decision/Plane model, reproducibility,
   capability-safety, zero-infra).
2. Add `agent-kit/reference/public-api.md` with the exact `create_decision`,
   `ReasoningBoundary`, and `ValidationResult` signatures and the eval/schedule JSON
   shapes.
3. Add `agent-kit/reference/workflow.md` for the `serve`/`submit`/`replay`/`eval` loop.

#### Implements
- [REQ-3] Accurate Reference Material

### [TASK-4] Add the entry points

Make the kit discoverable in one hop.

#### Steps
1. Add a root `AGENTS.md` (cross-tool convention) stating what Jaros is, the rules,
   and pointing at `agent-kit/`.
2. Add `agent-kit/README.md` orienting an agent and indexing the skills, reference,
   and templates, with the verify loop.
3. Link the kit from the project `README.md`.

#### Implements
- [REQ-1] Discoverable Entry Point
