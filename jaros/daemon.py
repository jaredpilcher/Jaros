"""The Jaros Runtime Daemon (EXT-007).

The daemon is the composition root that *stays running*. It assembles every
plane exactly once at boot — shared file system, queue, LLM client, harness,
agent pool, and the agent registry — then loops: ingest work from the shared FS
``inbox/``, load any new agents from ``plugins/``, run agents as lightweight
threads under the bounded pool, drive durable state-machine transitions for each
job, publish ``status.json`` + a stdout heartbeat, and move handled jobs aside.

Nothing enters except through the shared file system (``inbox/`` + ``plugins/``):
there is no socket and no port. Every job result is a validated
:class:`~jaros.core.decision.Decision` applied through the deterministic
executor and committed to a durable :class:`~jaros.state.TransitionLog`. A single
job's failure is contained — it is recorded in ``failed/`` with a reason and the
daemon and sibling jobs survive.

This module is part of the daemon's *composition root*: it legitimately wires
the comms planes together but performs no agent-to-agent or network channel of
its own. It lives directly under ``jaros/`` (not under ``jaros/runtime`` or an
agent package) so the structural comms / no-server checks correctly treat it as
an orchestrator rather than an agent.
"""

from __future__ import annotations

import json
import os
import signal
import threading
import time
from pathlib import Path
from typing import Any

from jaros.comms.fs import SharedFileSystem
from jaros.comms.queue import Queue
from jaros.core import Decision
from jaros.core.decision_gate import validate_decision
from jaros.execution import executor
from jaros.harness import Action, FsWrite, GrantSpec, Harness
from jaros.llm import LlmConfig, create_llm_client
from jaros.registry import AgentRegistry, load_plugins, register_builtins
from jaros.runtime import AgentPool, AgentThread
from jaros.state import INITIAL_STATE, TransitionLog, commit

#: The built-in agent kind the daemon registers an executor handler for.
ADVANCE_KIND = "advance"

#: The harness agent id used by the daemon to write per-job results to outbox.
_WRITER_AGENT = "daemon-writer"


