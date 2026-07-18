"""Session interaction log for Core (chat, proposals, apply, quality).

Writes under ``<repo>/logs/``:
- ``session.jsonl`` — append-only structured events (current Core process)
- ``LAST_SESSION.md`` — human-readable rolling summary for agent/debug inspection

No API keys or full LLM payloads are stored.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = _ROOT / "logs"
JSONL_PATH = LOG_DIR / "session.jsonl"
MARKDOWN_PATH = LOG_DIR / "LAST_SESSION.md"

_lock = threading.Lock()
_session_id: str | None = None
_started_at: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _ensure_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def start_session(*, label: str = "core") -> str:
    """Begin a new log for this Core process.

    Previous ``session.jsonl`` / ``LAST_SESSION.md`` are archived under ``logs/archive/``
    so a Core restart does not erase the last conversation for inspection.
    """
    global _session_id, _started_at
    with _lock:
        _ensure_dir()
        archive = LOG_DIR / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        stamp = _utc_now().replace(":", "").replace(".", "-")
        if JSONL_PATH.is_file() and JSONL_PATH.stat().st_size > 0:
            JSONL_PATH.replace(archive / f"session-{stamp}.jsonl")
        if MARKDOWN_PATH.is_file() and MARKDOWN_PATH.stat().st_size > 0:
            # Keep a stable pointer to the previous transcript for quick reading.
            prev = LOG_DIR / "PREV_SESSION.md"
            MARKDOWN_PATH.replace(prev)
            try:
                prev_bytes = prev.read_bytes()
                (archive / f"session-{stamp}.md").write_bytes(prev_bytes)
            except OSError:
                pass

        _started_at = _utc_now()
        _session_id = f"{label}-{_started_at.replace(':', '').replace('.', '-')}"
        JSONL_PATH.write_text("", encoding="utf-8")
        event = {
            "ts": _started_at,
            "session_id": _session_id,
            "type": "session_start",
            "label": label,
        }
        with JSONL_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        _rewrite_markdown_unlocked()
        return _session_id


def _slim_commands(commands, limit=40):
    out = []
    for cmd in (commands or [])[:limit]:
        if not isinstance(cmd, dict):
            continue
        entry = {"action": cmd.get("action")}
        if cmd.get("generator"):
            entry["generator"] = cmd.get("generator")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        # Keep placement-relevant crumbs only
        for key in ("name", "room", "kind", "wall_side", "location", "width", "depth", "length", "collection"):
            if key in params:
                entry[key] = params[key]
            elif key in cmd and key not in ("action", "generator", "params"):
                entry[key] = cmd[key]
        out.append(entry)
    return out


def _slim_quality(quality: dict | None) -> dict | None:
    if not isinstance(quality, dict):
        return None
    return {
        "ok": quality.get("ok"),
        "has_hard_errors": quality.get("has_hard_errors"),
        "has_solid_collisions": quality.get("has_solid_collisions"),
        "has_soft_warnings": quality.get("has_soft_warnings"),
        "has_expected_risks": quality.get("has_expected_risks"),
        "needs_user_confirm": quality.get("needs_user_confirm"),
        "blocks_apply": quality.get("blocks_apply"),
        "summary": quality.get("summary"),
        "soft_summary": quality.get("soft_summary"),
        "solid_messages": quality.get("solid_messages") or [],
        "finding_types": sorted(
            {
                f.get("constraint_type")
                for f in (quality.get("findings") or [])
                if isinstance(f, dict) and f.get("constraint_type")
            }
        ),
    }


def log_event(event_type: str, **payload) -> None:
    """Append one event immediately and refresh LAST_SESSION.md (flush to disk)."""
    global _session_id, _started_at
    with _lock:
        _ensure_dir()
        if not _session_id:
            _started_at = _utc_now()
            _session_id = f"core-{_started_at.replace(':', '').replace('.', '-')}"
        event = {
            "ts": _utc_now(),
            "session_id": _session_id,
            "type": event_type,
            **payload,
        }
        with JSONL_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
            fh.flush()
        _rewrite_markdown_unlocked()


def log_agent_turn(*, message: str, history_len: int, result: dict) -> None:
    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else {}
    commands = result.get("commands") or proposal.get("commands") or []
    tool_trace = result.get("tool_trace") or []
    log_event(
        "agent_turn",
        user_message=message,
        history_len=history_len,
        mode=result.get("mode"),
        reply=result.get("reply") or "",
        questions=result.get("questions") or [],
        proposal_title=proposal.get("title") or "",
        assumes=proposal.get("assumes") or [],
        expected_risks=proposal.get("expected_risks") or [],
        commands=_slim_commands(commands),
        command_count=len(commands),
        tools_used=[t.get("tool") for t in tool_trace if isinstance(t, dict)],
        quality=_slim_quality(result.get("quality") if isinstance(result.get("quality"), dict) else None),
        ok=result.get("ok"),
        error=result.get("error"),
    )


def log_apply(*, commands: list, result: dict, source: str = "commands") -> None:
    analysis = (result.get("export") or {}).get("analysis") if isinstance(result.get("export"), dict) else None
    summary = (analysis or {}).get("summary") if isinstance(analysis, dict) else None
    soft = (analysis or {}).get("soft_summary") if isinstance(analysis, dict) else None
    findings = (analysis or {}).get("findings") if isinstance(analysis, dict) else []
    finding_msgs = []
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        if f.get("severity") in ("error", "warning") or f.get("non_negotiable"):
            finding_msgs.append(
                f"{f.get('severity')}: {f.get('constraint_type')} — {f.get('message')}"
            )
    log_event(
        "apply_commands",
        source=source,
        commands=_slim_commands(commands),
        command_count=len(commands or []),
        ok=result.get("ok"),
        errors=result.get("errors") or [],
        analysis_summary=summary,
        soft_summary=soft,
        warnings=finding_msgs[:20],
        room_count=len(((result.get("export") or {}).get("rooms") or [])),
        object_count=len(((result.get("export") or {}).get("objects") or [])),
    )


def _read_events() -> list:
    if not JSONL_PATH.is_file():
        return []
    events = []
    for line in JSONL_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _rewrite_markdown_unlocked() -> None:
    events = _read_events()
    lines = [
        "# LayoutLab last session",
        "",
        f"- session_id: `{_session_id or '—'}`",
        f"- started: `{_started_at or '—'}`",
        f"- events: {len(events)}",
        f"- jsonl: `{JSONL_PATH.relative_to(_ROOT)}`",
        "",
        "---",
        "",
    ]
    for ev in events:
        et = ev.get("type")
        ts = ev.get("ts", "")
        if et == "session_start":
            lines.append(f"## {ts} · session start")
            lines.append("")
            continue
        if et == "agent_turn":
            lines.append(f"## {ts} · agent turn (`{ev.get('mode')}`)")
            lines.append("")
            lines.append(f"**User:** {ev.get('user_message') or ''}")
            lines.append("")
            lines.append(f"**AI:** {ev.get('reply') or ''}")
            lines.append("")
            qs = ev.get("questions") or []
            if qs:
                lines.append("**Questions:**")
                for q in qs:
                    lines.append(f"- {q}")
                lines.append("")
            risks = ev.get("expected_risks") or []
            if risks:
                lines.append("**expected_risks:**")
                for r in risks:
                    lines.append(f"- {r}")
                lines.append("")
            cmds = ev.get("commands") or []
            lines.append(f"**Commands ({ev.get('command_count', len(cmds))}):**")
            if cmds:
                lines.append("```json")
                lines.append(json.dumps(cmds, ensure_ascii=False, indent=2))
                lines.append("```")
            else:
                lines.append("_none_")
            lines.append("")
            quality = ev.get("quality")
            if quality:
                lines.append("**Quality:**")
                lines.append("```json")
                lines.append(json.dumps(quality, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
            tools = ev.get("tools_used") or []
            if tools:
                lines.append(f"**Tools:** {', '.join(str(t) for t in tools)}")
                lines.append("")
            continue
        if et == "apply_commands":
            lines.append(f"## {ts} · apply (`{ev.get('source')}`)")
            lines.append("")
            lines.append(f"- ok: `{ev.get('ok')}`")
            lines.append(f"- rooms/objects after: `{ev.get('room_count')}` / `{ev.get('object_count')}`")
            if ev.get("analysis_summary"):
                lines.append(f"- analysis: `{json.dumps(ev.get('analysis_summary'))}`")
            if ev.get("soft_summary"):
                lines.append(f"- soft: `{json.dumps(ev.get('soft_summary'))}`")
            warns = ev.get("warnings") or []
            if warns:
                lines.append("**Warnings / errors:**")
                for w in warns:
                    lines.append(f"- {w}")
            errs = ev.get("errors") or []
            if errs:
                lines.append("**Apply errors:**")
                lines.append("```json")
                lines.append(json.dumps(errs, ensure_ascii=False, indent=2))
                lines.append("```")
            cmds = ev.get("commands") or []
            lines.append("")
            lines.append(f"**Commands applied ({ev.get('command_count', len(cmds))}):**")
            lines.append("```json")
            lines.append(json.dumps(cmds, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
            continue
        lines.append(f"## {ts} · {et}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(ev, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    MARKDOWN_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def latest_summary() -> dict:
    """Return paths + last few events for HTTP/debug."""
    with _lock:
        events = _read_events()
        return {
            "ok": True,
            "session_id": _session_id,
            "started_at": _started_at,
            "jsonl": str(JSONL_PATH),
            "markdown": str(MARKDOWN_PATH),
            "event_count": len(events),
            "events_tail": events[-20:],
        }
