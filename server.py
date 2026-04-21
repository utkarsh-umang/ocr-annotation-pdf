#!/usr/bin/env python3
"""
OCR Engine — local proxy server.

Serves index.html and forwards POST /api/ocr to the Nanonets API,
keeping the API key on the server side so it never touches the browser.

Usage:
    pip install requests   (one-time)
    python3 server.py
Then open http://localhost:8765
"""
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed.\nRun:  pip install requests")
    sys.exit(1)

from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Load .env without requiring python-dotenv ─────────────────────────────
def _load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_env()

API_KEY      = os.environ.get("NANONETS_API_KEY", "")
NANONETS_URL = "https://extraction-api.nanonets.com/api/v1/extract/sync"
PORT         = 8765

if not API_KEY:
    print("WARNING: NANONETS_API_KEY not found in .env — OCR calls will fail.")


# ── Request handler ───────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {fmt % args}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    # Pre-flight
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # Serve index.html
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open("index.html", "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._cors()
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self._text(404, "index.html not found")
        else:
            self._text(404, "Not found")

    # Proxy OCR call
    def do_POST(self):
        if self.path != "/api/ocr":
            self._text(404, "Not found")
            return

        content_type   = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        body           = self.rfile.read(content_length)

        print(f"  → Forwarding to Nanonets ({content_length:,} bytes)…")

        try:
            resp = requests.post(
                NANONETS_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type":  content_type,   # must include multipart boundary
                },
                data=body,
                timeout=180,
            )
        except requests.exceptions.Timeout:
            self._text(504, "Nanonets request timed out")
            return
        except requests.exceptions.RequestException as e:
            self._text(502, f"Upstream error: {e}")
            return

        print(f"  ← Nanonets {resp.status_code}")

        resp_body = resp.content
        self.send_response(resp.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_body)))
        self._cors()
        self.end_headers()
        self.wfile.write(resp_body)

    def _text(self, code, msg):
        body = msg.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── Entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"\n  OCR Engine → http://localhost:{PORT}\n  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
