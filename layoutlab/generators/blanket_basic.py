# LayoutLab generator — see blanket_basic.md for parameter reference.
GENERATOR_NAME = "blanket_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Folded blanket / throw."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "BLANKET_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 1.2), 0.5, 1.2)
    depth = _clamp(params.get("depth", 0.8), 0.4, 0.8)
    height = _clamp(params.get("height", 0.05), 0.02, 0.05)
    color = params.get("color", [0.55, 0.62, 0.7, 1.0])
    fold = params.get("fold_color", [0.48, 0.55, 0.62, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="blanket_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height * 0.55], color, collection, "blanket_body", None)
    cb(f"{name}__fold", [x + width * 0.15, y, z + height * 0.55], [width * 0.7, depth, height * 0.45], fold, collection, "blanket_fold", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.04], name, collection, 0.022)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
