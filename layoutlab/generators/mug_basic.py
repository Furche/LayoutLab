# LayoutLab generator — see mug_basic.md for parameter reference.
GENERATOR_NAME = "mug_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Simple mug / cup."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "MUG_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.08), 0.05, 0.08)
    depth = _clamp(params.get("depth", 0.08), 0.05, 0.08)
    height = _clamp(params.get("height", 0.1), 0.06, 0.1)
    color = params.get("color", [0.9, 0.9, 0.92, 1.0])
    handle = params.get("handle_color", [0.85, 0.85, 0.88, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="mug_body")
    cb(f"{name}__cup", [x, y, z], [width, depth, height], color, collection, "mug_cup", None)
    hw, hd, hh = 0.015, 0.03, height * 0.45
    cb(f"{name}__handle", [x + width, y + (depth - hd) * 0.5, z + height * 0.3], [hw, hd, hh], handle, collection, "mug_handle", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.015)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width + hw, depth, height]}
