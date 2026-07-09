# LayoutLab generator
GENERATOR_NAME = "wardrobe_basic"
GENERATOR_CATEGORY = "Storage"
GENERATOR_DESCRIPTION = "Parametric wardrobe with carcass, doors, shelves, handles, and optional front clearance."
GENERATOR_VERSION = "0.1"
GENERATOR_ICON = "OUTLINER_COLLECTION"

# Units:
# LayoutLab uses Blender scene units.
# In Alexander's reference room convention: 1 unit ≈ 10 cm.

MIN_WIDTH = 3.0
MIN_DEPTH = 2.5
MIN_HEIGHT = 8.0

DEFAULT_WIDTH = 8.0
DEFAULT_DEPTH = 4.0
DEFAULT_HEIGHT = 15.0

PANEL_THICKNESS_DEFAULT = 0.25
BACK_THICKNESS_DEFAULT = 0.15
SHELF_THICKNESS_DEFAULT = 0.18
DOOR_THICKNESS_DEFAULT = 0.18
HANDLE_WIDTH_DEFAULT = 0.12
HANDLE_DEPTH_DEFAULT = 0.12
HANDLE_HEIGHT_DEFAULT = 1.6
CLEARANCE_DEPTH_DEFAULT = 6.0

DOUBLE_DOOR_THRESHOLD = 6.0
TRIPLE_DOOR_THRESHOLD = 12.0


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

    # Rough semantic default: more height means more shelves, but not absurdly many.
    if height < 10:
        return 1
    if height < 14:
        return 2
    if height < 18:
        return 3
    return 4


def generate(params, api):
    name = params.get("name", "WARDROBE_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")

    width = _clamp(params.get("width", DEFAULT_WIDTH), MIN_WIDTH, DEFAULT_WIDTH)
    depth = _clamp(params.get("depth", DEFAULT_DEPTH), MIN_DEPTH, DEFAULT_DEPTH)
    height = _clamp(params.get("height", DEFAULT_HEIGHT), MIN_HEIGHT, DEFAULT_HEIGHT)

    panel = min(_clamp(params.get("panel_thickness", PANEL_THICKNESS_DEFAULT), 0.08, PANEL_THICKNESS_DEFAULT), width * 0.18, depth * 0.18)
    back = min(_clamp(params.get("back_thickness", BACK_THICKNESS_DEFAULT), 0.05, BACK_THICKNESS_DEFAULT), depth * 0.15)
    shelf_thickness = min(_clamp(params.get("shelf_thickness", SHELF_THICKNESS_DEFAULT), 0.05, SHELF_THICKNESS_DEFAULT), height * 0.05)
    door_thickness = min(_clamp(params.get("door_thickness", DOOR_THICKNESS_DEFAULT), 0.05, DOOR_THICKNESS_DEFAULT), depth * 0.12)

    door_count = _door_count(width, params.get("door_count"))
    shelf_count = _shelf_count(height, params.get("shelf_count"))

    show_clearance = bool(params.get("show_clearance", True))
    clearance_depth = _clamp(params.get("clearance_depth", CLEARANCE_DEPTH_DEFAULT), 0.0, CLEARANCE_DEPTH_DEFAULT)

    carcass_color = params.get("carcass_color", [0.70, 0.58, 0.42, 1.0])
    door_color = params.get("door_color", [0.82, 0.74, 0.62, 1.0])
    shelf_color = params.get("shelf_color", [0.76, 0.64, 0.48, 1.0])
    handle_color = params.get("handle_color", [0.15, 0.15, 0.14, 1.0])
    clearance_color = params.get("clearance_color", [0.2, 0.8, 1.0, 0.18])

    cb = api["create_box"]
    cl = api["create_label"]

    # Carcass: separate panels, not one scaled block.
    cb(f"{name}_side_left", [x, y, z], [panel, depth, height], carcass_color, collection, "wardrobe_side", None)
    cb(f"{name}_side_right", [x + width - panel, y, z], [panel, depth, height], carcass_color, collection, "wardrobe_side", None)
    cb(f"{name}_top", [x, y, z + height - panel], [width, depth, panel], carcass_color, collection, "wardrobe_top", None)
    cb(f"{name}_bottom", [x, y, z], [width, depth, panel], carcass_color, collection, "wardrobe_bottom", None)
    cb(f"{name}_back", [x, y + depth - back, z], [width, back, height], carcass_color, collection, "wardrobe_back", None)

    # Shelves inside the carcass.
    usable_height = max(height - 2 * panel, 0.1)
    inner_width = max(width - 2 * panel, 0.1)
    inner_depth = max(depth - back - 0.15, 0.1)

    for i in range(shelf_count):
        shelf_z = z + panel + (usable_height * (i + 1) / (shelf_count + 1))
        cb(
            f"{name}_shelf_{i + 1}",
            [x + panel, y + 0.05, shelf_z],
            [inner_width, inner_depth, shelf_thickness],
            shelf_color,
            collection,
            "wardrobe_shelf",
            None,
        )

    # Doors on the front side (y_min).
    door_width = width / door_count
    for i in range(door_count):
        door_x = x + i * door_width
        suffix = f"door_{i + 1}"
        cb(
            f"{name}_{suffix}",
            [door_x, y - door_thickness, z + panel * 0.5],
            [door_width, door_thickness, height - panel],
            door_color,
            collection,
            "wardrobe_door",
            None,
        )

        # Handle placement: one handle per door, near the vertical seam / opening edge.
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
            f"{name}_handle_{i + 1}",
            [handle_x, y - door_thickness - handle_d, handle_z],
            [handle_w, handle_d, handle_h],
            handle_color,
            collection,
            "wardrobe_handle",
            None,
        )

    # Front usage clearance: a semantic helper volume for opening/standing area.
    # In v0.5 generator API, create_clearance is not exposed yet, so we use create_box.
    if show_clearance and clearance_depth > 0:
        cb(
            f"{name}_front_clearance",
            [x, y - door_thickness - clearance_depth, z],
            [width, clearance_depth, 0.1],
            clearance_color,
            collection,
            "clearance",
            "WIRE",
        )

    cl(
        f"{name}_label",
        [x + width / 2, y + depth / 2, z + height + 0.5],
        name,
        collection,
    )

    return {
        "created": name,
        "type": GENERATOR_NAME,
        "size": [width, depth, height],
        "door_count": door_count,
        "shelf_count": shelf_count,
        "clearance": show_clearance,
    }
