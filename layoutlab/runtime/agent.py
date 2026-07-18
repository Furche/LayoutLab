"""Agent turn: tool calling → structured proposal (agent_tools 0.5)."""

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

AGENT_SYSTEM_PROMPT = """You are LayoutLab's planning agent (DD-009 / DD-015 / DD-016 / agent_tools 0.5).
AI decides WHAT (goals, recipe, tradeoffs); LayoutLab Core decides WHERE for standard rooms
via plan_layout recipes, and HOW via generators. You invent no meshes, bpy, or free Python.

Planning recipes (DD-016 — prefer this):
- For a normal bedroom (bed ± wardrobe ± desk, door + window): call plan_layout with
  recipe="bedroom_basic" and the room size / openings the user gave (or defaults).
- Use the returned commands as the proposal baseline. Then validate_commands + dry_run_commands.
- Do NOT invent free location/head_side for standard bedrooms when plan_layout covers the request.
- Free-form run_generator placement is only for custom overrides ("Tisch genau hier")
  after a recipe baseline, or when no recipe fits.

Spatial perception (critical):
- You cannot see the 3D viewport. Your eyes are tools: get_layout_sketch and dry_run_commands.layout_sketch.
- layout_sketch.ascii is a top-down map: top=N, bottom=S, left=W, right=E;
  #=wall D=door W=window letters=furniture +=preferred clearance *=required clearance.
- After drafting commands, dry_run and READ the ascii + soft_summary before finishing.
- If a letter sits on D/W, or * clearances are crushed, or + zones are packed away,
  adjust recipe options or one targeted placement change and dry_run again.

Role (compassionate planner):
- Work in the user's interest: rooms should feel comfortable AND be practically usable.
- Prefer free floor, light, and door/window access over packing like a warehouse.
- Gather missing context with a few bundled questions when size, use, or priorities are unclear.
  If the user already answered or said you may choose, document defaults in proposal.assumes — do not ask again.
- Soft metrics (packing density, opening_access) are comfort/usability proxies from Core — treat warnings seriously.

Observation vs action (critical):
- If the user only asks what is in the scene / whether you can see it / to describe the room:
  answer from the seed/tools, set proposal.commands to [], do NOT rebuild or Apply anything.
- Only emit mutating commands when the user asks to create, change, clear, or rearrange.

Physics (non-negotiable):
- Furniture must sit fully inside the room volume. Never place objects inside walls or through doors/windows.
- solid_wall_penetration errors are physically invalid — NOT a tradeoff. Replan; do not put them in expected_risks.

Context:
- A scene seed (get_scene_summary + list_generators) is already injected — trust it.
- Call get_room / list_objects only when you need details the seed lacks.
- Before a non-empty final proposal, prefer validate_commands then dry_run_commands.
- After dry_run: READ layout_sketch.ascii + soft_summary. If furniture sits on a door (D)
  or packs the room badly, revise commands and dry_run again — do not ship the first draft.
- You do NOT see the 3D viewport; layout_sketch is your spatial eyes (top-down XY).
- On soft warnings (soft_packing, opening_access): replan if possible.
- On hard clearance errors: try plan_layout again with different options, or one repair pass.
- If a clearance compromise is unavoidable (e.g. wardrobe reduces door swing but does not enter the wall):
  explain the tradeoff in reply and fill proposal.expected_risks. Never hide it.
- Wall penetration / impossible geometry: always fix, never waive.
- dry_run does NOT commit — the user must Apply (Apply = consent only to documented clearance tradeoffs).

Workflow:
1. Read the seed. For bedroom intents → plan_layout first.
2. validate + dry_run the recipe commands; read the sketch.
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
- Fresh layout sequence typically comes from plan_layout (delete → create_room → openings → generators).

Command shape (critical):
- Prefer params{} for create_room / add_opening / run_generator.
- delete_collection_objects MUST include collection, e.g.
  {"action":"delete_collection_objects","collection":"layoutlab_room"}
- run_generator MUST put placement in params (location, head_side, …) — flat keys alone are fragile.

Bed size (critical):
- Human "120×200" = mattress width × length. With head on south/north (y_min/y_max):
  length=1.2 (along wall), width=2.0 (into room). Never put 2.0 along the wall for a single bed.
- Prefer plan_layout with bed_width / bed_length for size changes.

When the user asks for a better / different arrangement:
- Call plan_layout again and/or change recipe options; do not repeat identical coords.
- Keep door access clear.

Rules:
- Prefer Metric meters (1 unit = 1 m). width = X, depth = Y.
- Generators: bed_basic, desk_basic, wardrobe_basic only.
- Do not claim you applied changes — the user must Apply.
- If you only need questions, set proposal.commands to [] AND leave questions non-empty.
"""

