"""Bedroom layout recipe (DD-016 / DD-011) — deterministic commands, no bpy."""

from __future__ import annotations

from typing import Any

RECIPE_NAME = "bedroom_basic"
RECIPE_KIND = "room_use"
RECIPE_GOALS = ("sleep", "storage")
ROOM_NAME = "BEDROOM"
COLLECTION = "layoutlab_room"

MARGIN = 0.08
# Semantic mattress sizes (human: width × length). Mapped to bed_basic axes below.
BED_MATTRESS_WIDTH = 1.2  # side-to-side
BED_MATTRESS_LENGTH = 2.0  # head-to-foot
WARDROBE_WIDTH = 1.0
WARDROBE_DEPTH = 0.55
WARDROBE_HEIGHT = 2.0
DESK_WIDTH = 1.0
DESK_DEPTH = 0.55
DESK_HEIGHT = 0.75
DOOR_ACCESS_KEEP = 1.0  # keep east strip clear when east door

# Default matches historic single-layout behaviour (bed south, storage north).
DEFAULT_STRATEGY = "bed_south__storage_north"

# Finite option matrix for DD-011 candidates (2–4 strategies).
_STRATEGY_SPECS: tuple[dict[str, str], ...] = (
    {"strategy": "bed_south__storage_north", "bed_wall": "south", "storage_order": "wardrobe_west"},
    {"strategy": "bed_north__storage_south", "bed_wall": "north", "storage_order": "wardrobe_west"},
    {"strategy": "bed_south__storage_swapped", "bed_wall": "south", "storage_order": "wardrobe_east"},
    {"strategy": "bed_north__storage_swapped", "bed_wall": "north", "storage_order": "wardrobe_east"},
)


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


def _resolve_strategy(params: dict) -> dict[str, str]:
    """Resolve bed_wall / storage_order / strategy id from params."""
    bed_wall = str(params.get("bed_wall") or params.get("prefer_bed_wall") or "").strip().lower()
    if bed_wall not in ("south", "north"):
        bed_wall = ""
    storage_order = str(params.get("storage_order") or "").strip().lower()
    if storage_order not in ("wardrobe_west", "wardrobe_east"):
        storage_order = ""

    strategy = str(params.get("strategy") or "").strip().lower()
    for spec in _STRATEGY_SPECS:
        if strategy and spec["strategy"] == strategy:
            return dict(spec)
        if bed_wall and storage_order:
            if spec["bed_wall"] == bed_wall and spec["storage_order"] == storage_order:
                return dict(spec)
        if bed_wall and not storage_order and spec["bed_wall"] == bed_wall and spec["storage_order"] == "wardrobe_west":
            return dict(spec)

    return dict(_STRATEGY_SPECS[0])


