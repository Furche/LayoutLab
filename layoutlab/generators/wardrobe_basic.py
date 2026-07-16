# LayoutLab generator
GENERATOR_NAME = "wardrobe_basic"
GENERATOR_CATEGORY = "Storage"
GENERATOR_DESCRIPTION = "Parametric wardrobe with carcass, doors, shelves, handles, and optional front clearance."
GENERATOR_VERSION = "0.7.0"
GENERATOR_ICON = "OUTLINER_COLLECTION"

MIN_WIDTH = 0.3
MIN_DEPTH = 0.25
MIN_HEIGHT = 0.8

DEFAULT_WIDTH = 0.8
DEFAULT_DEPTH = 0.4
DEFAULT_HEIGHT = 1.5

PANEL_THICKNESS_DEFAULT = 0.025
BACK_THICKNESS_DEFAULT = 0.015
SHELF_THICKNESS_DEFAULT = 0.018
DOOR_THICKNESS_DEFAULT = 0.018
HANDLE_WIDTH_DEFAULT = 0.012
HANDLE_DEPTH_DEFAULT = 0.012
HANDLE_HEIGHT_DEFAULT = 0.16
CLEARANCE_DEPTH_DEFAULT = 0.6

DOUBLE_DOOR_THRESHOLD = 0.6
TRIPLE_DOOR_THRESHOLD = 1.2


def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)


def _door_count(width, requested=None):
    if requested is not None:
        try:
            requested = int(requested)
            if requested >= 1:
                return min(requested, 4)
        except (TypeError, ValueError):
            pass

    if width >= TRIPLE_DOOR_THRESHOLD:
        return 3
    if width >= DOUBLE_DOOR_THRESHOLD:
        return 2
    return 1


def _shelf_count(height, requested=None):
    if requested is not None:
        try:
            requested = int(requested)
            return max(0, min(requested, 8))
        except (TypeError, ValueError):
            pass

    if height < 1.0:
        return 1
    if height < 1.4:
        return 2
    if height < 1.8:
        return 3
    return 4


def _normalize_front_side(value):
    side = (value or "y_min").strip().lower()
    if side in ("y_min", "y_max"):
        return side
    raise ValueError(f"unknown wardrobe front_side {value!r} (use y_min or y_max)")


def _clearance_spec(front_side, width, depth, height, door_thickness, clearance_depth):
    """Return (local_location, dimensions) for front_access in body local space."""
    if front_side == "y_min":
        return (
            [0.0, -door_thickness - clearance_depth, 0.0],
            [width, clearance_depth, height],
        )
    return (
        [0.0, depth + door_thickness, 0.0],
        [width, clearance_depth, height],
    )


