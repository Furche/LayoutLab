"""Generic recipe resolution — room_type / conversation → Core recipe id.

Bedroom is the first mapped recipe; add new room types to ROOM_TYPE_RECIPES
when their Core recipes exist. Unmapped intents return None (no force path).
"""

from __future__ import annotations

from .intent import is_retry_request, user_wants_bed, user_wants_room

# room_type → recipe id (extensible registry; bedroom is first entry only)
ROOM_TYPE_RECIPES: dict[str, str] = {
    "bedroom": "bedroom_basic",
    # future: "kids_room": "kids_room_basic", "home_office": "home_office_basic",
}

# recipe id → default room_type (inverse for overlays)
RECIPE_ROOM_TYPES: dict[str, str] = {v: k for k, v in ROOM_TYPE_RECIPES.items()}

_LAYOUT_PLANNING_CUES = (
    "einricht",
    "möbel",
    "mobel",
    "gestalt",
    "planen",
    "plane ",
    "furnished",
    "furniture",
    "layout",
    "schlafzimmer",
    "bedroom",
    "kids room",
    "kinderzimmer",
    "büro",
    "buero",
    "home office",
    "homeoffice",
)

_BEDROOM_CUES = (
    "schlafzimmer",
    "bedroom",
    "schlafgemach",
)


def wants_layout_planning(text: str) -> bool:
    """User wants a (re)furnished room layout — not observation-only."""
    t = (text or "").lower()
    if any(k in t for k in _LAYOUT_PLANNING_CUES):
        return True
    if user_wants_room(t) and (
        user_wants_bed(t)
        or any(k in t for k in ("möbel", "mobel", "furniture", "schrank", "desk", "tisch"))
    ):
        return True
    # "bau.*zimmer" / build a room for living
    if ("bau" in t or "erstell" in t) and ("zimmer" in t or "raum" in t or "room" in t):
        return True
    return False


def _recipe_from_conversation(text: str) -> str | None:
    t = (text or "").lower()
    if any(k in t for k in _BEDROOM_CUES) or user_wants_bed(t):
        return ROOM_TYPE_RECIPES.get("bedroom")
    return None


def resolve_recipe_id(
    *,
    conversation: str = "",
    requirements: dict | None = None,
    session=None,
) -> str | None:
    """Return recipe id if Core can plan this intent; else None.

    Priority: requirements.room_type → ROOM_TYPE_RECIPES;
    conversation cues; session.agent_state.requirements.room_type.
    """
    if isinstance(requirements, dict):
        rt = str(requirements.get("room_type") or "").strip().lower()
        if rt and rt in ROOM_TYPE_RECIPES:
            return ROOM_TYPE_RECIPES[rt]

    cue = _recipe_from_conversation(conversation)
    if cue:
        return cue

    state = getattr(session, "agent_state", None) if session is not None else None
    if isinstance(state, dict):
        req = state.get("requirements")
        if isinstance(req, dict):
            rt = str(req.get("room_type") or "").strip().lower()
            if rt and rt in ROOM_TYPE_RECIPES:
                return ROOM_TYPE_RECIPES[rt]
        goal = str(state.get("goal") or "").lower()
        cue = _recipe_from_conversation(goal)
        if cue:
            return cue
    return None


def session_wants_recipe_planning(session, text: str) -> bool:
    """True if we should force Core recipe path (incl. retry with stored requirements)."""
    if resolve_recipe_id(conversation=text, session=session):
        if wants_layout_planning(text) or user_wants_bed(text):
            return True
        if is_retry_request(text):
            return True
    if is_retry_request(text):
        state = getattr(session, "agent_state", None) or {}
        if not isinstance(state, dict):
            return False
        req = state.get("requirements")
        if isinstance(req, dict):
            rt = str(req.get("room_type") or "").strip().lower()
            if rt in ROOM_TYPE_RECIPES:
                return True
        goal = str(state.get("goal") or "").lower()
        return bool(_recipe_from_conversation(goal))
    return False


def wants_bedroom_layout(text: str) -> bool:
    """Back-compat: True when Core should use the bedroom recipe."""
    return resolve_recipe_id(conversation=text) == ROOM_TYPE_RECIPES.get("bedroom")


def session_wants_bedroom_fallback(session, text: str) -> bool:
    """Back-compat alias for session_wants_recipe_planning."""
    return session_wants_recipe_planning(session, text)
