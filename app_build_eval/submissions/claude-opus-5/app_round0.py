#!/usr/bin/env python3
"""URL shortener service.

Single-file, standard library only. SQLite-backed, safe under concurrency.

    python app.py --port 8080 --db links.db
"""

import argparse
import json
import re
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
CODE_LENGTH = 7
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
ALLOWED_SCHEMES = ("http", "https")
MAX_BODY_BYTES = 64 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS links (
    code       TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    clicks     INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    expires_at INTEGER
);
"""


class Store:
    """SQLite persistence.

    One connection shared across request threads, guarded by a lock. SQLite
    serialises writes anyway; the lock keeps read-modify-write sequences atomic
    and avoids relying on per-thread connection semantics. Every statement is
    parameterised.
    """

    def __init__(self, path):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def create(self, code, url, expires_at):
        """Insert a link. Returns False if the code is already taken."""
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO links (code, url, clicks, created_at, expires_at) "
                    "VALUES (?, ?, 0, ?, ?)",
                    (code, url, int(time.time()), expires_at),
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get(self, code):
        with self._lock:
            row = self._conn.execute(
                "SELECT code, url, clicks, created_at, expires_at "
                "FROM links WHERE code = ?", (code,)
            ).fetchone()
        return dict(row) if row else None

    def register_click(self, code):
        """Increment clicks and return the row, or None / 'expired'.

        The read and the increment happen under one lock so concurrent
        redirects cannot lose an update.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT code, url, clicks, created_at, expires_at "
                "FROM links WHERE code = ?", (code,)
            ).fetchone()
            if row is None:
                return None
            if row["expires_at"] is not None and row["expires_at"] <= int(time.time()):
                return "expired"
            self._conn.execute(
                "UPDATE links SET clicks = clicks + 1 WHERE code = ?", (code,)
            )
            self._conn.commit()
            return dict(row)

    def delete(self, code):
        with self._lock:
            cur = self._conn.execute("DELETE FROM links WHERE code = ?", (code,))
            self._conn.commit()
            return cur.rowcount > 0

    def exists(self, code):
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM links WHERE code = ?", (code,)
            ).fetchone()
        return row is not None


class ValidationError(Exception):
    """Raised with a client-safe message for any 400-class input problem."""


def validate_url(payload):
    if "url" not in payload:
        raise ValidationError("field 'url' is required")
    url = payload["url"]
    if not isinstance(url, str) or not url.strip():
        raise ValidationError("field 'url' must be a non-empty string")
    try:
        parts = urlsplit(url)
    except ValueError:
        raise ValidationError("field 'url' is not a parseable URL")
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValidationError("url scheme must be http or https")
    if not parts.netloc:
        raise ValidationError("url must be absolute and include a host")
    return url


def validate_alias(payload):
    if "alias" not in payload or payload["alias"] is None:
        return None
    alias = payload["alias"]
    if not isinstance(alias, str) or not ALIAS_RE.match(alias):
        raise ValidationError(
            "alias must match ^[A-Za-z0-9_-]{3,32}$")
    return alias


def validate_expires_in(payload):
    if "expires_in" not in payload or payload["expires_in"] is None:
        return None
    value = payload["expires_in"]
    # bool is an int subclass; reject it explicitly rather than treating
    # True as 1 second.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("expires_in must be a positive integer")
    return int(time.time()) + value


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "urlshortener/1.0"

    # -------------------------------------------------- response helpers

    def _send(self, status, payload=None, headers=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, status, message):
        self._send(status, {"error": message})

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValidationError("invalid Content-Length")
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValidationError("request body too large")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            raise ValidationError("request body must be JSON")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("request body is not valid JSON")
        if not isinstance(payload, dict):
            raise ValidationError("request body must be a JSON object")
        return payload

    def log_message(self, *args):
        """Silence per-request stderr logging."""

    # -------------------------------------------------- routing

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            return self._send(200, {"status": "ok"})
        if path.startswith("/api/links/"):
            return self._stats(path[len("/api/links/"):])
        if path == "/api/links":
            return self._error(405, "method not allowed")
        if path.startswith("/api/"):
            return self._error(404, "not found")
        code = path.lstrip("/")
        if not code or "/" in code:
            return self._error(404, "not found")
        return self._redirect(code)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/links":
            return self._create()
        if path == "/api/health" or path.startswith("/api/links/"):
            return self._error(405, "method not allowed")
        return self._error(404, "not found")

    def do_DELETE(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/links/"):
            return self._delete(path[len("/api/links/"):])
        if path in ("/api/health", "/api/links"):
            return self._error(405, "method not allowed")
        return self._error(404, "not found")

    def do_PUT(self):
        self._error(405, "method not allowed")

    def do_PATCH(self):
        self._error(405, "method not allowed")

    # -------------------------------------------------- endpoints

    def _create(self):
        try:
            payload = self._read_json()
            url = validate_url(payload)
            alias = validate_alias(payload)
            expires_at = validate_expires_in(payload)
        except ValidationError as exc:
            return self._error(400, str(exc))

        store = self.server.store
        if alias is not None:
            if not store.create(alias, url, expires_at):
                return self._error(409, "alias already in use")
            code = alias
        else:
            for _ in range(10):
                candidate = "".join(
                    secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH)
                )
                if store.create(candidate, url, expires_at):
                    code = candidate
                    break
            else:
                return self._error(500, "could not allocate a unique code")

        return self._send(201, {
            "code": code,
            "url": url,
            "short_url": "http://localhost:%d/%s" % (self.server.public_port, code),
        })

    def _redirect(self, code):
        result = self.server.store.register_click(code)
        if result is None:
            return self._error(404, "no such link")
        if result == "expired":
            return self._error(410, "link has expired")
        return self._send(302, None, {"Location": result["url"]})

    def _stats(self, code):
        if not code or "/" in code:
            return self._error(404, "not found")
        row = self.server.store.get(code)
        if row is None:
            return self._error(404, "no such link")
        return self._send(200, {
            "code": row["code"],
            "url": row["url"],
            "clicks": row["clicks"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
        })

    def _delete(self, code):
        if not code or "/" in code:
            return self._error(404, "not found")
        if not self.server.store.delete(code):
            return self._error(404, "no such link")
        return self._send(204, None)


def main():
    parser = argparse.ArgumentParser(description="URL shortener service")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db", default="links.db")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    server.store = Store(args.db)
    server.public_port = args.port
    print("listening on http://127.0.0.1:%d" % args.port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
