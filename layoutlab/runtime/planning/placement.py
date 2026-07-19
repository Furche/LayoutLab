"""Deterministic placement fixes (bed snap, overlaps, improve-layout)."""

from __future__ import annotations

from .intent import (
    parse_bed_size_m,
    user_mentions_bed_head,
    user_wants_bed,
    user_wants_better_layout,
    user_wants_room,
)

# Last accepted proposal fingerprint (this Core process) — detect identical "improve" replies.
last_placement_fp: tuple | None = None


def mattress_to_bed_axes(head_side: str | None, mattress_w: float, mattress_l: float):
    """Map human width×length onto bed_basic length(X)/width(Y)."""
    side = (head_side or "y_min").strip().lower()
    if side in ("x_min", "x_max"):
        return round(mattress_l, 3), round(mattress_w, 3)
    return round(mattress_w, 3), round(mattress_l, 3)


def loc_delta(a, b) -> float:
    ax, ay, _az = as_xyz(a)
    bx, by, _bz = as_xyz(b)
    return max(abs(ax - bx), abs(ay - by))


def apply_requested_bed_size(commands: list, mattress_w: float, mattress_l: float) -> bool:
    """Set bed dims from human mattress size; keep head_side. Returns True if changed."""
    changed = False
    for cmd in commands:
        if cmd.get("action") != "run_generator" or cmd.get("generator") != "bed_basic":
            continue
        params = dict(cmd.get("params") or {})
        head = params.get("head_side") or "y_min"
        length, width = mattress_to_bed_axes(head, mattress_w, mattress_l)
        try:
            old_l = float(params.get("length") or 0)
            old_w = float(params.get("width") or 0)
        except (TypeError, ValueError):
            old_l, old_w = 0.0, 0.0
        if abs(old_l - length) < 0.02 and abs(old_w - width) < 0.02:
            continue
        params["length"] = length
        params["width"] = width
        cmd["params"] = params
        changed = True
    return changed


def room_size_from_commands(commands: list) -> tuple[float, float]:
    for cmd in commands or []:
        if cmd.get("action") != "create_room":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        w = params.get("width", cmd.get("width"))
        d = params.get("depth", cmd.get("depth"))
        try:
            return float(w), float(d)
        except (TypeError, ValueError):
            break
    return 4.0, 3.0


def nearest_wall_side(location, room_w: float, room_d: float) -> str:
    x, y, _z = as_xyz(location)
    dist = {
        "x_min": x,
        "x_max": max(0.0, room_w - x),
        "y_min": y,
        "y_max": max(0.0, room_d - y),
    }
    return min(dist, key=dist.get)


def east_door_present(commands: list) -> bool:
    for cmd in commands or []:
        if cmd.get("action") != "add_opening":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        kind = str(params.get("kind") or cmd.get("kind") or "").lower()
        wall = str(params.get("wall_side") or cmd.get("wall_side") or "").lower()
        if kind == "door" and wall == "east":
            return True
    return False


def as_xyz(location) -> list[float]:
    """Normalize location to [x,y,z] — LLM sometimes emits dicts instead of arrays."""
    if isinstance(location, dict):

        def _pick(*keys):
            for k in keys:
                candidates = (k, str(k)) if isinstance(k, int) else (k,)
                for key in candidates:
                    if key in location and location[key] is not None:
                        try:
                            return float(location[key])
                        except (TypeError, ValueError):
                            continue
            return 0.0

        return [_pick("x", "X", 0), _pick("y", "Y", 1), _pick("z", "Z", 2)]
    if isinstance(location, (list, tuple)):
        out = []
        for i in range(3):
            try:
                out.append(float(location[i]) if i < len(location) else 0.0)
            except (TypeError, ValueError):
                out.append(0.0)
        return out
    return [0.0, 0.0, 0.0]


def placement_fingerprint(commands: list) -> tuple:
    parts = []
    for cmd in commands or []:
        if cmd.get("action") != "run_generator":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        loc = as_xyz(params.get("location"))
        loc_t = tuple(round(v, 3) for v in loc)
        parts.append(
            (
                cmd.get("generator"),
                loc_t,
                params.get("head_side"),
                params.get("front_side"),
            )
        )
    return tuple(parts)


