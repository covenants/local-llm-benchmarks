import argparse
import http.server
import json
import re
import sqlite3
import threading
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Database setup
DB_PATH = "links.db"
PORT = 8080

# Regular expression for valid alias
ALIAS_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,32}$')

# Generate a random 7-character code
def generate_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=7))

# Initialize database
def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            code TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            alias TEXT UNIQUE,
            clicks INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            expires_at INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Validate URL
def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False

# Validate alias
def is_valid_alias(alias):
    return ALIAS_PATTERN.match(alias) is not None

# Check if code exists
def code_exists(code, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM links WHERE code = ?', (code,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Check if alias exists
def alias_exists(alias, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM links WHERE alias = ?', (alias,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Get link by code
def get_link_by_code(code, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT code, url, clicks, created_at, expires_at FROM links WHERE code = ?', (code,))
    result = cursor.fetchone()
    conn.close()
    return result

# Get link by alias
def get_link_by_alias(alias, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT code, url, clicks, created_at, expires_at FROM links WHERE alias = ?', (alias,))
    result = cursor.fetchone()
    conn.close()
    return result

# Create a new link
def create_link(code, url, alias, expires_in, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    created_at = int(time.time())
    expires_at = None
    if expires_in:
        expires_at = created_at + expires_in
    try:
        cursor.execute('''
            INSERT INTO links (code, url, alias, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, url, alias, created_at, expires_at))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# Increment click counter
def increment_clicks(code, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE links SET clicks = clicks + 1 WHERE code = ?', (code,))
    conn.commit()
    conn.close()

# Delete a link
def delete_link(code, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM links WHERE code = ?', (code,))
    conn.commit()
    conn.close()

# Check if link is expired
def is_expired(expires_at):
    if expires_at is None:
        return False
    return time.time() > expires_at

class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db_path = DB_PATH
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return

        # Handle redirect
        if self.path.startswith('/'):
            code = self.path[1:]
            if code == '':
                self.send_response(404)
                self.end_headers()
                return

            link = get_link_by_code(code, self.db_path)
            if not link:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Link not found"}).encode())
                return

            _, url, _, _, expires_at = link
            if is_expired(expires_at):
                self.send_response(410)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Link has expired"}).encode())
                return

            # Increment click counter atomically
            increment_clicks(code, self.db_path)

            self.send_response(302)
            self.send_header('Location', url)
            self.end_headers()
            return

        # Handle API endpoints
        if self.path.startswith('/api/links/'):
            code = self.path.split('/')[-1]
            link = get_link_by_code(code, self.db_path)
            if not link:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Link not found"}).encode())
                return

            _, url, clicks, created_at, expires_at = link
            response = {
                "code": code,
                "url": url,
                "clicks": clicks,
                "created_at": created_at,
                "expires_at": expires_at
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/links':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                return

            url = data.get('url')
            alias = data.get('alias')
            expires_in = data.get('expires_in')

            # Validate URL
            if not url or not isinstance(url, str) or not is_valid_url(url):
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid URL"}).encode())
                return

            # Validate alias if provided
            if alias is not None:
                if not isinstance(alias, str) or not is_valid_alias(alias):
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid alias"}).encode())
                    return
                if alias_exists(alias, self.db_path):
                    self.send_response(409)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Alias already in use"}).encode())
                    return

            # Validate expires_in if provided
            if expires_in is not None:
                if not isinstance(expires_in, int) or expires_in <= 0:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid expires_in"}).encode())
                    return

            # Generate code
            if alias is not None:
                code = alias
            else:
                code = generate_code()
                while code_exists(code, self.db_path):
                    code = generate_code()

            # Create link
            if not create_link(code, url, alias, expires_in, self.db_path):
                self.send_response(409)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Code already in use"}).encode())
                return

            # Prepare response
            host = self.headers.get('Host', f'localhost:{PORT}')
            short_url = f"http://{host}/{code}"
            response = {
                "code": code,
                "url": url,
                "short_url": short_url
            }
            self.send_response(201)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        if self.path.startswith('/api/links/'):
            code = self.path.split('/')[-1]
            link = get_link_by_code(code, self.db_path)
            if not link:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Link not found"}).encode())
                return

            delete_link(code, self.db_path)
            self.send_response(204)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        self.send_response(405)
        self.end_headers()

    def do_PATCH(self):
        self.send_response(405)
        self.end_headers()

    def do_HEAD(self):
        self.send_response(405)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(405)
        self.end_headers()

def main():
    global DB_PATH, PORT
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--db', type=str, default='links.db')
    args = parser.parse_args()
    PORT = args.port
    DB_PATH = args.db

    init_db(DB_PATH)
    server = HTTPServer(('', PORT), Handler)
    print(f"Server running on port {PORT}")
    server.serve_forever()

if __name__ == '__main__':
    main()