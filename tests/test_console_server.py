"""Tests for the bundled, zero-Node console server (EXT-010 / REQ-10).

The console ships as the sibling ``jaros_console`` package so a plain
``pip install jaros`` serves the prebuilt SPA + the REST API with no Node. These
tests drive the real stdlib server over loopback on an ephemeral port.
"""

from __future__ import annotations

import http.client
import json
from pathlib import Path

import pytest

from jaros_console import data as D
from jaros_console.server import make_server


@pytest.fixture()
def server(tmp_path: Path):
    httpd = make_server(tmp_path, port=0)  # 0 -> ephemeral port
    import threading

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield tmp_path, httpd.server_address[1]
    finally:
        httpd.shutdown()


def _request(port: int, method: str, path: str, body: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"content-type": "application/json"} if body is not None else {}
    conn.request(method, path, json.dumps(body) if body is not None else None, headers)
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8")
    conn.close()
    return resp.status, raw


def test_health_reports_data_dir(server):
    data, port = server
    status, raw = _request(port, "GET", "/api/health")
    assert status == 200
    body = json.loads(raw)
    assert Path(body["dataDir"]) == data.resolve()
    assert body["connected"] is True


def test_snapshot_shape(server):
    _, port = server
    status, raw = _request(port, "GET", "/api/snapshot")
    assert status == 200
    body = json.loads(raw)
    assert set(body) >= {"ts", "connected", "status", "counts"}
    assert set(body["counts"]) >= {"inbox", "processed", "failed", "outbox", "decisions"}


def test_submit_writes_job_to_inbox(server):
    data, port = server
    status, raw = _request(port, "POST", "/api/jobs", {"agent": "advance", "input": {}})
    assert status == 200
    job_id = json.loads(raw)["id"]
    written = data / "inbox" / f"{job_id}.json"
    assert written.is_file()
    assert json.loads(written.read_text())["agent"] == "advance"
    # and it now shows up in the jobs listing
    _, jobs_raw = _request(port, "GET", "/api/jobs")
    assert any(j["id"] == job_id and j["area"] == "inbox" for j in json.loads(jobs_raw))


def test_submit_requires_agent(server):
    _, port = server
    status, raw = _request(port, "POST", "/api/jobs", {"input": {}})
    assert status == 400
    assert "agent" in json.loads(raw)["error"]


def test_serves_spa_with_fallback(server):
    _, port = server
    # root serves the bundled index.html
    status, raw = _request(port, "GET", "/")
    assert status == 200
    assert 'id="root"' in raw
    # unknown non-/api path falls back to the SPA shell (client-side routing)
    status2, raw2 = _request(port, "GET", "/some/deep/route")
    assert status2 == 200
    assert 'id="root"' in raw2


def test_unknown_api_route_is_404(server):
    _, port = server
    status, _ = _request(port, "GET", "/api/nope")
    assert status == 404


def test_install_module_rejects_traversal(server):
    data, port = server
    status, raw = _request(port, "POST", "/api/agents",
                           {"name": "../evil", "source": "x = 1\n"})
    assert status == 400


def test_data_dir_resolution_prefers_explicit(tmp_path):
    assert D.resolve_data_dir(tmp_path) == tmp_path.resolve()
