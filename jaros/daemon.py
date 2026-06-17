"""The Jaros Runtime Daemon (EXT-007).

The daemon is the composition root that *stays running*. It assembles every
plane exactly once at boot — shared file system, queue, LLM client, harness,
agent pool, and the agent registry — then loops: ingest work from the shared FS
``inbox/``, load any new agents from ``agents/``, run agents as lightweight
threads under the bounded pool, drive durable state-machine transitions for each
job, publish ``status.json`` + a stdout heartbeat, and move handled jobs aside.

Nothing enters except through the shared file system (``inbox/`` + ``agents/``):
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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from jaros.comms.fs import SharedFileSystem
from jaros.comms.queue import Queue
from jaros.core import Decision
from jaros.core.decision_gate import validate_decision
from jaros.execution import executor
from jaros.execution.handlers import register_runtime_handlers
from jaros.harness import Action, GrantSpec, Harness
from jaros.llm import LlmConfig, create_llm_client
from jaros.registry import AgentRegistry, load_agents, register_builtins
from jaros.runtime import AgentPool, AgentThread
from jaros.scheduling import Scheduler, load_schedules
from jaros.state import (
    INITIAL_STATE,
    DecisionLog,
    TransitionLog,
    record_decision,
)

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
        env_bound = os.environ.get("JAROS_POOL_BOUND")
        if env_bound is not None:
            try:
                pool_bound = int(env_bound)
            except ValueError:
                pass
        self._lock = threading.RLock()
        # Durable audit log: every mediated action (allowed/denied) is recorded
        # to state/audit.log — the auditable record the directive demands (P2).
        self.harness = Harness(audit_path=self.fs.base_dir / "state" / "audit.log")
        self.pool = AgentPool(bound=max(1, pool_bound))
        # Grant the daemon's own writer a scoped FsWrite handle so even the
        # daemon's result writes flow through the harness (mediated side effect).
        self.harness.spawn(
            _WRITER_AGENT,
            GrantSpec(role="ReporterRole", fs=self.fs, queue=self.queue),
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
        # Durable decision log: records each accepted Decision (the run's only
        # non-deterministic input) so a run can be re-executed deterministically
        # by replay (EXT-002 / REQ-6).
        self.decision_log = DecisionLog(self.fs.base_dir / "state")
        self.decision_log.ensure()

        # Native scheduler (EXT-011): operator schedules under schedules/ are
        # evaluated each tick; last-fire state is persisted for crash-safety.
        self._schedules_dir = self.fs.base_dir / "schedules"
        self._schedules_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = Scheduler(self.fs.base_dir / "state" / "schedules.state.json")

        # Register the shared runtime handlers (advance + fs.write) and load any
        # custom tools. `jaros replay` registers these SAME handlers over a
        # sandbox, so replay re-uses this exact code path (EXT-008 / REQ-6).
        register_runtime_handlers(
            harness=self.harness,
            writer_agent=_WRITER_AGENT,
            tools_dir=self.fs.base_dir / "tools",
        )

        # --- run-loop bookkeeping -----------------------------------------
        self._active_jobs: set[str] = set()
        # Names of claims THIS node is actively processing. Heartbeated each tick
        # so a live node never reclaims its own in-flight work; a crashed node
        # stops heartbeating, so its claims go stale and a sibling reclaims them.
        self._processing: set[str] = set()
        lease_ms = os.environ.get("JAROS_CLAIM_LEASE_MS")
        try:
            self._claim_lease_s = (int(lease_ms) if lease_ms else 60000) / 1000.0
        except ValueError:
            self._claim_lease_s = 60.0
        # Reference counts for per-kind harness grants, so concurrent jobs of the
        # same kind share one grant (torn down only when the last finishes).
        self._grant_refs: dict[str, int] = {}
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
        self.scheduled = 0
        self.last_result: dict[str, Any] | None = None
        self.state = INITIAL_STATE
    # #EXT-007-REQ-1 End

    # -- inbox ingestion + fault isolation ----------------------------------

    # #EXT-007-REQ-5 Start
    # #EXT-002-REQ-7 Start
    def _claim_maintenance(self) -> None:
        """Heartbeat this node's in-flight claims; reclaim siblings' stale ones.

        A claim is a file in ``claimed/`` whose mtime is its lease. Each tick this
        node **touches** (refreshes) the claims it is actively processing, so as
        long as it is alive its claims never expire. Any *other* claim whose lease
        has expired (``> JAROS_CLAIM_LEASE_MS``, default 60s) is assumed orphaned
        by a crashed node and moved back to ``inbox/`` for re-processing. This is
        crash recovery for distribution: exactly-once in the happy path,
        at-least-once under node failure (so agents must be idempotent).
        """
        claimed = self.fs.base_dir / "claimed"
        if not claimed.is_dir():
            return
        inbox = self.fs.base_dir / "inbox"
        now = time.time()
        with self._lock:
            active = set(self._processing)
        for job_path in sorted(claimed.glob("*.json")):
            if job_path.name in active:
                try:
                    os.utime(job_path, None)  # heartbeat: refresh our lease
                except OSError:
                    pass
                continue
            try:
                age = now - job_path.stat().st_mtime
            except OSError:
                continue
            if age > self._claim_lease_s:  # orphaned by a crashed node -> recover
                try:
                    inbox.mkdir(parents=True, exist_ok=True)
                    os.replace(job_path, inbox / job_path.name)
                    print(f"JAROS_RECLAIM stale claim job={job_path.name} age={age:.0f}s", flush=True)
                except OSError:
                    pass
    # #EXT-002-REQ-7 End

    def _process_inbox(self) -> None:
        """Atomically claim each inbox job (multi-node safe) and process it.

        The claim is an atomic rename ``inbox/<id> -> claimed/<id>``. On a shared
        volume only ONE daemon wins that rename for a given job; sibling nodes get
        ``ENOENT`` and skip it, so the same job is never processed twice across
        containers — bounded multi-node coordination over the shared file system
        (EXT-002 / REQ-7). The winner runs the job, then moves ``claimed/ ->
        processed/`` or ``failed/``. Work admitted up to the pool's bound.
        """
        inbox = self.fs.base_dir / "inbox"
        claimed_dir = self.fs.base_dir / "claimed"
        claimed_dir.mkdir(parents=True, exist_ok=True)
        for job_path in sorted(inbox.glob("*.json")):
            # #EXT-002-REQ-7 Start
            claimed = claimed_dir / job_path.name
            try:
                os.replace(job_path, claimed)  # atomic claim; the loser gets ENOENT
            except OSError:
                continue  # another node already claimed it (or it vanished)
            try:
                os.utime(claimed, None)  # stamp the claim time — the lease clock
            except OSError:
                pass
            with self._lock:
                self._processing.add(claimed.name)
            # #EXT-002-REQ-7 End

            def _job_runner_factory(path=claimed):
                def _body():
                    self._execute_job_lifecycle(path)
                return AgentThread.spawn(f"job-{path.stem}", _body)

            self.pool.submit(_job_runner_factory)

    def _execute_job_lifecycle(self, job_path: Path) -> None:
        """Complete in-thread lifecycle for a single job."""
        try:
            self._run_job(job_path)
            print(f"JAROS_JOB ok job={job_path.name}", flush=True)
            with self._lock:
                self._move(job_path, "processed")
                self.processed += 1
                self._write_status()
        except FileNotFoundError:
            # The job file vanished between scan and processing (e.g. cleared by an
            # operator, or reclaimed). That's benign — skip it silently rather
            # than recording a spurious failure.
            return
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            # Surface failures on stdout so operators see *why* a job failed,
            # not just an incremented counter.
            print(f"JAROS_JOB FAILED job={job_path.name}: {reason}", flush=True)
            with self._lock:
                dest = self._move(job_path, "failed")
                if dest is not None:
                    self.fs.write(
                        f"failed/{dest.name}.reason", reason + "\n"
                    )
                self.failed += 1
                self.last_result = {"error": reason, "job": job_path.name}
                self._write_status()
        finally:
            # Release the claim's lease — we are no longer heartbeating it.
            with self._lock:
                self._processing.discard(job_path.name)
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

        # Spawn each job kind under a fixed least-privilege role. Capability-safety
        # is structural least-privilege via the harness-granted handles (EXT-005);
        # Jaros enforces no authorization policy of its own.
        role_name = "GuestRole"

        # Spawn in the harness under its assigned role before running reasoning.
        # Reference-counted so concurrent jobs of the same kind share one grant
        # (one job's teardown must not revoke the grant another is still using).
        with self._lock:
            if self._grant_refs.get(kind, 0) == 0:
                self.harness.spawn(kind, GrantSpec(role=role_name, fs=self.fs, queue=self.queue))
            self._grant_refs[kind] = self._grant_refs.get(kind, 0) + 1

        try:
            # Run the boundary directly (we are already in a pool thread)
            decisions = boundary.decide(job_input)

            if not decisions:
                raise RuntimeError(f"agent for kind {kind!r} emitted no decision")

            decision = decisions[0]
            
            # Gating, execution, and writing are serialized safely under lock
            with self._lock:
                gated = validate_decision(decision)
                if not gated.ok:
                    raise RuntimeError(f"decision rejected by gate: {gated.reason}")

                outcome = executor.apply(
                    decision,
                    on_accept=lambda d: record_decision(self.decision_log, d),
                    log=self.log,
                )
                if not outcome.applied:
                    raise RuntimeError(f"executor refused decision: {outcome.reason}")

                result = outcome.output
                self.last_result = result if isinstance(result, dict) else {"output": result}
                # The advance handler is now pure; the daemon reflects the final
                # machine state it reports (the handler no longer mutates state).
                if isinstance(result, dict) and isinstance(result.get("finalState"), str):
                    self.state = result["finalState"]

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
        finally:
            with self._lock:
                self._grant_refs[kind] = self._grant_refs.get(kind, 1) - 1
                if self._grant_refs[kind] <= 0:
                    self._grant_refs.pop(kind, None)
                    self.harness.teardown(kind)

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
        try:
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
                "scheduled": self.scheduled,
                "schedules": self.scheduler.describe(
                    load_schedules(self._schedules_dir), datetime.now()
                ),
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
        except Exception as exc:
            # Contain any temporary filesystem write errors and print it as a heartbeat warning
            print(
                f"JAROS_HEARTBEAT tick={self.tick_count} state={self.state} "
                f"STATUS_WRITE_ERROR={exc}",
                flush=True,
            )
    # #EXT-007-REQ-4 End

    # -- native scheduling --------------------------------------------------

    # #EXT-011-REQ-4 Start
    def _dispatch_schedules(self) -> None:
        """Submit any due scheduled jobs to the inbox (atomic), each contained.

        Reads the operator schedules, prunes durable state for removed ones, and
        for every due schedule writes one ``inbox/<id>.json`` and records the
        dispatch so a restart neither double-fires nor skips it. A failure on one
        schedule never affects the others or the daemon.
        """
        now = datetime.now()
        schedules = load_schedules(self._schedules_dir)
        self.scheduler.prune({s.id for s in schedules})
        for sch in self.scheduler.due(schedules, now):
            try:
                job_id = f"{sch.id}-{int(now.timestamp())}-{uuid.uuid4().hex[:6]}"
                inbox = self.fs.base_dir / "inbox"
                inbox.mkdir(parents=True, exist_ok=True)
                tmp = inbox / f".tmp-{job_id}"
                dest = inbox / f"{job_id}.json"
                tmp.write_text(
                    json.dumps({"id": job_id, "kind": sch.kind, "input": sch.input}),
                    encoding="utf-8",
                )
                os.replace(tmp, dest)
                self.scheduler.mark_fired(sch, now)
                with self._lock:
                    self.scheduled += 1
                print(f"JAROS_SCHED fired schedule={sch.id} kind={sch.kind} job={job_id}", flush=True)
            except Exception as exc:
                print(f"JAROS_SCHED FAILED schedule={sch.id}: {exc}", flush=True)
    # #EXT-011-REQ-4 End

    # -- tick + run loop ----------------------------------------------------

    # #EXT-007-REQ-1 Start
    def tick(self) -> None:
        """Run exactly one loop pass.

        One pass: scan ``agents/`` for new agents (REQ-3), process the
        ``inbox/`` (REQ-2/REQ-5), then publish ``status.json`` + a heartbeat
        (REQ-4). Wrapped so a fault in any phase is contained and the daemon
        survives to tick again.
        """
        self.tick_count += 1
        try:
            load_agents(self.registry, self.fs.base_dir / "agents", self.llm)
            # Idempotently scan and register any new custom tools dropped at runtime
            from jaros.execution.tools import load_custom_tools
            load_custom_tools(self.fs.base_dir / "tools")
        except Exception:  # a bad agent/tool must never kill the loop
            pass
        try:
            self._dispatch_schedules()
        except Exception:  # a bad schedule must never kill the loop
            pass
        try:
            self._claim_maintenance()  # heartbeat ours; reclaim siblings' stale claims
        except Exception:
            pass
        self._process_inbox()
        self.pool.drain()
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
