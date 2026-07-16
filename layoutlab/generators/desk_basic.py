# LayoutLab generator — see desk_basic.md for parameter reference.
GENERATOR_NAME = "desk_basic"
GENERATOR_CATEGORY = "Work"
GENERATOR_DESCRIPTION = "Parametric desk with tabletop, legs, and optional chair-access clearance."
GENERATOR_VERSION = "0.2.0"
GENERATOR_ICON = "MESH_CUBE"

MIN_WIDTH = 0.4
MIN_DEPTH = 0.3
MIN_HEIGHT = 0.5

DEFAULT_WIDTH = 1.2
DEFAULT_DEPTH = 0.6
DEFAULT_HEIGHT = 0.75

TOP_THICKNESS_DEFAULT = 0.025
LEG_THICKNESS_DEFAULT = 0.04
CLEARANCE_DEPTH_DEFAULT = 0.6
CLEARANCE_HEIGHT_DEFAULT = 0.7

CLEARANCE_COLOR = (0.2, 0.8, 1.0, 0.22)


def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)


def _chair_zone_local(width, depth, clearance_depth, clearance_height):
    """Return (local_location, dimensions) for chair_access in body local space.

    Front / sitting side is y_min (local y = 0). Clearance extends in −Y.
    """
    depth = max(float(clearance_depth), 0.01)
    height = max(float(clearance_height), 0.01)
    return [0.0, -depth, 0.0], [float(width), depth, height]


def generate(params, api):
    name = params.get("name", "DESK_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")

    width = _clamp(params.get("width", DEFAULT_WIDTH), MIN_WIDTH, DEFAULT_WIDTH)
    depth = _clamp(params.get("depth", DEFAULT_DEPTH), MIN_DEPTH, DEFAULT_DEPTH)
    height = _clamp(params.get("height", DEFAULT_HEIGHT), MIN_HEIGHT, DEFAULT_HEIGHT)

    top_thickness = min(
        _clamp(params.get("top_thickness", TOP_THICKNESS_DEFAULT), 0.008, TOP_THICKNESS_DEFAULT),
        height * 0.2,
    )
    leg_thickness = min(
        _clamp(params.get("leg_thickness", LEG_THICKNESS_DEFAULT), 0.015, LEG_THICKNESS_DEFAULT),
        width * 0.15,
        depth * 0.15,
    )

    show_clearance = bool(params.get("show_clearance", True))
    clearance_depth = _clamp(params.get("clearance_depth", CLEARANCE_DEPTH_DEFAULT), 0.0, CLEARANCE_DEPTH_DEFAULT)
    clearance_height = _clamp(
        params.get("clearance_height", CLEARANCE_HEIGHT_DEFAULT),
        0.01,
        CLEARANCE_HEIGHT_DEFAULT,
    )
    clearance_requirement = params.get("clearance_requirement", "required")

    top_color = params.get("top_color", [0.72, 0.58, 0.40, 1.0])
    leg_color = params.get("leg_color", [0.55, 0.42, 0.28, 1.0])
    clearance_color = params.get("clearance_color", CLEARANCE_COLOR)

    cb = api["create_box"]
    cc = api["create_clearance"]
    cl = api["create_label"]
    bp = api["begin_part"]
    ep = api["end_part"]

    leg_height = max(height - top_thickness, 0.01)

    bp("body", main=True, role="desk_body")
    cb(
        f"{name}__body_top",
        [x, y, z + height - top_thickness],
        [width, depth, top_thickness],
        top_color,
        collection,
        "desk_top",
        None,
    )

    leg_positions = [
        (x, y),
        (x + width - leg_thickness, y),
        (x, y + depth - leg_thickness),
        (x + width - leg_thickness, y + depth - leg_thickness),
    ]
    for i, (leg_x, leg_y) in enumerate(leg_positions, start=1):
        cb(
            f"{name}__body_leg_{i}",
            [leg_x, leg_y, z],
            [leg_thickness, leg_thickness, leg_height],
            leg_color,
            collection,
            "desk_leg",
            None,
        )
    ep()

    if show_clearance and clearance_depth > 0:
        local_loc, dims = _chair_zone_local(width, depth, clearance_depth, clearance_height)
        bp("clearance_chair_access", role="clearance")
        cc(
            f"{name}__clearance_chair_access",
            dims,
            local_location=local_loc,
            clearance_name="chair_access",
            purpose="seating_access",
            requirement=clearance_requirement,
            priority=0,
            params={"depth": clearance_depth, "height": clearance_height},
            color=clearance_color,
            collection=collection,
        )
        ep()

    bp("label", role="label")
    cl(
        f"{name}__label",
        [x + width / 2, y + depth / 2, z + height + 0.05],
        name,
        collection,
        0.035,
    )
    ep()

    return {
        "created": name,
        "type": GENERATOR_NAME,
        "size": [width, depth, height],
        "clearance": show_clearance and clearance_depth > 0,
    }