SOFT_REPLAN_HINT = (
    "Your previous proposal still has soft comfort/usability warnings from dry_run "
    "(opening_access and/or soft_packing). Return ONLY a new JSON proposal that fixes them: "
    "move storage away from doors/windows, set bed head_side against the wall the user wants, "
    "and keep clear circulation. Prefer a real geometry change over repeating the same locations. "
    "questions must be []. No markdown, no tools."
)

HARD_REPLAN_HINT = (
    "Your previous proposal still has HARD layout errors from dry_run "
    "(zone_must_be_clear / blocked required clearances / overlapping furniture). "
    "Return ONLY a new JSON proposal that is physically valid: "
    "no furniture AABB overlap, required clearances free, bed against a wall with head_side, "
    "desk not inside the bed, wardrobe not blocking the door. "
    "Change locations for real. questions must be []. No markdown, no tools."
)

IMPROVE_LAYOUT_HINT = (
    "The user asked for a BETTER / different placement. Your previous locations are not good enough. "
    "Return ONLY a new JSON proposal with REAL geometry changes: move the bed against a wall "
    "(set head_side to that wall), keep the east door clear, put the wardrobe on the west/north wall, "
    "and place the desk by the window without blocking the door. "
    "Do NOT repeat the same location arrays. questions must be []. No markdown, no tools."
)

MAX_TOOL_ROUNDS = 6
REPAIR_HINT = (
    "Your previous proposal was incomplete for the user's request. "
    "Return ONLY a new JSON proposal whose commands include ALL required parts "
    "(create_room, add_opening kind=door, add_opening kind=window for EACH requested window "
    "with sill_height, and run_generator for furniture). "
    "A door does not replace windows. questions must be []. No markdown, no tools."
)

# Last accepted proposal fingerprint (this Core process) — detect identical "improve" replies.
_LAST_PLACEMENT_FP: tuple | None = None

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


def _is_observation_query(message: str) -> bool:
    """True when the user only wants scene status/description, not mutations."""
    t = (message or "").strip().lower()
    if not t:
        return False
    # Explicit build/mutate verbs → not observation-only
    mutate = (
        "bau",
        "erstell",
        "einricht",
        "lösch",
        "losch",
        "clear",
        "leeren",
        "platzi",
        "verschieb",
        "änder",
        "ander",
        "add ",
        "remove",
        "put ",
        "make ",
        "create",
        "delete",
        "move ",
        "neu plan",
        "neuplan",
        "umplan",
    )
    if any(k in t for k in mutate):
        return False
    patterns = (
        r"\b(kannst|kann)\b.*\b(sehen|siehst)\b",
        r"\bsiehst du\b",
        r"\bwas (ist|steht|siehst|hast)\b",
        r"\bbeschreib",
        r"\baktuell\w*\s+(scene|szene|raum|zimmer)\b",
        r"\b(scene|szene)\s+(sehen|zeigen|beschreib)",
        r"\bcurrent scene\b",
        r"\bwhat('?s| is)\b.*\b(scene|room)\b",
        r"\bwelche m[oö]bel\b",
        r"\bwas siehst du\b",
        r"\bproblematisch\b",
        r"\bproblem\b",
        r"\bkollision\b",
        r"\büberlapp",
        r"\buberlapp",
        r"\bim bett\b",
        r"\bfalsch\b",
        r"\bstimmt (das|etwas|was)\b",
    )
    return any(re.search(p, t) for p in patterns)


