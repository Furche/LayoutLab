"""Stdlib HTTP service for headless LayoutLab Core (DD-014 + agent tools).

Endpoints:
  GET  /health
  POST /v1/commands
  POST /v1/chat          (legacy thin chat)
  POST /v1/agent/turn    (tool-calling agent → proposal)
  POST /v1/tools/{name}  (deterministic read tools)

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

from layoutlab.runtime.agent import run_agent_turn  # noqa: E402
from layoutlab.runtime.chat import llm_configured, plan_from_message  # noqa: E402
from layoutlab.runtime.session import RoomSession  # noqa: E402
from layoutlab.runtime.tools import TOOL_NAMES, dispatch_tool  # noqa: E402

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
    server_version = "LayoutLabCore/0.3"

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
                    "slice": "room+generators+analyze+agent_tools_0.3",
                    "chat": "llm" if llm_configured() else "demo",
                    "tools": sorted(TOOL_NAMES),
                },
            )
            return
        self._json(404, {"ok": False, "error": f"not found: {path}"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = _read_json(self)
        except json.JSONDecodeError as exc:
            self._json(400, {"ok": False, "error": f"invalid JSON: {exc}"})
            return

        if path == "/v1/chat":
            message = body.get("message") or body.get("prompt") or ""
            scene = body.get("scene")
            llm = body.get("llm") if isinstance(body.get("llm"), dict) else None
            try:
                result = plan_from_message(
                    str(message),
                    scene_summary=scene if isinstance(scene, dict) else None,
                    llm_config=llm,
                )
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc), "commands": [], "reply": ""})
                return
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/agent/turn":
            message = body.get("message") or body.get("prompt") or ""
            llm = body.get("llm") if isinstance(body.get("llm"), dict) else None
            history = body.get("history") if isinstance(body.get("history"), list) else None
            try:
                result = run_agent_turn(SESSION, str(message), llm_config=llm, history=history)
            except Exception as exc:
                self._json(
                    500,
                    {
                        "ok": False,
                        "error": str(exc),
                        "commands": [],
                        "reply": "",
                        "proposal": {"commands": []},
                    },
                )
                return
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path.startswith("/v1/tools/"):
            name = path[len("/v1/tools/") :].strip("/")
            if not name:
                self._json(400, {"ok": False, "error": "tool name required"})
                return
            params = body.get("params") if isinstance(body.get("params"), dict) else body
            if not isinstance(params, dict):
                params = {}
            # Prefer explicit params key; if body is the params itself, drop reserved keys
            if "params" in body and isinstance(body.get("params"), dict):
                params = body["params"]
            elif isinstance(body, dict):
                params = {k: v for k, v in body.items() if k not in ("params",)}
            try:
                result = dispatch_tool(SESSION, name, params)
            except ValueError as exc:
                self._json(400, {"ok": False, "error": str(exc)})
                return
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            self._json(200, result)
            return

        if path == "/v1/commands":
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
    print(f"  POST /v1/agent/turn  (mode={mode})", flush=True)
    print("  POST /v1/tools/{name}", flush=True)
    print(f"  POST /v1/chat  (legacy, mode={mode})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
