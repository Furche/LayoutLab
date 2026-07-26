"""FC-002/WP-03 — semantic conversation state, focus, preferences (DD-022)."""

from __future__ import annotations

import re
from typing import Any

AGENT_STATE_SCHEMA = "0.3.0"
FOCUS_STACK_MAX = 5

PROVENANCE_EXPLICIT = "explicit"
PROVENANCE_INFERRED = "inferred"
PROVENANCE_PROJECT_DEFAULT = "project_default"
PROVENANCE_TURN_TEMPORARY = "turn_temporary"

VALID_PROVENANCE = frozenset(
    {
        PROVENANCE_EXPLICIT,
        PROVENANCE_INFERRED,
        PROVENANCE_PROJECT_DEFAULT,
        PROVENANCE_TURN_TEMPORARY,
    }
)

_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "bed": ("bett", "bed", "schlafstelle"),
    "wardrobe": ("schrank", "kleiderschrank", "wardrobe", "closet"),
    "desk": ("schreibtisch", "desk", "arbeitstisch", "schreibtische"),
    "lamp": ("lampe", "lamp", "leuchte", "stehlampe", "tischlampe"),
    "chair": ("stuhl", "chair", "sessel"),
    "plant": ("pflanze", "plant"),
    "rug": ("teppich", "rug", "vorleger"),
}

_PRONOUN_PATTERNS = (
    r"(?<![a-zäöüß])(das|es)(?![a-zäöüß])",
    r"\b(ihn|ihm)\b",
    r"\b(it|that|this|them)\b",
    r"\b(davon|daran|damit)\b",
    # Standalone "die/den/sie" only when not followed by a noun (article use)
    r"\b(die|den|sie)\b(?!\s+\w)",
)

_EXPLICIT_PREF_PATTERNS: tuple[tuple[str, str, Any], ...] = (
    (r"\b(lieber|möglichst|moeglichst)\s+minimal\b", "style", "minimal"),
    (r"\bminimalistisch\b", "style", "minimal"),
    (r"\b(lieber|möglichst|moeglichst)\s+gemütlich\b", "style", "cozy"),
    (r"\bgemütlich(er)?\b", "style", "cozy"),
    (r"\b(lieber|möglichst)\s+sparsam\b", "density", "sparse"),
    (r"\bnicht\s+vollgestellt\b", "density", "sparse"),
    (r"\bzu\s+voll\b", "density", "sparse"),
    (r"\bmehr\s+platz\b", "density", "sparse"),
    (r"\bweniger\s+möbel\b", "density", "sparse"),
    (r"\bweniger\s+mobel\b", "density", "sparse"),
    (r"\bkein(e|en)?\s+teppich\b", "avoid_rug", True),
    (r"\bkein(e|en)?\s+pflanze\b", "avoid_plant", True),
    (r"\bich\s+(möchte|moechte|will|brauche)\s+.{0,40}\b(hell|viel licht)\b", "daylight", "high"),
)

_INFERRED_PREF_PATTERNS: tuple[tuple[str, str, Any], ...] = (
    (r"\b(kühl|kuehl)\b", "warmth", "warmer"),
    (r"\bleer\b", "density", "richer"),
    (r"\bvollgestellt\b", "density", "sparse"),
    (r"\beng\b", "circulation", "more"),
)


def empty_focus() -> dict:
    return {
        "object_ids": [],
        "labels": [],
        "candidate_id": None,
        "room_id": None,
        "stack": [],
    }


def empty_agent_state_v3() -> dict:
    return {
        "schema": AGENT_STATE_SCHEMA,
        "goal": None,
        "requirements": None,
        "open_questions": [],
        "last_proposal_id": None,
        "last_analysis_summary": None,
        "last_placement_fp": None,
        "last_reply": None,
        "last_shortlist": None,
        "last_selected_id": None,
        "last_turn_kind": None,
        "last_observed_revision": None,
        "last_observed_findings": None,
        "focus": empty_focus(),
        "preferences": [],
        "resolved_refs": None,
    }


def normalize_agent_state(state: dict | None) -> dict:
    """Upgrade/ensure WP-03 fields; never drop known WP-A keys."""
    base = empty_agent_state_v3()
    if not isinstance(state, dict):
        return base
    out = dict(base)
    out.update({k: v for k, v in state.items() if k in out or k.startswith("last_")})
    # Preserve extra keys (last_planning, etc.)
    for k, v in state.items():
        if k not in out:
            out[k] = v
    out["schema"] = AGENT_STATE_SCHEMA
    focus = out.get("focus")
    if not isinstance(focus, dict):
        out["focus"] = empty_focus()
    else:
        merged = empty_focus()
        merged.update({k: focus.get(k) for k in merged if k in focus})
        stack = focus.get("stack")
        merged["stack"] = list(stack) if isinstance(stack, list) else []
        out["focus"] = merged
    prefs = out.get("preferences")
    if not isinstance(prefs, list):
        out["preferences"] = []
    else:
        out["preferences"] = [_normalize_pref(p) for p in prefs if _normalize_pref(p)]
    return out