def _observation_reply(session) -> dict:
    summary = dispatch_tool(session, "get_scene_summary", {})
    analysis = dispatch_tool(session, "get_analysis", {"scope": "scene"})
    sketch = dispatch_tool(session, "get_layout_sketch", {})
    rooms = summary.get("rooms") or []
    gens = summary.get("generators_present") or []
    counts = summary.get("object_counts") or {}
    findings = analysis.get("findings") or []
    hard = [
        f
        for f in findings
        if f.get("severity") == "error" or f.get("non_negotiable")
    ]
    soft = [
        f
        for f in findings
        if f.get("severity") == "warning"
        and f.get("constraint_type") in ("soft_packing", "opening_access", "zone_must_be_clear")
    ]
    # Prefer listing zone blocks even if severity varies
    zone_hits = [
        f for f in findings if f.get("constraint_type") == "zone_must_be_clear"
    ]

    tool_trace = [
        {"tool": "get_scene_summary", "arguments": {}, "ok": True, "seed": False},
        {"tool": "get_analysis", "arguments": {"scope": "scene"}, "ok": True, "seed": False},
        {"tool": "get_layout_sketch", "arguments": {}, "ok": True, "seed": False},
    ]

    if not rooms:
        reply = "Die aktuelle Scene ist leer — kein Raum im Core."
    else:
        room_bits = []
        for r in rooms:
            room_bits.append(
                f"{r.get('name')} ({r.get('width')}×{r.get('depth')} m, "
                f"{r.get('opening_count', 0)} Öffnungen)"
            )
        furn = ", ".join(gens) if gens else "keine Generator-Möbel"
        lines = [
            "Ja — ich prüfe die aktuelle Core-Scene (Summary + Analysis + Top-Down-Sketch):",
            "; ".join(room_bits) + f". Möbel: {furn}.",
            f"Counts: furniture={counts.get('furniture', 0)}, walls={counts.get('walls', 0)}.",
        ]
        if hard or zone_hits:
            lines.append("Probleme:")
            for f in (hard or zone_hits)[:8]:
                lines.append(
                    f"- [{f.get('severity')}] {f.get('constraint_type')}: {f.get('message')}"
                )
        elif soft:
            lines.append("Auffälligkeiten (soft/warn):")
            for f in soft[:6]:
                lines.append(f"- {f.get('constraint_type')}: {f.get('message')}")
        else:
            lines.append("Keine harten Analysis-Fehler; Soft-Warnings: keine oder gering.")

        ascii_map = sketch.get("ascii") or ""
        if ascii_map and ascii_map != "(empty scene — no rooms)":
            lines.append("Top-down sketch (# Wand, D Tür, W Fenster, Buchstaben=Möbel, +/* Clearance):")
            lines.append(ascii_map)
            # Heuristic overlap callout from sketch letters colliding is hard;
            # mention if bed+desk bounds overlap from sketch furniture list.
            overlap_note = _observation_overlap_note(sketch)
            if overlap_note:
                lines.append(overlap_note)

        reply = "\n".join(lines)

    quality = {
        "ok": not hard,
        "has_hard_errors": len(hard) > 0 or any(
            f.get("severity") == "error" for f in zone_hits
        ),
        "has_soft_warnings": len(soft) > 0,
        "summary": analysis.get("summary"),
        "soft_summary": analysis.get("soft_summary"),
        "finding_types": sorted(
            {f.get("constraint_type") for f in findings if f.get("constraint_type")}
        ),
        "layout_sketch_ascii": sketch.get("ascii"),
        "layout_sketch_legend": sketch.get("legend") or {},
    }

    return {
        "ok": True,
        "mode": "observe",
        "reply": reply,
        "questions": [],
        "proposal": {
            "proposal_id": str(uuid.uuid4()),
            "title": "Scene-Status",
            "rationale": "Observation-only — no mutations",
            "assumes": [],
            "commands": [],
            "expected_risks": [],
        },
        "suggested_next_tools": [],
        "commands": [],
        "tool_trace": tool_trace,
        "scene_summary": summary,
        "quality": quality,
    }


def _observation_overlap_note(sketch: dict) -> str:
    rooms = sketch.get("rooms") or []
    if not rooms:
        return ""
    furn = rooms[0].get("furniture") or []
    by_gen = {}
    for f in furn:
        gen = f.get("generator") or ""
        b = f.get("bounds_xy") or {}
        if b.get("min") and b.get("max"):
            by_gen.setdefault(gen, []).append(b)
    bed = (by_gen.get("bed_basic") or [None])[0]
    desk = (by_gen.get("desk_basic") or [None])[0]
    if not bed or not desk:
        return ""
    if _bounds_xy_overlap(bed, desk):
        return (
            "Hinweis aus Sketch-Bounds: Schreibtisch und Bett überlappen sich "
            "(Tisch steht im Bett-Bereich)."
        )
    return ""


def _bounds_xy_overlap(a: dict, b: dict) -> bool:
    amin, amax = a.get("min") or [0, 0], a.get("max") or [0, 0]
    bmin, bmax = b.get("min") or [0, 0], b.get("max") or [0, 0]
    return not (
        float(amax[0]) <= float(bmin[0])
        or float(bmax[0]) <= float(amin[0])
        or float(amax[1]) <= float(bmin[1])
        or float(bmax[1]) <= float(amin[1])
    )


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


def _user_mentions_bed_head(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in (
            "kopfende",
            "kopfseite",
            "kopfteile",
            "headboard",
            "head of the bed",
            "head of bed",
            "bett dreh",
            "bett rotier",
            "rotate the bed",
            "turn the bed",
        )
    )


def _user_wants_better_layout(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in (
            "besser",
            "bessere",
            "besseren",
            "andere lösung",
            "andere losung",
            "anders stellen",
            "umstellen",
            "neu platz",
            "neuplatz",
            "verbesser",
            "optimize",
            "optimier",
            "better",
            "rearrange",
            "umräumen",
            "umraumen",
            "schickere",
            "geeignetere",
        )
    )


def _parse_bed_size_m(text: str) -> tuple[float, float] | None:
    """Parse human mattress size as (width, length) in meters.

    '120x200' / '120 × 200' → 1.2 × 2.0 (Breite × Länge). Order matters.
    """
    t = (text or "").lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", t)
    if not m:
        return None
    a = float(m.group(1))
    b = float(m.group(2))
    # cm if both look like centimeters
    if a >= 10 and b >= 10:
        a, b = a / 100.0, b / 100.0
    if a < 0.5 or b < 0.5 or a > 3.5 or b > 3.5:
        return None
    return round(a, 3), round(b, 3)


