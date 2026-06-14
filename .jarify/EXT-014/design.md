# EXT-014 — Agent Kit Design

## Intent

Make Jaros self-describing to an AI coding agent. The kit is pure onboarding: it
adds no runtime code and changes no public API. It is a curated, accurate,
verifiable bundle of *guidance* and *starter material* that turns "read the whole
repo and infer the conventions" into "read one folder and follow it."

## Structure

```text
AGENTS.md                     root entry point (cross-tool convention)
   │  "if you are an agent, start at agent-kit/README.md"
   ▼
agent-kit/
├── README.md                 orientation: mental model + index + verify loop
├── skills/                   task-focused SKILL.md guides
│   ├── jaros-build-agent/SKILL.md
│   ├── jaros-build-tool/SKILL.md
│   ├── jaros-write-eval/SKILL.md
│   └── jaros-schedule-agent/SKILL.md
├── reference/                accurate, current facts
│   ├── architecture.md       Decision/Plane, reproducibility, capability-safety
│   ├── public-api.md         exact signatures an author calls
│   └── workflow.md           the CLI loop: serve / submit / replay / eval
└── templates/                runnable, matched starter set (`word-count`)
    ├── agent.py              ReasoningBoundary: KIND + build(llm) + decide
    ├── tool.py               NAME + validate + execute (deterministic)
    ├── eval.json             input -> expected decision/result
    └── schedule.json         interval/cron/one-shot
```

## How an agent consumes it

```text
 developer points agent at repo
            │
            ▼
   reads AGENTS.md ──► reads agent-kit/README.md
            │                     │
            │            ┌────────┴─────────┐
            ▼            ▼                  ▼
      pick a skill   read reference    copy a template
      (build-agent)  (public-api)      (agent.py + tool.py)
            └──────────────┬───────────────┘
                           ▼
              author artifact into <data-dir>/{agents,tools,evals}/
                           ▼
              VERIFY: `jaros eval` (and `jaros replay`) — exit 0
```

## Correctness contract

The templates are the executable specification of the kit: the matched
`word-count` agent + tool + eval must pass `jaros eval` unmodified. Anything the
skills or reference docs claim about contracts is mirrored by a template that
actually runs, so the guidance cannot silently drift from the code.

## Non-goals

- No runtime behavior, no new public API, no coupling to a specific agent vendor.
- Not a replacement for the full specs in `.jarify/` — it points to them.