def _normalize_pref(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    key = str(raw.get("key") or "").strip()
    if not key:
        return None
    provenance = str(raw.get("provenance") or PROVENANCE_INFERRED).strip()
    if provenance not in VALID_PROVENANCE:
        provenance = PROVENANCE_INFERRED
    return {
        "key": key,
        "value": raw.get("value"),
        "provenance": provenance,
        "source": str(raw.get("source") or "")[:120] or None,
    }


def upsert_preference(
    state: dict,
    *,
    key: str,
    value: Any,
    provenance: str,
    source: str | None = None,
) -> dict:
    state = normalize_agent_state(state)
    prov = provenance if provenance in VALID_PROVENANCE else PROVENANCE_INFERRED
    prefs = [p for p in state["preferences"] if p.get("key") != key]
    prefs.append(
        {
            "key": key,
            "value": value,
            "provenance": prov,
            "source": (source or "")[:120] or None,
        }
    )
    state["preferences"] = prefs
    return state


def extract_preferences_from_message(message: str) -> list[dict]:
    """Detect labeled preferences from user text (explicit first, then soft inferred)."""
    t = (message or "").strip().lower()
    if not t:
        return []
    found: list[dict] = []
    seen: set[str] = set()
    for pattern, key, value in _EXPLICIT_PREF_PATTERNS:
        if re.search(pattern, t):
            if key in seen:
                continue
            seen.add(key)
            found.append(
                {
                    "key": key,
                    "value": value,
                    "provenance": PROVENANCE_EXPLICIT,
                    "source": message.strip()[:120],
                }
            )
    # Inferred only when no explicit conflict on same key
    for pattern, key, value in _INFERRED_PREF_PATTERNS:
        if key in seen:
            continue
        if re.search(pattern, t):
            seen.add(key)
            found.append(
                {
                    "key": key,
                    "value": value,
                    "provenance": PROVENANCE_INFERRED,
                    "source": message.strip()[:120],
                }
            )
    return found


def apply_preferences_from_message(state: dict, message: str) -> dict:
    state = normalize_agent_state(state)
    for pref in extract_preferences_from_message(message):
        # Explicit overwrites inferred; inferred does not overwrite explicit
        existing = next((p for p in state["preferences"] if p.get("key") == pref["key"]), None)
        if (
            existing
            and existing.get("provenance") == PROVENANCE_EXPLICIT
            and pref.get("provenance") != PROVENANCE_EXPLICIT
        ):
            continue
        state = upsert_preference(
            state,
            key=pref["key"],
            value=pref["value"],
            provenance=pref["provenance"],
            source=pref.get("source"),
        )
    return state


def _scene_furniture(session) -> list[dict]:
    from ..tools import list_objects

    try:
        data = list_objects(session, {"limit": 80})
    except Exception:
        return []
    items = []
    for obj in data.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        gen = str(obj.get("layoutlab_generator") or obj.get("generator") or "").lower()
        role = str(obj.get("role") or obj.get("layoutlab_role") or "").lower()
        oid = str(obj.get("object_id") or obj.get("layoutlab_object_id") or "").strip()
        if not oid:
            continue
        if role in ("clearance", "room_wall", "room_floor", "opening", "label"):
            continue
        if not gen and role not in ("body", "main", ""):
            # skip non-furniture parts unless they look like mains
            if "clearance" in role:
                continue
        items.append(
            {
                "object_id": oid,
                "generator": gen,
                "role": role,
                "name": str(obj.get("name") or ""),
                "room_id": obj.get("room_id") or obj.get("layoutlab_room_id"),
            }
        )
    # Prefer unique object_ids (main pieces)
    by_id: dict[str, dict] = {}
    for it in items:
        prev = by_id.get(it["object_id"])
        if prev is None or (it["generator"] and not prev.get("generator")):
            by_id[it["object_id"]] = it
    return list(by_id.values())


def labels_in_text(text: str) -> list[str]:
    t = (text or "").lower()
    hits = []
    for label, aliases in _LABEL_ALIASES.items():
        if any(a in t for a in aliases):
            hits.append(label)
    return hits


_labels_in_text = labels_in_text


def _match_label(item: dict, label: str) -> bool:
    gen = item.get("generator") or ""
    name = (item.get("name") or "").lower()
    aliases = _LABEL_ALIASES.get(label, ())
    if label in gen:
        return True
    if any(a in gen or a in name for a in aliases):
        return True
    return False


def push_focus(
    state: dict,
    *,
    object_ids: list[str] | None = None,
    labels: list[str] | None = None,
    candidate_id: str | None = None,
    room_id: str | None = None,
) -> dict:
    state = normalize_agent_state(state)
    focus = state["focus"]
    oids = [str(x) for x in (object_ids or []) if x]
    labs = [str(x) for x in (labels or []) if x]
    entry = {
        "object_ids": oids,
        "labels": labs,
        "candidate_id": candidate_id,
        "room_id": room_id,
    }
    if not any((oids, labs, candidate_id, room_id)):
        return state
    stack = [e for e in (focus.get("stack") or []) if isinstance(e, dict)]
    stack.insert(0, entry)
    focus["stack"] = stack[:FOCUS_STACK_MAX]
    if oids:
        focus["object_ids"] = oids
    if labs:
        focus["labels"] = labs
    if candidate_id:
        focus["candidate_id"] = candidate_id
    if room_id:
        focus["room_id"] = room_id
    state["focus"] = focus
    return state


def update_focus_from_message(state: dict, session, message: str) -> dict:
    """Push furniture mentioned by label into focus when uniquely present."""
    state = normalize_agent_state(state)
    labels = _labels_in_text(message)
    if not labels:
        return state
    furniture = _scene_furniture(session)
    oids: list[str] = []
    for label in labels:
        matches = [f for f in furniture if _match_label(f, label)]
        if len(matches) == 1:
            oids.append(matches[0]["object_id"])
    return push_focus(state, object_ids=oids, labels=labels)


def update_focus_from_result(state: dict, result: dict) -> dict:
    """Capture candidate selection and commanded object ids when present."""
    state = normalize_agent_state(state)
    selected = result.get("selected_id") or state.get("last_selected_id")
    oids: list[str] = []
    for cmd in result.get("commands") or []:
        if not isinstance(cmd, dict):
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        for key in ("object_id", "host_object_id"):
            val = cmd.get(key) or params.get(key)
            if val:
                oids.append(str(val))
    oids = list(dict.fromkeys(oids))
    if selected or oids:
        state = push_focus(
            state,
            object_ids=oids or None,
            candidate_id=str(selected) if selected else None,
        )
    return state


def message_has_deictic(message: str) -> bool:
    t = (message or "").strip().lower()
    if not t:
        return False
    return any(re.search(p, t) for p in _PRONOUN_PATTERNS)


def resolve_reference(session, state: dict | None, message: str) -> dict:
    """Resolve 'das Bett' / 'es' against scene + focus.

    Returns:
      status: resolved | ambiguous | unresolved | none
      object_ids, labels, ask (optional clarification text)
    """
    state = normalize_agent_state(state)
    t = (message or "").strip().lower()
    furniture = _scene_furniture(session)
    labels = _labels_in_text(t)
    deictic = message_has_deictic(t)

    # Explicit label(s)
    if labels:
        matched: list[dict] = []
        for label in labels:
            hits = [f for f in furniture if _match_label(f, label)]
            if len(hits) > 1:
                return {
                    "status": "ambiguous",
                    "object_ids": [h["object_id"] for h in hits],
                    "labels": labels,
                    "ask": (
                        f"Welches {label} meinst du? "
                        + ", ".join(h["object_id"][:8] for h in hits[:4])
                    ),
                }
            if len(hits) == 1:
                matched.append(hits[0])
            elif not hits:
                return {
                    "status": "unresolved",
                    "object_ids": [],
                    "labels": labels,
                    "ask": f"Ich finde kein Objekt für „{label}“ in der Scene.",
                }
        if matched:
            oids = list(dict.fromkeys(m["object_id"] for m in matched))
            return {"status": "resolved", "object_ids": oids, "labels": labels, "ask": None}

    if not deictic:
        return {"status": "none", "object_ids": [], "labels": [], "ask": None}

    # Pronoun → focus stack
    focus = state.get("focus") or {}
    focus_ids = [str(x) for x in (focus.get("object_ids") or []) if x]
    if len(focus_ids) == 1:
        return {
            "status": "resolved",
            "object_ids": focus_ids,
            "labels": list(focus.get("labels") or []),
            "ask": None,
        }
    if len(focus_ids) > 1:
        return {
            "status": "ambiguous",
            "object_ids": focus_ids,
            "labels": list(focus.get("labels") or []),
            "ask": "Welches Objekt meinst du — " + " oder ".join(focus_ids[:3]) + "?",
        }

    # Fall back to single furniture in scene
    if len(furniture) == 1:
        return {
            "status": "resolved",
            "object_ids": [furniture[0]["object_id"]],
            "labels": [],
            "ask": None,
        }
    if len(furniture) > 1:
        return {
            "status": "ambiguous",
            "object_ids": [f["object_id"] for f in furniture[:5]],
            "labels": [],
            "ask": (
                "Welches Objekt meinst du? "
                + ", ".join(
                    (f.get("generator") or f["object_id"][:8]) for f in furniture[:4]
                )
            ),
        }
    return {
        "status": "unresolved",
        "object_ids": [],
        "labels": [],
        "ask": "In der Scene ist kein Möbel zum Beziehen.",
    }


def clarification_for_reference(resolution: dict) -> dict:
    ask = resolution.get("ask") or "Welches Objekt meinst du?"
    return {
        "ok": True,
        "mode": "converse",
        "turn_kind": "clarification",
        "reply": ask,
        "questions": [ask],
        "open_question": ask,
        "resolved_refs": resolution,
        "proposal": {
            "title": "Referenz klären",
            "rationale": "Ambiguous or missing referent — no mutations",
            "assumes": [],
            "commands": [],
            "expected_risks": [],
        },
        "commands": [],
    }
