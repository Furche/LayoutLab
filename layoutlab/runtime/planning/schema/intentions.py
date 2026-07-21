"""DD-017 Evaluation v0.1 — allowlisted semantic intention keys (strings only)."""

from __future__ import annotations

INTENTIONS = frozenset(
    {
        "plan_layout_candidates",
        "plan_layout_single",
        "prefer_bed_wall_south",
        "prefer_bed_wall_north",
        "omit_desk",
        "recipe_bedroom_basic",
        "assign_role",  # value must be allowlisted role
    }
)


def validate_intention(name) -> bool:
    """True iff name is an allowlisted intention key (no free-form invent)."""
    if name is None:
        return False
    return str(name).strip() in INTENTIONS