def _mattress_to_bed_axes(head_side: str | None, mattress_w: float, mattress_l: float):
    """Map human width×length onto bed_basic length(X)/width(Y)."""
    side = (head_side or "y_min").strip().lower()
    if side in ("x_min", "x_max"):
        return round(mattress_l, 3), round(mattress_w, 3)
    return round(mattress_w, 3), round(mattress_l, 3)


def _loc_delta(a, b) -> float:
    try:
        return max(abs(float(a[0]) - float(b[0])), abs(float(a[1]) - float(b[1])))
    except (TypeError, ValueError, IndexError):
        return 999.0


def _apply_requested_bed_size(commands: list, mattress_w: float, mattress_l: float) -> bool:
    """Set bed dims from human mattress size; keep head_side. Returns True if changed."""
    changed = False
    for cmd in commands:
        if cmd.get("action") != "run_generator" or cmd.get("generator") != "bed_basic":
            continue
        params = dict(cmd.get("params") or {})
        head = params.get("head_side") or "y_min"
        length, width = _mattress_to_bed_axes(head, mattress_w, mattress_l)
        try:
            old_l = float(params.get("length") or 0)
            old_w = float(params.get("width") or 0)
        except (TypeError, ValueError):
            old_l, old_w = 0.0, 0.0
        if abs(old_l - length) < 0.02 and abs(old_w - width) < 0.02:
            continue
        params["length"] = length
        params["width"] = width
        cmd["params"] = params
        changed = True
    return changed


def _room_size_from_commands(commands: list) -> tuple[float, float]:
    for cmd in commands or []:
        if cmd.get("action") != "create_room":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        w = params.get("width", cmd.get("width"))
        d = params.get("depth", cmd.get("depth"))
        try:
            return float(w), float(d)
        except (TypeError, ValueError):
            break
    return 4.0, 3.0


def _nearest_wall_side(location, room_w: float, room_d: float) -> str:
    try:
        x = float(location[0])
        y = float(location[1])
    except (TypeError, ValueError, IndexError):
        return "y_min"
    dist = {
        "x_min": x,
        "x_max": max(0.0, room_w - x),
        "y_min": y,
        "y_max": max(0.0, room_d - y),
    }
    return min(dist, key=dist.get)


def _east_door_present(commands: list) -> bool:
    for cmd in commands or []:
        if cmd.get("action") != "add_opening":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        kind = str(params.get("kind") or cmd.get("kind") or "").lower()
        wall = str(params.get("wall_side") or cmd.get("wall_side") or "").lower()
        if kind == "door" and wall == "east":
            return True
    return False


def _placement_fingerprint(commands: list) -> tuple:
    parts = []
    for cmd in commands or []:
        if cmd.get("action") != "run_generator":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        loc = params.get("location") or []
        try:
            loc_t = tuple(round(float(v), 3) for v in loc[:3])
        except (TypeError, ValueError):
            loc_t = tuple(loc[:3])
        parts.append(
            (
                cmd.get("generator"),
                loc_t,
                params.get("head_side"),
                params.get("front_side"),
            )
        )
    return tuple(parts)


