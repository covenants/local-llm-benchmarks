# Build Task: URL Shortener Service

Implement a URL shortener as a **single Python file** named `app.py`.

## Hard constraints

- **Python standard library only.** No Flask, FastAPI, requests, or any pip package.
  Use `http.server`, `sqlite3`, `json`, `urllib`, `threading`, etc.
- Must run as: `python app.py --port <PORT> --db <PATH>`
- Both flags are required to work. Default port 8080, default db `links.db`.
- Data persists in SQLite at `--db`. State MUST survive a process restart.
- The server must handle concurrent requests (use `ThreadingHTTPServer`).
- Print nothing to stdout except an optional startup line. Never crash on bad input.

## API

All request and response bodies are JSON with `Content-Type: application/json`.
All error responses have the shape `{"error": "<message>"}`.

### `GET /api/health`
- `200` -> `{"status": "ok"}`

### `POST /api/links`
Request body:
```json
{"url": "https://example.com/page", "alias": "optional-custom", "expires_in": 3600}
```
- `url` (required): must parse as an absolute URL with scheme `http` or `https`.
  Any other scheme (`javascript:`, `data:`, `file:`, `ftp:`) is rejected.
- `alias` (optional): must match `^[A-Za-z0-9_-]{3,32}$`.
- `expires_in` (optional): positive integer, seconds from now.

Responses:
- `201` -> `{"code": "<code>", "url": "<original url>", "short_url": "http://localhost:<port>/<code>"}`
- `400` if `url` is missing, empty, not a string, unparseable, or has a disallowed scheme.
- `400` if `alias` is present but does not match the pattern.
- `400` if `expires_in` is present but is not a positive integer.
- `400` if the body is not valid JSON.
- `409` if `alias` is already in use.

When `alias` is omitted, generate a unique 7-character code from
`[A-Za-z0-9]`. Codes must not collide with existing codes.

### `GET /<code>`
- `302` with a `Location` header equal to the original URL. Body may be empty.
- Increments that link's click counter by exactly 1, atomically.
- `404` -> `{"error": "..."}` if the code does not exist.
- `410` -> `{"error": "..."}` if the link exists but has expired.
  An expired link does NOT increment its click counter.

### `GET /api/links/<code>`
- `200` -> `{"code": ..., "url": ..., "clicks": <int>, "created_at": <int unix ts>, "expires_at": <int unix ts or null>}`
- `404` if unknown. Does NOT increment the click counter.

### `DELETE /api/links/<code>`
- `204` with an empty body.
- `404` if unknown.
- After deletion, `GET /<code>` returns `404`.

### Anything else
- `404` for unknown paths, `405` for a known path with the wrong method.

## Correctness notes

- The click counter must be exact under concurrent load: 50 simultaneous
  redirects on one code must produce `clicks == 50`.
- SQL must be parameterised. A url or alias containing `'; DROP TABLE ...` must be
  stored and returned verbatim without affecting the database.
- Reserved prefix: `/api/...` is never a short code.
