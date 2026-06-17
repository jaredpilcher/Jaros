"""Pure-stdlib console server: serves the prebuilt SPA + the REST/SSE API.

The Python twin of ``console/server/index.ts``. Same routes, same response
shapes — so the same React bundle runs against either bridge. It serves the
SPA and the ``/api`` surface on a single localhost port (production-style),
reading and writing the shared data directory; the Jaros node stays serverless.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import data as D

# #EXT-010-REQ-10 Start
DIST = Path(__file__).resolve().parent / "_dist"

_MIME = {
    ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
    ".ico": "image/x-icon", ".woff2": "font/woff2", ".map": "application/json",
}


class _Handler(BaseHTTPRequestHandler):
    # Quiet by default — the console matches jaros's change-only logging.
    def log_message(self, *args) -> None:  # noqa: D401
        pass

    # -- helpers --------------------------------------------------------------

    @property
    def data_dir(self) -> Path:
        return self.server.data_dir  # type: ignore[attr-defined]

    def _json(self, code: int, body: object) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict:
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            return json.loads(raw) if raw.strip() else {}
        except ValueError:
            return {}

    # -- routing --------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        d = self.data_dir
        try:
            if path == "/api/health":
                return self._json(200, {"dataDir": str(d), "connected": D.data_dir_exists(d)})
            if path == "/api/snapshot":
                return self._json(200, D.snapshot(d))
            if path == "/api/status":
                return self._json(200, D.get_status(d) or {})
            if path == "/api/jobs":
                return self._json(200, D.get_jobs(d))
            if path == "/api/outbox":
                return self._json(200, D.get_outbox(d))
            if path == "/api/decisions":
                return self._json(200, D.get_decisions(d))
            if path == "/api/transitions":
                return self._json(200, D.get_transitions(d))
            if path == "/api/agents":
                return self._json(200, {"agents": D.get_agents(d), "tools": D.get_tools(d)})
            if path == "/api/schedules":
                return self._json(200, D.get_schedules(d))
            if path == "/api/model":
                return self._json(200, _cached(self.server, "model", D.do_model))
            if path == "/api/harness":
                return self._json(200, _cached(self.server, "harness", D.do_harness))
            if path == "/api/events":
                return self._sse()
            if path.startswith("/api/"):
                return self._json(404, {"error": "not found"})
            return self._serve_static(path)
        except Exception as exc:  # surface a clean error
            return self._json(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        d = self.data_dir
        try:
            if path == "/api/jobs":
                body = self._read_body()
                if not body.get("kind"):
                    return self._json(400, {"error": "kind is required"})
                job_input = body.get("input", {})
                if isinstance(job_input, str):
                    try:
                        job_input = json.loads(job_input) if job_input.strip() else {}
                    except ValueError:
                        return self._json(400, {"error": "input must be valid JSON"})
                return self._json(200, D.submit_job(d, str(body["kind"]), job_input))
            if path in ("/api/agents", "/api/tools"):
                area = "tools" if path.endswith("/tools") else "agents"
                body = self._read_body()
                if not body.get("name") or not isinstance(body.get("source"), str):
                    return self._json(400, {"error": "name and source are required"})
                try:
                    return self._json(200, D.install_module(d, area, str(body["name"]), body["source"]))
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
            if path == "/api/schedules":
                body = self._read_body()
                if not body.get("name") or not body.get("schedule"):
                    return self._json(400, {"error": "name and schedule are required"})
                try:
                    return self._json(200, D.write_schedule(d, str(body["name"]), body["schedule"]))
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
            if path == "/api/replay":
                return self._json(200, D.do_replay(d))
            if path == "/api/evals":
                return self._json(200, D.do_evals(d))
            return self._json(404, {"error": "not found"})
        except Exception as exc:
            return self._json(500, {"error": str(exc)})

    def do_DELETE(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        if parts.path == "/api/schedules":
            name = (parse_qs(parts.query).get("name") or [None])[0]
            if not name:
                return self._json(400, {"error": "name query param required"})
            try:
                return self._json(200, D.delete_schedule(self.data_dir, name))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
        return self._json(404, {"error": "not found"})

    # -- server-sent events ---------------------------------------------------

    def _sse(self) -> None:
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "keep-alive")
        self.end_headers()
        try:
            while not getattr(self.server, "_stopping", False):
                payload = f"data: {json.dumps(D.snapshot(self.data_dir))}\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # client disconnected

    # -- static SPA -----------------------------------------------------------

    def _serve_static(self, path: str) -> None:
        if not DIST.is_dir():
            html = (b"<h1>Jaros Console</h1><p>The bundled UI is missing from "
                    b"this install.</p>")
            self.send_response(200)
            self.send_header("content-type", "text/html")
            self.send_header("content-length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        rel = "index.html" if path == "/" else path.lstrip("/")
        target = (DIST / rel).resolve()
        if not str(target).startswith(str(DIST)) or not target.is_file():
            target = DIST / "index.html"  # SPA fallback
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("content-type", _MIME.get(target.suffix, "application/octet-stream"))
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _cached(server, key, fn):
    cache = server._cache  # type: ignore[attr-defined]
    if key not in cache:
        cache[key] = fn()
    return cache[key]


def make_server(data_dir: Path, port: int = 5500, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Build (but don't start) the console HTTP server bound to ``port``."""
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.daemon_threads = True
    httpd.data_dir = Path(data_dir).resolve()  # type: ignore[attr-defined]
    httpd._cache = {}  # type: ignore[attr-defined]
    httpd._stopping = False  # type: ignore[attr-defined]
    return httpd


def serve_console(data_dir: Path, port: int = 5500, *, background: bool = False,
                  host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Start the console server. Returns the server (call ``shutdown()`` to stop).

    With ``background=True`` it serves on a daemon thread and returns
    immediately (used by ``jaros serve``); otherwise it blocks in the caller.
    """
    httpd = make_server(data_dir, port, host)
    if background:
        t = threading.Thread(target=httpd.serve_forever, name="jaros-console", daemon=True)
        t.start()
    else:
        httpd.serve_forever()
    return httpd
# #EXT-010-REQ-10 End
