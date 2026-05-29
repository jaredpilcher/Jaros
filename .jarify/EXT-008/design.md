# Design — Host Control CLI and Shared-FS Ingestion

The CLI is a thin, pure-files client. The shared data directory (a Docker-mounted volume) is the entire interface between host and OS. Every command is a read or write under that directory.

## Host ↔ OS via the shared volume

```text
   HOST (Windows / macOS / Linux)              CONTAINER (Jaros daemon)
   +-----------------------------+             +---------------------------+
   |  jaros submit advance ...   | --write-->  |  inbox/<id>.json          |
   |  jaros add-agent greet.py   | --write-->  |  plugins/greet.py         |
   |  jaros status / watch       | <--read---  |  status.json, outbox/*    |
   +-----------------------------+             +---------------------------+
              \__________ same dir, mounted: -v <host-dir>:/data __________/

   No sockets. No HTTP. Just files on a shared volume.
```

## Commands

```text
  jaros serve                 run the daemon (used inside the container)
  jaros submit <kind> [--input JSON]   -> inbox/<id>.json
  jaros add-agent <file.py> [--name K] -> plugins/<file>.py
  jaros status                -> print status.json
  jaros watch [--interval S]  -> live status + new outbox results
  jaros logs                  -> tail the daemon log (if present)

  global: --data-dir DIR (else $JAROS_DATA_DIR, else ./.jaros-data)
```

## Atomic writes (so the daemon never sees a partial file)

```text
  write to inbox/.tmp-<id>  ->  os.replace() -> inbox/<id>.json
  (os.replace is atomic on Windows and POSIX alike)
```

## Invariants

- Pure standard library + `pathlib`; identical behavior on every OS.
- The only transport is the shared data directory; no network is ever opened.
- Writes are atomic via `os.replace`, so the daemon reads only complete jobs/plugins.