def snap_bed_to_wall(params: dict, room_w: float, room_d: float, *, prefer: str | None = None):
    """Move bed footprint against a wall; set matching head_side.

    bed_basic axes are fixed: length=X, width=Y. Orientation:
    - head on south/north (y_*): sleep along Y → X = mattress width, Y = mattress length
      (normal 120×200 → length=1.2, width=2.0 — NOT 2.0 along the wall).
    - head on east/west (x_*): sleep along X → length = mattress length, width = mattress width.
    Returns (location, head_side, dim_updates_or_None).
    """
    try:
        length = float(params.get("length") or 2.0)
        width = float(params.get("width") or 1.2)
    except (TypeError, ValueError):
        length, width = 2.0, 1.2
    margin = 0.08
    hug = 0.18
    x, y, z = as_xyz(params.get("location"))

    gap = {
        "y_min": y,
        "y_max": room_d - (y + width),
        "x_min": x,
        "x_max": room_w - (x + length),
    }
    side = prefer or min(gap, key=gap.get)
    # Not already hugging a wall → default south wall for bedrooms.
    if prefer is None and min(gap.values()) > 0.25:
        side = "y_min"

    # Ensure sleep axis is the longer mattress dimension when dims look swapped.
    swapped = False
    if side in ("y_min", "y_max") and length > width:
        length, width = width, length
        swapped = True
    elif side in ("x_min", "x_max") and width > length:
        length, width = width, length
        swapped = True

    # Recompute gap after possible dim swap.
    gap = {
        "y_min": y,
        "y_max": room_d - (y + width),
        "x_min": x,
        "x_max": room_w - (x + length),
    }
    already_hugging = gap.get(side, 999) <= hug

    if already_hugging and prefer is None:
        # Keep placement; only clamp footprint inside the room.
        x = max(margin, min(room_w - length - margin, x))
        y = max(margin, min(room_d - width - margin, y))
        if side == "y_min":
            y = margin
            head = "y_min"
        elif side == "y_max":
            y = max(margin, room_d - width - margin)
            head = "y_max"
        elif side == "x_min":
            x = margin
            head = "x_min"
        else:
            x = max(margin, room_w - length - margin)
            head = "x_max"
    elif side == "y_min":
        x = max(margin, min(room_w - length - margin, (room_w - length) / 2))
        y = margin
        head = "y_min"
    elif side == "y_max":
        x = max(margin, min(room_w - length - margin, (room_w - length) / 2))
        y = max(margin, room_d - width - margin)
        head = "y_max"
    elif side == "x_min":
        x = margin
        y = max(margin, min(room_d - width - margin, (room_d - width) / 2))
        head = "x_min"
    else:
        x = max(margin, room_w - length - margin)
        y = max(margin, min(room_d - width - margin, (room_d - width) / 2))
        head = "x_max"
    dims = {"length": round(length, 3), "width": round(width, 3)} if swapped else None
    return [round(x, 3), round(y, 3), round(z, 3)], head, dims


def gen_xy_aabb(gen: str, params: dict):
    x, y, _z = as_xyz(params.get("location"))
    if gen == "bed_basic":
        try:
            length = float(params.get("length") or 2.0)
            width = float(params.get("width") or 1.2)
        except (TypeError, ValueError):
            length, width = 2.0, 1.2
        return (x, y, x + length, y + width)
    if gen in ("desk_basic", "wardrobe_basic"):
        try:
            w = float(params.get("width") or 1.0)
            d = float(params.get("depth") or 0.6)
        except (TypeError, ValueError):
            w, d = 1.0, 0.6
        return (x, y, x + w, y + d)
    return None


def aabb_overlap_tuple(a, b) -> bool:
    if not a or not b:
        return False
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def separate_furniture_overlaps(commands: list, room_w: float, room_d: float) -> bool:
    """Push desk/wardrobe out of bed footprint if AABBs overlap."""
    items = []
    for cmd in commands:
        if cmd.get("action") != "run_generator":
            continue
        gen = cmd.get("generator")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        if not params or not gen:
            continue
        box = gen_xy_aabb(gen, params)
        if box:
            items.append((cmd, gen, params, box))

    changed = False
    beds = [it for it in items if it[1] == "bed_basic"]
    desks = [it for it in items if it[1] == "desk_basic"]
    wards = [it for it in items if it[1] == "wardrobe_basic"]
    margin = 0.12

    for cmd, _gen, params, box in desks:
        for _bcmd, _bgen, bparams, bbox in beds:
            if not aabb_overlap_tuple(box, bbox):
                continue
            bw = float(bparams.get("length") or 2.0)
            bh = float(bparams.get("width") or 1.2)
            bx, by, _bz = as_xyz(bparams.get("location"))
            dw = float(params.get("width") or 1.2)
            dd = float(params.get("depth") or 0.6)
            candidates = [
                [bx + bw + margin, by, 0.0],
                [bx, by + bh + margin, 0.0],
                [max(0.08, bx - dw - margin), by, 0.0],
            ]
            new_loc = None
            for cand in candidates:
                if cand[0] < 0.05 or cand[1] < 0.05:
                    continue
                if cand[0] + dw > room_w - 0.05 or cand[1] + dd > room_d - 0.05:
                    continue
                test = (cand[0], cand[1], cand[0] + dw, cand[1] + dd)
                if not aabb_overlap_tuple(test, bbox):
                    new_loc = [round(cand[0], 3), round(cand[1], 3), 0.0]
                    break
            if new_loc is None:
                new_loc = [0.15, round(max(0.15, room_d - dd - 0.15), 3), 0.0]
            params = dict(params)
            params["location"] = new_loc
            cmd["params"] = params
            box = gen_xy_aabb("desk_basic", params)
            changed = True

    for cmd, _gen, params, box in wards:
        for _bcmd, _bgen, bparams, bbox in beds:
            if not aabb_overlap_tuple(box, bbox):
                continue
            depth = float(params.get("depth") or 0.6)
            width = float(params.get("width") or 1.0)
            _bx, by, _bz = as_xyz(bparams.get("location"))
            params = dict(params)
            params["location"] = [
                round(0.08, 3),
                round(
                    max(0.15, min(by, room_d - depth - 0.15)),
                    3,
                ),
                0.0,
            ]
            params["front_side"] = "y_min"
            cmd["params"] = params
            changed = True
    return changed


