"""Surface Core candidate selection in agent reply + session log (DD-011/017)."""

from __future__ import annotations

import re
from typing import Any

# Strip prior force / selection suffixes so we can re-attach a clean note.
_PLANNING_NOTE_RE = re.compile(
    r"\s*(?:\(|—)\s*(?:Layout über Core-Rezept|Layout aus plan_layout|"
    r"Layout vom Core-Rezept|Core-Vorschlag:).*?(?:\)|$)",
    re.IGNORECASE | re.DOTALL,
)


def slim_candidates(candidates: list | None, *, limit: int = 8) -> list[dict[str, Any]]:
    """Compact candidate rows for logs (no full command lists)."""
    out: list[dict[str, Any]] = []
    for c in (candidates or [])[:limit]:
        if not isinstance(c, dict):
            continue
        q = c.get("quality") if isinstance(c.get("quality"), dict) else {}
        soft = q.get("soft_summary") if isinstance(q.get("soft_summary"), dict) else {}
        entry: dict[str, Any] = {
            "candidate_id": c.get("candidate_id"),
            "strategy": c.get("strategy"),
        }
        if q:
            entry["has_hard_errors"] = bool(q.get("has_hard_errors"))
            entry["soft_warnings"] = int(soft.get("warnings") or 0)
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
    return {
        "recipe": planned.get("recipe"),
        "mode": planned.get("mode") or "candidates",
        "selected_id": planned.get("selected_id"),
        "strategy": planned.get("strategy"),
        "selection_reason": planned.get("selection_reason") or "",
        "shortlist_ids": shortlist,
        "candidate_count": len(planned.get("candidates") or candidates),
        "candidates": candidates,
        "revision_rounds": int(planned.get("revision_rounds") or 0),
    }


def format_planning_reply_note(summary: dict | None, *, enforced: bool = False) -> str:
    """Short German note for the user-facing reply (not debug jargon)."""
    if not isinstance(summary, dict):
        return ""
    selected = summary.get("selected_id")
    shortlist = list(summary.get("shortlist_ids") or [])
    n_cand = int(summary.get("candidate_count") or 0) or len(summary.get("candidates") or [])
    reason = str(summary.get("selection_reason") or "").strip()
    rounds = int(summary.get("revision_rounds") or 0)

    parts: list[str] = []
    if enforced and not selected:
        parts.append("Layout vom Core-Rezept.")
    if selected:
        if shortlist and n_cand:
            parts.append(
                f"Core-Vorschlag: {selected} "
                f"(Shortlist {len(shortlist)}/{n_cand})."
            )
        elif shortlist:
            parts.append(
                f"Core-Vorschlag: {selected} (Shortlist {len(shortlist)})."
            )
        else:
            parts.append(f"Core-Vorschlag: {selected}.")
    if reason:
        parts.append(reason)
    if rounds > 0 and "Revision" not in reason:
        parts.append(f"Revision: {rounds} Runde(n).")
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
    if isinstance(planned, dict):
        for key in (
            "selected_id",
            "shortlist_ids",
            "selection_reason",
            "revision_rounds",
            "strategy",
            "recipe",
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
