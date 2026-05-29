"""Host Control CLI and shared-FS ingestion (EXT-008).

A cross-platform, pure-standard-library command-line client for driving a running
Jaros OS *from the host*. The entire interface between host and OS is the shared
data directory (a Docker-mounted volume): every command's effect is a read or a
write under that directory. No socket is ever opened and no network call is ever
made — the CLI reaches the daemon exclusively through files.

Commands::

    jaros serve                            run the daemon (inside the container)
    jaros submit <kind> [--input JSON]     -> inbox/<id>.json
    jaros add-agent <file.py> [--name K]   -> plugins/<name-or-file>.py
    jaros status                           -> print status.json
    jaros watch [--interval S]             -> live status + new outbox results
    jaros logs                             -> print the daemon log (if present)

    global: --data-dir DIR (else $JAROS_DATA_DIR, else ./.jaros-data)

Writes are atomic (temp file + :func:`os.replace`), so the daemon never observes a
partial job or plugin. This module lives directly under ``jaros/`` (not under an
agent package), so the structural comms / no-server checks correctly treat it as a
host orchestrator rather than an agent.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Sequence

#: Default shared data directory when neither --data-dir nor $JAROS_DATA_DIR is set.
DEFAULT_DATA_DIR = ".jaros-data"

#: Environment variable naming the shared data directory.
DATA_DIR_ENV = "JAROS_DATA_DIR"

#: Candidate daemon log file locations searched (relative to the data dir).
LOG_CANDIDATES = ("daemon.log", "logs/daemon.log")


# #EXT-008-REQ-1 Start
def resolve_data_dir(args: argparse.Namespace) -> Path:
    """Resolve the shared data directory using ``pathlib`` only.

    Preference order: the ``--data-dir`` flag, then the ``$JAROS_DATA_DIR``
    environment variable, then the ``./.jaros-data`` default. Uses no
    platform-specific separators; the returned path is the same directory the
    daemon uses.
    """
    chosen = getattr(args, "data_dir", None)
    if not chosen:
        chosen = os.environ.get(DATA_DIR_ENV)
    if not chosen:
        chosen = DEFAULT_DATA_DIR
    return Path(chosen)
# #EXT-008-REQ-1 End


def _atomic_write(target: Path, data: str) -> None:
    """Write ``data`` to ``target`` atomically via a temp file + ``os.replace``.

    The temp file is created in the same directory so the rename is atomic on
    Windows and POSIX alike; the daemon never sees a partial file.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".tmp-{uuid.uuid4().hex}-{target.name}")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, target)


# #EXT-008-REQ-2 Start
def cmd_submit(kind: str, input_json: str | None, data_dir: Path) -> Path:
    """Write a job descriptor ``{id, kind, input}`` into ``inbox/`` atomically.

    The ``--input`` string (if given) must parse as JSON; on malformed JSON a
    :class:`ValueError` is raised and *nothing* is written. The job id is a fresh
    ``uuid4``; the file is written to ``inbox/.tmp-<id>`` then ``os.replace``-d to
    ``inbox/<id>.json`` so the daemon never reads a partial job. Returns the path
    of the created job file.
    """
    if input_json is None:
        parsed_input: object = None
    else:
        try:
            parsed_input = json.loads(input_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--input is not valid JSON: {exc}") from exc

    job_id = uuid.uuid4().hex
    job = {"id": job_id, "kind": kind, "input": parsed_input}
    target = data_dir / "inbox" / f"{job_id}.json"
    # Validate-then-write: the bad-JSON path above never reaches here, so a
    # rejected submission leaves the inbox untouched.
    tmp = (data_dir / "inbox" / f".tmp-{job_id}")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(job, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, target)
    return target
# #EXT-008-REQ-2 End


# #EXT-008-REQ-3 Start
def _discover_kind(source: str) -> str | None:
    """Statically read a plugin module's top-level ``KIND`` string, if any.

    Parses the source with :mod:`ast` (no import, so no plugin side effects run on
    the host) and returns the literal value of a module-level ``KIND = "..."``
    assignment, or ``None`` when it is absent / not a string literal.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target] if node.target is not None else []
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "KIND":
                value = getattr(node, "value", None)
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
    return None


def cmd_add_agent(path: str, name: str | None, data_dir: Path) -> tuple[Path, str | None]:
    """Install an agent plugin module into the watched ``plugins/`` folder.

    Validates the source ``*.py`` exists and is readable, then copies it to
    ``plugins/.tmp-<file>`` and ``os.replace``-s it to
    ``plugins/<name-or-filename>.py`` so the daemon never loads a partial module.
    The destination filename defaults to the source filename; ``name`` overrides
    its stem. Returns ``(installed_path, discovered_kind)``.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"source plugin not found or not a file: {path}")
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"source plugin is not readable: {path} ({exc})") from exc

    if name:
        filename = name if name.endswith(".py") else f"{name}.py"
    else:
        filename = source.name
    target = data_dir / "plugins" / filename
    _atomic_write(target, content)
    return target, _discover_kind(content)
# #EXT-008-REQ-3 End


