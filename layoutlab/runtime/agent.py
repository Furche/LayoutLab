"""Agent turn: tool calling → structured proposal (agent_tools 0.3)."""

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

AGENT_SYSTEM_PROMPT = """You are LayoutLab's planning agent (DD-009 / DD-015 / agent_tools 0.3).
AI decides WHAT; LayoutLab Core executes HOW. You invent no meshes, bpy, or free Python.

Role (compassionate planner):
- Work in the user's interest: rooms should feel comfortable AND be practically usable.
- Prefer free floor, light, and door/window access over packing like a warehouse.
- Gather missing context with a few bundled questions when size, use, or priorities are unclear.
  If the user already answered or said you may choose, document defaults in proposal.assumes — do not ask again.
- Soft metrics (packing density, opening_access) are comfort/usability proxies from Core — treat warnings seriously.

Context:
- A scene seed (get_scene_summary + list_generators) is already injected — trust it.
- Call get_room / list_objects only when you need details the seed lacks.
- Before a non-empty final proposal, prefer validate_commands then dry_run_commands.
- On soft warnings (soft_packing, opening_access): replan if possible.
- On hard clearance errors: try alternatives first.
- If a compromise is unavoidable (e.g. wardrobe blocks full door swing): keep the proposal,
  explain the tradeoff in reply, and fill proposal.expected_risks (human language). Never hide it.
- dry_run does NOT commit — the user must Apply (Apply = consent to documented risks).

Workflow:
1. Read the seed. Use at most a few extra tools if needed.
2. Think zones (sleep / work / storage / circulation) before placing furniture.
3. Do NOT loop tools forever. After you understand the plan, STOP tools and output final JSON.
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
- If the user wants a door, commands MUST include add_opening with kind "door".
- If the user wants N windows, commands MUST include N add_opening with kind "window"
  (and sill_height, typically ~0.8–1.0 m). A door alone does NOT satisfy windows.
- If the user wants a bed/desk/wardrobe, commands MUST include run_generator for that item.
- Never say you will place furniture/openings unless those commands are in proposal.commands.
- Fresh layout sequence typically:
  1) delete_collection_objects collection=layoutlab_room
  2) create_room (width/depth/height in meters, collection=layoutlab_room)
  3) add_opening for EACH door and EACH window
  4) run_generator for each furniture item (leave circulation; do not block openings)

Example openings:
{"action":"add_opening","params":{"room":"ROOM","opening_name":"door_east","kind":"door","wall_side":"east","offset":0.3,"width":0.9,"height":2.0}}
{"action":"add_opening","params":{"room":"ROOM","opening_name":"win_south_1","kind":"window","wall_side":"south","offset":0.5,"width":1.2,"height":1.2,"sill_height":0.9}}
{"action":"run_generator","generator":"bed_basic","params":{"name":"BED","location":[1.0,0.15,0],"length":1.2,"width":2.0,"head_side":"y_max","collection":"layoutlab_room"}}

Rules:
- Prefer Metric meters (1 unit = 1 m). width = X, depth = Y.
- Generators: bed_basic, desk_basic, wardrobe_basic only.
- Do not claim you applied changes — the user must Apply.
- If you only need questions, set proposal.commands to [] AND leave questions non-empty.
"""

MAX_TOOL_ROUNDS = 6
REPAIR_HINT = (
    "Your previous proposal was incomplete for the user's request. "
    "Return ONLY a new JSON proposal whose commands include ALL required parts "
    "(create_room, add_opening kind=door, add_opening kind=window for EACH requested window "
    "with sill_height, and run_generator for furniture). "
    "A door does not replace windows. questions must be []. No markdown, no tools."
)