def apply_improved_bedroom_layout(commands: list, room_w: float, room_d: float) -> bool:
    """Force a distinct wall-based arrangement (used when user asks for better)."""
    margin = 0.08
    east_door = east_door_present(commands)
    changed = False
    for cmd in commands:
        if cmd.get("action") != "run_generator":
            continue
        gen = cmd.get("generator")
        params = dict(cmd.get("params") or {})
        if gen == "bed_basic":
            # Alternate: north wall
            loc, head, dims = snap_bed_to_wall(params, room_w, room_d, prefer="y_max")
            if params.get("location") != loc or params.get("head_side") != head or dims:
                params["location"] = loc
                params["head_side"] = head
                if dims:
                    params.update(dims)
                cmd["params"] = params
                changed = True
        elif gen == "wardrobe_basic":
            depth = float(params.get("depth") or 0.6)
            width = float(params.get("width") or 1.0)
            # North wall west — wardrobe_basic only supports y fronts
            loc = [
                round(margin, 3),
                round(max(margin, room_d - depth - margin), 3),
                0.0,
            ]
            if east_door and loc[0] + width > room_w - 1.0:
                loc[0] = round(max(margin, room_w - 1.0 - width), 3)
            if params.get("location") != loc or params.get("front_side") != "y_min":
                params["location"] = loc
                params["front_side"] = "y_min"
                cmd["params"] = params
                changed = True
        elif gen == "desk_basic":
            depth = float(params.get("depth") or 0.6)
            width = float(params.get("width") or 1.2)
            # West / north of south window strip — not on top of a south-wall bed
            loc = [
                round(margin, 3),
                round(margin + 1.4, 3),
                0.0,
            ]
            if east_door and loc[0] + width > room_w - 1.0:
                loc[0] = round(max(margin, room_w - width - 1.1), 3)
            if params.get("location") != loc:
                params["location"] = loc
                cmd["params"] = params
                changed = True
    return changed


