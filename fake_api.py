"""A tiny fake API for trying out Contract Watch locally.

Run this in a SEPARATE terminal (with run.py still running in the first
one). It serves one endpoint, GET /api/users/1, on port 5001.

Edit BODY below and restart this script to simulate a backend change
(e.g. rename "user_id" to "userId") and see Contract Watch catch it.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

BODY = {"user_id": 1, "name": "Souvik", "email": "souvik@example.com"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(BODY).encode())


if __name__ == "__main__":
    print("Fake API running on http://localhost:5001/api/users/1")
    HTTPServer(("127.0.0.1", 5001), Handler).serve_forever()
