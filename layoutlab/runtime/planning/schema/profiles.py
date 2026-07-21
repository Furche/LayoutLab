"""DD-017 Evaluation v0.1 — versioned object-type profiles (data, not generators)."""

from __future__ import annotations

SCHEMA_VERSION = "0.1.0"

# Provisional profile catalog. Capabilities/anchors are declarative only —
# no preference scoring engine lives here yet.
PROFILES = {
    "bed": {
        "profile_id": "bed",
        "capabilities": ["sleep", "entry_sides"],
        "anchors": ["head", "foot"],
        "notes": "Sleeping surface; head/foot anchors; lateral entry sides.",
    },
    "wardrobe": {
        "profile_id": "wardrobe",
        "capabilities": ["storage", "openable_front"],
        "anchors": ["back", "front"],
        "notes": "Storage carcass; openable front needs standing access.",
    },
    "desk": {
        "profile_id": "desk",
        "capabilities": ["work_surface", "chair_access"],
        "anchors": ["front", "back"],
        "notes": "Work surface; chair access in front is primary usability.",
    },
    "unknown": {
        "profile_id": "unknown",
        "capabilities": [],
        "anchors": [],
        "notes": "Unresolved type — collision only, no invented preferences.",
    },
}

# Generator name / type hint → profile_id (explicit map; never invent new profiles).
_GENERATOR_TO_PROFILE = {
    "bed": "bed",
    "bed_basic": "bed",
    "wardrobe": "wardrobe",
    "wardrobe_basic": "wardrobe",
    "desk": "desk",
    "desk_basic": "desk",
}


def list_profiles() -> list[str]:
    return sorted(PROFILES.keys())


def get_profile(profile_id: str) -> dict:
    """Return profile dict; unknown ids fall back to the unknown profile."""
    key = str(profile_id or "").strip().lower()
    if key in PROFILES:
        return dict(PROFILES[key])
    return dict(PROFILES["unknown"])


def resolve_profile_id(generator_name_or_type_hint) -> str:
    """Map generator name or type hint → allowlisted profile_id."""
    raw = str(generator_name_or_type_hint or "").strip().lower()
    if not raw:
        return "unknown"
    if raw in PROFILES:
        return raw
    if raw in _GENERATOR_TO_PROFILE:
        return _GENERATOR_TO_PROFILE[raw]
    # Strip common suffixes like "_basic" once more for loose hints
    if raw.endswith("_basic"):
        base = raw[: -len("_basic")]
        if base in PROFILES:
            return base
    return "unknown"