def generate(params, api):
    name = params.get("name", "WARDROBE_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")

    width = _clamp(params.get("width", DEFAULT_WIDTH), MIN_WIDTH, DEFAULT_WIDTH)
    depth = _clamp(params.get("depth", DEFAULT_DEPTH), MIN_DEPTH, DEFAULT_DEPTH)
    height = _clamp(params.get("height", DEFAULT_HEIGHT), MIN_HEIGHT, DEFAULT_HEIGHT)

    panel = min(_clamp(params.get("panel_thickness", PANEL_THICKNESS_DEFAULT), 0.008, PANEL_THICKNESS_DEFAULT), width * 0.18, depth * 0.18)
    back = min(_clamp(params.get("back_thickness", BACK_THICKNESS_DEFAULT), 0.005, BACK_THICKNESS_DEFAULT), depth * 0.15)
    shelf_thickness = min(_clamp(params.get("shelf_thickness", SHELF_THICKNESS_DEFAULT), 0.005, SHELF_THICKNESS_DEFAULT), height * 0.05)
    door_thickness = min(_clamp(params.get("door_thickness", DOOR_THICKNESS_DEFAULT), 0.005, DOOR_THICKNESS_DEFAULT), depth * 0.12)

    door_count = _door_count(width, params.get("door_count"))
    shelf_count = _shelf_count(height, params.get("shelf_count"))

    show_clearance = bool(params.get("show_clearance", True))
    clearance_depth = _clamp(params.get("clearance_depth", CLEARANCE_DEPTH_DEFAULT), 0.0, CLEARANCE_DEPTH_DEFAULT)
    front_side = _normalize_front_side(params.get("front_side", "y_min"))

    carcass_color = params.get("carcass_color", [0.70, 0.58, 0.42, 1.0])
    door_color = params.get("door_color", [0.82, 0.74, 0.62, 1.0])
    shelf_color = params.get("shelf_color", [0.76, 0.64, 0.48, 1.0])
    handle_color = params.get("handle_color", [0.15, 0.15, 0.14, 1.0])
    clearance_color = params.get("clearance_color", [0.2, 0.8, 1.0, 0.18])

    cb = api["create_box"]
    cc = api["create_clearance"]
    cl = api["create_label"]
    bp = api["begin_part"]
    ep = api["end_part"]

    bp("body", main=True, role="wardrobe_body")
    cb(f"{name}__body_side_left", [x, y, z], [panel, depth, height], carcass_color, collection, "wardrobe_side", None)
    cb(f"{name}__body_side_right", [x + width - panel, y, z], [panel, depth, height], carcass_color, collection, "wardrobe_side", None)
    cb(f"{name}__body_top", [x, y, z + height - panel], [width, depth, panel], carcass_color, collection, "wardrobe_top", None)
    cb(f"{name}__body_bottom", [x, y, z], [width, depth, panel], carcass_color, collection, "wardrobe_bottom", None)
    if front_side == "y_min":
        back_y = y + depth - back
    else:
        back_y = y
    cb(f"{name}__body_back", [x, back_y, z], [width, back, height], carcass_color, collection, "wardrobe_back", None)

    usable_height = max(height - 2 * panel, 0.1)
    inner_width = max(width - 2 * panel, 0.1)
    inner_depth = max(depth - back - 0.15, 0.1)

    for i in range(shelf_count):
        shelf_z = z + panel + (usable_height * (i + 1) / (shelf_count + 1))
        cb(
            f"{name}__body_shelf_{i + 1}",
            [x + panel, y + 0.05, shelf_z],
            [inner_width, inner_depth, shelf_thickness],
            shelf_color,
            collection,
            "wardrobe_shelf",
            None,
        )
    ep()

    door_width = width / door_count
    if front_side == "y_min":
        door_y = y - door_thickness
        handle_y = y - door_thickness - HANDLE_DEPTH_DEFAULT
    else:
        door_y = y + depth
        handle_y = y + depth + HANDLE_DEPTH_DEFAULT

    for i in range(door_count):
        door_x = x + i * door_width
        part_id = f"door_{i + 1}"
        bp(part_id, dynamic=True, role="wardrobe_door")
        cb(
            f"{name}__{part_id}_panel",
            [door_x, door_y, z + panel * 0.5],
            [door_width, door_thickness, height - panel],
            door_color,
            collection,
            "wardrobe_door",
            None,
        )

        handle_w = min(HANDLE_WIDTH_DEFAULT, max(door_width * 0.12, 0.08))
        handle_d = HANDLE_DEPTH_DEFAULT
        handle_h = min(HANDLE_HEIGHT_DEFAULT, max(height * 0.14, 0.7))

        if door_count == 1:
            handle_x = door_x + door_width - door_width * 0.18
        elif i % 2 == 0:
            handle_x = door_x + door_width - door_width * 0.15
        else:
            handle_x = door_x + door_width * 0.15

        handle_z = z + height * 0.48
        cb(
            f"{name}__{part_id}_handle",
            [handle_x, handle_y, handle_z],
            [handle_w, handle_d, handle_h],
            handle_color,
            collection,
            "wardrobe_handle",
            None,
        )
        ep()

    if show_clearance and clearance_depth > 0:
        local_loc, dims = _clearance_spec(
            front_side, width, depth, height, door_thickness, clearance_depth
        )
        bp("clearance_front_access", role="clearance")
        cc(
            f"{name}__clearance_front_access",
            dims,
            local_location=local_loc,
            clearance_name="front_access",
            purpose="door_access",
            requirement="preferred",
            priority=0,
            params={"depth": clearance_depth, "front_side": front_side},
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
        "door_count": door_count,
        "shelf_count": shelf_count,
        "clearance": show_clearance,
        "front_side": front_side,
    }
