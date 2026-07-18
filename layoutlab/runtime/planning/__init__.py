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