def _snap_bed_to_wall(params: dict, room_w: float, room_d: float, *, prefer: str | None = None):
    """Move bed footprint against a wall; set matching head_side.

    bed_basic axes are fixed: length=X, width=Y. Orientation:
    - head on south/north (y_*): sleep along Y → X = mattress width, Y = mattress length
      (normal 120×200 → length=1.2, width=2.0 — NOT 2.0 along the wall).
    - head on east/west (x_*): sleep along X → length = mattress length, width = mattress width.
    Returns (location, head_side, dim_updates_or_None).
    """
    try:
        length = float(params.get("length") or 2.0)
        width = float(params.get("width") or 1.2)
    except (TypeError, ValueError):
        length, width = 2.0, 1.2
    margin = 0.08
    hug = 0.18
    loc = list(params.get("location") or [0, 0, 0])
    try:
        x = float(loc[0])
        y = float(loc[1])
        z = float(loc[2]) if len(loc) > 2 else 0.0
    except (TypeError, ValueError, IndexError):
        x, y, z = 0.0, 0.0, 0.0

    gap = {
        "y_min": y,
        "y_max": room_d - (y + width),
        "x_min": x,
        "x_max": room_w - (x + length),
    }
    side = prefer or min(gap, key=gap.get)
    # Not already hugging a wall → default south wall for bedrooms.
    if prefer is None and min(gap.values()) > 0.25:
        side = "y_min"

    # Ensure sleep axis is the longer mattress dimension when dims look swapped.
    swapped = False
    if side in ("y_min", "y_max") and length > width:
        length, width = width, length
        swapped = True
    elif side in ("x_min", "x_max") and width > length:
        length, width = width, length
        swapped = True

    # Recompute gap after possible dim swap.
    gap = {
        "y_min": y,
        "y_max": room_d - (y + width),
        "x_min": x,
        "x_max": room_w - (x + length),
    }
    already_hugging = gap.get(side, 999) <= hug

    if already_hugging and prefer is None:
        # Keep placement; only clamp footprint inside the room.
        x = max(margin, min(room_w - length - margin, x))
        y = max(margin, min(room_d - width - margin, y))
        if side == "y_min":
            y = margin
            head = "y_min"
        elif side == "y_max":
            y = max(margin, room_d - width - margin)
            head = "y_max"
        elif side == "x_min":
            x = margin
            head = "x_min"
        else:
            x = max(margin, room_w - length - margin)
            head = "x_max"
    elif side == "y_min":
        x = max(margin, min(room_w - length - margin, (room_w - length) / 2))
        y = margin
        head = "y_min"
    elif side == "y_max":
        x = max(margin, min(room_w - length - margin, (room_w - length) / 2))
        y = max(margin, room_d - width - margin)
        head = "y_max"
    elif side == "x_min":
        x = margin
        y = max(margin, min(room_d - width - margin, (room_d - width) / 2))
        head = "x_min"
    else:
        x = max(margin, room_w - length - margin)
        y = max(margin, min(room_d - width - margin, (room_d - width) / 2))
        head = "x_max"
    dims = {"length": round(length, 3), "width": round(width, 3)} if swapped else None
    return [round(x, 3), round(y, 3), round(z, 3)], head, dims


def _gen_xy_aabb(gen: str, params: dict):
    loc = list(params.get("location") or [0, 0, 0])
    try:
        x, y = float(loc[0]), float(loc[1])
    except (TypeError, ValueError, IndexError):
        return None
    if gen == "bed_basic":
        try:
            length = float(params.get("length") or 2.0)
            width = float(params.get("width") or 1.2)
        except (TypeError, ValueError):
            length, width = 2.0, 1.2
        return (x, y, x + length, y + width)
    if gen in ("desk_basic", "wardrobe_basic"):
        try:
            w = float(params.get("width") or 1.0)
            d = float(params.get("depth") or 0.6)
        except (TypeError, ValueError):
            w, d = 1.0, 0.6
        return (x, y, x + w, y + d)
    return None


def _aabb_overlap_tuple(a, b) -> bool:
    if not a or not b:
        return False
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _separate_furniture_overlaps(commands: list, room_w: float, room_d: float) -> bool:
    """Push desk/wardrobe out of bed footprint if AABBs overlap."""
    items = []
    for cmd in commands:
        if cmd.get("action") != "run_generator":
            continue
        gen = cmd.get("generator")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        if not params or not gen:
            continue
        box = _gen_xy_aabb(gen, params)
        if box:
            items.append((cmd, gen, params, box))

    changed = False
    beds = [it for it in items if it[1] == "bed_basic"]
    desks = [it for it in items if it[1] == "desk_basic"]
    wards = [it for it in items if it[1] == "wardrobe_basic"]
    margin = 0.12

    for cmd, _gen, params, box in desks:
        for _bcmd, _bgen, bparams, bbox in beds:
            if not _aabb_overlap_tuple(box, bbox):
                continue
            bw = float(bparams.get("length") or 2.0)
            bh = float(bparams.get("width") or 1.2)
            bloc = bparams.get("location") or [0, 0, 0]
            bx, by = float(bloc[0]), float(bloc[1])
            dw = float(params.get("width") or 1.2)
            dd = float(params.get("depth") or 0.6)
            candidates = [
                [bx + bw + margin, by, 0.0],
                [bx, by + bh + margin, 0.0],
                [max(0.08, bx - dw - margin), by, 0.0],
            ]
            new_loc = None
            for cand in candidates:
                if cand[0] < 0.05 or cand[1] < 0.05:
                    continue
                if cand[0] + dw > room_w - 0.05 or cand[1] + dd > room_d - 0.05:
                    continue
                test = (cand[0], cand[1], cand[0] + dw, cand[1] + dd)
                if not _aabb_overlap_tuple(test, bbox):
                    new_loc = [round(cand[0], 3), round(cand[1], 3), 0.0]
                    break
            if new_loc is None:
                new_loc = [0.15, round(max(0.15, room_d - dd - 0.15), 3), 0.0]
            params = dict(params)
            params["location"] = new_loc
            cmd["params"] = params
            box = _gen_xy_aabb("desk_basic", params)
            changed = True

    for cmd, _gen, params, box in wards:
        for _bcmd, _bgen, bparams, bbox in beds:
            if not _aabb_overlap_tuple(box, bbox):
                continue
            depth = float(params.get("depth") or 0.6)
            width = float(params.get("width") or 1.0)
            bloc = bparams.get("location") or [0, 1, 0]
            params = dict(params)
            params["location"] = [
                round(0.08, 3),
                round(
                    max(0.15, min(float(bloc[1]), room_d - depth - 0.15)),
                    3,
                ),
                0.0,
            ]
            params["front_side"] = "y_min"
            cmd["params"] = params
            changed = True
    return changed


