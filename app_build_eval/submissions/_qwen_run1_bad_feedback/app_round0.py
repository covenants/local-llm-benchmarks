import argparse
import http.server
import json
import os
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingHTTPServer

# Database setup
DB_PATH = "links.db"
DEFAULT_PORT = 8080

# Regular expressions
ALIAS_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,32}$')
URL_PATTERN = re.compile(r'^https?://')

# Global variables
db_lock = threading.Lock()

def init_db(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                alias TEXT UNIQUE,
                clicks INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                expires_at INTEGER
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS deleted_codes (
                code TEXT PRIMARY KEY
            )
        ''')

def generate_code():
    import random
    import string
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(7))
        if not is_code_exists(code):
            return code

def is_code_exists(code):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT 1 FROM links WHERE code = ?', (code,))
            return cursor.fetchone() is not None

def is_alias_exists(alias):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT 1 FROM links WHERE alias = ?', (alias,))
            return cursor.fetchone() is not None

def is_code_deleted(code):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT 1 FROM deleted_codes WHERE code = ?', (code,))
            return cursor.fetchone() is not None

def store_link(code, url, alias, expires_in):
    now = int(time.time())
    expires_at = now + expires_in if expires_in else None
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO links (code, url, alias, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (code, url, alias, now, expires_at))

def get_link(code):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT code, url, alias, clicks, created_at, expires_at
                FROM links WHERE code = ?
            ''', (code,))
            return cursor.fetchone()

def increment_clicks(code):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('UPDATE links SET clicks = clicks + 1 WHERE code = ?', (code,))

def delete_link(code):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('DELETE FROM links WHERE code = ?', (code,))
            conn.execute('INSERT OR IGNORE INTO deleted_codes (code) VALUES (?)', (code,))

def is_expired(expires_at):
    if expires_at is None:
        return False
    return int(time.time()) > expires_at

class URLShortenerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return

        if self.path.startswith('/api/links/'):
            code = self.path.split('/')[-1]
            if not code:
                self.send_error(404)
                return
            link = get_link(code)
            if not link:
                self.send_error(404)
                return
            if is_expired(link[5]):
                self.send_error(410)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "code": link[0],
                "url": link[1],
                "clicks": link[3],
                "created_at": link[4],
                "expires_at": link[5]
            }
            self.wfile.write(json.dumps(response).encode())
            return

        if self.path.startswith('/'):
            code = self.path[1:]
            if not code:
                self.send_error(404)
                return
            if code.startswith('api/'):
                self.send_error(404)
                return
            if is_code_deleted(code):
                self.send_error(404)
                return
            link = get_link(code)
            if not link:
                self.send_error(404)
                return
            if is_expired(link[5]):
                self.send_error(410)
                return
            increment_clicks(code)
            self.send_response(302)
            self.send_header('Location', link[1])
            self.end_headers()
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == '/api/links':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
                return

            url = data.get('url')
            alias = data.get('alias')
            expires_in = data.get('expires_in')

            # Validate URL
            if not url or not isinstance(url, str):
                self.send_error(400, "URL is required and must be a string")
                return
            if not URL_PATTERN.match(url):
                self.send_error(400, "URL must be an absolute HTTP or HTTPS URL")
                return

            # Validate alias
            if alias is not None:
                if not isinstance(alias, str) or not ALIAS_PATTERN.match(alias):
                    self.send_error(400, "Alias must match the pattern ^[A-Za-z0-9_-]{3,32}$")
                    return
                if is_alias_exists(alias):
                    self.send_error(409, "Alias already in use")
                    return

            # Validate expires_in
            if expires_in is not None:
                if not isinstance(expires_in, int) or expires_in <= 0:
                    self.send_error(400, "expires_in must be a positive integer")
                    return

            # Generate code
            if alias:
                code = alias
                if is_code_exists(code):
                    self.send_error(409, "Alias already in use")
                    return
            else:
                code = generate_code()

            # Store link
            try:
                store_link(code, url, alias, expires_in)
            except Exception:
                self.send_error(400, "Failed to store link")
                return

            # Send response
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            short_url = f"http://{self.headers.get('Host')}/{code}"
            response = {
                "code": code,
                "url": url,
                "short_url": short_url
            }
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith('/api/links/'):
            code = self.path.split('/')[-1]
            if not code:
                self.send_error(404)
                return
            link = get_link(code)
            if not link:
                self.send_error(404)
                return
            delete_link(code)
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404)

    def do_PUT(self):
        self.send_error(405)

    def do_PATCH(self):
        self.send_error(405)

    def do_HEAD(self):
        self.send_error(405)

    def do_OPTIONS(self):
        self.send_error(405)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--db', type=str, default=DB_PATH)
    args = parser.parse_args()

    global DB_PATH
    DB_PATH = args.db
    init_db(DB_PATH)

    server = ThreadingHTTPServer(('', args.port), URLShortenerHandler)
    print(f"Server running on port {args.port}")
    server.serve_forever()

if __name__ == '__main__':
    main()