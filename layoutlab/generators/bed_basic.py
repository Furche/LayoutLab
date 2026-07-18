# LayoutLab generator — see bed_basic.md for parameter reference.
GENERATOR_NAME = "bed_basic"
GENERATOR_CATEGORY = "Beds"
GENERATOR_DESCRIPTION = "Parametric low bed: posts, raised frame loop, headboard rise, mattress, pillows."
GENERATOR_VERSION = "0.7.0"
GENERATOR_ICON = "BED"

# Thresholds in Blender units (Metric default: 1 unit = 1 meter)
MIN_BED_DIMENSION = 0.3
PILLOW_COUNT_WIDTH_THRESHOLD = 1.3  # width >= 1.3 → two pillows
PILLOW_HEIGHT = 0.045
PILLOW_GAP = 0.02
MATTRESS_Z_INSET_FACTOR = 0.55  # mattress sits above lower rail within frame

DEFAULT_HEADBOARD_RISE = 0.32  # decorative panel height above frame top
DEFAULT_ENTRY_CLEARANCE_DEPTH = 0.6
CLEARANCE_COLOR = (0.2, 0.8, 1.0, 0.22)


def _clearance_height(bed, mattress_height):
    return max(bed.mattress_z + float(mattress_height) - bed.floor_z, bed.post_height)


def _zone_for_side(bed, side, depth, mattress_height):
    """Return (local_location, dimensions) for a bed_entry clearance in body local space."""
    h = _clearance_height(bed, mattress_height)
    depth = max(float(depth), 0.01)
    length, width = bed.length, bed.width
    side = (side or "foot").strip().lower()

    if bed.head_side == "y_max":
        if side in ("foot", "y_min", "foot_end"):
            return [0.0, -depth, 0.0], [length, depth, h]
        if side in ("head", "y_max", "head_end"):
            return [0.0, width, 0.0], [length, depth, h]
        if side in ("left", "x_min"):
            return [-depth, 0.0, 0.0], [depth, width, h]
        if side in ("right", "x_max"):
            return [length, 0.0, 0.0], [depth, width, h]
    elif bed.head_side == "y_min":
        if side in ("foot", "y_max", "foot_end"):
            return [0.0, width, 0.0], [length, depth, h]
        if side in ("head", "y_min", "head_end"):
            return [0.0, -depth, 0.0], [length, depth, h]
        if side in ("left", "x_min"):
            return [-depth, 0.0, 0.0], [depth, width, h]
        if side in ("right", "x_max"):
            return [length, 0.0, 0.0], [depth, width, h]
    elif bed.head_side == "x_max":
        if side in ("foot", "x_min", "foot_end"):
            return [-depth, 0.0, 0.0], [depth, width, h]
        if side in ("head", "x_max", "head_end"):
            return [length, 0.0, 0.0], [depth, width, h]
        if side in ("left", "y_min"):
            return [0.0, -depth, 0.0], [length, depth, h]
        if side in ("right", "y_max"):
            return [0.0, width, 0.0], [length, depth, h]
    else:
        if side in ("foot", "x_max", "foot_end"):
            return [length, 0.0, 0.0], [depth, width, h]
        if side in ("head", "x_min", "head_end"):
            return [-depth, 0.0, 0.0], [depth, width, h]
        if side in ("left", "y_min"):
            return [0.0, -depth, 0.0], [length, depth, h]
        if side in ("right", "y_max"):
            return [0.0, width, 0.0], [length, depth, h]

    raise ValueError(f"unknown bed clearance side {side!r} for head_side={bed.head_side!r}")


