"""Mini layout requirements (Agent → Core planning input).

The LLM fills this structured object from natural language.
Core maps it to plan_layout / recipe params — no free xy from the agent.
"""

from __future__ import annotations

from typing import Any

REQUIREMENTS_SCHEMA = "layoutlab_requirements/0.1"

_FURNITURE_ALIASES = {
    "bed": "bed",
    "bett": "bed",
    "wardrobe": "wardrobe",
    "schrank": "wardrobe",
    "kleiderschrank": "wardrobe",
    "desk": "desk",
    "schreibtisch": "desk",
    "tisch": "desk",
}


def _f(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _i(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _side(value, default: str = "east") -> str:
    side = str(value or default).strip().lower()
    if side in ("north", "south", "east", "west"):
        return side
    return default


def normalize_requirements(raw: dict | None, *, room_type_default: str = "bedroom") -> dict[str, Any]:
    """Coerce LLM / tool JSON into a stable requirements object."""
    raw = raw if isinstance(raw, dict) else {}
    room_type = str(raw.get("room_type") or room_type_default).strip().lower() or room_type_default

    width = _f(raw.get("width"), 4.0) or 4.0
    depth = _f(raw.get("depth"), 3.5) or 3.5
    height = _f(raw.get("height"), 2.5) or 2.5
    width = max(2.5, min(20.0, width))
    depth = max(2.5, min(20.0, depth))
    height = max(2.2, min(4.0, height))

    doors = max(0, min(3, _i(raw.get("doors"), 1)))
    windows = max(0, min(6, _i(raw.get("windows"), 1)))

    furniture_in = raw.get("furniture")
    furniture: list[str] = []
    if isinstance(furniture_in, list):
        for item in furniture_in:
            key = _FURNITURE_ALIASES.get(str(item).strip().lower())
            if key and key not in furniture:
                furniture.append(key)
    if not furniture and room_type == "bedroom":
        furniture = ["bed", "wardrobe", "desk"]

    bed_w = _f(raw.get("bed_width"), 1.2) or 1.2
    bed_l = _f(raw.get("bed_length"), 2.0) or 2.0
    # Swap if LLM put length first as the larger dim into bed_width by mistake
    if bed_w > bed_l and bed_w >= 1.6:
        bed_w, bed_l = bed_l, bed_w
    bed_w = max(0.8, min(2.2, bed_w))
    bed_l = max(1.6, min(2.5, bed_l))

    door_wall = _side(raw.get("door_wall"), "east")
    assumes = [str(a) for a in (raw.get("assumes") or []) if a]

    return {
        "schema": REQUIREMENTS_SCHEMA,
        "room_type": room_type,
        "width": round(width, 3),
        "depth": round(depth, 3),
        "height": round(height, 3),
        "doors": doors,
        "windows": windows,
        "furniture": furniture,
        "bed_width": round(bed_w, 3),
        "bed_length": round(bed_l, 3),
        "door_wall": door_wall,
        "assumes": assumes,
    }


def requirements_to_plan_params(requirements: dict | None) -> dict[str, Any]:
    """Map normalized requirements → plan_layout / recipe kwargs."""
    from .recipe_routing import ROOM_TYPE_RECIPES

    req = normalize_requirements(requirements)
    furniture = set(req.get("furniture") or [])
    recipe = ROOM_TYPE_RECIPES.get(req["room_type"]) or "bedroom_basic"
    params: dict[str, Any] = {
        "recipe": recipe,
        "width": req["width"],
        "depth": req["depth"],
        "height": req["height"],
        "window_count": req["windows"],
        "include_bed": "bed" in furniture,
        "include_wardrobe": "wardrobe" in furniture,
        "include_desk": "desk" in furniture,
        "bed_width": req["bed_width"],
        "bed_length": req["bed_length"],
        "collection": "layoutlab_room",
    }
    if req["doors"] >= 1:
        params["door"] = {"wall_side": req["door_wall"], "width": 0.9}
    else:
        params["door"] = None
    # Carry assumes for the planner response
    params["_requirements"] = req
    return params


def merge_requirements(base: dict | None, overlay: dict | None) -> dict[str, Any]:
    """Overlay non-null fields from overlay onto base, then normalize."""
    merged = dict(normalize_requirements(base))
    if not isinstance(overlay, dict):
        return merged
    for key in (
        "room_type",
        "width",
        "depth",
        "height",
        "doors",
        "windows",
        "furniture",
        "bed_width",
        "bed_length",
        "door_wall",
        "assumes",
    ):
        if key in overlay and overlay[key] is not None:
            merged[key] = overlay[key]
    return normalize_requirements(merged)
