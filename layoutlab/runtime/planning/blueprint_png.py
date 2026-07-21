"""Standardized top-down blueprint PNGs for DD-017 aesthetic visual evidence.

Stdlib only (no Pillow). Same conventions as Viewer floorplan: top=N, right=E.
"""

from __future__ import annotations

import base64
import struct
import zlib
from typing import Any

# Role → RGB
_FURNITURE_RGB = {
    "bed_frame": (196, 165, 116),
    "bed_mattress": (212, 196, 168),
    "bed_pillow": (232, 220, 200),
    "wardrobe_body": (138, 155, 176),
    "wardrobe_door": (154, 171, 190),
    "desk_body": (139, 115, 85),
    "desk_top": (196, 165, 116),
    "desk_leg": (139, 115, 85),
    "default": (160, 168, 180),
}

_SKIP_ROLES = frozenset(
    {"label", "clearance", "room_floor", "room_wall", "room_opening", "room_fixed"}
)

_BG = (14, 17, 22)
_FLOOR = (28, 36, 48)
_WALL = (215, 222, 232)
_DOOR = (97, 175, 239)
_WINDOW = (152, 195, 121)


def _role_of(obj: dict) -> str:
    lab = obj.get("layoutlab") if isinstance(obj.get("layoutlab"), dict) else {}
    return str(lab.get("role") or "default")


def _aabb_xy(obj: dict) -> tuple[float, float, float, float] | None:
    corners = obj.get("world_bbox_corners")
    if not isinstance(corners, list) or len(corners) < 2:
        return None
    xs, ys = [], []
    for c in corners:
        if isinstance(c, (list, tuple)) and len(c) >= 2:
            xs.append(float(c[0]))
            ys.append(float(c[1]))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _opening_span(room_w: float, room_d: float, opening: dict) -> dict | None:
    side = str(opening.get("wall_side") or "").lower()
    offset = float(opening.get("offset") or 0)
    width = max(0.2, float(opening.get("width") or 0.9))
    if side == "south":
        return {"side": side, "x0": offset, "y0": 0.0, "x1": offset + width, "y1": 0.0}
    if side == "north":
        return {"side": side, "x0": offset, "y0": room_d, "x1": offset + width, "y1": room_d}
    if side == "west":
        return {"side": side, "x0": 0.0, "y0": offset, "x1": 0.0, "y1": offset + width}
    if side == "east":
        return {"side": side, "x0": room_w, "y0": offset, "x1": room_w, "y1": offset + width}
    return None