def _iter_clearance_specs(params):
    raw = params.get("clearances")
    if not raw or not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _build_clearances(bed, name, params, mattress_height, collection, api):
    specs = _iter_clearance_specs(params)
    if not specs:
        return

    cc = api["create_clearance"]
    bp = api["begin_part"]
    ep = api["end_part"]
    seen_names = set()

    for spec in specs:
        side = spec.get("side", "foot")
        depth = spec.get("depth", DEFAULT_ENTRY_CLEARANCE_DEPTH)
        clearance_name = str(spec.get("clearance_name", "bed_entry")).strip() or "bed_entry"
        if clearance_name in seen_names:
            clearance_name = f"{clearance_name}_{side}"
        seen_names.add(clearance_name)

        local_loc, dims = _zone_for_side(bed, side, depth, mattress_height)
        part_id = f"clearance_{clearance_name}"

        bp(part_id, role="clearance")
        cc(
            f"{name}__{part_id}",
            dims,
            local_location=local_loc,
            clearance_name=clearance_name,
            purpose=str(spec.get("purpose", "bed_access")),
            requirement=spec.get("requirement", "preferred"),
            priority=int(spec.get("priority", 0) or 0),
            params={"side": side, "depth": float(depth)},
            color=tuple(spec.get("color", CLEARANCE_COLOR)),
            collection=collection,
        )
        ep()


