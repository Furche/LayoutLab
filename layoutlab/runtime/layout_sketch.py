"""Top-down layout sketch for the agent (text + structured XY) — no meshes / no bpy.

Gives the LLM a spatial abstraction of the room: walls, openings, furniture AABBs,
and clearance usage zones.
"""

from __future__ import annotations

import json

from .analyze import world_bounds_for_target

_GEN_LABEL = {
    "bed_basic": "B",
    "wardrobe_basic": "S",
    "desk_basic": "T",
}

_MAX_COLS = 48
_MAX_ROWS = 32


def _round2(v) -> float:
    return round(float(v), 2)


def _furniture_groups(session, collection: str | None):
    """Main furniture meshes keyed by object_id (skip clearances/labels/walls)."""
    groups = {}
    for obj in session.mesh_store.objects:
        if collection and obj.collection != collection:
            continue
        role = obj.get("layoutlab_role") or ""
        if role in ("clearance", "label", "room_wall", "room_floor", "opening"):
            continue
        if obj.get("layoutlab_clearance_name"):
            continue
        if obj.type == "FONT" or role == "label":
            continue
        gen = obj.get("layoutlab_generator") or ""
        if not gen and role not in ("body", "main", ""):
            continue
        if not gen:
            continue
        oid = obj.get("layoutlab_object_id") or obj.name
        groups.setdefault(oid, []).append(obj)
    return groups


def _iter_clearances(session, collection: str | None):
    for obj in session.mesh_store.objects:
        if collection and obj.collection != collection:
            continue
        cname = obj.get("layoutlab_clearance_name")
        role = obj.get("layoutlab_role") or ""
        if not cname and role != "clearance":
            continue
        yield obj


def _group_bounds_xy(objs):
    mins_x, mins_y, maxs_x, maxs_y = [], [], [], []
    for obj in objs:
        b = world_bounds_for_target(obj)
        mn, mx = b["min"], b["max"]
        mins_x.append(float(mn[0]))
        mins_y.append(float(mn[1]))
        maxs_x.append(float(mx[0]))
        maxs_y.append(float(mx[1]))
    return {
        "min": [_round2(min(mins_x)), _round2(min(mins_y))],
        "max": [_round2(max(maxs_x)), _round2(max(maxs_y))],
    }


def _pick_label(name: str, generator: str, used: set) -> str:
    preferred = _GEN_LABEL.get(generator or "")
    candidates = []
    if preferred:
        candidates.append(preferred)
    for ch in (name or "").upper():
        if "A" <= ch <= "Z":
            candidates.append(ch)
    candidates.extend("ABCDEFGHJKLMNPQRSTUVWXYZ")
    for ch in candidates:
        if ch not in used:
            used.add(ch)
            return ch
    for i in range(10):
        ch = str(i)
        if ch not in used:
            used.add(ch)
            return ch
    return "?"


def _opening_cells(wall_side: str, offset, width, cols: int, rows: int, room_w: float, room_d: float):
    """Map an opening onto border cells of the ascii grid."""
    try:
        offset = float(offset or 0.0)
        width = float(width or 0.0)
    except (TypeError, ValueError):
        return []
    if cols < 2 or rows < 2 or room_w <= 0 or room_d <= 0 or width <= 0:
        return []
    cells = []
    side = (wall_side or "").lower()
    if side == "south":
        c0 = int(offset / room_w * (cols - 1))
        c1 = int((offset + width) / room_w * (cols - 1))
        for c in range(max(0, c0), min(cols, c1 + 1)):
            cells.append((rows - 1, c))
    elif side == "north":
        c0 = int(offset / room_w * (cols - 1))
        c1 = int((offset + width) / room_w * (cols - 1))
        for c in range(max(0, c0), min(cols, c1 + 1)):
            cells.append((0, c))
    elif side == "west":
        r0 = int((1.0 - (offset + width) / room_d) * (rows - 1))
        r1 = int((1.0 - offset / room_d) * (rows - 1))
        for r in range(max(0, min(r0, r1)), min(rows, max(r0, r1) + 1)):
            cells.append((r, 0))
    elif side == "east":
        r0 = int((1.0 - (offset + width) / room_d) * (rows - 1))
        r1 = int((1.0 - offset / room_d) * (rows - 1))
        for r in range(max(0, min(r0, r1)), min(rows, max(r0, r1) + 1)):
            cells.append((r, cols - 1))
    return cells


