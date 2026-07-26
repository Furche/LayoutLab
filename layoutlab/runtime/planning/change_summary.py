"""FC-002/WP-04 — semantic change summaries from transaction operations (DD-018 §7)."""

from __future__ import annotations

from typing import Any


def _cmd_params(cmd: dict) -> dict:
    params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
    return params


def _oid(cmd: dict) -> str | None:
    params = _cmd_params(cmd)
    raw = cmd.get("object_id") or params.get("object_id")
    return str(raw) if raw else None


def _short_id(oid: str | None) -> str:
    if not oid:
        return "Objekt"
    return oid if len(oid) <= 12 else f"{oid[:8]}…"


def describe_operation(cmd: dict) -> str | None:
    """One domain-language line for a committed command (DE)."""
    if not isinstance(cmd, dict):
        return None
    action = str(cmd.get("action") or "").strip()
    params = _cmd_params(cmd)
    oid = _oid(cmd)

    if action in ("move", "move_object"):
        loc = params.get("location") or cmd.get("location")
        if isinstance(loc, (list, tuple)) and len(loc) >= 2:
            try:
                x, y = float(loc[0]), float(loc[1])
                return f"{_short_id(oid)} verschoben (≈ {x:.2f}, {y:.2f} m)"
            except (TypeError, ValueError):
                pass
        return f"{_short_id(oid)} verschoben"

    if action in ("rotate", "rotate_object", "rotate_z"):
        deg = params.get("rotation_euler_deg") or params.get("rotation_z_deg") or cmd.get(
            "rotation_z_deg"
        )
        if isinstance(deg, (list, tuple)) and len(deg) >= 3:
            try:
                return f"{_short_id(oid)} rotiert (Z≈ {float(deg[2]):.0f}°)"
            except (TypeError, ValueError):
                pass
        if deg is not None:
            try:
                return f"{_short_id(oid)} rotiert (≈ {float(deg):.0f}°)"
            except (TypeError, ValueError):
                pass
        return f"{_short_id(oid)} rotiert"

    if action in ("resize", "set_params", "update_params"):
        keys = sorted(
            k
            for k in params.keys()
            if k not in ("object_id", "location", "rotation_euler_deg")
        )
        if keys:
            return f"{_short_id(oid)} Parameter geändert ({', '.join(keys[:4])})"
        return f"{_short_id(oid)} Größe/Parameter geändert"

    if action == "place_on":
        host = params.get("host_object_id") or cmd.get("host_object_id")
        surf = params.get("surface_id") or cmd.get("surface_id") or "surface"
        return f"{_short_id(oid)} auf {_short_id(str(host) if host else None)}.{surf} platziert"

    if action == "set_support":
        ref = params.get("support_ref") or cmd.get("support_ref")
        return f"{_short_id(oid)} Support → {ref or '?'}"

    if action == "run_generator":
        gen = params.get("generator") or cmd.get("generator") or "generator"
        return f"Möbel hinzugefügt ({gen})"

    if action in ("delete_object", "remove_object"):
        return f"{_short_id(oid)} gelöscht"

    if action == "duplicate_object":
        return f"{_short_id(oid)} dupliziert"

    if action == "create_room":
        name = params.get("name") or cmd.get("name") or "Raum"
        w = params.get("width")
        d = params.get("depth")
        if w is not None and d is not None:
            return f"Raum „{name}“ erstellt ({w}×{d} m)"
        return f"Raum „{name}“ erstellt"

    if action == "delete_room":
        return "Raum gelöscht"

    if action == "add_opening":
        kind = params.get("kind") or cmd.get("kind") or "opening"
        return f"Öffnung hinzugefügt ({kind})"

    if action == "remove_opening":
        return "Öffnung entfernt"

    if action in ("move_wall", "move_corner"):
        return f"Raumgrundriss geändert ({action})"

    if action in ("move_room", "rotate_room", "rotate_room_z"):
        return f"Raum transformiert ({action})"

    if action in ("delete_collection_objects", "delete_prefix"):
        return "Objekte gelöscht (Sammlung/Präfix)"

    if action == "select_object":
        return None  # ephemeral / noise

    if action:
        return f"{action}" + (f" ({_short_id(oid)})" if oid else "")
    return None