class BedConstruction:
    """Logical bed stack — only posts reach the floor.

    Vertical order (bottom → top):
      floor
        posts (leg_height + frame_height)
        frame loop at frame_bottom_z (side rails + footboard + headboard base)
        optional headboard rise above frame_top_z
        mattress / pillows (separate Parts)
    """

    __slots__ = (
        "x",
        "y",
        "floor_z",
        "length",
        "width",
        "leg_height",
        "frame_height",
        "rail",
        "post",
        "headboard_rise",
        "head_side",
        "frame_bottom_z",
        "frame_top_z",
        "post_height",
    )

    def __init__(
        self,
        x,
        y,
        floor_z,
        length,
        width,
        leg_height,
        frame_height,
        rail,
        post,
        headboard_rise,
        head_side,
    ):
        self.x = x
        self.y = y
        self.floor_z = floor_z
        self.length = length
        self.width = width
        self.leg_height = leg_height
        self.frame_height = frame_height
        self.rail = rail
        self.post = post
        self.headboard_rise = max(float(headboard_rise), 0.0)
        self.head_side = head_side
        self.frame_bottom_z = floor_z + leg_height
        self.frame_top_z = self.frame_bottom_z + frame_height
        self.post_height = leg_height + frame_height

    @property
    def mattress_x(self):
        return self.x + self.rail

    @property
    def mattress_y(self):
        return self.y + self.rail

    @property
    def mattress_l(self):
        return max(self.length - 2 * self.rail, 1)

    @property
    def mattress_w(self):
        return max(self.width - 2 * self.rail, 1)

    @property
    def mattress_z(self):
        return self.frame_bottom_z + self.frame_height * MATTRESS_Z_INSET_FACTOR

    def build_posts(self, cb, name, color, collection):
        for sx, sy, suffix in [
            (0, 0, "post_xmin_ymin"),
            (self.length - self.post, 0, "post_xmax_ymin"),
            (0, self.width - self.post, "post_xmin_ymax"),
            (self.length - self.post, self.width - self.post, "post_xmax_ymax"),
        ]:
            cb(
                f"{name}__body_{suffix}",
                [self.x + sx, self.y + sy, self.floor_z],
                [self.post, self.post, self.post_height],
                color,
                collection,
                "bed_post",
                None,
            )

    def build_side_rails(self, cb, name, color, collection):
        z = self.frame_bottom_z
        h = self.frame_height
        cb(
            f"{name}__body_rail_y_min",
            [self.x, self.y, z],
            [self.length, self.rail, h],
            color,
            collection,
            "bed_frame",
            None,
        )
        cb(
            f"{name}__body_rail_y_max",
            [self.x, self.y + self.width - self.rail, z],
            [self.length, self.rail, h],
            color,
            collection,
            "bed_frame",
            None,
        )
        cb(
            f"{name}__body_rail_x_min",
            [self.x, self.y, z],
            [self.rail, self.width, h],
            color,
            collection,
            "bed_frame",
            None,
        )
        cb(
            f"{name}__body_rail_x_max",
            [self.x + self.length - self.rail, self.y, z],
            [self.rail, self.width, h],
            color,
            collection,
            "bed_frame",
            None,
        )

    def _frame_end_board(self, cb, name, color, collection, part_id, role, origin, size):
        cb(
            f"{name}__body_{part_id}",
            origin,
            size,
            color,
            collection,
            role,
            None,
        )

    def build_frame_ends(self, cb, name, color, collection):
        """Footboard and structural headboard base — same Z band as side rails."""
        z = self.frame_bottom_z
        h = self.frame_height
        x, y = self.x, self.y
        length, width, rail = self.length, self.width, self.rail

        if self.head_side == "y_max":
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "footboard",
                "bed_footboard",
                [x, y, z],
                [length, rail, h],
            )
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "headboard_base",
                "bed_frame",
                [x, y + width - rail, z],
                [length, rail, h],
            )
        elif self.head_side == "y_min":
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "footboard",
                "bed_footboard",
                [x, y + width - rail, z],
                [length, rail, h],
            )
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "headboard_base",
                "bed_frame",
                [x, y, z],
                [length, rail, h],
            )
        elif self.head_side == "x_max":
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "footboard",
                "bed_footboard",
                [x, y, z],
                [rail, width, h],
            )
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "headboard_base",
                "bed_frame",
                [x + length - rail, y, z],
                [rail, width, h],
            )
        else:
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "footboard",
                "bed_footboard",
                [x + length - rail, y, z],
                [rail, width, h],
            )
            self._frame_end_board(
                cb,
                name,
                color,
                collection,
                "headboard_base",
                "bed_frame",
                [x, y, z],
                [rail, width, h],
            )

    def build_headboard_rise(self, cb, name, color, collection):
        """Optional decorative panel above the frame loop."""
        if self.headboard_rise <= 0:
            return

        z = self.frame_top_z
        h = self.headboard_rise
        x, y = self.x, self.y
        length, width, rail = self.length, self.width, self.rail

        if self.head_side == "y_max":
            origin = [x, y + width - rail, z]
            size = [length, rail, h]
        elif self.head_side == "y_min":
            origin = [x, y, z]
            size = [length, rail, h]
        elif self.head_side == "x_max":
            origin = [x + length - rail, y, z]
            size = [rail, width, h]
        else:
            origin = [x, y, z]
            size = [rail, width, h]

        cb(
            f"{name}__body_headboard_rise",
            origin,
            size,
            color,
            collection,
            "bed_headboard",
            None,
        )

    def pillow_anchor_y(self, pillow_depth):
        """Y position for pillow row at the head end (y-axis beds)."""
        if self.head_side == "y_max":
            return self.y + self.width - self.rail - pillow_depth - 0.02
        if self.head_side == "y_min":
            return self.y + self.rail + 0.02
        return self.mattress_y + self.mattress_w - 0.2

    def pillow_anchor_x(self, pillow_depth):
        """X position for pillow column at the head end (x-axis beds)."""
        if self.head_side == "x_max":
            return self.mattress_x + self.mattress_l - pillow_depth - 0.02
        if self.head_side == "x_min":
            return self.mattress_x + 0.02
        return self.mattress_x + 0.02


def _headboard_rise_from_params(params):
    """Decorative headboard height above ``frame_top_z`` (see bed_basic.md)."""
    raw = params.get("headboard_height", params.get("headboard_rise", DEFAULT_HEADBOARD_RISE))
    try:
        return max(float(raw), 0.0)
    except (TypeError, ValueError):
        return DEFAULT_HEADBOARD_RISE


