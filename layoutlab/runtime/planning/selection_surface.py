"""Surface Core candidate selection in agent reply + session log (DD-011/017).

Also: persist shortlist entries with commands for user/AI re-selection before Apply.
"""

from __future__ import annotations

import re
from typing import Any

# Strip prior force / selection suffixes so we can re-attach a clean note.
_PLANNING_NOTE_RE = re.compile(
    r"\s*(?:\(|—)\s*(?:Layout über Core-Rezept|Layout aus plan_layout|"
    r"Layout vom Core-Rezept|Core-Vorschlag:|Gewählt:).*?(?:\)|$)",
    re.IGNORECASE | re.DOTALL,
)

_ORDINAL_DE = {
    1: ("1", "erste", "erster", "erstes", "eins"),
    2: ("2", "zweite", "zweiter", "zweites", "zwei"),
    3: ("3", "dritte", "dritter", "drittes", "drei"),
    4: ("4", "vierte", "vierter", "viertes", "vier"),
}

_WALL_DE = {
    "north": "Nord",
    "south": "Süd",
    "east": "Ost",
    "west": "West",
}


def strategy_label_de(strategy: str | None) -> str:
    """Readable German label for recipe strategy / candidate ids."""
    s = str(strategy or "").strip().lower()
    if not s:
        return "Variante"

    bed_wall = None
    for wall in ("north", "south", "east", "west"):
        if f"bed_{wall}" in s:
            bed_wall = wall
            break

    if "storage_swapped" in s:
        storage = "Schrank eher Ost"
    elif "wardrobe_east" in s:
        storage = "Schrank Ost"
    elif "wardrobe_west" in s:
        storage = "Schrank West"
    elif "storage_north" in s:
        storage = "Stauraum Nord"
    elif "storage_south" in s:
        storage = "Stauraum Süd"
    elif "storage_east" in s:
        storage = "Stauraum Ost"
    elif "storage_west" in s:
        storage = "Stauraum West"
    else:
        storage = None

    if bed_wall and storage:
        return f"Bett {_WALL_DE[bed_wall]}wand, {storage}"
    if bed_wall:
        return f"Bett {_WALL_DE[bed_wall]}wand"
    if storage:
        return storage
    # Fallback: humanize raw id
    return s.replace("__", " · ").replace("_", " ")


def slim_candidates(candidates: list | None, *, limit: int = 8) -> list[dict[str, Any]]:
    """Compact candidate rows for logs (no full command lists / sketches)."""
    out: list[dict[str, Any]] = []
    for c in (candidates or [])[:limit]:
        if not isinstance(c, dict):
            continue
        q = c.get("quality") if isinstance(c.get("quality"), dict) else {}
        soft = q.get("soft_summary") if isinstance(q.get("soft_summary"), dict) else {}
        sid = c.get("strategy") or c.get("candidate_id")
        entry: dict[str, Any] = {
            "candidate_id": c.get("candidate_id"),
            "strategy": c.get("strategy"),
            "label_de": c.get("label_de") or strategy_label_de(sid),
        }
        if q:
            entry["has_hard_errors"] = bool(q.get("has_hard_errors"))
            entry["soft_warnings"] = int(soft.get("warnings") or q.get("soft_warnings") or 0)
        out.append(entry)
    return out


def _slim_quality_preview(quality: dict | None) -> dict[str, Any] | None:
    if not isinstance(quality, dict):
        return None
    soft = quality.get("soft_summary") if isinstance(quality.get("soft_summary"), dict) else {}
    return {
        "ok": quality.get("ok"),
        "has_hard_errors": bool(quality.get("has_hard_errors")),
        "has_soft_warnings": bool(
            quality.get("has_soft_warnings")
            or int(soft.get("warnings") or quality.get("soft_warnings") or 0) > 0
        ),
        "summary": quality.get("summary"),
        "soft_summary": soft
        or {
            "warnings": int(quality.get("soft_warnings") or 0),
            "info": int(quality.get("soft_info") or 0),
        },
        "soft_warnings": int(soft.get("warnings") or quality.get("soft_warnings") or 0),
        "needs_user_confirm": bool(
            quality.get("has_hard_errors")
            or int(soft.get("warnings") or quality.get("soft_warnings") or 0) > 0
        ),
        "blocks_apply": False,
        "has_solid_collisions": False,
    }


def _sketch_from_candidate(c: dict) -> tuple[str | None, dict | None]:
    sketch = c.get("layout_sketch")
    if not isinstance(sketch, dict):
        q = c.get("quality") if isinstance(c.get("quality"), dict) else {}
        sketch = q.get("layout_sketch") if isinstance(q.get("layout_sketch"), dict) else None
    if not isinstance(sketch, dict):
        return None, None
    ascii_map = sketch.get("ascii")
    legend = sketch.get("legend") if isinstance(sketch.get("legend"), dict) else None
    return (str(ascii_map) if ascii_map else None), legend


