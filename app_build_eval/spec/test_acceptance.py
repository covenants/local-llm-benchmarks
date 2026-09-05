"""
Black-box acceptance tests for the URL shortener build task.

Derived only from spec/SPEC.md. Talks to the server over HTTP and never imports
the submission, so every implementation is judged on the same externally
observable contract.

Usage:
    python -m pytest app_build_eval/spec/test_acceptance.py --app <path/to/app.py>
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep 3xx responses intact so the Location header can be asserted on."""

    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, port):
        self.base = "http://127.0.0.1:%d" % port

    def request(self, method, path, body=None):
        url = self.base + path
        if isinstance(body, str):          # raw payload, for malformed-JSON tests
            data = body.encode()
        elif body is not None:
            data = json.dumps(body).encode()
        else:
            data = None

        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")

        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(req, timeout=10) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def json(self, method, path, body=None):
        status, _headers, raw = self.request(method, path, body)
        try:
            return status, (json.loads(raw) if raw else None)
        except json.JSONDecodeError:
            return status, None


def _spawn(app_path, port, db_path):
    return subprocess.Popen(
        [sys.executable, app_path, "--port", str(port), "--db", db_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _await_health(client, proc, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            _out, err = proc.communicate()
            pytest.fail("server exited during startup:\n" + err.decode(errors="replace")[:2000])
        try:
            if client.json("GET", "/api/health")[0] == 200:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


@pytest.fixture(scope="module")
def server(request):
    app_path = request.config.getoption("--app")
    port = _free_port()
    db_path = os.path.join(tempfile.mkdtemp(), "links.db")
    proc = _spawn(app_path, port, db_path)
    client = Client(port)
    if not _await_health(client, proc):
        proc.kill()
        pytest.fail("server never became healthy")
    yield client, app_path, port, db_path
    proc.kill()
    proc.wait()


@pytest.fixture
def c(server):
    return server[0]


# ---------------------------------------------------------------- health

def test_health(c):
    status, body = c.json("GET", "/api/health")
    assert status == 200
    assert body == {"status": "ok"}


# ---------------------------------------------------------------- create

def test_create_returns_201_and_code(c):
    status, body = c.json("POST", "/api/links", {"url": "https://example.com/a"})
    assert status == 201
    assert body["url"] == "https://example.com/a"
    assert isinstance(body["code"], str)
    assert len(body["code"]) == 7
    assert body["code"].isalnum()
    assert body["short_url"].endswith("/" + body["code"])


def test_generated_codes_are_unique(c):
    codes = set()
    for _ in range(25):
        _status, body = c.json("POST", "/api/links", {"url": "https://example.com/x"})
        codes.add(body["code"])
    assert len(codes) == 25


def test_custom_alias(c):
    status, body = c.json("POST", "/api/links",
                          {"url": "https://example.com/b", "alias": "my-alias"})
    assert status == 201
    assert body["code"] == "my-alias"


def test_duplicate_alias_conflicts(c):
    c.json("POST", "/api/links", {"url": "https://example.com/c", "alias": "taken1"})
    status, body = c.json("POST", "/api/links",
                          {"url": "https://example.com/d", "alias": "taken1"})
    assert status == 409
    assert "error" in body


@pytest.mark.parametrize("payload", [
    {},
    {"url": ""},
    {"url": None},
    {"url": 12345},
    {"url": "javascript:alert(1)"},
    {"url": "data:text/html,<script>alert(1)</script>"},
    {"url": "file:///etc/passwd"},
    {"url": "ftp://example.com/x"},
    {"url": "not-a-url"},
    {"url": "https://example.com", "alias": "ab"},
    {"url": "https://example.com", "alias": "a" * 33},
    {"url": "https://example.com", "alias": "bad alias"},
    {"url": "https://example.com", "alias": "bad/slash"},
    {"url": "https://example.com", "expires_in": 0},
    {"url": "https://example.com", "expires_in": -5},
    {"url": "https://example.com", "expires_in": "soon"},
])
def test_invalid_create_returns_400(c, payload):
    status, body = c.json("POST", "/api/links", payload)
    assert status == 400, "payload %r returned %s" % (payload, status)
    assert isinstance(body, dict) and "error" in body


def test_malformed_json_returns_400(c):
    status, _headers, _raw = c.request("POST", "/api/links", "{not json")
    assert status == 400


# ---------------------------------------------------------------- redirect

def test_redirect_302_with_location(c):
    _status, made = c.json("POST", "/api/links", {"url": "https://example.com/target"})
    status, headers, _raw = c.request("GET", "/" + made["code"])
    assert status == 302
    assert headers.get("Location") == "https://example.com/target"


def test_redirect_unknown_404(c):
    status, body = c.json("GET", "/definitely-not-a-real-code")
    assert status == 404
    assert "error" in body


def test_clicks_increment(c):
    _status, made = c.json("POST", "/api/links", {"url": "https://example.com/clicks"})
    code = made["code"]
    for _ in range(3):
        c.request("GET", "/" + code)
    _status, stats = c.json("GET", "/api/links/" + code)
    assert stats["clicks"] == 3


def test_stats_does_not_increment_clicks(c):
    _status, made = c.json("POST", "/api/links", {"url": "https://example.com/noclick"})
    code = made["code"]
    c.request("GET", "/" + code)
    c.json("GET", "/api/links/" + code)
    c.json("GET", "/api/links/" + code)
    _status, stats = c.json("GET", "/api/links/" + code)
    assert stats["clicks"] == 1


def test_concurrent_clicks_are_exact(c):
    _status, made = c.json("POST", "/api/links", {"url": "https://example.com/race"})
    code = made["code"]
    with ThreadPoolExecutor(max_workers=25) as ex:
        list(ex.map(lambda _: c.request("GET", "/" + code), range(50)))
    _status, stats = c.json("GET", "/api/links/" + code)
    assert stats["clicks"] == 50


# ---------------------------------------------------------------- expiry

def test_expired_link_returns_410(c):
    _status, made = c.json("POST", "/api/links",
                           {"url": "https://example.com/exp", "expires_in": 1})
    code = made["code"]
    assert c.request("GET", "/" + code)[0] == 302
    time.sleep(2.2)
    status, body = c.json("GET", "/" + code)
    assert status == 410
    assert "error" in body


def test_expired_link_does_not_count_click(c):
    _status, made = c.json("POST", "/api/links",
                           {"url": "https://example.com/exp2", "expires_in": 1})
    code = made["code"]
    time.sleep(2.2)
    c.request("GET", "/" + code)
    c.request("GET", "/" + code)
    _status, stats = c.json("GET", "/api/links/" + code)
    assert stats["clicks"] == 0


# ---------------------------------------------------------------- stats

def test_stats_shape(c):
    _status, made = c.json("POST", "/api/links",
                           {"url": "https://example.com/shape", "expires_in": 600})
    status, stats = c.json("GET", "/api/links/" + made["code"])
    assert status == 200
    assert stats["code"] == made["code"]
    assert stats["url"] == "https://example.com/shape"
    assert isinstance(stats["clicks"], int)
    assert isinstance(stats["created_at"], int)
    assert isinstance(stats["expires_at"], int)
    assert stats["expires_at"] > stats["created_at"]


def test_stats_null_expiry(c):
    _status, made = c.json("POST", "/api/links", {"url": "https://example.com/noexp"})
    _status, stats = c.json("GET", "/api/links/" + made["code"])
    assert stats["expires_at"] is None


def test_stats_unknown_404(c):
    status, _body = c.json("GET", "/api/links/nope-nope")
    assert status == 404


# ---------------------------------------------------------------- delete

def test_delete_204_then_404(c):
    _status, made = c.json("POST", "/api/links", {"url": "https://example.com/del"})
    code = made["code"]
    status, _headers, raw = c.request("DELETE", "/api/links/" + code)
    assert status == 204
    assert raw == b""
    assert c.request("GET", "/" + code)[0] == 404


def test_delete_unknown_404(c):
    status, _body = c.json("DELETE", "/api/links/never-existed")
    assert status == 404


# ---------------------------------------------------------------- routing

def test_wrong_method_405(c):
    status, _headers, _raw = c.request("DELETE", "/api/health")
    assert status == 405


def test_unknown_api_path_404(c):
    status, _headers, _raw = c.request("GET", "/api/does-not-exist")
    assert status == 404


# ---------------------------------------------------------------- security

def test_sql_injection_stored_verbatim(c):
    nasty = "https://example.com/?q=%27%3B+DROP+TABLE+links%3B--"
    status, made = c.json("POST", "/api/links", {"url": nasty})
    assert status == 201
    _status, stats = c.json("GET", "/api/links/" + made["code"])
    assert stats["url"] == nasty
    assert c.json("GET", "/api/health")[0] == 200


def test_sql_injection_in_alias_rejected(c):
    bad_alias = "a" + chr(39) + "; DROP TABLE links;--"
    status, _body = c.json("POST", "/api/links",
                           {"url": "https://example.com", "alias": bad_alias})
    assert status == 400
    assert c.json("GET", "/api/health")[0] == 200


# ---------------------------------------------------------------- persistence

def test_state_survives_restart(request):
    """Create a link, kill the server, restart on the same db, confirm state is intact.

    Uses its own server instance rather than the module-scoped one so that
    killing it cannot affect the other tests.
    """
    app_path = request.config.getoption("--app")
    port = _free_port()
    db_path = os.path.join(tempfile.mkdtemp(), "restart.db")
    client = Client(port)

    first = _spawn(app_path, port, db_path)
    try:
        assert _await_health(client, first), "server never became healthy"
        _status, made = client.json("POST", "/api/links",
                                    {"url": "https://example.com/persist"})
        code = made["code"]
        assert client.request("GET", "/" + code)[0] == 302
    finally:
        first.kill()
        first.wait()

    second = _spawn(app_path, port, db_path)
    try:
        assert _await_health(client, second), "server did not come back up"
        status, stats = client.json("GET", "/api/links/" + code)
        assert status == 200
        assert stats["url"] == "https://example.com/persist"
        assert stats["clicks"] == 1, "click count did not persist across restart"
    finally:
        second.kill()
        second.wait()