def _fill_rect(grid, bounds, label, ox, oy, room_w, room_d, cols, rows, *, overwrite=None):
    """Paint AABB onto grid. ``overwrite`` = cells that may be replaced."""
    if overwrite is None:
        overwrite = (".", "#")
    mn, mx = bounds["min"], bounds["max"]
    x0 = (float(mn[0]) - ox) / room_w
    x1 = (float(mx[0]) - ox) / room_w
    y0 = (float(mn[1]) - oy) / room_d
    y1 = (float(mx[1]) - oy) / room_d
    c0 = int(max(0, min(cols - 1, x0 * (cols - 1))))
    c1 = int(max(0, min(cols - 1, x1 * (cols - 1))))
    r_south = int(max(0, min(rows - 1, (1.0 - y0) * (rows - 1))))
    r_north = int(max(0, min(rows - 1, (1.0 - y1) * (rows - 1))))
    for r in range(min(r_north, r_south), max(r_north, r_south) + 1):
        for c in range(min(c0, c1), max(c0, c1) + 1):
            if grid[r][c] in overwrite:
                grid[r][c] = label


def build_layout_sketch(session, params=None) -> dict:
    """Return structured XY + ASCII top-down for rooms in the session."""
    params = params or {}
    collection = params.get("collection")
    # Clearance zones on by default — agent needs usage space, not only solids.
    include_clearances = bool(params.get("include_clearances", True))

    rooms_out = []
    ascii_blocks = []
    legend = {}

    for model in session._rooms.values():
        coll = model.get("collection") or "layoutlab_room"
        if collection and coll != collection:
            continue
        fp = model.get("footprint") or {}
        try:
            room_w = float(fp.get("width") or 0)
            room_d = float(fp.get("depth") or 0)
        except (TypeError, ValueError):
            room_w = room_d = 0.0
        origin = list(model.get("origin") or [0, 0, 0])
        ox, oy = float(origin[0]), float(origin[1])
        if room_w <= 0 or room_d <= 0:
            continue

        if room_w >= room_d:
            cols = _MAX_COLS
            rows = max(8, int(round(_MAX_COLS * room_d / room_w)))
            rows = min(rows, _MAX_ROWS)
        else:
            rows = _MAX_ROWS
            cols = max(8, int(round(_MAX_ROWS * room_w / room_d)))
            cols = min(cols, _MAX_COLS)

        grid = [["." for _ in range(cols)] for _ in range(rows)]
        for c in range(cols):
            grid[0][c] = "#"
            grid[rows - 1][c] = "#"
        for r in range(rows):
            grid[r][0] = "#"
            grid[r][cols - 1] = "#"

        clearances_out = []
        if include_clearances:
            legend["+"] = "preferred clearance (usage zone)"
            legend["*"] = "required clearance (must stay clear)"
            # Preferred first, then required overwrites preferred where both exist.
            preferred = []
            required = []
            for obj in _iter_clearances(session, coll):
                req = str(obj.get("layoutlab_clearance_requirement") or "preferred").lower()
                (required if req == "required" else preferred).append(obj)
            for obj in preferred + required:
                req = str(obj.get("layoutlab_clearance_requirement") or "preferred").lower()
                mark = "*" if req == "required" else "+"
                bounds = _group_bounds_xy([obj])
                cname = obj.get("layoutlab_clearance_name") or "clearance"
                clearances_out.append(
                    {
                        "name": obj.name,
                        "clearance_name": cname,
                        "requirement": req,
                        "mark": mark,
                        "object_id": obj.get("layoutlab_object_id") or "",
                        "bounds_xy": bounds,
                    }
                )
                overwrite = (".",) if mark == "+" else (".", "+")
                _fill_rect(
                    grid,
                    bounds,
                    mark,
                    ox,
                    oy,
                    room_w,
                    room_d,
                    cols,
                    rows,
                    overwrite=overwrite,
                )

        openings_out = []
        for op in model.get("openings") or []:
            kind = str(op.get("kind") or "").lower()
            mark = "D" if kind == "door" else "W" if kind == "window" else "O"
            side = op.get("wall_side") or ""
            openings_out.append(
                {
                    "name": op.get("name"),
                    "kind": kind,
                    "wall_side": side,
                    "offset": _round2(op.get("offset") or 0),
                    "width": _round2(op.get("width") or 0),
                }
            )

        used_labels = {"D", "W", "O", "#", "+", "*"}
        furniture_out = []
        groups = _furniture_groups(session, coll)
        for oid, objs in groups.items():
            gen = objs[0].get("layoutlab_generator") or ""
            name = objs[0].get("layoutlab_name") or objs[0].name
            for o in objs:
                if o.get("layoutlab_role") in ("body", "main") or o.name.endswith("_body"):
                    name = o.name.rsplit("_", 1)[0] if "_" in o.name else o.name
                    break
            else:
                name = name.rsplit("_", 1)[0] if "_" in str(name) else name
            bounds = _group_bounds_xy(objs)
            label = _pick_label(str(name), gen, used_labels)
            head_side = None
            for o in objs:
                raw = o.get("layoutlab_params")
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except Exception:
                        raw = None
                if isinstance(raw, dict) and raw.get("head_side"):
                    head_side = raw.get("head_side")
                    break
            entry = {
                "label": label,
                "name": name,
                "generator": gen,
                "object_id": oid,
                "bounds_xy": bounds,
            }
            if head_side:
                entry["head_side"] = head_side
            furniture_out.append(entry)
            legend[label] = f"{name} ({gen})" if gen else str(name)
            _fill_rect(
                grid,
                bounds,
                label,
                ox,
                oy,
                room_w,
                room_d,
                cols,
                rows,
                overwrite=(".", "+", "*", "#"),
            )

        # Openings last so D/W stay visible on the wall edge.
        for op in model.get("openings") or []:
            kind = str(op.get("kind") or "").lower()
            mark = "D" if kind == "door" else "W" if kind == "window" else "O"
            for r, c in _opening_cells(
                op.get("wall_side") or "",
                op.get("offset"),
                op.get("width"),
                cols,
                rows,
                room_w,
                room_d,
            ):
                grid[r][c] = mark

        ascii_map = "\n".join("".join(row) for row in grid)
        header = (
            f"room={model.get('name')} {room_w:.2f}x{room_d:.2f}m  "
            f"(ascii: top=N / bottom=S / left=W / right=E)"
        )
        ascii_blocks.append(header + "\n" + ascii_map)

        room_entry = {
            "name": model.get("name"),
            "room_id": model.get("room_id"),
            "collection": coll,
            "origin_xy": [_round2(ox), _round2(oy)],
            "width": _round2(room_w),
            "depth": _round2(room_d),
            "openings": openings_out,
            "furniture": furniture_out,
        }
        if include_clearances:
            room_entry["clearances"] = clearances_out
            room_entry["clearance_count"] = len(clearances_out)
        rooms_out.append(room_entry)

    notes = [
        "Top-down XY abstraction (not the 3D viewport).",
        "#=wall  D=door  W=window  .=free floor  letters=furniture (see legend)",
        "ascii top = north (+Y), right = east (+X)",
        "Use bounds_xy / openings / clearances to revise placement; head_side when present.",
    ]
    if include_clearances:
        notes.insert(
            2,
            "+=preferred clearance  *=required clearance — keep * clear; avoid packing into +",
        )

    if not rooms_out:
        return {
            "ok": True,
            "unit": "METRIC",
            "include_clearances": include_clearances,
            "rooms": [],
            "ascii": "(empty scene — no rooms)",
            "legend": {},
            "notes": notes + ["Call after dry_run_commands to see the proposed layout."],
        }

    return {
        "ok": True,
        "unit": "METRIC",
        "include_clearances": include_clearances,
        "rooms": rooms_out,
        "ascii": "\n\n".join(ascii_blocks),
        "legend": legend,
        "notes": notes,
    }