# #EXT-008-REQ-4 Start
def _read_status(data_dir: Path) -> dict[str, object] | None:
    """Return the parsed ``status.json`` or ``None`` when it is absent/unreadable."""
    status_path = data_dir / "status.json"
    if not status_path.is_file():
        return None
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cmd_status(data_dir: Path, stream=None) -> int:
    """Read and pretty-print ``status.json`` (graceful message when absent).

    Returns 0 when status was printed and 1 when no status file exists yet.
    """
    out = stream if stream is not None else sys.stdout
    status_path = data_dir / "status.json"
    if not status_path.is_file():
        print(
            f"no status available yet (no {status_path} — is the daemon running?)",
            file=out,
        )
        return 1
    status = _read_status(data_dir)
    if status is None:
        print(f"status file is present but unreadable: {status_path}", file=out)
        return 1
    print(json.dumps(status, indent=2, sort_keys=True), file=out)
    return 0


def cmd_watch(data_dir: Path, interval: float, stream=None) -> int:
    """Loop printing status + newly-appeared ``outbox/*.json`` until interrupted.

    Reads purely from the shared FS: on each pass it prints the current status and
    any ``outbox/`` result files that have appeared since the previous pass. Exits
    cleanly (returns 0) on ``KeyboardInterrupt``. No socket or network is used.
    """
    out = stream if stream is not None else sys.stdout
    outbox = data_dir / "outbox"
    seen: set[str] = set()
    try:
        while True:
            cmd_status(data_dir, stream=out)
            if outbox.is_dir():
                for result in sorted(outbox.glob("*.json")):
                    if result.name in seen:
                        continue
                    seen.add(result.name)
                    print(f"--- new result: outbox/{result.name} ---", file=out)
                    try:
                        print(result.read_text(encoding="utf-8"), file=out)
                    except OSError:
                        pass
            time.sleep(max(interval, 0.0))
    except KeyboardInterrupt:
        print("watch stopped.", file=out)
        return 0


def cmd_logs(data_dir: Path, stream=None) -> int:
    """Print the daemon log file under the data dir, if one is present.

    Searches the conventional log locations (``daemon.log``, ``logs/daemon.log``)
    and prints the first that exists. Returns 0 when a log was printed, 1 when no
    log file was found. Reads only the shared FS — no socket, no network.
    """
    out = stream if stream is not None else sys.stdout
    for candidate in LOG_CANDIDATES:
        log_path = data_dir / candidate
        if log_path.is_file():
            try:
                print(log_path.read_text(encoding="utf-8"), end="", file=out)
            except OSError as exc:
                print(f"log present but unreadable: {log_path} ({exc})", file=out)
                return 1
            return 0
    searched = ", ".join(str(data_dir / c) for c in LOG_CANDIDATES)
    print(f"no daemon log found (looked for: {searched})", file=out)
    return 1
# #EXT-008-REQ-4 End


# #EXT-008-REQ-1 Start
def _build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with the global ``--data-dir`` + subcommands."""
    parser = argparse.ArgumentParser(
        prog="jaros",
        description="Host control CLI for a Jaros OS (shared-filesystem only).",
    )
    parser.add_argument(
        "--data-dir",
        dest="data_dir",
        default=None,
        help=(
            "shared data directory the daemon uses "
            f"(else ${DATA_DIR_ENV}, else ./{DEFAULT_DATA_DIR})"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="run the daemon (used inside the container)")

    p_submit = sub.add_parser("submit", help="write a job descriptor into inbox/")
    p_submit.add_argument("kind", help="agent kind that should handle the job")
    p_submit.add_argument(
        "--input", dest="input", default=None, help="job input as a JSON string"
    )

    p_add = sub.add_parser("add-agent", help="install a plugin module into plugins/")
    p_add.add_argument("path", help="path to the agent module (*.py)")
    p_add.add_argument(
        "--name", dest="name", default=None, help="override the installed kind/filename"
    )

    sub.add_parser("status", help="read and print status.json")

    p_watch = sub.add_parser("watch", help="live status + new outbox results")
    p_watch.add_argument(
        "--interval",
        dest="interval",
        type=float,
        default=1.0,
        help="seconds between refreshes (default: 1.0)",
    )

    sub.add_parser("logs", help="print the daemon log file if present")
    return parser


def load_dotenv(env_path: Path | None = None) -> None:
    """Load keys/values from a .env file into os.environ if it exists."""
    if env_path is None:
        env_path = Path(".env")
    if not env_path.is_file():
        return
    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if key:
                    os.environ.setdefault(key, val)
    except Exception:
        pass


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: parse ``argv`` and dispatch to the matching command.

    Returns a process exit code. Never opens a socket or makes a network call;
    every command's effect is a read or write under the shared data directory.
    """
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(argv)
    data_dir = resolve_data_dir(args)

    if args.command == "serve":
        # Imported lazily so the lightweight host commands don't pull in the whole
        # daemon dependency graph just to submit a job or read status.
        from jaros.daemon import Daemon

        return Daemon(data_dir=data_dir).run()

    if args.command == "submit":
        try:
            target = cmd_submit(args.kind, args.input, data_dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        job_id = target.stem
        print(f"submitted job {job_id} -> {target}")
        return 0

    if args.command == "add-agent":
        try:
            target, kind = cmd_add_agent(args.path, args.name, data_dir)
        except (FileNotFoundError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if kind:
            print(f"installed agent -> {target} (registers kind {kind!r})")
        else:
            print(f"installed agent -> {target}")
        return 0

    if args.command == "status":
        return cmd_status(data_dir)

    if args.command == "watch":
        return cmd_watch(data_dir, args.interval)

    if args.command == "logs":
        return cmd_logs(data_dir)

    parser.error(f"unknown command: {args.command!r}")  # pragma: no cover
    return 2  # pragma: no cover
# #EXT-008-REQ-1 End


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
