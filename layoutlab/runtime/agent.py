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
1. Call tools to understand the scene (start with get_scene_summary when unsure).
2. Ask clarifying questions in the final JSON if critical info is missing.
3. Finish with ONLY a JSON object (no markdown fences):
{
  "reply": "short explanation in the user's language",
  "questions": ["optional clarifying questions"],
  "proposal": {
    "proposal_id": "uuid-or-string",
    "title": "short title",
    "rationale": "why this plan",
    "assumes": [],
    "commands": [ /* LayoutLab commands only */ ],
    "expected_risks": []
  },
  "suggested_next_tools": []
}

Rules:
- Prefer Metric meters (1 unit = 1 m).
- Commands: only allowlisted actions (use list_supported_actions if needed).
- Generators: bed_basic, desk_basic, wardrobe_basic.
- For a fresh kids room, delete_collection_objects on layoutlab_room first, then create_room.
- Do not claim you applied changes — the user must Apply.
- If you only need questions, set proposal.commands to [].
"""

MAX_TOOL_ROUNDS = 6


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
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            raw = _chat_completions(settings, messages, tools=tools, tool_choice="auto")
            choice = (raw.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            tool_calls = msg.get("tool_calls") or []

            if tool_calls:
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

            # No tool calls — force JSON proposal
            content = msg.get("content") or ""
            try:
                parsed = _extract_json_object(content)
            except Exception:
                # One more turn asking for JSON only
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": "Return ONLY the final JSON proposal object now (no tools, no markdown).",
                    }
                )
                raw2 = _chat_completions(settings, messages, tools=None)
                content2 = (((raw2.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
                parsed = _extract_json_object(content2)

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

        return {
            "ok": False,
            "mode": "agent",
            "error": "tool round limit exceeded",
            "reply": "Zu viele Tool-Runden — bitte Prompt eingrenzen oder Apply mit kleinerem Ziel.",
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
