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
from .planning import intent as intent
from .planning import placement as placement
from .tools import dispatch_tool, openai_tool_definitions

# Compatibility aliases — tests import layoutlab.runtime.agent and call underscored names.
_WORD_COUNTS = intent.WORD_COUNTS
_user_wants_bed = intent.user_wants_bed
_wants_bedroom_layout = intent.wants_bedroom_layout
_is_retry_request = intent.is_retry_request
_session_wants_bedroom_fallback = intent.session_wants_bedroom_fallback
_user_wants_door = intent.user_wants_door
_user_wants_room = intent.user_wants_room
_count_requested_noun = intent.count_requested_noun
_requested_window_count = intent.requested_window_count
_opening_kind_counts = intent.opening_kind_counts
_user_mentions_bed_head = intent.user_mentions_bed_head
_user_wants_better_layout = intent.user_wants_better_layout
_parse_bed_size_m = intent.parse_bed_size_m
_parse_room_size_m = intent.parse_room_size_m

_mattress_to_bed_axes = placement.mattress_to_bed_axes
_loc_delta = placement.loc_delta
_apply_requested_bed_size = placement.apply_requested_bed_size
_room_size_from_commands = placement.room_size_from_commands
_nearest_wall_side = placement.nearest_wall_side
_east_door_present = placement.east_door_present
_as_xyz = placement.as_xyz
_placement_fingerprint = placement.placement_fingerprint
_snap_bed_to_wall = placement.snap_bed_to_wall
_gen_xy_aabb = placement.gen_xy_aabb
_aabb_overlap_tuple = placement.aabb_overlap_tuple
_separate_furniture_overlaps = placement.separate_furniture_overlaps
_apply_improved_bedroom_layout = placement.apply_improved_bedroom_layout
_apply_deterministic_placement_fixes = placement.apply_deterministic_placement_fixes
_layout_shell_fingerprint = placement.layout_shell_fingerprint
_proposal_wants_layout = placement.proposal_wants_layout