def shortlist_entries_from_planned(planned: dict | None) -> list[dict[str, Any]]:
    """Shortlist members with commands + DE label + sketch — Viewer cards (DD-017)."""
    if not isinstance(planned, dict):
        return []
    shortlist_ids = list(planned.get("shortlist_ids") or [])
    if not shortlist_ids:
        return []
    by_id = {
        c.get("candidate_id"): c
        for c in (planned.get("candidates") or [])
        if isinstance(c, dict) and c.get("candidate_id")
    }
    selected = planned.get("selected_id")
    out: list[dict[str, Any]] = []
    for cid in shortlist_ids:
        c = by_id.get(cid)
        if not c:
            continue
        cmds = list(c.get("commands") or [])
        if not cmds:
            continue
        strategy = c.get("strategy") or cid
        label = c.get("label_de") or strategy_label_de(strategy)
        ascii_map, legend = _sketch_from_candidate(c)
        entry: dict[str, Any] = {
            "candidate_id": cid,
            "strategy": strategy,
            "label_de": label,
            "commands": cmds,
            "recommended": bool(c.get("recommended")) or cid == selected,
        }
        aesthetic = planned.get("aesthetic") if isinstance(planned.get("aesthetic"), dict) else {}
        if aesthetic.get("recommended_id") == cid:
            entry["aesthetic_recommended"] = True
        if ascii_map:
            entry["sketch_ascii"] = ascii_map
        if legend:
            entry["sketch_legend"] = legend
        preview = c.get("viewer_preview")
        if isinstance(preview, dict) and (preview.get("rooms") or preview.get("objects")):
            entry["viewer_preview"] = preview
        q = _slim_quality_preview(c.get("quality") if isinstance(c.get("quality"), dict) else None)
        if q:
            entry["quality"] = q
        out.append(entry)
    return out


def planning_summary_from_planned(planned: dict | None) -> dict[str, Any] | None:
    """Build a log/reply-ready planning summary from plan_layout output."""
    if not isinstance(planned, dict):
        return None
    if not (
        planned.get("selected_id")
        or planned.get("shortlist_ids")
        or planned.get("candidates")
        or planned.get("mode") == "candidates"
    ):
        return None
    candidates = slim_candidates(planned.get("candidates"))
    shortlist = list(planned.get("shortlist_ids") or [])
    selected = planned.get("selected_id")
    selected_label = None
    if selected:
        for c in candidates:
            if c.get("candidate_id") == selected:
                selected_label = c.get("label_de")
                break
        if not selected_label:
            selected_label = strategy_label_de(planned.get("strategy") or selected)
    return {
        "recipe": planned.get("recipe"),
        "mode": planned.get("mode") or "candidates",
        "selected_id": selected,
        "selected_label_de": selected_label,
        "strategy": planned.get("strategy"),
        "selection_reason": planned.get("selection_reason") or "",
        "shortlist_ids": shortlist,
        "candidate_count": len(planned.get("candidates") or candidates),
        "candidates": candidates,
        "revision_rounds": int(planned.get("revision_rounds") or 0),
        "aesthetic": planned.get("aesthetic") if isinstance(planned.get("aesthetic"), dict) else None,
    }


def format_planning_reply_note(summary: dict | None, *, enforced: bool = False) -> str:
    """Short German note for the user-facing reply (not debug jargon)."""
    if not isinstance(summary, dict):
        return ""
    selected = summary.get("selected_id")
    selected_label = summary.get("selected_label_de") or strategy_label_de(
        summary.get("strategy") or selected
    )
    shortlist = list(summary.get("shortlist_ids") or [])
    n_cand = int(summary.get("candidate_count") or 0) or len(summary.get("candidates") or [])
    reason = str(summary.get("selection_reason") or "").strip()
    rounds = int(summary.get("revision_rounds") or 0)
    by_id = {
        c.get("candidate_id"): c.get("label_de") or strategy_label_de(c.get("strategy"))
        for c in (summary.get("candidates") or [])
        if isinstance(c, dict) and c.get("candidate_id")
    }

    parts: list[str] = []
    if enforced and not selected:
        parts.append("Layout vom Core-Rezept.")
    if selected:
        label = selected_label or selected
        if shortlist and n_cand:
            parts.append(
                f"Core-Vorschlag: {label} "
                f"(Shortlist {len(shortlist)}/{n_cand})."
            )
        elif shortlist:
            parts.append(f"Core-Vorschlag: {label} (Shortlist {len(shortlist)}).")
        else:
            parts.append(f"Core-Vorschlag: {label}.")
    if reason:
        cleaned = reason
        if selected and cleaned.startswith("Gewählt aus Shortlist:"):
            if "—" in cleaned:
                cleaned = cleaned.split("—", 1)[1].strip()
            elif " - " in cleaned:
                cleaned = cleaned.split(" - ", 1)[1].strip()
        if cleaned and cleaned not in " ".join(parts):
            parts.append(cleaned)
    if rounds > 0 and "Revision" not in reason:
        parts.append(f"Revision: {rounds} Runde(n).")
    aesthetic = summary.get("aesthetic") if isinstance(summary.get("aesthetic"), dict) else None
    if aesthetic and aesthetic.get("summary_de"):
        parts.append(f"Ästhetik (experimentell): {aesthetic['summary_de']}")
    if shortlist and len(shortlist) > 1:
        others = []
        for sid in shortlist:
            if sid == selected:
                continue
            others.append(by_id.get(sid) or strategy_label_de(sid))
            if len(others) >= 3:
                break
        if others:
            parts.append(
                "Alternativen: " + "; ".join(others) + " (Viewer oder „Variante 2“)."
            )
    return " ".join(parts).strip()


