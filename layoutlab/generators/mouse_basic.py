# LayoutLab generator — see mouse_basic.md for parameter reference.
GENERATOR_NAME = "mouse_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Computer mouse."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "MOUSE_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.06), 0.04, 0.06)
    depth = _clamp(params.get("depth", 0.1), 0.07, 0.1)
    height = _clamp(params.get("height", 0.035), 0.02, 0.035)
    color = params.get("color", [0.2, 0.2, 0.22, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="mouse_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "mouse_body", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.014)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
