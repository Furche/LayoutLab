"""Stdlib HTTP service for headless LayoutLab Core (DD-014).

Endpoints:
  GET  /health
  POST /v1/commands  body: { "commands": [ ... ] }
  POST /v1/chat      body: { "message": "...", "scene"?: {...} } → proposed commands (no apply)

CORS allows the Vite viewer on localhost:5173.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from layoutlab.runtime.chat import llm_configured, plan_from_message  # noqa: E402
from layoutlab.runtime.session import RoomSession  # noqa: E402

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

SESSION = RoomSession()


def _cors_origin(handler: BaseHTTPRequestHandler) -> str:
    origin = handler.headers.get("Origin", "")
    if origin in CORS_ORIGINS:
        return origin
    return CORS_ORIGINS[0]


def _read_json(handler: BaseHTTPRequestHandler):
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


class Handler(BaseHTTPRequestHandler):
    server_version = "LayoutLabCore/0.2"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/health", "/health/"):
            self._json(
                200,
                {
                    "ok": True,
                    "service": "layoutlab-core",
                    "slice": "room_write+generators+analyze+chat",
                    "chat": "llm" if llm_configured() else "demo",
                },
            )
            return
        self._json(404, {"ok": False, "error": f"not found: {path}"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = _read_json(self)
        except json.JSONDecodeError as exc:
            self._json(400, {"ok": False, "error": f"invalid JSON: {exc}"})
            return

        if path in ("/v1/chat", "/v1/chat/"):
            message = body.get("message") or body.get("prompt") or ""
            scene = body.get("scene")
            try:
                result = plan_from_message(str(message), scene_summary=scene if isinstance(scene, dict) else None)
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc), "commands": [], "reply": ""})
                return
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path in ("/v1/commands", "/v1/commands/"):
            commands = body.get("commands")
            if commands is None and isinstance(body, list):
                commands = body
            if not isinstance(commands, list):
                self._json(400, {"ok": False, "error": 'body must include "commands": [...]'})
                return
            try:
                result = SESSION.apply_commands(commands)
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        self._json(404, {"ok": False, "error": f"not found: {path}"})


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    server = ThreadingHTTPServer((host, port), Handler)
    mode = "llm" if llm_configured() else "demo"
    print(f"LayoutLab Core listening on http://{host}:{port}", flush=True)
    print("  GET  /health", flush=True)
    print("  POST /v1/commands", flush=True)
    print(f"  POST /v1/chat  (mode={mode})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