def strip_planning_notes(reply: str) -> str:
    text = (reply or "").rstrip()
    prev = None
    while prev != text:
        prev = text
        text = _PLANNING_NOTE_RE.sub("", text).rstrip()
    return text


def merge_planning_into_result(
    result: dict, planned: dict | None, *, enforced: bool = False
) -> dict:
    """Copy selection fields onto the agent result and append a reply note."""
    result = dict(result)
    summary = planning_summary_from_planned(planned)
    shortlist = shortlist_entries_from_planned(planned)
    if isinstance(planned, dict):
        for key in (
            "selected_id",
            "shortlist_ids",
            "selection_reason",
            "revision_rounds",
            "strategy",
            "recipe",
            "aesthetic",
        ):
            if key in planned:
                result[key] = planned[key]
    if summary:
        result["planning"] = summary
        note = format_planning_reply_note(summary, enforced=enforced)
        if note:
            base = strip_planning_notes(result.get("reply") or "")
            result["reply"] = f"{base} — {note}" if base else note
    elif enforced:
        base = strip_planning_notes(result.get("reply") or "")
        note = "Layout vom Core-Rezept."
        result["reply"] = f"{base} — {note}" if base else note
        result["plan_layout_enforced"] = True
    if shortlist:
        result["shortlist"] = shortlist
    if enforced:
        result["plan_layout_enforced"] = True
    return result


def append_plan_layout_trace(
    result: dict, args: dict | None, *, ok: bool, enforced: bool = False
) -> dict:
    """Ensure plan_layout appears in tool_trace / Tools line when Core forced planning."""
    result = dict(result)
    trace = list(result.get("tool_trace") or [])
    already = any(
        isinstance(t, dict) and t.get("tool") == "plan_layout" for t in trace
    )
    if not already:
        entry: dict[str, Any] = {
            "tool": "plan_layout",
            "arguments": {
                "mode": (args or {}).get("mode") or "candidates",
                "recipe": (args or {}).get("recipe"),
            },
            "ok": bool(ok),
        }
        if enforced:
            entry["enforced"] = True
        trace.append(entry)
        result["tool_trace"] = trace
    return result


def stored_shortlist(session) -> list[dict[str, Any]]:
    state = getattr(session, "agent_state", None) or {}
    if not isinstance(state, dict):
        return []
    items = state.get("last_shortlist")
    return list(items) if isinstance(items, list) else []


def resolve_shortlist_selection(
    text: str, shortlist: list[dict[str, Any]] | None
) -> str | None:
    """Map user text → shortlist candidate_id, or None if not a selection turn."""
    items = [c for c in (shortlist or []) if isinstance(c, dict) and c.get("candidate_id")]
    if not items:
        return None
    t = (text or "").strip().lower()
    if not t:
        return None

    ids = [str(c["candidate_id"]) for c in items]
    # Exact / substring id match (prefer longest)
    for cid in sorted(ids, key=len, reverse=True):
        if cid.lower() in t:
            return cid

    # German label match (e.g. "bett nordwand")
    for c in items:
        label = str(c.get("label_de") or "").strip().lower()
        if label and len(label) >= 8 and label in t:
            return c["candidate_id"]

    # "variante 2" / "option 2" / "die zweite" / "nimm 2"
    for idx, words in _ORDINAL_DE.items():
        if idx > len(items):
            continue
        for w in words:
            patterns = (
                rf"\bvariante\s+{re.escape(w)}\b",
                rf"\boption\s+{re.escape(w)}\b",
                rf"\bvorschlag\s+{re.escape(w)}\b",
                rf"\bdie\s+{re.escape(w)}\b",
                rf"\bden\s+{re.escape(w)}\b",
                rf"\bnimm\s+(?:die\s+|den\s+)?{re.escape(w)}\b",
                rf"\bwähle\s+(?:die\s+|den\s+)?{re.escape(w)}\b",
                rf"\bwaehle\s+(?:die\s+|den\s+)?{re.escape(w)}\b",
            )
            if any(re.search(p, t) for p in patterns):
                return items[idx - 1]["candidate_id"]
        if re.search(rf"\b(?:variante|option|vorschlag)\s+{idx}\b", t):
            return items[idx - 1]["candidate_id"]
        if re.search(rf"\bnimm\s+{idx}\b", t):
            return items[idx - 1]["candidate_id"]

    # "andere" / "alternative" → next after recommended, else second
    if any(k in t for k in ("andere", "alternative", "anders")):
        rec_i = next((i for i, c in enumerate(items) if c.get("recommended")), 0)
        return items[(rec_i + 1) % len(items)]["candidate_id"]

    return None


