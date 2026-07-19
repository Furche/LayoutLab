"""Deterministic layout recipes (DD-016) — Planning Layer v0."""

from __future__ import annotations

from typing import Any

from .bedroom_basic import RECIPE_NAME as BEDROOM_BASIC
from .bedroom_basic import plan_bedroom_basic

RECIPES = {
    BEDROOM_BASIC: plan_bedroom_basic,
}


def list_recipes():
    return sorted(RECIPES.keys())


def plan_layout(params: dict | None = None) -> dict[str, Any]:
    """Dispatch recipe → commands. Pure Core planning; live session unchanged."""
    params = params or {}
    recipe = str(params.get("recipe") or BEDROOM_BASIC).strip().lower()
    handler = RECIPES.get(recipe)
    if handler is None:
        return {
            "ok": False,
            "error": f"unknown recipe {recipe!r}",
            "known_recipes": list_recipes(),
            "commands": [],
            "assumes": [],
            "notes": [],
        }
    return handler(params)


def reconcile_plan_layout_params(
    args: dict | None,
    *,
    window_count: int = 0,
    room_size: tuple[float, float] | None = None,
    bed_size: tuple[float, float] | None = None,
    wants_door: bool = True,
) -> dict:
    """Merge conversation facts into plan_layout args (Core owns geometry)."""
    out = dict(args or {})
    out.setdefault("recipe", BEDROOM_BASIC)
    if room_size is not None:
        out["width"] = float(room_size[0])
        out["depth"] = float(room_size[1])
    if window_count > 0:
        out["window_count"] = int(window_count)
        out.pop("windows", None)
    if bed_size is not None:
        out["bed_width"] = float(bed_size[0])
        out["bed_length"] = float(bed_size[1])
    if wants_door and not isinstance(out.get("door"), dict):
        out["door"] = {"wall_side": "east", "width": 0.9}
    return out
