# Reference agents — build spec

Three recognizable, genuinely useful agents that turn "okay… what do I build with
this?" into "oh, I'd build *that*." They are the on-ramps **and** the proof.

## The rules (read first — they're the whole point)

- **Build the *pattern*, never clone a named project.** "A code-fixing agent," not
  "the production version of <someone's repo>." No parasitic framing, no enemies.
- **Claim only what's true and checkable:** *reproducible · replayable · auditable ·
  deterministic-in-CI · least-privilege.* **Never** "production-ready" or "better
  than X" — those are the claims that get you dismantled on dimensions Jaros doesn't
  own (quality/cost/latency/prompts).
- **The intelligence lives in the reasoning boundary; the executor handler is a thin
  deterministic effect.** The LLM's output is captured in the `Decision`, so replay
  reconstructs the run exactly. Handlers must be pure (no clock/RNG/ambient I/O) so
  `check_determinism` stays green.
- **Each ships with a deterministic eval** (use the default/echo adapter or a recorded
  fixture response so the eval itself is reproducible — that's the demo). "Reproducible
  *and* tested," in one repo.
- **Each agent is least-privilege:** grant only the handles it needs (read-only on
  inputs, write only to its output dir), and the audit log shows every action.

Each agent = a `ReasoningBoundary` plugin in `plugins/`, an executor handler/tool in
`tools/`, an eval in `evals/`, and a short README with the honest one-liner.

---

## Agent 1 — `repo-fixer` (the code/PR agent) ★ build first

**Pattern:** given a failing test or an issue description (+ the relevant file in the
shared FS), propose a patch.

**The demo moment (why it dramatizes Jaros):** *replay the agent's reasoning for a
code change.* You can re-run the exact decision that produced a diff, byte-for-byte —
"here's *why* it changed line 42," reproducible forever. For code, that's trust gold.

- **Inputs (shared FS):** `inbox` job `{file, failing_test|issue}`; reads the target
  file via a read-only `FsRead` grant.
- **Reasoning boundary:** consults the LLM, emits one `Decision` kind `patch` with
  inert payload `{path, new_content | unified_diff, rationale}`.
- **Executor handler (`patch`):** deterministically writes the proposed content to an
  **output/sandbox** path (never the live file by default) via the harness writer;
  returns `{path, bytes}`.
- **Eval (`evals/repo-fixer.json`):** fixed input + fixture LLM response →
  `decision_kind: "patch"`, `payload_contains: {path: ...}`, `gate: "accept"`,
  `deterministic: true`.
- **Least-privilege:** `FsRead` on the input dir, `FsWrite` only on the output dir.
- **One-liner:** *"A code-fixing agent whose every change is replayable — re-run the
  exact decision that produced the diff, and audit what it was allowed to touch."*

## Agent 2 — `extractor` (document → structured data)

**Pattern:** given documents (text/markdown/CSV in the shared FS), extract structured
fields to JSON (e.g. invoice fields, contract terms, contact records).

**The demo moment:** *deterministic re-runs.* Run it today and next month on the same
docs → byte-identical output. For anything compliance-adjacent, reproducibility *is*
the feature.

- **Inputs:** `inbox` job `{docs_dir, schema}`; read-only over `docs_dir`.
- **Reasoning boundary:** LLM emits one `Decision` kind `extract` with payload
  `{records: [...], source_files: [...]}` (inert JSON).
- **Executor handler (`extract`):** deterministically writes `outputs/<id>.json`.
- **Eval (`evals/extractor.json`):** fixed docs + fixture response →
  `result_contains: {records: ...}`, `deterministic: true`.
- **Least-privilege:** `FsRead` on docs, `FsWrite` on outputs only.
- **One-liner:** *"A data-extraction agent you can re-run and get the exact same
  output — every extracted field traceable to the run that produced it."*

## Agent 3 — `researcher` (RAG / Q&A with citations)

**Pattern:** given a question + a local corpus (files in the shared FS), retrieve
relevant chunks and synthesize an answer with citations. The most recognizable "agent"
archetype — rides the biggest search demand.

**The demo moment:** *replay the exact retrieval + reasoning.* Reproduce an answer and
its citations from the recorded decisions, with no model call — "show me exactly how it
got that answer," every time.

- **Inputs:** `inbox` job `{question, corpus_dir}`; read-only over `corpus_dir`.
- **Reasoning boundary:** retrieve (deterministic, in-boundary) + LLM synthesize; emits
  one `Decision` kind `answer` with payload `{answer, citations: [...]}`.
- **Executor handler (`answer`):** writes `outbox/<id>.json` deterministically.
- **Eval (`evals/researcher.json`):** fixed corpus + question + fixture response →
  `payload_contains: {citations: ...}`, `deterministic: true`.
- **Least-privilege:** `FsRead` on the corpus, `FsWrite` on outbox only. No network.
- **One-liner:** *"A research agent whose answers replay exactly — reproduce the answer
  and its citations from the decision log, with zero model calls."*

---

## How each one becomes adoption fuel

For every agent: a 5-minute quickstart, a 30-second replay clip, a short SEO page/blog
("Build a reproducible \<X\> agent"), and a line in the README's examples. Each is also
a **design-partner conversation starter** — "you're building an X agent? here's a
reproducible one; want help porting yours?"

## The stronger follow-up (when these land)

Once the three exist, the highest-leverage next step is **bring-your-own-agent**: a thin
adapter + guide so someone runs *their* existing agent on Jaros and gains replay for
free. Additive, not parasitic — it wins the community instead of antagonizing it. Spec
that only after the three reference agents prove the shape.