def _apply_improved_bedroom_layout(commands: list, room_w: float, room_d: float) -> bool:
    """Force a distinct wall-based arrangement (used when user asks for better)."""
    margin = 0.08
    east_door = _east_door_present(commands)
    changed = False
    for cmd in commands:
        if cmd.get("action") != "run_generator":
            continue
        gen = cmd.get("generator")
        params = dict(cmd.get("params") or {})
        if gen == "bed_basic":
            # Alternate: north wall
            loc, head, dims = _snap_bed_to_wall(params, room_w, room_d, prefer="y_max")
            if params.get("location") != loc or params.get("head_side") != head or dims:
                params["location"] = loc
                params["head_side"] = head
                if dims:
                    params.update(dims)
                cmd["params"] = params
                changed = True
        elif gen == "wardrobe_basic":
            depth = float(params.get("depth") or 0.6)
            width = float(params.get("width") or 1.0)
            # North wall west — wardrobe_basic only supports y fronts
            loc = [
                round(margin, 3),
                round(max(margin, room_d - depth - margin), 3),
                0.0,
            ]
            if east_door and loc[0] + width > room_w - 1.0:
                loc[0] = round(max(margin, room_w - 1.0 - width), 3)
            if params.get("location") != loc or params.get("front_side") != "y_min":
                params["location"] = loc
                params["front_side"] = "y_min"
                cmd["params"] = params
                changed = True
        elif gen == "desk_basic":
            depth = float(params.get("depth") or 0.6)
            width = float(params.get("width") or 1.2)
            # West / north of south window strip — not on top of a south-wall bed
            loc = [
                round(margin, 3),
                round(margin + 1.4, 3),
                0.0,
            ]
            if east_door and loc[0] + width > room_w - 1.0:
                loc[0] = round(max(margin, room_w - width - 1.1), 3)
            if params.get("location") != loc:
                params["location"] = loc
                cmd["params"] = params
                changed = True
    return changed


