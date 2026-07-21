"""DD-017 Evaluation v0.1 — allowlisted object roles."""

from __future__ import annotations

ROLES = frozenset(
    {
        "primary_sleeping_place",
        "guest_sleeping_place",
        "primary_workspace",
        "secondary_workspace",
        "primary_storage",
        "secondary_storage",
        "primary_dining_place",
        "neutral",
    }
)

HIGH_IMPACT_ROLES = frozenset(
    {
        "primary_sleeping_place",
        "primary_workspace",
        "primary_dining_place",
        "primary_storage",
    }
)

# Default role seed per profile — provisional, not a preference solver.
_DEFAULT_ROLE_BY_PROFILE = {
    "bed": "primary_sleeping_place",
    "wardrobe": "primary_storage",
    "desk": "primary_workspace",
    "unknown": "neutral",
}


def normalize_role(role) -> str | None:
    """Return allowlisted role string, or None if unknown (never invent)."""
    if role is None:
        return None
    key = str(role).strip().lower()
    if not key:
        return None
    if key in ROLES:
        return key
    return None


def is_high_impact(role) -> bool:
    normalized = normalize_role(role)
    return normalized is not None and normalized in HIGH_IMPACT_ROLES


def default_role_for_profile(profile_id) -> str:
    """Seed role for a profile_id; unknown profiles → neutral."""
    key = str(profile_id or "").strip().lower()
    return _DEFAULT_ROLE_BY_PROFILE.get(key, "neutral")