def _place_furniture(
    *,
    room_w: float,
    room_d: float,
    room_h: float,
    collection: str,
    door,
    door_side: str,
    win_south: tuple | None,
    include_bed: bool,
    include_wardrobe: bool,
    include_desk: bool,
    mattress_w: float,
    mattress_l: float,
    bed_wall: str,
    storage_order: str,
) -> tuple[list[dict], list[str], tuple | None]:
    """Place bed / wardrobe / desk for one strategy. Returns commands, notes, bed_box."""
    commands: list[dict] = []
    notes: list[str] = []
    bed_box = None

    axis_x = min(mattress_w, room_w - 2 * MARGIN)  # along wall (side-to-side)
    axis_y = min(mattress_l, room_d - 2 * MARGIN)  # into room (head-to-foot)
    bed_x = MARGIN
    if win_south is not None and bed_wall == "south":
        # Prefer west of south window when it fits
        w_off, _w_w = win_south
        if axis_x + MARGIN <= w_off - 0.05:
            bed_x = MARGIN

    if bed_wall == "north":
        head_side = "y_max"
        bed_y = max(MARGIN, room_d - axis_y - MARGIN)
        notes.append(
            "Bed on north wall (head_side=y_max): mattress "
            f"{axis_x:.2f}m wide × {axis_y:.2f}m long (sleep along −Y)."
        )
    else:
        head_side = "y_min"
        bed_y = MARGIN
        notes.append(
            "Bed on south wall (head_side=y_min): mattress "
            f"{axis_x:.2f}m wide × {axis_y:.2f}m long (sleep along +Y)."
        )

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
                    "head_side": head_side,
                    "collection": collection,
                },
            }
        )
        bed_box = (bed_x, bed_y, bed_x + axis_x, bed_y + axis_y)

    notes.append("Circulation kept toward east door when door is east.")

    # Storage wall is opposite the bed wall.
    storage_wall = "north" if bed_wall == "south" else "south"
    ww = min(WARDROBE_WIDTH, room_w * 0.35)
    wd = min(WARDROBE_DEPTH, 0.6)
    dw = min(DESK_WIDTH, 1.2)
    dd = min(DESK_DEPTH, 0.6)
    wardrobe_west = storage_order != "wardrobe_east"

    ward_box = None
    if include_wardrobe:
        if storage_wall == "north":
            wy = room_d - wd - MARGIN
            front_side = "y_min"
        else:
            wy = MARGIN
            front_side = "y_max"
        if wardrobe_west:
            wx = MARGIN
        else:
            wx = max(MARGIN, room_w - ww - MARGIN)
            if door is not None and door_side == "east":
                wx = max(MARGIN, min(wx, room_w - DOOR_ACCESS_KEEP - ww))
        if door is not None and door_side == "east" and wx + ww > room_w - DOOR_ACCESS_KEEP:
            wx = max(MARGIN, room_w - DOOR_ACCESS_KEEP - ww)
        # Avoid bed overlap on same Y band (rare when room is shallow)
        if bed_box is not None and _overlap((wx, wy, wx + ww, wy + wd), bed_box):
            if wardrobe_west:
                wx = max(MARGIN, bed_box[2] + 0.12)
            else:
                wx = max(MARGIN, min(wx, bed_box[0] - ww - 0.12))
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
                    "front_side": front_side,
                    "show_clearance": True,
                    "clearance_depth": 0.55,
                    "collection": collection,
                },
            }
        )
        notes.append(
            f"Wardrobe on {storage_wall} wall (front_side={front_side}); "
            "wardrobe_basic has Y fronts only."
        )
        ward_box = (wx, wy, wx + ww, wy + wd)

    if include_desk:
        if storage_wall == "north":
            # Desk on north wall; chair −Y into room (desk_basic convention).
            dy = room_d - dd - MARGIN
            if wardrobe_west:
                dx = (ward_box[2] + 0.15) if ward_box is not None else MARGIN
            else:
                dx = MARGIN if ward_box is None else max(MARGIN, ward_box[0] - dw - 0.15)
            if door is not None and door_side == "east":
                max_x = room_w - DOOR_ACCESS_KEEP - dw
                if dx > max_x:
                    dx = max(MARGIN, max_x)
            desk_box = (dx, dy, dx + dw, dy + dd)
            if _overlap(desk_box, bed_box):
                dx = max(MARGIN, bed_box[2] + 0.15)
                desk_box = (dx, dy, dx + dw, dy + dd)
            chair = (dx, dy - 0.55, dx + dw, dy)
            if _overlap(chair, bed_box) or _overlap(desk_box, bed_box):
                dx = MARGIN
                if ward_box is not None and wardrobe_west:
                    dx = ward_box[2] + 0.12
                desk_box = (dx, dy, dx + dw, dy + dd)
                chair = (dx, dy - 0.55, dx + dw, dy)
                if _overlap(chair, bed_box) or _overlap(desk_box, bed_box):
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
        else:
            # Bed on north → keep desk on north wall east of bed (chair −Y into room).
            # Wardrobe already on south; desk must not use south (chair would hit wall).
            dy = room_d - dd - MARGIN
            if bed_box is not None:
                dx = bed_box[2] + 0.15
            else:
                dx = MARGIN
            if wardrobe_west is False:
                # Prefer desk west of bed when storage order is wardrobe_east.
                dx = MARGIN
                if bed_box is not None and dx + dw > bed_box[0] - 0.1:
                    # Fall back east of bed if west strip too tight.
                    dx = bed_box[2] + 0.15
            if door is not None and door_side == "east":
                max_x = room_w - DOOR_ACCESS_KEEP - dw
                if dx > max_x:
                    dx = max(MARGIN, max_x)
            desk_box = (dx, dy, dx + dw, dy + dd)
            if _overlap(desk_box, bed_box):
                # Mid-west free floor south of bed footprint.
                dx = MARGIN
                dy = max(MARGIN, (bed_box[1] if bed_box else room_d * 0.5) - dd - 0.6)
                if ward_box is not None and dy < ward_box[3] + 0.15:
                    dy = ward_box[3] + 0.15
                desk_box = (dx, dy, dx + dw, dy + dd)
            chair = (dx, dy - 0.55, dx + dw, dy)
            if _overlap(chair, bed_box) or _overlap(desk_box, bed_box) or _overlap(desk_box, ward_box):
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
                notes.append("Desk near north/west; chair clearance shortened to fit.")
            else:
                commands.append(_desk_cmd(dx, dy, dw, dd, collection))
                notes.append("Desk on north strip; chair clearance faces south into free floor.")

    return commands, notes, bed_box


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
    spec = _resolve_strategy(params)

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
    assumes.append(f"strategy={spec['strategy']}")

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

    furn_cmds, notes, _bed_box = _place_furniture(
        room_w=room_w,
        room_d=room_d,
        room_h=room_h,
        collection=collection,
        door=door,
        door_side=door_side,
        win_south=win_south,
        include_bed=include_bed,
        include_wardrobe=include_wardrobe,
        include_desk=include_desk,
        mattress_w=mattress_w,
        mattress_l=mattress_l,
        bed_wall=spec["bed_wall"],
        storage_order=spec["storage_order"],
    )
    commands.extend(furn_cmds)

    return {
        "ok": True,
        "recipe": RECIPE_NAME,
        "recipe_kind": RECIPE_KIND,
        "recipe_goals": list(RECIPE_GOALS),
        "strategy": spec["strategy"],
        "commands": commands,
        "assumes": assumes,
        "notes": notes,
        "room": {"width": room_w, "depth": room_d, "height": room_h, "name": ROOM_NAME},
    }


def enumerate_bedroom_candidates(params: dict | None = None) -> list[dict[str, Any]]:
    """Expand bedroom_basic into 2–4 distinct candidate command sets (no quality yet)."""
    params = dict(params or {})
    prefer = str(params.get("prefer_bed_wall") or params.get("bed_wall") or "").strip().lower()
    specs = list(_STRATEGY_SPECS)
    if prefer in ("south", "north"):
        preferred = [s for s in specs if s["bed_wall"] == prefer]
        other = [s for s in specs if s["bed_wall"] != prefer]
        specs = preferred + other

    out: list[dict[str, Any]] = []
    for spec in specs[:4]:
        call = dict(params)
        call["strategy"] = spec["strategy"]
        call["bed_wall"] = spec["bed_wall"]
        call["storage_order"] = spec["storage_order"]
        planned = plan_bedroom_basic(call)
        out.append(
            {
                "candidate_id": spec["strategy"],
                "strategy": spec["strategy"],
                "commands": planned.get("commands") or [],
                "assumes": planned.get("assumes") or [],
                "notes": planned.get("notes") or [],
            }
        )
    return out


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