_WORD_COUNTS = {
    "ein": 1,
    "eine": 1,
    "einem": 1,
    "einen": 1,
    "einer": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "fuenf": 5,
    "sechs": 6,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


def _user_wants_bed(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("bett", "bed"))


def _user_wants_door(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("tür", "tur", "door", "eingang"))


def _user_wants_room(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("raum", "zimmer", "room", "erstell", "bau"))


def _count_requested_noun(text: str, nouns: tuple[str, ...]) -> int:
    """Best-effort count for 'zwei fenster' / '2 windows' / bare 'fenster' → 1."""
    t = text.lower()
    best = 0
    for noun in nouns:
        npat = re.escape(noun)
        scored = []
        for m in re.finditer(rf"(\d+)\s*x?\s*{npat}\b", t):
            scored.append(max(1, int(m.group(1))))
        for word, n in _WORD_COUNTS.items():
            if re.search(rf"\b{re.escape(word)}\s+{npat}\b", t):
                scored.append(n)
        if scored:
            best = max(best, sum(scored))
        elif re.search(rf"\b{npat}\b", t):
            best = max(best, 1)
    return best


def _requested_window_count(text: str) -> int:
    return _count_requested_noun(text, ("fenstern", "fenster", "windows", "window"))


def _opening_kind_counts(commands: list) -> tuple[int, int]:
    doors = 0
    windows = 0
    for cmd in commands or []:
        if cmd.get("action") != "add_opening":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        kind = str(params.get("kind") or cmd.get("kind") or "").lower()
        if kind == "window":
            windows += 1
        elif kind == "door":
            doors += 1
    return doors, windows


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
    doors, windows = _opening_kind_counts(commands)
    want_windows = _requested_window_count(conversation)

    if _user_wants_room(conversation) and "create_room" not in actions:
        missing.append("create_room")
    if _user_wants_door(conversation) and doors < 1:
        missing.append("add_opening kind=door")
    if want_windows > windows:
        missing.append(f"add_opening kind=window x{want_windows} (have {windows})")
    if _user_wants_bed(conversation) and "bed_basic" not in gens:
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
        "Include every requested door (kind=door) and every requested window "
        "(kind=window + sill_height), plus furniture generators — not only create_room."
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
    repaired_cmds = repaired.get("commands") or []
    still_missing = _proposal_missing_requested(conversation, repaired_cmds)
    # Prefer repaired if it closes more gaps (or adds commands when still incomplete).
    if len(still_missing) < len(missing):
        return repaired
    if not still_missing:
        return repaired
    if len(repaired_cmds) > len(commands):
        return repaired
    return result


def _attach_quality_preview(session, result: dict) -> dict:
    """Dry-run final proposal commands for hard/soft findings (live session unchanged)."""
    commands = result.get("commands") or []
    if not commands:
        return result
    try:
        dry = dispatch_tool(
            session,
            "dry_run_commands",
            {"commands": commands, "analyze": True, "stop_on_invalid": False},
        )
    except Exception as exc:
        result["quality"] = {"ok": False, "error": str(exc)}
        return result

    analysis = dry.get("analysis") or {}
    summary = analysis.get("summary") or {}
    soft = dry.get("soft_summary") or analysis.get("soft_summary") or {}
    hard_errors = int(summary.get("errors") or 0)
    soft_warnings = int(soft.get("warnings") or 0)
    risks = list((result.get("proposal") or {}).get("expected_risks") or [])
    result["quality"] = {
        "ok": bool(dry.get("ok")),
        "apply_ok": bool(dry.get("apply_ok")),
        "summary": summary,
        "soft_summary": soft,
        "findings": analysis.get("findings") or [],
        "has_hard_errors": hard_errors > 0,
        "has_soft_warnings": soft_warnings > 0,
        "has_expected_risks": len(risks) > 0,
        "needs_user_confirm": hard_errors > 0 or soft_warnings > 0 or len(risks) > 0,
    }
    # Nudge reply if hard errors without documented risks
    if hard_errors > 0 and not risks:
        note = (
            " Hinweis: Dry-Run meldet noch harte Clearance-Fehler — "
            "bitte Tradeoff prüfen oder umplanen (expected_risks setzen wenn Kompromiss)."
        )
        result["reply"] = (result.get("reply") or "").rstrip() + note
    return result


def _tool_call_fingerprint(tool_calls: list) -> str:
    parts = []
    for call in tool_calls:
        fn = call.get("function") or {}
        parts.append(f"{fn.get('name')}:{(fn.get('arguments') or '').strip()}")
    return "|".join(parts)


def _inject_scene_seed(session, messages: list, tool_trace: list) -> None:
    """Prepend authoritative Core seed as synthetic tool results (no LLM round)."""
    seeds = (
        ("seed_scene_summary", "get_scene_summary", {}),
        ("seed_list_generators", "list_generators", {}),
    )
    tool_calls = []
    tool_msgs = []
    for call_id, name, args in seeds:
        try:
            result = dispatch_tool(session, name, args)
            err = None
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
            err = str(exc)
        tool_trace.append({"tool": name, "arguments": args, "ok": err is None, "error": err, "seed": True})
        tool_calls.append(
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        )
        tool_msgs.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
    messages.append(
        {
            "role": "assistant",
            "content": "Core seed loaded.",
            "tool_calls": tool_calls,
        }
    )
    messages.extend(tool_msgs)


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
            return _attach_quality_preview(session, demo)
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
    _inject_scene_seed(session, messages, tool_trace)
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
                    result = _maybe_repair_proposal(settings, messages, result, conversation)
                    return _attach_quality_preview(session, result)
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
                result = _maybe_repair_proposal(settings, messages, result, conversation)
                return _attach_quality_preview(session, result)

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
            result = _maybe_repair_proposal(settings, messages, result, conversation)
            return _attach_quality_preview(session, result)

        result = _finalize_proposal_from_messages(settings, messages, tool_trace)
        result = _maybe_repair_proposal(settings, messages, result, conversation)
        return _attach_quality_preview(session, result)
    except Exception as exc:
        demo = _demo_as_agent_result(message)
        if demo:
            demo["reply"] = f"(Agent/LLM fehlgeschlagen: {exc}) {demo['reply']}"
            demo["llm_error"] = str(exc)
            return _attach_quality_preview(session, demo)
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