def _png_rgb(width: int, height: int, pixels: bytearray) -> bytes:
    """Encode raw RGB rows as PNG (zlib, no filter)."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = bytearray()
    row = width * 3
    for y in range(height):
        raw.append(0)  # filter None
        start = y * row
        raw.extend(pixels[start : start + row])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


class _Canvas:
    def __init__(self, width: int, height: int, bg=_BG):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        self.fill(0, 0, width, height, bg)

    def _set(self, x: int, y: int, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i : i + 3] = bytes(rgb)

    def fill(self, x0: int, y0: int, x1: int, y1: int, rgb):
        xa, xb = sorted((int(x0), int(x1)))
        ya, yb = sorted((int(y0), int(y1)))
        xa = max(0, xa)
        ya = max(0, ya)
        xb = min(self.w, xb)
        yb = min(self.h, yb)
        for y in range(ya, yb):
            for x in range(xa, xb):
                self._set(x, y, rgb)

    def line(self, x0: float, y0: float, x1: float, y1: float, rgb, thickness: int = 2):
        # Bresenham + thickness
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for ox in range(-thickness // 2, thickness // 2 + 1):
                for oy in range(-thickness // 2, thickness // 2 + 1):
                    self._set(x0 + ox, y0 + oy, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def arc_quarter(self, hx: float, hy: float, cx: float, cy: float, ox: float, oy: float, rgb, steps: int = 24):
        """Polyline quarter-circle hinge→closed→open (convex into room)."""
        import math

        r = math.hypot(cx - hx, cy - hy)
        if r < 1:
            return
        a0 = math.atan2(cy - hy, cx - hx)
        a1 = math.atan2(oy - hy, ox - hx)
        # shortest signed delta
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        pts = []
        for i in range(steps + 1):
            t = i / steps
            a = a0 + da * t
            pts.append((hx + r * math.cos(a), hy + r * math.sin(a)))
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], rgb, thickness=2)

    def png(self) -> bytes:
        return _png_rgb(self.w, self.h, self.px)


def render_blueprint_png(
    viewer_preview: dict | None, *, max_side: int = 512, pad_px: int = 28
) -> bytes | None:
    """Render slim viewer_preview → PNG bytes (identical framing for aesthetics)."""
    if not isinstance(viewer_preview, dict):
        return None
    rooms = viewer_preview.get("rooms") or []
    if not rooms or not isinstance(rooms[0], dict):
        return None
    room = rooms[0]
    fp = room.get("footprint") if isinstance(room.get("footprint"), dict) else {}
    room_w = float(fp.get("width") or 0)
    room_d = float(fp.get("depth") or 0)
    if room_w <= 0 or room_d <= 0:
        return None

    scale = (max_side - 2 * pad_px) / max(room_w, room_d)
    img_w = int(round(room_w * scale + 2 * pad_px))
    img_h = int(round(room_d * scale + 2 * pad_px))
    canvas = _Canvas(img_w, img_h)

    def to_px(x: float, y: float) -> tuple[float, float]:
        # top = north
        return pad_px + x * scale, pad_px + (room_d - y) * scale

    # Floor
    x0, y0 = to_px(0, room_d)
    x1, y1 = to_px(room_w, 0)
    canvas.fill(x0, y0, x1, y1, _FLOOR)

    openings = [o for o in (room.get("openings") or []) if isinstance(o, dict)]
    walls = [w for w in (room.get("walls") or []) if isinstance(w, dict)]

    def wall_gaps(side: str, ax0, ay0, ax1, ay1):
        segs = []
        for op in openings:
            span = _opening_span(room_w, room_d, op)
            if span and span["side"] == side:
                segs.append(span)
        horizontal = side in ("south", "north")
        pieces = []
        if horizontal:
            segs.sort(key=lambda s: s["x0"])
            cursor = min(ax0, ax1)
            end = max(ax0, ax1)
            y = ay0
            for g in segs:
                g0, g1 = min(g["x0"], g["x1"]), max(g["x0"], g["x1"])
                if g0 > cursor:
                    pieces.append((cursor, y, g0, y))
                cursor = max(cursor, g1)
            if cursor < end:
                pieces.append((cursor, y, end, y))
        else:
            segs.sort(key=lambda s: s["y0"])
            cursor = min(ay0, ay1)
            end = max(ay0, ay1)
            x = ax0
            for g in segs:
                g0, g1 = min(g["y0"], g["y1"]), max(g["y0"], g["y1"])
                if g0 > cursor:
                    pieces.append((x, cursor, x, g0))
                cursor = max(cursor, g1)
            if cursor < end:
                pieces.append((x, cursor, x, end))
        for p in pieces:
            sx, sy = to_px(p[0], p[1])
            ex, ey = to_px(p[2], p[3])
            canvas.line(sx, sy, ex, ey, _WALL, thickness=3)

    if walls:
        for w in walls:
            side = str(w.get("side") or "").lower()
            seg = w.get("segment") if isinstance(w.get("segment"), dict) else {}
            s, e = seg.get("start"), seg.get("end")
            if not (isinstance(s, (list, tuple)) and isinstance(e, (list, tuple))):
                continue
            wall_gaps(side, float(s[0]), float(s[1]), float(e[0]), float(e[1]))
    else:
        wall_gaps("south", 0, 0, room_w, 0)
        wall_gaps("east", room_w, 0, room_w, room_d)
        wall_gaps("north", 0, room_d, room_w, room_d)
        wall_gaps("west", 0, 0, 0, room_d)

    for op in openings:
        span = _opening_span(room_w, room_d, op)
        if not span:
            continue
        sx, sy = to_px(span["x0"], span["y0"])
        ex, ey = to_px(span["x1"], span["y1"])
        kind = str(op.get("kind") or "").lower()
        if kind == "door":
            # open tip into room from hinge (start)
            r = ((ex - sx) ** 2 + (ey - sy) ** 2) ** 0.5
            side = span["side"]
            hx, hy = sx, sy
            if side == "east":
                ox, oy = hx - r, hy
            elif side == "west":
                ox, oy = hx + r, hy
            elif side == "south":
                ox, oy = hx, hy - r
            else:
                ox, oy = hx, hy + r
            canvas.arc_quarter(hx, hy, ex, ey, ox, oy, _DOOR)
            canvas.line(hx, hy, ox, oy, _DOOR, thickness=2)
        else:
            canvas.line(sx, sy, ex, ey, _WINDOW, thickness=4)

    # Furniture (largest AABB per object_id)
    by_id: dict[str, tuple] = {}
    for obj in viewer_preview.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        role = _role_of(obj)
        if role in _SKIP_ROLES:
            continue
        box = _aabb_xy(obj)
        if not box:
            continue
        min_x, min_y, max_x, max_y = box
        w, d = max_x - min_x, max_y - min_y
        if w < 0.05 or d < 0.05:
            continue
        lab = obj.get("layoutlab") if isinstance(obj.get("layoutlab"), dict) else {}
        oid = str(lab.get("object_id") or obj.get("name") or role)
        area = w * d
        prev = by_id.get(oid)
        if not prev or area > prev[0]:
            by_id[oid] = (area, role, box)

    for _area, role, box in by_id.values():
        min_x, min_y, max_x, max_y = box
        x0, y0 = to_px(min_x, max_y)
        x1, y1 = to_px(max_x, min_y)
        canvas.fill(x0, y0, x1, y1, _FURNITURE_RGB.get(role, _FURNITURE_RGB["default"]))

    return canvas.png()


def blueprint_data_url(viewer_preview: dict | None, *, max_side: int = 512) -> str | None:
    png = render_blueprint_png(viewer_preview, max_side=max_side)
    if not png:
        return None
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def evidence_from_candidate(candidate: dict) -> dict[str, Any]:
    """Pick visual evidence for one shortlist candidate (png preferred)."""
    preview = candidate.get("viewer_preview")
    if not isinstance(preview, dict):
        preview = None
    data_url = blueprint_data_url(preview) if preview else None
    ascii_map = None
    sketch = candidate.get("layout_sketch")
    if isinstance(sketch, dict):
        ascii_map = sketch.get("ascii")
    ascii_map = ascii_map or candidate.get("sketch_ascii")
    return {
        "candidate_id": candidate.get("candidate_id"),
        "strategy": candidate.get("strategy"),
        "label_de": candidate.get("label_de"),
        "soft_warnings": candidate.get("soft_warnings")
        or (candidate.get("quality") or {}).get("soft_warnings"),
        "image_data_url": data_url,
        "layout_sketch_ascii": ascii_map,
        "evidence_kind": "blueprint_png" if data_url else "ascii",
    }
