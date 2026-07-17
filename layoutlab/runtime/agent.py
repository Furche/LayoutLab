"""Agent turn: tool calling → structured proposal (agent_tools 0.1)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import uuid

from .chat import (
    demo_plan,
    llm_configured,
    resolve_llm_settings,
    sanitize_commands,
)
from .tools import dispatch_tool, openai_tool_definitions

AGENT_SYSTEM_PROMPT = """You are LayoutLab's planning agent (DD-009 / agent_tools 0.1).
AI decides WHAT; LayoutLab Core executes HOW. You invent no meshes, bpy, or free Python.

Workflow:
1. Use at most a few tools (prefer get_scene_summary, then get_room / list_objects only if needed).
2. Do NOT keep calling tools in a loop. After you understand the room, STOP tools and output the final JSON.
3. Ask clarifying questions ONLY if size/placement is still unknown. If the user already answered, do NOT ask again — emit complete commands.
4. Finish with ONLY a JSON object (no markdown fences):
{
  "reply": "short explanation in the user's language",
  "questions": [],
  "proposal": {
    "proposal_id": "uuid-or-string",
    "title": "short title",
    "rationale": "why this plan",
    "assumes": [],
    "commands": [ /* full LayoutLab commands */ ],
    "expected_risks": []
  },
  "suggested_next_tools": []
}

Completeness (critical):
- If the user wants a room WITH a door/window, commands MUST include add_opening (not only create_room).
- If the user wants a bed/desk/wardrobe, commands MUST include run_generator for that item.
- Never say you will place furniture/openings unless those commands are in proposal.commands.
- Fresh layout sequence typically:
  1) delete_collection_objects collection=layoutlab_room
  2) create_room (width/depth/height in meters, collection=layoutlab_room)
  3) add_opening for door/window (wall_side, offset, width, height, sill_height for windows)
  4) run_generator e.g. bed_basic with location so the bed sits near the door wall but does not block the opening.

Example fragment (door on east, bed near east wall):
{"action":"add_opening","params":{"room":"ROOM","opening_name":"door_east","kind":"door","wall_side":"east","offset":0.3,"width":0.9,"height":2.0}}
{"action":"run_generator","generator":"bed_basic","params":{"name":"BED","location":[1.0,0.15,0],"length":1.2,"width":2.0,"head_side":"y_max","collection":"layoutlab_room"}}

