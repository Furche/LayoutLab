# LayoutLab generator — see rug_basic.md for parameter reference.
GENERATOR_NAME = "rug_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Floor rug / carpet rectangle."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "RUG_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 1.6), 0.6, 1.6)
    depth = _clamp(params.get("depth", 1.0), 0.5, 1.0)
    height = _clamp(params.get("height", 0.012), 0.005, 0.012)
    color = params.get("color", [0.45, 0.28, 0.22, 1.0])
    border = params.get("border_color", [0.35, 0.22, 0.18, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="rug_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "rug_body", None)
    b = 0.04
    cb(f"{name}__border", [x + b, y + b, z + height], [max(width - 2 * b, 0.1), max(depth - 2 * b, 0.1), 0.002], border, collection, "rug_border", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.04], name, collection, 0.025)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
