# LayoutLab generator — see tablet_basic.md for parameter reference.
GENERATOR_NAME = "tablet_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Flat tablet / large phone slab."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "TABLET_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.18), 0.12, 0.18)
    depth = _clamp(params.get("depth", 0.26), 0.18, 0.26)
    height = _clamp(params.get("height", 0.01), 0.006, 0.01)
    color = params.get("color", [0.12, 0.12, 0.14, 1.0])
    screen = params.get("screen_color", [0.25, 0.35, 0.45, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="tablet_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "tablet_body", None)
    m = 0.008
    cb(f"{name}__screen", [x + m, y + m, z + height], [max(width - 2 * m, 0.05), max(depth - 2 * m, 0.05), 0.002], screen, collection, "tablet_screen", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.016)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
