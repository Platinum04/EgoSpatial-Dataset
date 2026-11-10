"""Minimal dependency-free HTTP/JSON API so any XR client (Unity, WebXR, Android XR) can call the engine.

    python -m egospatial.server --host 0.0.0.0 --port 8765

Endpoints (all JSON):
  GET  /health                         -> {"status": "ok", "version": ...}
  POST /ask        {"state": {...}, "question": "..."}           -> SpatialEngine.ask(...)
  POST /evaluate   {"state": {...}, "query": {"op","target","reference"}}
  POST /relations  {"state": {...}}                              -> all object-to-agent relations
CORS is enabled so a WebXR page can call a local engine during development.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .orchestrator import SpatialEngine
from .query import Query
from .relations import all_relations
from .state import SpatialState, SpatialStateError

ENGINE = SpatialEngine()


def handle(path: str, body: dict) -> tuple:
    try:
        if path == "/ask":
            return 200, ENGINE.ask(body["state"], body["question"])
        state = SpatialState.from_dict(body["state"])
        if path == "/evaluate":
            q = body["query"]
            return 200, {"status": "ok", "result": ENGINE.evaluate(state, Query(q["op"], q["target"], q.get("reference", "agent")))}
        if path == "/relations":
            return 200, {"status": "ok", "source": state.source, "relations": all_relations(state)}
        return 404, {"status": "error", "error": f"unknown endpoint {path}"}
    except (SpatialStateError, ValueError) as e:
        return 400, {"status": "error", "error": str(e)}
    except KeyError as e:
        return 400, {"status": "error", "error": f"missing field {e}"}


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "version": __version__})
        else:
            self._send(404, {"status": "error", "error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send(400, {"status": "error", "error": f"invalid JSON body: {e}"})
        self._send(*handle(self.path, body))

    def log_message(self, *a):  # quiet
        pass


def serve(host="127.0.0.1", port=8765):
    srv = ThreadingHTTPServer((host, port), _Handler)
    print(f"EgoSpatial engine {__version__} listening on http://{host}:{port}")
    srv.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    serve(a.host, a.port)
