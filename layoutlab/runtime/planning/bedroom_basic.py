"""Bedroom layout recipe (DD-016) — deterministic commands, no bpy."""

from __future__ import annotations

from typing import Any

RECIPE_NAME = "bedroom_basic"
ROOM_NAME = "BEDROOM"
COLLECTION = "layoutlab_room"

MARGIN = 0.08
# Semantic mattress sizes (human: width × length). Mapped to bed_basic axes below.
BED_MATTRESS_WIDTH = 1.2   # side-to-side
BED_MATTRESS_LENGTH = 2.0  # head-to-foot
WARDROBE_WIDTH = 1.0
WARDROBE_DEPTH = 0.55
WARDROBE_HEIGHT = 2.0
DESK_WIDTH = 1.0
DESK_DEPTH = 0.55
DESK_HEIGHT = 0.75
DOOR_ACCESS_KEEP = 1.0  # keep east strip clear when east door


def _f(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _side(value, default: str) -> str:
    side = str(value or default).strip().lower()
    if side in ("north", "south", "east", "west"):
        return side
    return default


def _opening_offset(wall_side: str, width: float, room_w: float, room_d: float) -> float:
    """Center-ish offset along the wall, with margin."""
    along = room_d if wall_side in ("east", "west") else room_w
    span = max(0.2, along - width - 2 * MARGIN)
    return round(MARGIN + span * 0.35, 3)


def _default_windows_for_count(n: int, *, avoid_side: str | None = None) -> list[dict]:
    """Prefer south/north first; never put a default window on the door wall."""
    n = max(0, int(n))
    if n == 0:
        return []
    sides = [s for s in ("south", "north", "west", "east") if s != avoid_side]
    if not sides:
        sides = ["south", "north", "west", "east"]
    return [
        {"wall_side": sides[i % len(sides)], "width": 1.2, "sill_height": 0.9}
        for i in range(n)
    ]


def _spaced_window_commands(windows_in: list, room_w: float, room_d: float, room_name: str) -> tuple[list[dict], tuple | None]:
    """Emit add_opening commands with non-overlapping offsets per wall."""
    groups: dict[str, list[dict]] = {}
    for win in windows_in:
        if not isinstance(win, dict):
            continue
        side = _side(win.get("wall_side"), "south")
        groups.setdefault(side, []).append(win)

    commands = []
    win_south = None
    idx = 0
    for side, wins in groups.items():
        along = room_d if side in ("east", "west") else room_w
        n = len(wins)
        widths = [max(0.6, _f(w.get("width"), 1.2)) for w in wins]
        # Equal slots along the wall; center each window in its slot.
        usable = max(0.2, along - 2 * MARGIN)
        slot = usable / n if n else usable
        for i, win in enumerate(wins):
            w_w = widths[i]
            w_h = max(0.8, _f(win.get("height"), 1.2))
            sill = max(0.4, _f(win.get("sill_height"), 0.9))
            if win.get("offset") is not None and n == 1:
                w_off = _f(win.get("offset"), 0.5)
            else:
                w_off = MARGIN + i * slot + max(0.0, (slot - w_w) / 2)
            w_off = max(MARGIN, min(along - w_w - MARGIN, w_off))
            # Nudge forward if still overlapping previous on this wall
            if i > 0:
                prev = commands[-1]["params"]
                prev_end = float(prev["offset"]) + float(prev["width"]) + 0.05
                if w_off < prev_end:
                    w_off = min(along - w_w - MARGIN, prev_end)
            idx += 1
            commands.append(
                {
                    "action": "add_opening",
                    "params": {
                        "room": room_name,
                        "opening_name": f"win_{side}_{idx}",
                        "kind": "window",
                        "wall_side": side,
                        "offset": round(w_off, 3),
                        "width": round(w_w, 3),
                        "height": round(w_h, 3),
                        "sill_height": round(sill, 3),
                    },
                }
            )
            if side == "south" and win_south is None:
                win_south = (w_off, w_w)
    return commands, win_south


def plan_bedroom_basic(params: dict | None = None) -> dict[str, Any]:
    """Return {ok, recipe, commands, assumes, notes} for a rectangular bedroom."""
    params = params or {}
    room_w = max(2.8, _f(params.get("width"), 4.0))
    room_d = max(2.6, _f(params.get("depth"), 3.5))
    room_h = max(2.2, _f(params.get("height"), 2.5))
    collection = str(params.get("collection") or COLLECTION).strip() or COLLECTION
    include_desk = bool(params.get("include_desk", True))
    include_wardrobe = bool(params.get("include_wardrobe", True))
    include_bed = bool(params.get("include_bed", True))

    door = params.get("door")
    if door is False or door is None:
        door = None
    elif not isinstance(door, dict):
        door = {}
    door_side = _side((door or {}).get("wall_side"), "east") if door is not None else "east"
    door_w = max(0.7, _f((door or {}).get("width"), 0.9))
    door_h = max(1.8, _f((door or {}).get("height"), 2.0))
    door_off = (door or {}).get("offset") if door else None
    if door is not None:
        if door_off is None:
            door_off = _opening_offset(door_side, door_w, room_w, room_d)
        else:
            door_off = _f(door_off, 0.3)

    windows_in = params.get("windows")
    if params.get("window_count") is not None:
        try:
            windows_in = _default_windows_for_count(
                int(params.get("window_count")),
                avoid_side=door_side if door is not None else None,
            )
        except (TypeError, ValueError):
            windows_in = _default_windows_for_count(1, avoid_side=door_side if door else None)
    elif windows_in is None:
        windows_in = [{"wall_side": "south", "width": 1.2, "sill_height": 0.9}]
    if not isinstance(windows_in, list):
        windows_in = []

    assumes = []
    if params.get("width") is None:
        assumes.append(f"room width={room_w} m (default)")
    if params.get("depth") is None:
        assumes.append(f"room depth={room_d} m (default)")
    if door is None:
        assumes.append("no door")
    elif params.get("door") is None and "_requirements" not in params:
        assumes.append(f"door on {door_side} wall")
    if params.get("windows") is None and params.get("window_count") is None:
        assumes.append("one south window")
    elif params.get("window_count") is not None:
        assumes.append(f"{len(windows_in)} window(s) from window_count")

    commands: list[dict] = [
        {"action": "delete_collection_objects", "collection": collection},
        {
            "action": "create_room",
            "params": {
                "name": ROOM_NAME,
                "location": [0, 0, 0],
                "width": round(room_w, 3),
                "depth": round(room_d, 3),
                "height": round(room_h, 3),
                "wall_thickness": 0.02,
                "collection": collection,
            },
        },
    ]
    if door is not None:
        commands.append(
            {
                "action": "add_opening",
                "params": {
                    "room": ROOM_NAME,
                    "opening_name": f"door_{door_side}",
                    "kind": "door",
                    "wall_side": door_side,
                    "offset": round(door_off, 3),
                    "width": round(door_w, 3),
                    "height": round(door_h, 3),
                },
            }
        )

    win_cmds, win_south = _spaced_window_commands(windows_in, room_w, room_d, ROOM_NAME)
    commands.extend(win_cmds)
    # bed_basic axes are fixed: length=X, width=Y. With head_side=y_min/y_max,
    # sleeping is along Y → X = mattress width, Y = mattress length (120×200 → 1.2×2.0).
    mattress_w = max(0.8, _f(params.get("bed_width"), BED_MATTRESS_WIDTH))
    mattress_l = max(1.6, _f(params.get("bed_length"), BED_MATTRESS_LENGTH))
    axis_x = min(mattress_w, room_w - 2 * MARGIN)  # along wall (side-to-side)
    axis_y = min(mattress_l, room_d - 2 * MARGIN)  # into room (head-to-foot)
    bed_x = MARGIN
    if win_south is not None:
        # Prefer west of south window when it fits
        w_off, w_w = win_south
        if axis_x + MARGIN <= w_off - 0.05:
            bed_x = MARGIN
        else:
            bed_x = MARGIN  # still west; window soft access may warn
    bed_y = MARGIN
    bed_box = None
    if include_bed:
        commands.append(
            {
                "action": "run_generator",
                "generator": "bed_basic",
                "params": {
                    "name": "BED",
                    "location": [round(bed_x, 3), round(bed_y, 3), 0],
                    "length": round(axis_x, 3),
                    "width": round(axis_y, 3),
                    "head_side": "y_min",
                    "collection": collection,
                },
            }
        )
        bed_box = (bed_x, bed_y, bed_x + axis_x, bed_y + axis_y)

    notes = [
        "Circulation kept toward east door when door is east.",
    ]
    if include_bed:
        notes.insert(
            0,
            "Bed on south wall (head_side=y_min): mattress "
            f"{axis_x:.2f}m wide × {axis_y:.2f}m long (sleep along +Y).",
        )

    # --- Wardrobe: north wall, west, doors face south ---
    if include_wardrobe:
        ww = min(WARDROBE_WIDTH, room_w * 0.35)
        wd = min(WARDROBE_DEPTH, 0.6)
        wx = MARGIN
        wy = room_d - wd - MARGIN
        # Keep out of east door strip
        if door is not None and door_side == "east" and wx + ww > room_w - DOOR_ACCESS_KEEP:
            wx = max(MARGIN, room_w - DOOR_ACCESS_KEEP - ww)
        commands.append(
            {
                "action": "run_generator",
                "generator": "wardrobe_basic",
                "params": {
                    "name": "WARDROBE",
                    "location": [round(wx, 3), round(wy, 3), 0],
                    "width": round(ww, 3),
                    "depth": round(wd, 3),
                    "height": round(min(WARDROBE_HEIGHT, room_h - 0.1), 3),
                    "front_side": "y_min",
                    "show_clearance": True,
                    "clearance_depth": 0.55,
                    "collection": collection,
                },
            }
        )
        notes.append("Wardrobe on north wall (front_side=y_min); wardrobe_basic has Y fronts only.")
        ward_box = (wx, wy, wx + ww, wy + wd)
    else:
        ward_box = None

    # --- Desk: north wall, east of wardrobe, chair −Y into room ---
    if include_desk:
        dw = min(DESK_WIDTH, 1.2)
        dd = min(DESK_DEPTH, 0.6)
        dy = room_d - dd - MARGIN
        if ward_box is not None:
            dx = ward_box[2] + 0.15
        else:
            dx = MARGIN
        # Keep east door strip free
        if door is not None and door_side == "east":
            max_x = room_w - DOOR_ACCESS_KEEP - dw
            if dx > max_x:
                dx = max(MARGIN, max_x)
        # Must not overlap bed
        desk_box = (dx, dy, dx + dw, dy + dd)
        if _overlap(desk_box, bed_box):
            dx = max(MARGIN, bed_box[2] + 0.15)
            desk_box = (dx, dy, dx + dw, dy + dd)
        # Chair zone must stay off bed (desk front = −Y)
        chair = (dx, dy - 0.55, dx + dw, dy)
        if _overlap(chair, bed_box):
            # Fall back: west of bed along north, or smaller desk
            dx = MARGIN
            if ward_box is not None:
                dx = ward_box[2] + 0.12
            desk_box = (dx, dy, dx + dw, dy + dd)
            chair = (dx, dy - 0.55, dx + dw, dy)
            if _overlap(chair, bed_box) or _overlap(desk_box, bed_box):
                # Last resort: omit required chair by reducing clearance depth
                commands.append(
                    {
                        "action": "run_generator",
                        "generator": "desk_basic",
                        "params": {
                            "name": "DESK",
                            "location": [round(dx, 3), round(dy, 3), 0],
                            "width": round(dw, 3),
                            "depth": round(dd, 3),
                            "height": DESK_HEIGHT,
                            "show_clearance": True,
                            "clearance_depth": 0.45,
                            "collection": collection,
                        },
                    }
                )
                notes.append("Desk on north wall; chair clearance shortened to fit.")
            else:
                commands.append(_desk_cmd(dx, dy, dw, dd, collection))
                notes.append("Desk on north wall; chair clearance faces south into free floor.")
        else:
            commands.append(_desk_cmd(dx, dy, dw, dd, collection))
            notes.append("Desk on north wall; chair clearance faces south into free floor.")

    return {
        "ok": True,
        "recipe": RECIPE_NAME,
        "commands": commands,
        "assumes": assumes,
        "notes": notes,
        "room": {"width": room_w, "depth": room_d, "height": room_h, "name": ROOM_NAME},
    }


def _desk_cmd(dx, dy, dw, dd, collection):
    return {
        "action": "run_generator",
        "generator": "desk_basic",
        "params": {
            "name": "DESK",
            "location": [round(dx, 3), round(dy, 3), 0],
            "width": round(dw, 3),
            "depth": round(dd, 3),
            "height": DESK_HEIGHT,
            "show_clearance": True,
            "clearance_depth": 0.55,
            "collection": collection,
        },
    }


def _overlap(a, b) -> bool:
    if not a or not b:
        return False
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
