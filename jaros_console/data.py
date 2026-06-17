"""File-system access + introspection for the console server.

A faithful Python port of ``console/server/jarosData.ts`` and
``console/server/jaros_introspect.py``: the console never talks to the daemon
over a socket (there is none) — it reads and writes the shared data directory
exactly as the host CLI does, and shells *in-process* into ``jaros`` for the
real state model, harness rules, deterministic replay, and the eval suite.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

# #EXT-010-REQ-10 Start
# Mirror jaros's own data-dir discovery without importing the CLI.
DEFAULT_DATA_DIR = ".jaros-data"
DATA_DIR_ENV = "JAROS_DATA_DIR"


def resolve_data_dir(explicit: str | os.PathLike[str] | None = None) -> Path:
    """``--data-dir`` arg → ``$JAROS_DATA_DIR`` → ``./.jaros-data``."""
    chosen = explicit or os.environ.get(DATA_DIR_ENV) or DEFAULT_DATA_DIR
    return Path(chosen).resolve()


# --- small safe readers -----------------------------------------------------

def _read_text(data: Path, rel: str) -> str | None:
    try:
        return (data / rel).read_text(encoding="utf-8")
    except OSError:
        return None


def _read_json(data: Path, rel: str) -> Any | None:
    raw = _read_text(data, rel)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _list_files(data: Path, rel: str, ext: str | None = None) -> list[str]:
    try:
        names = [p.name for p in (data / rel).iterdir() if p.is_file()]
    except OSError:
        return []
    if ext:
        names = [n for n in names if n.endswith(ext)]
    return sorted(names)


def _read_ndjson(data: Path, rel: str) -> list[Any]:
    """NDJSON reader that tolerates a torn trailing line (crash-safe logs)."""
    raw = _read_text(data, rel)
    if not raw:
        return []
    out: list[Any] = []
    for line in raw.split("\n"):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            pass  # partial trailing line — skip defensively
    return out


# --- reads (mirror jarosData.ts) --------------------------------------------

def data_dir_exists(data: Path) -> bool:
    return data.is_dir()


def get_status(data: Path) -> dict | None:
    return _read_json(data, "status.json")


def get_decisions(data: Path) -> list[Any]:
    return _read_ndjson(data, "state/decisions.log")


def get_transitions(data: Path) -> list[Any]:
    return _read_ndjson(data, "state/transitions.log")


def get_jobs(data: Path) -> list[dict]:
    jobs: list[dict] = []
    for area in ("inbox", "processed", "failed"):
        for file in _list_files(data, area, ".json"):
            jid = file[:-5]
            body = _read_json(data, f"{area}/{file}") or {}
            reason = None
            if area == "failed":
                r = _read_text(data, f"failed/{file}.reason")
                reason = r.strip() if r else None
            jobs.append({"id": jid, "agent": body.get("agent"), "area": area, "reason": reason})
    return jobs


def get_outbox(data: Path) -> list[dict]:
    results = []
    for file in _list_files(data, "outbox", ".json"):
        body = _read_json(data, f"outbox/{file}") or {}
        results.append({"id": file[:-5], "agent": body.get("agent"), "result": body.get("result")})
    return results


def get_agents(data: Path) -> list[str]:
    return [f for f in _list_files(data, "agents", ".py") if not f.startswith("_")]


def get_tools(data: Path) -> list[str]:
    return [f for f in _list_files(data, "tools", ".py") if not f.startswith("_")]


def get_schedules(data: Path) -> list[dict]:
    status = get_status(data) or {}
    live = status.get("schedules") or []
    by_id = {s.get("id"): s for s in live if isinstance(s, dict)}
    out = []
    for file in _list_files(data, "schedules", ".json"):
        body = _read_json(data, f"schedules/{file}") or {}
        timing = by_id.get(body.get("id")) if body.get("id") else None
        out.append({
            **body,
            "name": file[:-5],
            "trigger": (timing or {}).get("trigger"),
            "lastRun": (timing or {}).get("lastRun"),
            "nextRun": (timing or {}).get("nextRun"),
        })
    return out


def snapshot(data: Path) -> dict:
    jobs = get_jobs(data)
    return {
        "ts": _now_ms(),
        "connected": data_dir_exists(data),
        "status": get_status(data),
        "counts": {
            "inbox": sum(1 for j in jobs if j["area"] == "inbox"),
            "processed": sum(1 for j in jobs if j["area"] == "processed"),
            "failed": sum(1 for j in jobs if j["area"] == "failed"),
            "outbox": len(get_outbox(data)),
            "decisions": len(get_decisions(data)),
            "agents": len(get_agents(data)),
            "tools": len(get_tools(data)),
        },
    }


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


# --- writes (atomic temp-file + rename, like the CLI) -----------------------

def _atomic_write(dest: Path, content: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f".tmp-{uuid.uuid4().hex}"
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, dest)


def submit_job(data: Path, agent: str, job_input: Any) -> dict:
    jid = uuid.uuid4().hex
    _atomic_write(data / "inbox" / f"{jid}.json",
                  json.dumps({"id": jid, "agent": agent, "input": job_input}, indent=2))
    return {"id": jid}


def _safe_name(name: str, suffix: str) -> str:
    safe = name if name.endswith(suffix) else f"{name}{suffix}"
    if "/" in safe or "\\" in safe or safe.startswith("."):
        raise ValueError("invalid name")
    return safe


def install_module(data: Path, area: str, name: str, source: str) -> dict:
    safe = _safe_name(name, ".py")
    _atomic_write(data / area / safe, source)
    return {"path": f"{area}/{safe}"}


def write_schedule(data: Path, name: str, body: dict) -> dict:
    safe = _safe_name(name, ".json")
    _atomic_write(data / "schedules" / safe, json.dumps(body, indent=2))
    return {"name": safe}


def delete_schedule(data: Path, name: str) -> dict:
    safe = _safe_name(name, ".json")
    try:
        (data / "schedules" / safe).unlink()
        return {"removed": True}
    except OSError:
        return {"removed": False}


# --- introspection (in-process; jaros is the single source of truth) --------

def do_model() -> dict:
    from jaros.state.model import EVENTS, INITIAL_STATE, STATES, list_transitions

    return {
        "states": list(STATES),
        "events": list(EVENTS),
        "initial": INITIAL_STATE,
        "transitions": [{"from": f, "event": e, "to": t} for (f, e, t) in list_transitions()],
    }


def do_harness() -> dict:
    from jaros.harness.capabilities import BUILTIN_ROLES
    from jaros.harness.rules import DEFAULT_RULES

    return {
        "rules": {action: cap.__name__ for action, cap in DEFAULT_RULES.items()},
        "roles": {role: [c.__name__ for c in caps] for role, caps in BUILTIN_ROLES.items()},
    }


def do_replay(data: Path) -> dict:
    from jaros.state import replay_swarm

    res = replay_swarm(str(data))
    attribution = None
    if res.attribution is not None:
        a = res.attribution
        attribution = {"kind": a.kind, "index": a.index, "id": a.id, "source": a.source, "reason": a.reason}
    return {
        "decisions": res.decisions,
        "byAgent": {t.source: t.decisions for t in res.by_agent},
        "finalState": res.final_state,
        "byteIdentical": res.byte_identical,
        "deterministic": res.byte_identical,
        "chainOk": res.chain_ok,
        "attribution": attribution,
        "modelCalls": 0,
        "ok": res.ok,
    }


def do_evals(data: Path) -> dict:
    from jaros.eval import load_cases, run_suite
    from jaros.execution import executor
    from jaros.execution.tools import load_custom_tools, reset_tools_registry
    from jaros.llm import LlmConfig, create_llm_client
    from jaros.registry import AgentRegistry, load_agents, register_builtins

    executor.reset_handlers()
    reset_tools_registry()
    llm = create_llm_client(LlmConfig(provider="default"))
    registry = AgentRegistry()
    register_builtins(registry, llm)
    load_agents(registry, data / "agents", llm)
    load_custom_tools(data / "tools")

    report = run_suite(load_cases(data / "evals"), registry)
    out = report.to_dict()
    out["ok"] = True
    return out
# #EXT-010-REQ-10 End