def summarize_transaction_record(record: dict | Any) -> dict:
    """Project one TransactionRecord to a summary entry."""
    if hasattr(record, "to_dict"):
        data = record.to_dict()
    elif isinstance(record, dict):
        data = dict(record)
    else:
        data = {}
    ops = data.get("operations") or []
    lines = []
    for cmd in ops:
        line = describe_operation(cmd if isinstance(cmd, dict) else {})
        if line:
            lines.append(line)
    return {
        "actor": data.get("actor"),
        "action": data.get("action"),
        "base_revision": data.get("base_revision"),
        "result_revision": data.get("result_revision"),
        "description": data.get("description") or "",
        "timestamp": data.get("timestamp"),
        "operation_count": len(ops),
        "lines": lines,
    }


def summarize_changes(
    session,
    *,
    from_revision: int | None = None,
    to_revision: int | None = None,
) -> dict:
    """Core change summary between two revisions (DD-018 §7 / FC-002/WP-04).

    Uses the session Undo/transaction window only — no mesh diffs.
    """
    current = int(getattr(session, "revision", 0) or 0)
    to_rev = current if to_revision is None else int(to_revision)
    if from_revision is None:
        state = getattr(session, "agent_state", None) or {}
        raw = state.get("last_observed_revision")
        from_rev = int(raw) if raw is not None else 0
    else:
        from_rev = int(from_revision)

    history = getattr(session, "_undo", None)
    records = list(history.records()) if history is not None else []
    oldest_base = history.oldest_base_revision if history is not None else None

    if from_rev > to_rev:
        return {
            "ok": False,
            "error": "from_revision must be <= to_revision",
            "from_revision": from_rev,
            "to_revision": to_rev,
            "current_revision": current,
            "changes": [],
            "lines": [],
            "history_available": False,
        }

    if from_rev == to_rev:
        return {
            "ok": True,
            "from_revision": from_rev,
            "to_revision": to_rev,
            "current_revision": current,
            "changes": [],
            "lines": [],
            "history_available": True,
            "note": "No revision delta",
        }

    # History window: if from_rev is older than what Undo still holds, report unavailable.
    if records and oldest_base is not None and from_rev < int(oldest_base):
        return {
            "ok": True,
            "from_revision": from_rev,
            "to_revision": to_rev,
            "current_revision": current,
            "changes": [],
            "lines": [],
            "history_available": False,
            "oldest_available_base_revision": int(oldest_base),
            "note": "History unavailable beyond Undo window — no mesh-diff fallback",
        }

    selected = [
        r
        for r in records
        if int(r.result_revision) > from_rev and int(r.result_revision) <= to_rev
    ]
    # If we expected commits but stack is empty while revisions advanced outside undo
    if not selected and from_rev < to_rev and not records and to_rev > 0:
        return {
            "ok": True,
            "from_revision": from_rev,
            "to_revision": to_rev,
            "current_revision": current,
            "changes": [],
            "lines": [],
            "history_available": False,
            "note": "History unavailable — no committed transactions in Undo window",
        }

    changes = [summarize_transaction_record(r) for r in selected]
    lines: list[str] = []
    for ch in changes:
        for line in ch.get("lines") or []:
            lines.append(line)
        if not ch.get("lines") and ch.get("description"):
            lines.append(str(ch["description"]))

    return {
        "ok": True,
        "from_revision": from_rev,
        "to_revision": to_rev,
        "current_revision": current,
        "transaction_count": len(changes),
        "changes": changes,
        "lines": lines,
        "history_available": True,
    }


def format_change_summary_de(summary: dict) -> str:
    """Short German prose block for chat replies."""
    if not summary.get("ok"):
        return ""
    if summary.get("history_available") is False:
        return (
            "Seit meiner letzten Beobachtung kann ich die Änderungen nicht mehr "
            "vollständig aus der Undo-Historie lesen (Fenster überschritten)."
        )
    lines = list(summary.get("lines") or [])
    if not lines:
        return "Seit meiner letzten Beobachtung sehe ich keine committed semantischen Änderungen."
    shown = lines[:12]
    body = "\n".join(f"- {ln}" for ln in shown)
    more = len(lines) - len(shown)
    header = (
        f"Seit Revision {summary.get('from_revision')} → {summary.get('to_revision')} "
        f"({summary.get('transaction_count', 0)} Transaktion(en)):"
    )
    if more > 0:
        body += f"\n- … und {more} weitere"
    return f"{header}\n{body}"