AGENT_SYSTEM_PROMPT = """You are LayoutLab's planning agent (DD-009 / DD-015 / DD-016 / agent_tools 0.5).
AI decides WHAT (goals, recipe, tradeoffs); LayoutLab Core decides WHERE for standard rooms
via plan_layout recipes, and HOW via generators. You invent no meshes, bpy, or free Python.

Planning recipes (DD-016 — prefer this):
- For a normal bedroom: extract structured requirements from the user language, then call
  plan_layout with requirements={...}. Example:
  {"requirements":{"room_type":"bedroom","width":4,"depth":3.5,"doors":1,"windows":2,
   "furniture":["bed","wardrobe","desk"],"bed_width":1.2,"bed_length":2.0,"door_wall":"east"}}
- You translate language → requirements (numbers, counts). Core translates requirements → geometry.
- Put the same requirements object into proposal.requirements in your final JSON.
- Do NOT invent free location/head_side or duplicate openings. Core re-applies plan_layout
  from requirements if your commands diverge.
- Free-form run_generator placement only for custom overrides ("Tisch genau hier")
  after a recipe baseline, or when no recipe fits.
- If size/openings are unknown, ask briefly OR document defaults in requirements.assumes.

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
    "requirements": { /* structured intent for plan_layout */ },
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


def _apply_plan_layout_baseline(
    session, result: dict, conversation: str, last_plan: dict | None
) -> dict:
    """When plan_layout ran this turn, Core recipe commands win over free LLM edits."""
    if not last_plan or not last_plan.get("commands"):
        return result
    commands = list(result.get("commands") or [])
    questions = list(result.get("questions") or [])
    if not _proposal_wants_layout(commands, conversation, questions):
        return result

    from .planning import reconcile_plan_layout_params

    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else {}
    req = None
    if isinstance(proposal.get("requirements"), dict):
        req = proposal.get("requirements")
    elif isinstance(last_plan.get("requirements"), dict):
        req = last_plan.get("requirements")
    elif isinstance((last_plan.get("arguments") or {}).get("requirements"), dict):
        req = (last_plan.get("arguments") or {}).get("requirements")

    args = reconcile_plan_layout_params(
        last_plan.get("arguments") or {},
        window_count=_requested_window_count(conversation),
        room_size=_parse_room_size_m(conversation),
        bed_size=_parse_bed_size_m(conversation),
        wants_door=_user_wants_door(conversation) or True,
        requirements=req,
    )
    planned = dispatch_tool(session, "plan_layout", args)
    if planned.get("ok") and planned.get("commands"):
        cmds = planned["commands"]
        assumes = list(planned.get("assumes") or [])
        req_out = planned.get("requirements")
    else:
        cmds = list(last_plan.get("commands") or [])
        assumes = list(last_plan.get("assumes") or [])
        req_out = last_plan.get("requirements")
        planned = last_plan

    llm_fp = _layout_shell_fingerprint(commands)
    core_fp = _layout_shell_fingerprint(cmds)
    replaced = bool(commands) and llm_fp != core_fp

    result = dict(result)
    result["commands"] = cmds
    result["questions"] = []
    proposal = dict(proposal)
    proposal["commands"] = cmds
    if isinstance(req_out, dict):
        proposal["requirements"] = req_out
    merged_assumes = list(proposal.get("assumes") or [])
    for a in assumes:
        if a not in merged_assumes:
            merged_assumes.append(a)
    proposal["assumes"] = merged_assumes
    result["proposal"] = proposal
    result["plan_layout_enforced"] = True
    result["plan_layout_args"] = args
    if replaced:
        note = (
            " (Layout aus plan_layout/requirements übernommen — Core-Rezept statt freier "
            "Agent-Koordinaten/Öffnungen.)"
        )
        result["reply"] = (result.get("reply") or "").rstrip() + note
    return result


def _maybe_improve_replan(session, settings, messages, result: dict, conversation: str) -> dict:
    """If user asked for better layout but placement still matches last turn, force LLM replan."""
    if not _user_wants_better_layout(conversation):
        return result
    if not (result.get("commands") or []):
        return result
    fp = _placement_fingerprint(result.get("commands") or [])
    if placement.last_placement_fp is None or fp != placement.last_placement_fp:
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


def _finish_agent_result(
    session, settings, messages, result: dict, conversation: str, *, last_plan=None
) -> dict:
    result = _maybe_repair_proposal(settings, messages, result, conversation)
    result = _apply_plan_layout_baseline(session, result, conversation, last_plan)
    result = _apply_deterministic_placement_fixes(conversation, result)
    result = _attach_quality_preview(session, result)
    result = _maybe_hard_replan(session, settings, messages, result, conversation)
    result = _maybe_soft_replan(session, settings, messages, result, conversation)
    result = _maybe_improve_replan(session, settings, messages, result, conversation)
    fp = _placement_fingerprint(result.get("commands") or [])
    placement.last_placement_fp = fp
    _update_agent_state(session, result, conversation, last_plan=last_plan, placement_fp=fp)
    result["agent_state"] = dict(getattr(session, "agent_state", {}) or {})
    return result


def _update_agent_state(
    session, result: dict, conversation: str, *, last_plan=None, placement_fp=None
) -> None:
    state = getattr(session, "agent_state", None)
    if not isinstance(state, dict):
        from .session import empty_agent_state

        state = empty_agent_state()
        session.agent_state = state
    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else {}
    req = proposal.get("requirements")
    if not isinstance(req, dict) and last_plan and isinstance(last_plan.get("requirements"), dict):
        req = last_plan.get("requirements")
    if isinstance(req, dict):
        from .planning import normalize_requirements

        state["requirements"] = normalize_requirements(req)
    if _wants_bedroom_layout(conversation):
        state["goal"] = state.get("goal") or "Schlafzimmer planen"
    elif _user_wants_room(conversation):
        state["goal"] = state.get("goal") or "Raum planen"
    state["open_questions"] = list(result.get("questions") or [])
    state["last_proposal_id"] = (proposal.get("proposal_id") if proposal else None) or state.get(
        "last_proposal_id"
    )
    quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}
    if quality:
        state["last_analysis_summary"] = {
            "errors": (quality.get("summary") or {}).get("errors"),
            "warnings": (quality.get("summary") or {}).get("warnings"),
            "has_hard_errors": quality.get("has_hard_errors"),
            "has_soft_warnings": quality.get("has_soft_warnings"),
        }
    if placement_fp is not None:
        state["last_placement_fp"] = list(placement_fp) if placement_fp else None
    state["last_reply"] = (result.get("reply") or "")[:240]


def _bedroom_plan_fallback(session, conversation: str, *, error: str | None = None) -> dict:
    """Core-only recovery when LLM fails — never fall back to kids-room demo for bedrooms."""
    from .planning import merge_requirements, normalize_requirements, reconcile_plan_layout_params

    state = getattr(session, "agent_state", {}) or {}
    base_req = state.get("requirements") if isinstance(state.get("requirements"), dict) else None
    overlay = {
        "room_type": "bedroom",
        "doors": 1,
        "furniture": ["bed", "wardrobe", "desk"],
    }
    wc = _requested_window_count(conversation)
    if wc > 0:
        overlay["windows"] = wc
    elif not base_req:
        overlay["windows"] = 1
    size = _parse_room_size_m(conversation)
    if size:
        overlay["width"], overlay["depth"] = size
    bed = _parse_bed_size_m(conversation)
    if bed:
        overlay["bed_width"], overlay["bed_length"] = bed
    req = merge_requirements(base_req, overlay)
    args = reconcile_plan_layout_params({}, requirements=req)
    planned = dispatch_tool(session, "plan_layout", args)
    commands = sanitize_commands(planned.get("commands") or [])
    reply = "Schlafzimmer über Core-Rezept (plan_layout) geplant."
    if error:
        reply = f"(Agent/LLM fehlgeschlagen: {error}) {reply}"
    result = {
        "ok": True,
        "mode": "agent_fallback",
        "reply": reply,
        "questions": [],
        "proposal": {
            "proposal_id": str(uuid.uuid4()),
            "title": "Schlafzimmer (Core-Fallback)",
            "rationale": "LLM unavailable or crashed; requirements → plan_layout",
            "assumes": list(planned.get("assumes") or req.get("assumes") or []),
            "requirements": planned.get("requirements") or req,
            "commands": commands,
            "expected_risks": [],
        },
        "suggested_next_tools": [],
        "commands": commands,
        "tool_trace": [{"tool": "plan_layout", "arguments": args, "ok": bool(planned.get("ok"))}],
        "llm_error": error,
    }
    result = _attach_quality_preview(session, result)
    _update_agent_state(session, result, conversation, last_plan=planned, placement_fp=_placement_fingerprint(commands))
    result["agent_state"] = dict(getattr(session, "agent_state", {}) or {})
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
    _inject_agent_state_hint(session, messages)


def _inject_agent_state_hint(session, messages: list) -> None:
    """Surface light session memory to the LLM (not chat history)."""
    state = getattr(session, "agent_state", None)
    if not isinstance(state, dict):
        return
    if not any(
        state.get(k)
        for k in ("goal", "requirements", "last_proposal_id", "last_analysis_summary", "last_reply")
    ):
        return
    messages.append(
        {
            "role": "system",
            "content": (
                "Session agent_state (authoritative memory — reuse requirements on retry/"
                "„nochmal“; do not invent conflicting intent):\n"
                + json.dumps(state, ensure_ascii=False)
            ),
        }
    )


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
    requirements = proposal.get("requirements")
    if requirements is not None and not isinstance(requirements, dict):
        requirements = None
    if requirements is None and isinstance(parsed.get("requirements"), dict):
        requirements = parsed.get("requirements")
    out_proposal = {
        "proposal_id": proposal_id,
        "title": str(proposal.get("title") or "Vorschlag").strip(),
        "rationale": str(proposal.get("rationale") or "").strip(),
        "assumes": list(proposal.get("assumes") or []),
        "commands": commands,
        "expected_risks": list(proposal.get("expected_risks") or []),
    }
    if requirements is not None:
        from .planning import normalize_requirements

        out_proposal["requirements"] = normalize_requirements(requirements)
    return {
        "reply": str(parsed.get("reply") or "Vorschlag bereit.").strip(),
        "questions": list(parsed.get("questions") or []),
        "proposal": out_proposal,
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
        if _session_wants_bedroom_fallback(session, message):
            return _bedroom_plan_fallback(session, message)
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
    last_plan = None
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
                        session,
                        settings,
                        messages,
                        result,
                        conversation,
                        last_plan=last_plan,
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
                        tool_result = dispatch_tool(session, name, args)
                        err = None
                    except Exception as exc:
                        tool_result = {"ok": False, "error": str(exc)}
                        err = str(exc)
                    tool_trace.append(
                        {"tool": name, "arguments": args, "ok": err is None, "error": err}
                    )
                    if (
                        name == "plan_layout"
                        and err is None
                        and tool_result.get("ok")
                        and tool_result.get("commands")
                    ):
                        last_plan = {
                            "arguments": args,
                            "commands": tool_result.get("commands"),
                            "assumes": tool_result.get("assumes") or [],
                            "notes": tool_result.get("notes") or [],
                            "recipe": tool_result.get("recipe"),
                            "requirements": tool_result.get("requirements")
                            or args.get("requirements"),
                        }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id") or name,
                            "content": json.dumps(tool_result, ensure_ascii=False),
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
                    session,
                    settings,
                    messages,
                    result,
                    conversation,
                    last_plan=last_plan,
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
            return _finish_agent_result(
                session,
                settings,
                messages,
                result,
                conversation,
                last_plan=last_plan,
            )

        result = _finalize_proposal_from_messages(settings, messages, tool_trace)
        return _finish_agent_result(
            session, settings, messages, result, conversation, last_plan=last_plan
        )
    except Exception as exc:
        if _session_wants_bedroom_fallback(session, conversation):
            return _bedroom_plan_fallback(session, conversation, error=str(exc))
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
