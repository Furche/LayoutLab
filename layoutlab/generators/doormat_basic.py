# LayoutLab generator — see doormat_basic.md for parameter reference.
GENERATOR_NAME = "doormat_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Entry doormat."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "DOORMAT_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.6), 0.35, 0.6)
    depth = _clamp(params.get("depth", 0.4), 0.25, 0.4)
    height = _clamp(params.get("height", 0.015), 0.008, 0.015)
    color = params.get("color", [0.35, 0.32, 0.28, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="doormat_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "doormat_body", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