def _apply_deterministic_placement_fixes(conversation: str, result: dict) -> dict:
    """Fix common LLM misses: floating beds, head_side, door-blocking storage."""
    commands = list(result.get("commands") or [])
    if not commands:
        return result
    room_w, room_d = _room_size_from_commands(commands)
    want_head = _user_mentions_bed_head(conversation)
    want_better = _user_wants_better_layout(conversation)
    east_door = _east_door_present(commands)
    requested_size = _parse_bed_size_m(conversation)
    changed = False
    notes = []
    bed_size_changed = False
    bed_size_already_ok = False

    if requested_size is not None:
        before = [c.get("params") for c in commands if c.get("generator") == "bed_basic"]
        bed_size_changed = _apply_requested_bed_size(commands, requested_size[0], requested_size[1])
        if bed_size_changed:
            changed = True
            notes.append(
                f"Bettmaß auf {int(requested_size[0] * 100)}×{int(requested_size[1] * 100)} cm "
                "(Breite × Länge)."
            )
        elif before:
            bed_size_already_ok = True

    if want_better:
        if _apply_improved_bedroom_layout(commands, room_w, room_d):
            changed = True
            notes.append("Layout-Korrektur: alternative Wandplatzierung (bessere Lösung).")

    for cmd in commands:
        if cmd.get("action") != "run_generator":
            continue
        gen = cmd.get("generator")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        if not params:
            continue
        if gen == "bed_basic":
            prefer = "y_max" if want_better else None
            if want_head and not want_better:
                prefer = _nearest_wall_side(params.get("location") or [0, 0, 0], room_w, room_d)
            loc, head, dims = _snap_bed_to_wall(params, room_w, room_d, prefer=prefer)
            old_head = params.get("head_side")
            moved = _loc_delta(params.get("location") or [0, 0, 0], loc) > 0.12
            head_fix = old_head != head
            orient_fix = bool(
                dims
                and (
                    abs(float(params.get("length") or 0) - dims["length"]) > 0.02
                    or abs(float(params.get("width") or 0) - dims["width"]) > 0.02
                )
            )
            if moved or head_fix or orient_fix:
                params = dict(params)
                params["location"] = loc
                params["head_side"] = head
                if dims:
                    params.update(dims)
                cmd["params"] = params
                changed = True
                # Announce only meaningful fixes — not silent re-snap of an already good bed.
                if moved or (head_fix and old_head not in (None, head)):
                    if "Bett an die Wand" not in "".join(notes):
                        notes.append("Layout-Korrektur: Bett an die Wand (head_side).")
                elif orient_fix and "Orientierung" not in "".join(notes):
                    notes.append("Layout-Korrektur: Bett-Orientierung (Schlafrichtung).")
        if gen == "wardrobe_basic" and east_door:
            loc = list(params.get("location") or [0, 0, 0])
            try:
                x = float(loc[0])
            except (TypeError, ValueError):
                x = 0.0
            if x > room_w * 0.55:
                depth = float(params.get("depth") or 0.6)
                try:
                    y = float(loc[1]) if len(loc) > 1 else 0.15
                    z = float(loc[2]) if len(loc) > 2 else 0.0
                except (TypeError, ValueError):
                    y, z = 0.15, 0.0
                params = dict(params)
                params["location"] = [max(0.15, depth / 2 + 0.05), max(0.15, y), z]
                # wardrobe_basic only supports y_min / y_max
                params["front_side"] = "y_min"
                cmd["params"] = params
                changed = True
                notes.append("Layout-Korrektur: Schrank von der Ost-Tür weg.")
        if gen == "desk_basic" and east_door:
            loc = list(params.get("location") or [0, 0, 0])
            try:
                x = float(loc[0])
                width = float(params.get("width") or 1.2)
            except (TypeError, ValueError):
                x, width = 0.0, 1.2
            if x + width > room_w - 1.0:
                params = dict(params)
                params["location"] = [
                    round(max(0.15, min(x, room_w - width - 1.1)), 3),
                    round(float(loc[1]) if len(loc) > 1 else 0.15, 3),
                    float(loc[2]) if len(loc) > 2 else 0.0,
                ]
                cmd["params"] = params
                changed = True
                notes.append("Layout-Korrektur: Schreibtisch aus dem Türbereich.")

    if want_better and _LAST_PLACEMENT_FP is not None:
        if _placement_fingerprint(commands) == _LAST_PLACEMENT_FP:
            if _apply_improved_bedroom_layout(commands, room_w, room_d):
                changed = True
                notes.append("Layout-Korrektur: erzwungene Umstellung (vorher identisch).")

    if _separate_furniture_overlaps(commands, room_w, room_d):
        changed = True
        notes.append("Layout-Korrektur: Möbel-Überlappung getrennt (z.B. Tisch aus dem Bett).")

    if bed_size_already_ok and not changed:
        result = dict(result)
        w_cm, l_cm = int(requested_size[0] * 100), int(requested_size[1] * 100)
        result["reply"] = (
            f"Das Bett ist bereits {w_cm}×{l_cm} cm (Breite × Länge) — keine Änderung nötig."
        )
        return result

    if not changed:
        return result

    result = dict(result)
    result["commands"] = commands
    proposal = dict(result.get("proposal") or {})
    proposal["commands"] = commands
    result["proposal"] = proposal
    if notes:
        result["reply"] = (result.get("reply") or "").rstrip() + " (" + " ".join(notes) + ")"
    return result


def _maybe_improve_replan(session, settings, messages, result: dict, conversation: str) -> dict:
    """If user asked for better layout but placement still matches last turn, force LLM replan."""
    if not _user_wants_better_layout(conversation):
        return result
    if not (result.get("commands") or []):
        return result
    fp = _placement_fingerprint(result.get("commands") or [])
    if _LAST_PLACEMENT_FP is None or fp != _LAST_PLACEMENT_FP:
        return result
    try:
        repaired = _finalize_proposal_from_messages(
            settings,
            messages,
            result.get("tool_trace") or [],
            repair_note=IMPROVE_LAYOUT_HINT,
        )
    except Exception:
        return result
    repaired = _apply_deterministic_placement_fixes(conversation, repaired)
    return _attach_quality_preview(session, repaired)


def _maybe_hard_replan(session, settings, messages, result: dict, conversation: str) -> dict:
    """One LLM replan when dry-run still has hard clearance/overlap errors."""
    quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}
    if not quality.get("has_hard_errors"):
        return result
    if quality.get("has_solid_collisions") or quality.get("blocks_apply"):
        # Solid hits already force a note; still try one geometry replan.
        pass
    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else {}
    if proposal.get("expected_risks") and not quality.get("has_solid_collisions"):
        return result
    if not (result.get("commands") or []):
        return result

    types = ",".join(quality.get("finding_types") or []) or "hard errors"
    ascii_map = quality.get("layout_sketch_ascii") or ""
    note = HARD_REPLAN_HINT + f" Finding types: {types}."
    if ascii_map:
        note += "\nCurrent dry-run top-down sketch:\n" + ascii_map
    try:
        repaired = _finalize_proposal_from_messages(
            settings, messages, result.get("tool_trace") or [], repair_note=note
        )
    except Exception:
        return result
    repaired = _apply_deterministic_placement_fixes(conversation, repaired)
    repaired = _attach_quality_preview(session, repaired)
    old_e = int((quality.get("summary") or {}).get("errors") or 0)
    new_q = repaired.get("quality") if isinstance(repaired.get("quality"), dict) else {}
    new_e = int((new_q.get("summary") or {}).get("errors") or 0)
    if new_e < old_e:
        return repaired
    if not new_q.get("has_hard_errors") and quality.get("has_hard_errors"):
        return repaired
    if (repaired.get("commands") or []) != (result.get("commands") or []):
        return repaired
    return result