def apply_deterministic_placement_fixes(conversation: str, result: dict) -> dict:
    """Fix common LLM misses: floating beds, head_side, door-blocking storage."""
    commands = list(result.get("commands") or [])
    if not commands:
        return result
    room_w, room_d = room_size_from_commands(commands)
    want_head = user_mentions_bed_head(conversation)
    want_better = user_wants_better_layout(conversation)
    east_door = east_door_present(commands)
    requested_size = parse_bed_size_m(conversation)
    changed = False
    notes = []
    bed_size_changed = False
    bed_size_already_ok = False

    if requested_size is not None:
        before = [c.get("params") for c in commands if c.get("generator") == "bed_basic"]
        bed_size_changed = apply_requested_bed_size(commands, requested_size[0], requested_size[1])
        if bed_size_changed:
            changed = True
            notes.append(
                f"Bettmaß auf {int(requested_size[0] * 100)}×{int(requested_size[1] * 100)} cm "
                "(Breite × Länge)."
            )
        elif before:
            bed_size_already_ok = True

    if want_better:
        if apply_improved_bedroom_layout(commands, room_w, room_d):
            changed = True
            notes.append("Layout-Korrektur: alternative Wandplatzierung (bessere Lösung).")

    for cmd in commands:
        if cmd.get("action") != "run_generator":
            continue
        gen = cmd.get("generator")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        if not params:
            continue
        if gen == "bed_basic":
            prefer = "y_max" if want_better else None
            if want_head and not want_better:
                prefer = nearest_wall_side(params.get("location") or [0, 0, 0], room_w, room_d)
            loc, head, dims = snap_bed_to_wall(params, room_w, room_d, prefer=prefer)
            old_head = params.get("head_side")
            moved = loc_delta(params.get("location") or [0, 0, 0], loc) > 0.12
            head_fix = old_head != head
            orient_fix = bool(
                dims
                and (
                    abs(float(params.get("length") or 0) - dims["length"]) > 0.02
                    or abs(float(params.get("width") or 0) - dims["width"]) > 0.02
                )
            )
            if moved or head_fix or orient_fix:
                params = dict(params)
                params["location"] = loc
                params["head_side"] = head
                if dims:
                    params.update(dims)
                cmd["params"] = params
                changed = True
                # Announce only meaningful fixes — not silent re-snap of an already good bed.
                if moved or (head_fix and old_head not in (None, head)):
                    if "Bett an die Wand" not in "".join(notes):
                        notes.append("Layout-Korrektur: Bett an die Wand (head_side).")
                elif orient_fix and "Orientierung" not in "".join(notes):
                    notes.append("Layout-Korrektur: Bett-Orientierung (Schlafrichtung).")
        if gen == "wardrobe_basic" and east_door:
            loc = as_xyz(params.get("location"))
            x = loc[0]
            if x > room_w * 0.55:
                depth = float(params.get("depth") or 0.6)
                y, z = loc[1], loc[2]
                params = dict(params)
                params["location"] = [max(0.15, depth / 2 + 0.05), max(0.15, y), z]
                # wardrobe_basic only supports y_min / y_max
                params["front_side"] = "y_min"
                cmd["params"] = params
                changed = True
                notes.append("Layout-Korrektur: Schrank von der Ost-Tür weg.")
        if gen == "desk_basic" and east_door:
            loc = as_xyz(params.get("location"))
            try:
                x = loc[0]
                width = float(params.get("width") or 1.2)
            except (TypeError, ValueError):
                x, width = 0.0, 1.2
            if x + width > room_w - 1.0:
                params = dict(params)
                params["location"] = [
                    round(max(0.15, min(x, room_w - width - 1.1)), 3),
                    round(float(loc[1]) if len(loc) > 1 else 0.15, 3),
                    float(loc[2]) if len(loc) > 2 else 0.0,
                ]
                cmd["params"] = params
                changed = True
                notes.append("Layout-Korrektur: Schreibtisch aus dem Türbereich.")

    if want_better and last_placement_fp is not None:
        if placement_fingerprint(commands) == last_placement_fp:
            if apply_improved_bedroom_layout(commands, room_w, room_d):
                changed = True
                notes.append("Layout-Korrektur: erzwungene Umstellung (vorher identisch).")

    if separate_furniture_overlaps(commands, room_w, room_d):
        changed = True
        notes.append("Layout-Korrektur: Möbel-Überlappung getrennt (z.B. Tisch aus dem Bett).")

    if bed_size_already_ok and not changed:
        result = dict(result)
        w_cm, l_cm = int(requested_size[0] * 100), int(requested_size[1] * 100)
        result["reply"] = (
            f"Das Bett ist bereits {w_cm}×{l_cm} cm (Breite × Länge) — keine Änderung nötig."
        )
        return result

    if not changed:
        return result

    result = dict(result)
    result["commands"] = commands
    proposal = dict(result.get("proposal") or {})
    proposal["commands"] = commands
    result["proposal"] = proposal
    if notes:
        result["reply"] = (result.get("reply") or "").rstrip() + " (" + " ".join(notes) + ")"
    return result


def layout_shell_fingerprint(commands: list) -> tuple:
    """Compare room shell + openings + generators (ignore tiny float noise)."""
    parts = []
    for cmd in commands or []:
        action = cmd.get("action")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        if action == "create_room":
            parts.append(
                (
                    "room",
                    round(float(params.get("width") or cmd.get("width") or 0), 2),
                    round(float(params.get("depth") or cmd.get("depth") or 0), 2),
                )
            )
        elif action == "add_opening":
            parts.append(
                (
                    "open",
                    params.get("kind") or cmd.get("kind"),
                    params.get("wall_side") or cmd.get("wall_side"),
                    round(float(params.get("width") or cmd.get("width") or 0), 2),
                )
            )
        elif action == "run_generator":
            parts.append(("gen", cmd.get("generator")))
    return tuple(parts)


def proposal_wants_layout(commands: list, conversation: str, questions: list) -> bool:
    if questions and not commands:
        return False
    actions = {c.get("action") for c in commands or []}
    if "create_room" in actions or "run_generator" in actions or "add_opening" in actions:
        return True
    if not commands and (
        user_wants_room(conversation) or user_wants_bed(conversation)
    ):
        return True
    return False