def wants_shortlist_selection(text: str, shortlist: list | None) -> bool:
    """True when the message looks like choosing among a stored shortlist."""
    return resolve_shortlist_selection(text, shortlist) is not None


def apply_shortlist_selection(
    *,
    session,
    candidate_id: str,
    shortlist: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an agent result that switches proposal.commands to a shortlist member."""
    items = shortlist if shortlist is not None else stored_shortlist(session)
    chosen = next(
        (c for c in items if isinstance(c, dict) and c.get("candidate_id") == candidate_id),
        None,
    )
    if not chosen or not chosen.get("commands"):
        return {
            "ok": False,
            "mode": "select_candidate",
            "error": f"candidate not in shortlist: {candidate_id}",
            "reply": (
                f"Die Variante `{candidate_id}` ist nicht in der aktuellen Shortlist. "
                "Bitte eine Shortlist-Option wählen."
            ),
            "questions": [],
            "commands": [],
            "proposal": {"commands": [], "title": "Auswahl fehlgeschlagen"},
            "shortlist": items,
            "tool_trace": [{"tool": "select_layout_candidate", "ok": False}],
        }

    commands = list(chosen["commands"])
    ids = [str(c.get("candidate_id")) for c in items if c.get("candidate_id")]
    quality = chosen.get("quality") if isinstance(chosen.get("quality"), dict) else None
    label = chosen.get("label_de") or strategy_label_de(
        chosen.get("strategy") or candidate_id
    )
    # Refresh recommended flags
    refreshed = []
    for c in items:
        if not isinstance(c, dict):
            continue
        row = dict(c)
        row["recommended"] = row.get("candidate_id") == candidate_id
        if not row.get("label_de"):
            row["label_de"] = strategy_label_de(row.get("strategy") or row.get("candidate_id"))
        refreshed.append(row)

    reply = (
        f"Gewählt: {label} "
        f"(Shortlist {len(ids)}). Apply übernimmt diese Variante."
    )
    result: dict[str, Any] = {
        "ok": True,
        "mode": "select_candidate",
        "reply": reply,
        "questions": [],
        "commands": commands,
        "proposal": {
            "title": label,
            "rationale": "User/AI selection from Core functional shortlist (DD-017)",
            "assumes": [],
            "commands": commands,
            "expected_risks": [],
        },
        "selected_id": candidate_id,
        "shortlist_ids": ids,
        "selection_reason": f"Nutzerwahl: {label}",
        "shortlist": refreshed,
        "planning": {
            "selected_id": candidate_id,
            "selected_label_de": label,
            "strategy": chosen.get("strategy") or candidate_id,
            "selection_reason": f"Nutzerwahl: {label}",
            "shortlist_ids": ids,
            "candidate_count": len(ids),
            "candidates": [
                {
                    "candidate_id": c.get("candidate_id"),
                    "strategy": c.get("strategy"),
                    "label_de": c.get("label_de")
                    or strategy_label_de(c.get("strategy") or c.get("candidate_id")),
                    "soft_warnings": int(
                        ((c.get("quality") or {}).get("soft_warnings"))
                        or ((c.get("quality") or {}).get("soft_summary") or {}).get("warnings")
                        or 0
                    ),
                    "has_hard_errors": bool((c.get("quality") or {}).get("has_hard_errors")),
                }
                for c in refreshed
            ],
            "revision_rounds": 0,
            "selection_source": "user",
        },
        "plan_layout_enforced": True,
        "tool_trace": [
            {
                "tool": "select_layout_candidate",
                "arguments": {"candidate_id": candidate_id},
                "ok": True,
            }
        ],
    }
    if quality:
        result["quality"] = quality
    return result