def _maybe_soft_replan(session, settings, messages, result: dict, conversation: str) -> dict:
    """One LLM replan when dry-run soft warnings remain and no tradeoff was declared."""
    quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}
    if not quality.get("has_soft_warnings"):
        return result
    if quality.get("has_solid_collisions") or quality.get("blocks_apply"):
        return result
    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else {}
    if proposal.get("expected_risks"):
        return result
    if not (result.get("commands") or []):
        return result

    soft = quality.get("soft_summary") or {}
    types = ",".join(soft.get("types") or []) or "soft warnings"
    ascii_map = quality.get("layout_sketch_ascii") or ""
    note = SOFT_REPLAN_HINT + f" Soft types: {types}."
    if ascii_map:
        note += (
            "\nCurrent dry-run top-down sketch (fix geometry so this improves):\n"
            + ascii_map
        )
    try:
        repaired = _finalize_proposal_from_messages(
            settings, messages, result.get("tool_trace") or [], repair_note=note
        )
    except Exception:
        return result
    repaired = _apply_deterministic_placement_fixes(conversation, repaired)
    repaired = _attach_quality_preview(session, repaired)
    # Prefer fewer soft warnings; otherwise keep original.
    old_w = int((quality.get("soft_summary") or {}).get("warnings") or 0)
    new_q = repaired.get("quality") if isinstance(repaired.get("quality"), dict) else {}
    new_w = int((new_q.get("soft_summary") or {}).get("warnings") or 0)
    if new_w < old_w:
        return repaired
    if new_w == old_w and (repaired.get("commands") or []) != (result.get("commands") or []):
        # Geometry changed but soft count same — still accept if head_side/wardrobe moved.
        return repaired
    return result


def _finish_agent_result(session, settings, messages, result: dict, conversation: str) -> dict:
    global _LAST_PLACEMENT_FP
    result = _maybe_repair_proposal(settings, messages, result, conversation)
    result = _apply_deterministic_placement_fixes(conversation, result)
    result = _attach_quality_preview(session, result)
    result = _maybe_hard_replan(session, settings, messages, result, conversation)
    result = _maybe_soft_replan(session, settings, messages, result, conversation)
    result = _maybe_improve_replan(session, settings, messages, result, conversation)
    _LAST_PLACEMENT_FP = _placement_fingerprint(result.get("commands") or [])
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
    findings = analysis.get("findings") or []
    solid = [
        f
        for f in findings
        if f.get("constraint_type") == "solid_wall_penetration" or f.get("non_negotiable")
    ]
    hard_errors = int(summary.get("errors") or 0)
    soft_warnings = int(soft.get("warnings") or 0)
    risks = list((result.get("proposal") or {}).get("expected_risks") or [])
    has_solid = len(solid) > 0
    sketch = dry.get("layout_sketch") if isinstance(dry.get("layout_sketch"), dict) else {}
    result["quality"] = {
        "ok": bool(dry.get("ok")) and not has_solid,
        "apply_ok": bool(dry.get("apply_ok")),
        "summary": summary,
        "soft_summary": soft,
        "findings": findings,
        "has_hard_errors": hard_errors > 0,
        "has_solid_collisions": has_solid,
        "has_soft_warnings": soft_warnings > 0,
        "has_expected_risks": len(risks) > 0,
        "needs_user_confirm": (hard_errors > 0 or soft_warnings > 0 or len(risks) > 0)
        and not has_solid,
        "blocks_apply": has_solid,
        "solid_messages": [f.get("message") for f in solid[:5]],
        "layout_sketch_ascii": sketch.get("ascii"),
        "layout_sketch_legend": sketch.get("legend") or {},
    }
    if has_solid:
        note = (
            " Hinweis: Physikalisch ungültig (Möbel durchdringt Wand) — "
            "nicht als Kompromiss akzeptierbar; bitte neu platzieren."
        )
        result["reply"] = (result.get("reply") or "").rstrip() + note
    elif hard_errors > 0 and not risks:
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
        ("seed_layout_sketch", "get_layout_sketch", {}),
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

    if _is_observation_query(message):
        return _observation_reply(session)

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
                    return _finish_agent_result(
                        session, settings, messages, result, conversation
                    )
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
                return _finish_agent_result(
                    session, settings, messages, result, conversation
                )

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
            return _finish_agent_result(session, settings, messages, result, conversation)

        result = _finalize_proposal_from_messages(settings, messages, tool_trace)
        return _finish_agent_result(session, settings, messages, result, conversation)
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
