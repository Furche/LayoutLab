"""Deterministic layout recipes (DD-016) — Planning Layer v0."""

from __future__ import annotations

from typing import Any

from .bedroom_basic import RECIPE_NAME as BEDROOM_BASIC
from .bedroom_basic import plan_bedroom_basic
from .requirements import (
    REQUIREMENTS_SCHEMA,
    merge_requirements,
    normalize_requirements,
    requirements_to_plan_params,
)

RECIPES = {
    BEDROOM_BASIC: plan_bedroom_basic,
}


def list_recipes():
    return sorted(RECIPES.keys())


def plan_layout(params: dict | None = None) -> dict[str, Any]:
    """Dispatch recipe → commands. Accepts flat params or requirements{}."""
    params = dict(params or {})
    requirements = None
    if isinstance(params.get("requirements"), dict):
        requirements = normalize_requirements(params.get("requirements"))
        mapped = requirements_to_plan_params(requirements)
        # Flat keys on the tool call still override (rare escape hatch)
        for key, value in params.items():
            if key in ("requirements", "recipe") or value is None:
                continue
            if key.startswith("_"):
                continue
            mapped[key] = value
        if params.get("recipe"):
            mapped["recipe"] = params["recipe"]
        params = mapped
        params["_requirements"] = requirements

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
            "requirements": requirements,
        }
    out = handler(params)
    if requirements is not None:
        out["requirements"] = requirements
        # Prefer requirements assumes + recipe assumes
        assumes = list(requirements.get("assumes") or [])
        for a in out.get("assumes") or []:
            if a not in assumes:
                assumes.append(a)
        out["assumes"] = assumes
    return out


def reconcile_plan_layout_params(
    args: dict | None,
    *,
    window_count: int = 0,
    room_size: tuple[float, float] | None = None,
    bed_size: tuple[float, float] | None = None,
    wants_door: bool = True,
    requirements: dict | None = None,
) -> dict:
    """Build plan_layout args from requirements and/or conversation fallbacks."""
    args = dict(args or {})
    base_req = None
    if isinstance(requirements, dict):
        base_req = normalize_requirements(requirements)
    elif isinstance(args.get("requirements"), dict):
        base_req = normalize_requirements(args.get("requirements"))

    overlay: dict[str, Any] = {}
    if room_size is not None:
        overlay["width"] = float(room_size[0])
        overlay["depth"] = float(room_size[1])
    if window_count > 0:
        overlay["windows"] = int(window_count)
    if bed_size is not None:
        overlay["bed_width"] = float(bed_size[0])
        overlay["bed_length"] = float(bed_size[1])
    if wants_door and (base_req is None or base_req.get("doors", 1) < 1):
        overlay["doors"] = 1

    if base_req is not None or overlay:
        req = merge_requirements(base_req, overlay if overlay else None)
        return {"requirements": req, "recipe": "bedroom_basic"}

    # Legacy flat-arg path
    out = dict(args)
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


__all__ = [
    "BEDROOM_BASIC",
    "REQUIREMENTS_SCHEMA",
    "list_recipes",
    "merge_requirements",
    "normalize_requirements",
    "plan_layout",
    "reconcile_plan_layout_params",
    "requirements_to_plan_params",
]