# #EXT-007-REQ-1 Start
class Daemon:
    """Boots every plane and runs the Jaros OS until signalled to stop.

    Args:
        data_dir: Root of the shared file system layout (inbox/outbox/...).
        llm_config: Provider-neutral LLM selection (defaults to the echo adapter).
        pool_bound: Maximum number of agents the pool runs concurrently.
        tick_ms: Loop period in milliseconds; overridden by ``JAROS_TICK_MS``.
    """

    def __init__(
        self,
        data_dir: str | os.PathLike[str],
        *,
        llm_config: LlmConfig | None = None,
        pool_bound: int = 4,
        tick_ms: int | None = None,
    ) -> None:
        # --- shared file system + queue -----------------------------------
        self.fs = SharedFileSystem(data_dir)
        self.fs.ensure_layout()
        self.queue: Queue[Any] = Queue()

        # --- LLM client (interchangeable, config-driven) ------------------
        self.llm = create_llm_client(llm_config or LlmConfig(provider="default"))

        # --- harness + bounded agent pool ---------------------------------
        self.harness = Harness()
        self.pool = AgentPool(bound=max(1, pool_bound))
        # Grant the daemon's own writer a scoped FsWrite handle so even the
        # daemon's result writes flow through the harness (mediated side effect).
        self.harness.spawn(
            _WRITER_AGENT,
            GrantSpec(capabilities=(FsWrite(),), fs=self.fs),
        )

        # --- agent registry + built-ins -----------------------------------
        self.registry = AgentRegistry()
        register_builtins(self.registry, self.llm)

        # --- durable state machine ----------------------------------------
        # A shared, durable transition log under state/. Each job advances the
        # machine through its own PENDING->RUNNING->DONE sequence; the log is the
        # append-only record of every committed transition.
        self.log = TransitionLog(self.fs.base_dir / "state")
        self.log.ensure()

        # Register the deterministic executor handler for the built-in kind.
        executor.register_handler(ADVANCE_KIND, self._advance_handler)

        # --- run-loop bookkeeping -----------------------------------------
        env_tick = os.environ.get("JAROS_TICK_MS")
        if env_tick is not None:
            try:
                tick_ms = int(env_tick)
            except ValueError:
                pass
        self.tick_ms = tick_ms if tick_ms is not None else 200
        self._stop = threading.Event()
        self._started_at = time.monotonic()
        self.tick_count = 0
        self.processed = 0
        self.failed = 0
        self.last_result: dict[str, Any] | None = None
        self.state = INITIAL_STATE
    # #EXT-007-REQ-1 End

    # -- executor handler ---------------------------------------------------

    # #EXT-007-REQ-2 Start
    def _advance_handler(self, decision: Decision, **collaborators: Any) -> dict[str, Any]:
        """Deterministically drive a per-job PENDING->RUNNING->DONE sequence.

        Runs in the Execution Plane: given the *validated* ``advance`` decision,
        it commits each declared event to the durable transition log and returns
        the inert result that the daemon then writes to ``outbox/<id>.json``.
        It performs no reasoning and touches no LLM.
        """
        payload = decision.payload if isinstance(decision.payload, dict) else {}
        events = payload.get("events") or ["start", "complete"]
        note = payload.get("note")

        state = INITIAL_STATE
        indices: list[int] = []
        for event in events:
            result = commit(self.log, state, event)
            state = result.state
            indices.append(result.index)
        self.state = state
        return {
            "decision": decision.id,
            "source": decision.source,
            "kind": decision.kind,
            "finalState": state,
            "events": list(events),
            "logIndices": indices,
            "note": note,
        }
    # #EXT-007-REQ-2 End

    # -- inbox ingestion + fault isolation ----------------------------------

    # #EXT-007-REQ-5 Start
    def _process_inbox(self) -> None:
        """Process every job descriptor currently in ``inbox/``.

        For each ``inbox/*.json`` ``{id, kind, input}``: resolve the kind, run
        its reasoning boundary as a thread under the bounded pool, pipe the
        emitted decision through the validation gate + deterministic executor,
        write the result to ``outbox/<id>.json`` via a harness-granted fs.write,
        and move the job to ``processed/``. Every job is wrapped in try/except:
        on any error the job is moved to ``failed/`` with a ``.reason`` sidecar
        and the failure count is incremented — one failure never kills the loop.
        """
        inbox = self.fs.base_dir / "inbox"
        for job_path in sorted(inbox.glob("*.json")):
            try:
                self._run_job(job_path)
                self._move(job_path, "processed")
                self.processed += 1
            except Exception as exc:  # contained: the loop must survive
                reason = f"{type(exc).__name__}: {exc}"
                dest = self._move(job_path, "failed")
                if dest is not None:
                    self.fs.write(
                        f"failed/{dest.name}.reason", reason + "\n"
                    )
                self.failed += 1
                self.last_result = {"error": reason, "job": job_path.name}
            # status reflects progress after every handled job (REQ-4).
            self._write_status()
    # #EXT-007-REQ-5 End

    # #EXT-007-REQ-2 Start
    def _run_job(self, job_path: Path) -> None:
        """Resolve, run, validate, execute, and persist one job's result."""
        raw = job_path.read_text(encoding="utf-8")
        job = json.loads(raw)
        job_id = job["id"]
        kind = job["kind"]
        job_input = job.get("input")

        boundary = self.registry.resolve(kind)  # KeyError -> failed/ (REQ-5)

        # Run the boundary as a lightweight thread under the bounded pool. The
        # agent body returns inert decisions only (no side effects).
        captured: dict[str, list[Decision]] = {}

        def _body() -> list[Decision]:
            decisions = boundary.decide(job_input)
            captured["decisions"] = list(decisions)
            return decisions

        agent_id = f"job-{job_id}"
        self.pool.submit(lambda: AgentThread.spawn(agent_id, _body))
        self.pool.drain()  # deterministic: join the agent we just submitted

        decisions = captured.get("decisions") or []
        if not decisions:
            raise RuntimeError(f"agent for kind {kind!r} emitted no decision")

        decision = decisions[0]
        # Gate first, then the deterministic executor dispatches to the handler.
        gated = validate_decision(decision)
        if not gated.ok:
            raise RuntimeError(f"decision rejected by gate: {gated.reason}")

        outcome = executor.apply(decision, log=self.log)
        if not outcome.applied:
            raise RuntimeError(f"executor refused decision: {outcome.reason}")

        result = outcome.output
        self.last_result = result if isinstance(result, dict) else {"output": result}

        # Write the per-job result to outbox via the harness (mediated fs.write).
        payload = json.dumps(
            {"id": job_id, "kind": kind, "result": self.last_result},
            indent=2,
            sort_keys=True,
        )
        action = Action(type="fs.write", path=f"outbox/{job_id}.json", data=payload)
        ar = self.harness.request(_WRITER_AGENT, action)
        if not ar.allowed:
            raise RuntimeError(f"harness denied outbox write: {ar.reason}")

    def _move(self, job_path: Path, area: str) -> Path | None:
        """Move ``job_path`` into ``<data>/<area>/`` so it never runs twice.

        Returns the destination path (or ``None`` if the source vanished).
        """
        if not job_path.exists():
            return None
        dest_dir = self.fs.base_dir / area
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / job_path.name
        os.replace(job_path, dest)
        return dest
    # #EXT-007-REQ-2 End

    # -- observable status + heartbeat --------------------------------------

    # #EXT-007-REQ-4 Start
    def _write_status(self) -> None:
        """Serialize live state to ``<data>/status.json`` atomically + heartbeat.

        Writes the current machine state, an agent-pool snapshot, processed /
        failed counts, the last result, the tick number, and uptime. The write
        is atomic (temp file + ``os.replace``). A one-line ``JAROS_HEARTBEAT``
        record is also printed to stdout so an operator can watch via logs.
        """
        snapshot = self.pool.snapshot()
        active = sum(1 for s in snapshot if s.state.value == "running")
        status = {
            "state": self.state,
            "pool": {
                "bound": self.pool.bound,
                "active": active,
                "pending": self.pool.pending,
                "agents": [
                    {"id": s.id, "state": s.state.value} for s in snapshot
                ],
            },
            "processed": self.processed,
            "failed": self.failed,
            "lastResult": self.last_result,
            "tick": self.tick_count,
            "uptimeSec": round(time.monotonic() - self._started_at, 3),
        }
        # Atomic write: temp file in base_dir + os.replace into status.json.
        target = self.fs.base_dir / "status.json"
        tmp = target.with_name(f".status.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, target)

        print(
            f"JAROS_HEARTBEAT tick={self.tick_count} state={self.state} "
            f"active={active} processed={self.processed} failed={self.failed}",
            flush=True,
        )
    # #EXT-007-REQ-4 End

    # -- tick + run loop ----------------------------------------------------

    # #EXT-007-REQ-1 Start
    def tick(self) -> None:
        """Run exactly one loop pass.

        One pass: scan ``plugins/`` for new agents (REQ-3), process the
        ``inbox/`` (REQ-2/REQ-5), then publish ``status.json`` + a heartbeat
        (REQ-4). Wrapped so a fault in any phase is contained and the daemon
        survives to tick again.
        """
        self.tick_count += 1
        try:
            load_plugins(self.registry, self.fs.base_dir / "plugins", self.llm)
        except Exception:  # a bad plugin must never kill the loop
            pass
        self._process_inbox()
        self._write_status()

    def stop(self) -> None:
        """Signal the run loop to stop accepting new work and exit."""
        self._stop.set()

    def run(self) -> int:
        """Install signal handlers, loop on every tick until stopped, teardown.

        Installs ``SIGINT``/``SIGTERM`` handlers that set the stop flag, then
        loops calling :meth:`tick` every ``tick_ms`` until stopped. On exit it
        stops accepting work, drains the pool (tearing down active agents), and
        tears down the harness writer — returning exit code 0.
        """
        self._install_signal_handlers()
        tick_seconds = max(self.tick_ms, 0) / 1000.0
        try:
            while not self._stop.is_set():
                self.tick()
                # Interruptible sleep: wakes immediately when stop is set.
                self._stop.wait(tick_seconds)
        finally:
            self._teardown()
        return 0

    def _install_signal_handlers(self) -> None:
        """Install SIGINT/SIGTERM -> stop flag (best-effort; main thread only)."""
        def _handler(signum: int, frame: Any) -> None:  # noqa: ARG001
            self._stop.set()

        for sig in (signal.SIGINT, getattr(signal, "SIGTERM", signal.SIGINT)):
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError, RuntimeError):
                # Not on the main thread (e.g. under a test) -> skip silently.
                pass

    def _teardown(self) -> None:
        """Stop accepting work, drain the pool, and release harness grants."""
        self._stop.set()
        try:
            self.pool.drain()
        finally:
            self.harness.teardown(_WRITER_AGENT)
            self._write_status()
# #EXT-007-REQ-1 End
