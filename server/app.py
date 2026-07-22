"""Stdlib HTTP service for headless LayoutLab Core (DD-014 + agent tools).

Endpoints:
  GET  /health
  POST /v1/commands
  POST /v1/undo
  POST /v1/redo
  POST /v1/preview/begin
  POST /v1/preview/update
  POST /v1/preview/commit
  POST /v1/preview/cancel
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
from layoutlab.runtime.chat import (  # noqa: E402
    llm_configured,
    plan_from_message,
    sanitize_commands,
)
from layoutlab.runtime.session import RoomSession  # noqa: E402
from layoutlab.runtime import session_log  # noqa: E402
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
                    "core_version": session_log.core_version_string(),
                    "slice": "room+generators+analyze+agent_tools_0.5+transactions",
                    "chat": "llm" if llm_configured() else "demo",
                    "tools": sorted(TOOL_NAMES),
                    "session_log": str(session_log.MARKDOWN_PATH),
                    "revision": SESSION.revision,
                    "can_undo": SESSION.can_undo,
                    "can_redo": SESSION.can_redo,
                },
            )
            return
        if path in ("/v1/session/log", "/v1/session/log/"):
            self._json(200, session_log.latest_summary())
            return
        self._json(404, {"ok": False, "error": f"not found: {path}"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = _read_json(self)
        except json.JSONDecodeError as exc:
            self._json(400, {"ok": False, "error": f"invalid JSON: {exc}"})
            return

        if path == "/v1/session/reset":
            reason = body.get("reason") if isinstance(body, dict) else None
            clear_scene = True
            if isinstance(body, dict) and "clear_scene" in body:
                clear_scene = bool(body.get("clear_scene"))
            if clear_scene:
                SESSION.clear()
            sid = session_log.start_session(
                label="core",
                reason=str(reason) if reason else "session_reset",
            )
            self._json(
                200,
                {
                    "ok": True,
                    "session_id": sid,
                    "core_version": session_log.core_version_string(),
                    "cleared_scene": clear_scene,
                    "session_log": str(session_log.MARKDOWN_PATH),
                    "revision": SESSION.revision,
                    "can_undo": SESSION.can_undo,
                    "can_redo": SESSION.can_redo,
                },
            )
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
                session_log.log_event(
                    "agent_turn_error",
                    user_message=str(message),
                    error=str(exc),
                )
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
            try:
                session_log.log_agent_turn(
                    message=str(message),
                    history_len=len(history or []),
                    result=result,
                )
            except Exception:
                pass
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
                commands = sanitize_commands(commands)
            except ValueError as exc:
                self._json(400, {"ok": False, "error": str(exc)})
                return
            actor = body.get("actor") if isinstance(body, dict) else None
            action = body.get("action") if isinstance(body, dict) else None
            description = body.get("description") if isinstance(body, dict) else None
            base_revision = body.get("base_revision") if isinstance(body, dict) else None
            if base_revision is not None:
                try:
                    base_revision = int(base_revision)
                except (TypeError, ValueError):
                    self._json(
                        400,
                        {"ok": False, "error": "base_revision must be an integer", "error_code": "invalid_base_revision"},
                    )
                    return
            # Default: AI when base_revision is present (proposal Apply); else user.
            if not actor:
                actor = "ai" if base_revision is not None else "user"
            try:
                result = SESSION.commit_commands(
                    commands,
                    actor=str(actor),
                    action=str(action or "commands"),
                    description=str(description or ""),
                    base_revision=base_revision,
                )
            except Exception as exc:
                session_log.log_event("apply_error", error=str(exc), command_count=len(commands))
                self._json(500, {"ok": False, "error": str(exc)})
                return
            try:
                session_log.log_apply(commands=commands, result=result, source="v1/commands")
            except Exception:
                pass
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/undo":
            try:
                result = SESSION.undo()
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            try:
                session_log.log_event(
                    "undo",
                    ok=bool(result.get("ok")),
                    revision=result.get("revision"),
                    error_code=result.get("error_code"),
                )
            except Exception:
                pass
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/redo":
            try:
                result = SESSION.redo()
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            try:
                session_log.log_event(
                    "redo",
                    ok=bool(result.get("ok")),
                    revision=result.get("revision"),
                    error_code=result.get("error_code"),
                )
            except Exception:
                pass
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/preview/begin":
            commands = body.get("commands") if isinstance(body, dict) else None
            if commands is not None and not isinstance(commands, list):
                self._json(400, {"ok": False, "error": '"commands" must be a list when provided'})
                return
            if isinstance(commands, list):
                try:
                    commands = sanitize_commands(commands)
                except ValueError as exc:
                    self._json(400, {"ok": False, "error": str(exc)})
                    return
            actor = (body.get("actor") if isinstance(body, dict) else None) or "user"
            description = (body.get("description") if isinstance(body, dict) else None) or ""
            try:
                result = SESSION.begin_preview(
                    commands,
                    actor=str(actor),
                    description=str(description),
                )
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/preview/update":
            commands = body.get("commands") if isinstance(body, dict) else None
            if not isinstance(commands, list):
                self._json(400, {"ok": False, "error": 'body must include "commands": [...]'})
                return
            try:
                commands = sanitize_commands(commands)
            except ValueError as exc:
                self._json(400, {"ok": False, "error": str(exc)})
                return
            try:
                result = SESSION.update_preview(commands)
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/preview/commit":
            action = body.get("action") if isinstance(body, dict) else None
            description = body.get("description") if isinstance(body, dict) else None
            try:
                result = SESSION.commit_preview(
                    action=str(action) if action else None,
                    description=str(description) if description is not None else None,
                )
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            try:
                session_log.log_apply(
                    commands=(result.get("transaction") or {}).get("operations") or [],
                    result=result,
                    source="v1/preview/commit",
                )
            except Exception:
                pass
            status = 200 if result.get("ok") else 400
            self._json(status, result)
            return

        if path == "/v1/preview/cancel":
            try:
                result = SESSION.cancel_preview()
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            self._json(200, result)
            return

        self._json(404, {"ok": False, "error": f"not found: {path}"})


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    sid = session_log.start_session(label="core")
    server = ThreadingHTTPServer((host, port), Handler)
    mode = "llm" if llm_configured() else "demo"
    print(f"LayoutLab Core {session_log.core_version_string()} listening on http://{host}:{port}", flush=True)
    print(f"  session log: {session_log.MARKDOWN_PATH} ({sid})", flush=True)
    print("  GET  /health", flush=True)
    print("  GET  /v1/session/log", flush=True)
    print("  POST /v1/session/reset", flush=True)
    print("  POST /v1/commands", flush=True)
    print("  POST /v1/undo", flush=True)
    print("  POST /v1/redo", flush=True)
    print("  POST /v1/preview/{begin,update,commit,cancel}", flush=True)
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