def generate(params, api):
    name = params.get("name", "BED_basic")
    x, y, z = params.get("location", [0, 0, 0])
    length = max(params.get("length", 2.0), MIN_BED_DIMENSION)
    width = max(params.get("width", 1.2), MIN_BED_DIMENSION)
    collection = params.get("collection", "layout_tests")

    leg_height = params.get("leg_height", 0.25)
    frame_height = params.get("frame_height", 0.1)
    mattress_height = params.get("mattress_height", 0.2)
    rail = min(params.get("rail_thickness", 0.035), width * 0.2, length * 0.2)
    post = min(params.get("post_size", 0.045), width * 0.25, length * 0.25)
    head_side = params.get("head_side", "y_max")
    headboard_rise = _headboard_rise_from_params(params)

    frame_color = params.get("frame_color", [0.72, 0.55, 0.35, 1])
    mattress_color = params.get("mattress_color", [0.86, 0.86, 0.82, 0.65])
    pillow_color = params.get("pillow_color", [0.95, 0.95, 0.92, 1])

    cb = api["create_box"]
    cl = api["create_label"]
    bp = api["begin_part"]
    ep = api["end_part"]

    bed = BedConstruction(
        x,
        y,
        z,
        length,
        width,
        leg_height,
        frame_height,
        rail,
        post,
        headboard_rise,
        head_side,
    )

    bp("body", main=True, role="bed_frame")
    bed.build_posts(cb, name, frame_color, collection)
    bed.build_side_rails(cb, name, frame_color, collection)
    bed.build_frame_ends(cb, name, frame_color, collection)
    bed.build_headboard_rise(cb, name, frame_color, collection)
    ep()

    _build_clearances(bed, name, params, mattress_height, collection, api)

    bp("mattress", role="bed_mattress")
    cb(
        f"{name}__mattress",
        [bed.mattress_x, bed.mattress_y, bed.mattress_z],
        [bed.mattress_l, bed.mattress_w, mattress_height],
        mattress_color,
        collection,
        "bed_mattress",
        None,
    )
    ep()

    pillow_count = 2 if width >= PILLOW_COUNT_WIDTH_THRESHOLD else 1
    if head_side in ("y_max", "y_min"):
        # Side-to-side is X (length); sleep along Y (width).
        pillow_count = 2 if length >= PILLOW_COUNT_WIDTH_THRESHOLD else 1
        pillow_span = bed.mattress_l
        pillow_depth = min(0.18, bed.mattress_w * 0.35)
        pillow_len = max((pillow_span - PILLOW_GAP * (pillow_count + 1)) / pillow_count, 0.08)
        for i in range(pillow_count):
            px = bed.mattress_x + PILLOW_GAP + i * (pillow_len + PILLOW_GAP)
            py = max(
                min(bed.pillow_anchor_y(pillow_depth), bed.mattress_y + bed.mattress_w - pillow_depth - 0.02),
                bed.mattress_y + 0.02,
            )
            bp(f"pillow_{i + 1}", role="bed_pillow")
            cb(
                f"{name}__pillow_{i + 1}",
                [px, py, bed.mattress_z + mattress_height + 0.005],
                [pillow_len, pillow_depth, PILLOW_HEIGHT],
                pillow_color,
                collection,
                "bed_pillow",
                None,
            )
            ep()
    else:
        pillow_span = bed.mattress_w
        pillow_depth = min(0.18, bed.mattress_l * 0.35)
        pillow_len = max((pillow_span - PILLOW_GAP * (pillow_count + 1)) / pillow_count, 0.08)
        px = bed.pillow_anchor_x(pillow_depth)
        for i in range(pillow_count):
            py = bed.mattress_y + PILLOW_GAP + i * (pillow_len + PILLOW_GAP)
            bp(f"pillow_{i + 1}", role="bed_pillow")
            cb(
                f"{name}__pillow_{i + 1}",
                [px, py, bed.mattress_z + mattress_height + 0.005],
                [pillow_depth, pillow_len, PILLOW_HEIGHT],
                pillow_color,
                collection,
                "bed_pillow",
                None,
            )
            ep()

    bp("label", role="label")
    cl(
        f"{name}__label",
        [x + length / 2, y + width / 2, bed.mattress_z + mattress_height + 0.07],
        name,
        collection,
        0.035,
    )
    ep()

    return {
        "created": name,
        "type": "bed_basic",
        "size": [length, width],
        "headboard_rise": headboard_rise,
        "clearance_count": len(_iter_clearance_specs(params)),
    }
