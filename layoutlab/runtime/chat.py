"""Thin planning helper: natural language → LayoutLab commands (DD-009 / pre-DD-012).

Does not execute. Returns proposed ``commands`` for the client to Apply via Core.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"

# Actions the headless session can run (keep in sync with RoomSession).
ALLOWED_ACTIONS = frozenset(
    {
        "create_room",
        "update_room",
        "delete_room",
        "add_opening",
        "update_opening",
        "remove_opening",
        "add_fixed_element",
        "update_fixed_element",
        "remove_fixed_element",
        "delete_collection_objects",
        "delete_prefix",
        "run_generator",
        "analyze_layout",
    }
)

SYSTEM_PROMPT = """You are LayoutLab's planning assistant (DD-009).
You propose WHAT should happen. LayoutLab Core executes HOW.

Reply with ONLY a JSON object (no markdown fences):
{
  "reply": "short human explanation in the user's language",
  "commands": [ /* LayoutLab command objects */ ]
}

Allowed command actions only:
create_room, update_room, delete_room, add_opening, update_opening, remove_opening,
add_fixed_element, update_fixed_element, remove_fixed_element,
delete_collection_objects, delete_prefix, run_generator, analyze_layout.

Rules:
- Prefer Metric meters (1 unit = 1 m).
- For a fresh kids room, clear collection "layoutlab_room" first, then create_room.
- Generators: bed_basic, desk_basic, wardrobe_basic only.
- Do not invent bpy or free-form Python.
- If the request is unclear, return commands: [] and ask a clarifying question in reply.
- If scene context is provided, prefer updating that room rather than inventing a second space.
"""


def _load_fixture_commands(name: str) -> list:
    path = _FIXTURES / name
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("commands") or [])


def empty_kids_room_commands() -> list:
    return _load_fixture_commands("reference_kids_room_shell_commands.json")


def furnished_kids_room_commands() -> list:
    return _load_fixture_commands("reference_kids_room_commands.json")


def llm_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("LAYOUTLAB_LLM_API_KEY"))


def sanitize_commands(commands) -> list:
    if not isinstance(commands, list):
        raise ValueError("commands must be a list")
    cleaned = []
    for cmd in commands:
        if not isinstance(cmd, dict):
            raise ValueError("each command must be an object")
        action = cmd.get("action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"disallowed action {action!r}")
        cleaned.append(cmd)
    return cleaned


def demo_plan(message: str) -> dict | None:
    """Keyword intents for local demo without an LLM key."""
    text = (message or "").strip().lower()
    if not text:
        return None

    furnished_keys = (
        "furnished",
        "möbliert",
        "moebliert",
        "einrichten",
        "möbel",
        "moebel",
        "bett",
        "schreibtisch",
        "bed and desk",
        "kids room with",
    )
    empty_keys = (
        "empty",
        "leer",
        "shell",
        "nur raum",
        "nur den raum",
        "create room",
        "raum anlegen",
        "kids room",
        "kinderzimmer",
    )

    if any(k in text for k in furnished_keys):
        return {
            "ok": True,
            "mode": "demo",
            "reply": (
                "Vorschlag: leeres Kids-Room-Shell löschen/neu anlegen und Bett + Schreibtisch "
                "platzieren. Bitte Apply, um Core auszuführen."
            ),
            "commands": furnished_kids_room_commands(),
        }

    if any(k in text for k in empty_keys):
        return {
            "ok": True,
            "mode": "demo",
            "reply": (
                "Vorschlag: Kids-Room-Schale (Wände, Fenster, Tür, Heizung) ohne Möbel. "
                "Bitte Apply, um Core auszuführen."
            ),
            "commands": empty_kids_room_commands(),
        }

    if any(k in text for k in ("analyze", "analys", "prüfung", "pruefung", "findings", "clearance")):
        return {
            "ok": True,
            "mode": "demo",
            "reply": "Vorschlag: analyze_layout auf der aktuellen Session. Apply ausführen.",
            "commands": [{"action": "analyze_layout", "scope": "scene", "include": ["clearances"]}],
        }

    return None


def _extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("LLM response did not contain a JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM JSON root must be an object")
    return data


def _openai_compatible_plan(message: str, scene_summary: dict | None) -> dict:
    api_key = os.environ.get("LAYOUTLAB_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("no LLM API key configured")

    base = (os.environ.get("LAYOUTLAB_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LAYOUTLAB_LLM_MODEL") or "gpt-4o-mini"

    user_payload = {"message": message}
    if scene_summary:
        user_payload["scene"] = scene_summary

    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM unreachable: {exc.reason}") from exc

    content = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    parsed = _extract_json_object(content)
    commands = sanitize_commands(parsed.get("commands") or [])
    reply = str(parsed.get("reply") or "Vorschlag bereit.").strip()
    return {
        "ok": True,
        "mode": "llm",
        "model": model,
        "reply": reply,
        "commands": commands,
    }


def plan_from_message(message: str, scene_summary: dict | None = None) -> dict:
    """Return ``{ ok, mode, reply, commands }`` — never applies commands."""
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "message required", "commands": [], "reply": ""}

    # Prefer LLM when configured; demo keywords remain as fallback / offline path.
    if llm_configured():
        try:
            return _openai_compatible_plan(message, scene_summary)
        except Exception as exc:
            demo = demo_plan(message)
            if demo:
                demo["reply"] = f"(LLM fehlgeschlagen: {exc}) {demo['reply']}"
                demo["llm_error"] = str(exc)
                return demo
            return {
                "ok": False,
                "error": str(exc),
                "mode": "llm",
                "reply": f"Planung fehlgeschlagen: {exc}",
                "commands": [],
            }

    demo = demo_plan(message)
    if demo:
        return demo

    return {
        "ok": True,
        "mode": "demo",
        "reply": (
            "Kein LLM-Key gesetzt (OPENAI_API_KEY oder LAYOUTLAB_LLM_API_KEY). "
            "Demo-Intents: „empty kids room“, „furnished kids room“, „analyze“. "
            "Oder Key setzen für freie Planung."
        ),
        "commands": [],
    }