Rules:
- Prefer Metric meters (1 unit = 1 m). width = X, depth = Y.
- Generators: bed_basic, desk_basic, wardrobe_basic only.
- Do not claim you applied changes — the user must Apply.
- If you only need questions, set proposal.commands to [] AND leave questions non-empty.
"""

MAX_TOOL_ROUNDS = 5
REPAIR_HINT = (
    "Your previous proposal was incomplete for the user's request. "
    "Return ONLY a new JSON proposal whose commands include ALL required parts "
    "(create_room AND add_opening for doors/windows AND run_generator for furniture). "
    "questions must be []. No markdown, no tools."
)


def _user_wants_bed(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("bett", "bed"))


def _user_wants_door(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("tür", "tur", "door", "eingang"))


def _user_wants_room(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("raum", "zimmer", "room", "erstell"))


def _conversation_text(message: str, history: list | None) -> str:
    parts = [message or ""]
    for item in history or []:
        if isinstance(item, dict) and item.get("role") == "user":
            parts.append(str(item.get("content") or ""))
    return "\n".join(parts)


def _proposal_missing_requested(conversation: str, commands: list) -> list:
    """Return list of missing requirement labels for a repair turn."""
    missing = []
    actions = [c.get("action") for c in commands]
    gens = [c.get("generator") for c in commands if c.get("action") == "run_generator"]
    if _user_wants_room(conversation) and "create_room" not in actions:
        missing.append("create_room")
    if _user_wants_door(conversation) and "add_opening" not in actions:
        missing.append("add_opening (door)")
    if _user_wants_bed(conversation) and "bed_basic" not in gens:
        missing.append("run_generator bed_basic")
    # Furniture/door requested but only empty shell
    if (_user_wants_bed(conversation) or _user_wants_door(conversation)) and commands:
        if "create_room" in actions and "add_opening" not in actions and "run_generator" not in actions:
            if "add_opening (door)" not in missing and _user_wants_door(conversation):
                missing.append("add_opening (door)")
            if "run_generator bed_basic" not in missing and _user_wants_bed(conversation):
                missing.append("run_generator bed_basic")
    return missing


def _finalize_proposal_from_messages(
    settings: dict,
    messages: list,
    tool_trace: list,
    *,
    repair_note: str | None = None,
) -> dict:
    """Force one JSON-only completion after tools (or when the model loops)."""
    force_msgs = list(messages)
    content = repair_note or (
        "Stop calling tools. Using the tool results and conversation already available, "
        "return ONLY a COMPLETE final JSON proposal now (no markdown, no tools). "
        "If the user asked for a door and bed, commands MUST include add_opening and "
        "run_generator bed_basic, not only create_room."
    )
    force_msgs.append({"role": "user", "content": content})
    raw = _chat_completions(settings, force_msgs, tools=None)
    text = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    parsed = _extract_json_object(text)
    normalized = _normalize_proposal(parsed)
    return {
        "ok": True,
        "mode": "agent",
        "model": settings["model"],
        "reply": normalized["reply"],
        "questions": normalized["questions"],
        "proposal": normalized["proposal"],
        "suggested_next_tools": normalized["suggested_next_tools"],
        "commands": normalized["proposal"]["commands"],
        "tool_trace": tool_trace,
    }


def _maybe_repair_proposal(settings, messages, result, conversation: str) -> dict:
    commands = result.get("commands") or []
    questions = result.get("questions") or []
    # If still asking questions and no commands, leave as-is.
    if questions and not commands:
        return result
    missing = _proposal_missing_requested(conversation, commands)
    if not missing:
        return result
    note = REPAIR_HINT + " Missing: " + ", ".join(missing) + "."
    repaired = _finalize_proposal_from_messages(
        settings, messages, result.get("tool_trace") or [], repair_note=note
    )
    # Prefer repaired if it covers more; else keep original
    if len(repaired.get("commands") or []) >= len(commands):
        return repaired
    return result


def _tool_call_fingerprint(tool_calls: list) -> str:
    parts = []
    for call in tool_calls:
        fn = call.get("function") or {}
        parts.append(f"{fn.get('name')}:{(fn.get('arguments') or '').strip()}")
    return "|".join(parts)


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
        raise ValueError("model response did not contain a JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _normalize_proposal(parsed: dict) -> dict:
    proposal = parsed.get("proposal")
    if not isinstance(proposal, dict):
        proposal = {}
    commands = sanitize_commands(proposal.get("commands") or parsed.get("commands") or [])
    proposal_id = proposal.get("proposal_id") or str(uuid.uuid4())
    return {
        "reply": str(parsed.get("reply") or "Vorschlag bereit.").strip(),
        "questions": list(parsed.get("questions") or []),
        "proposal": {
            "proposal_id": proposal_id,
            "title": str(proposal.get("title") or "Vorschlag").strip(),
            "rationale": str(proposal.get("rationale") or "").strip(),
            "assumes": list(proposal.get("assumes") or []),
            "commands": commands,
            "expected_risks": list(proposal.get("expected_risks") or []),
        },
        "suggested_next_tools": list(parsed.get("suggested_next_tools") or []),
    }


def _demo_as_agent_result(message: str) -> dict | None:
    demo = demo_plan(message)
    if not demo:
        return None
    commands = sanitize_commands(demo.get("commands") or [])
    return {
        "ok": True,
        "mode": "demo",
        "reply": demo.get("reply") or "",
        "questions": [],
        "proposal": {
            "proposal_id": str(uuid.uuid4()),
            "title": "Demo-Intent",
            "rationale": "Keyword demo without LLM tools",
            "assumes": [],
            "commands": commands,
            "expected_risks": [],
        },
        "suggested_next_tools": [],
        "commands": commands,  # convenience for existing Apply UI
        "tool_trace": [],
    }


def _chat_completions(settings: dict, messages: list, *, tools=None, tool_choice=None) -> dict:
    body = {
        "model": settings["model"],
        "temperature": 0.2,
        "messages": messages,
    }
    if tools is not None:
        body["tools"] = tools
        body["tool_choice"] = tool_choice or "auto"
    else:
        body["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{settings['base_url']}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM unreachable: {exc.reason}") from exc


def run_agent_turn(session, message: str, *, llm_config: dict | None = None, history: list | None = None) -> dict:
    """Run one user message through tools (if LLM) → structured proposal.

    Never mutates session via proposal commands.
    """
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "message required", "commands": [], "reply": ""}

    if not llm_configured(llm_config):
        demo = _demo_as_agent_result(message)
        if demo:
            return demo
        return {
            "ok": True,
            "mode": "demo",
            "reply": (
                "Kein LLM-Key. Unter LLM-Einstellungen einen Key setzen, "
                "oder Demo-Intents nutzen (empty/furnished kids room, schrank, lösche den raum, analyze)."
            ),
            "questions": [],
            "proposal": {
                "proposal_id": str(uuid.uuid4()),
                "title": "",
                "rationale": "",
                "assumes": [],
                "commands": [],
                "expected_risks": [],
            },
            "suggested_next_tools": ["get_scene_summary"],
            "commands": [],
            "tool_trace": [],
        }

    settings = resolve_llm_settings(llm_config)
    tools = openai_tool_definitions()
    conversation = _conversation_text(message, history)
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
    ]
    # Optional prior turns (user/assistant text only — no huge tool dumps)
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()})
    messages.append({"role": "user", "content": message})

    tool_trace = []
    seen_tool_fps = set()
    try:
        for round_i in range(MAX_TOOL_ROUNDS):
            # Last round: disallow tools so the model must answer.
            use_tools = tools if round_i < MAX_TOOL_ROUNDS - 1 else None
            raw = _chat_completions(
                settings,
                messages,
                tools=use_tools,
                tool_choice="auto" if use_tools else None,
            )
            choice = (raw.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            tool_calls = msg.get("tool_calls") or []

            if tool_calls and use_tools:
                fp = _tool_call_fingerprint(tool_calls)
                if fp in seen_tool_fps:
                    result = _finalize_proposal_from_messages(settings, messages, tool_trace)
                    return _maybe_repair_proposal(settings, messages, result, conversation)
                seen_tool_fps.add(fp)

                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.get("content"),
                        "tool_calls": tool_calls,
                    }
                )
                for call in tool_calls:
                    fn = call.get("function") or {}
                    name = fn.get("name") or ""
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    try:
                        result = dispatch_tool(session, name, args)
                        err = None
                    except Exception as exc:
                        result = {"ok": False, "error": str(exc)}
                        err = str(exc)
                    tool_trace.append({"tool": name, "arguments": args, "ok": err is None, "error": err})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id") or name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue

            # No tool calls — parse JSON proposal
            content = msg.get("content") or ""
            try:
                parsed = _extract_json_object(content)
            except Exception:
                result = _finalize_proposal_from_messages(settings, messages, tool_trace)
                return _maybe_repair_proposal(settings, messages, result, conversation)

            normalized = _normalize_proposal(parsed)
            result = {
                "ok": True,
                "mode": "agent",
                "model": settings["model"],
                "reply": normalized["reply"],
                "questions": normalized["questions"],
                "proposal": normalized["proposal"],
                "suggested_next_tools": normalized["suggested_next_tools"],
                "commands": normalized["proposal"]["commands"],
                "tool_trace": tool_trace,
            }
            return _maybe_repair_proposal(settings, messages, result, conversation)

        result = _finalize_proposal_from_messages(settings, messages, tool_trace)
        return _maybe_repair_proposal(settings, messages, result, conversation)
    except Exception as exc:
        demo = _demo_as_agent_result(message)
        if demo:
            demo["reply"] = f"(Agent/LLM fehlgeschlagen: {exc}) {demo['reply']}"
            demo["llm_error"] = str(exc)
            return demo
        return {
            "ok": False,
            "mode": "agent",
            "error": str(exc),
            "reply": f"Agent fehlgeschlagen: {exc}",
            "questions": [],
            "proposal": {
                "proposal_id": str(uuid.uuid4()),
                "title": "",
                "rationale": "",
                "assumes": [],
                "commands": [],
                "expected_risks": [],
            },
            "commands": [],
            "tool_trace": tool_trace,
        }
