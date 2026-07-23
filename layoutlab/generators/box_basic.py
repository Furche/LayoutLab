# LayoutLab generator — see box_basic.md for parameter reference.
GENERATOR_NAME = "box_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Cardboard / storage box."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "BOX_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.4), 0.2, 0.4)
    depth = _clamp(params.get("depth", 0.3), 0.2, 0.3)
    height = _clamp(params.get("height", 0.3), 0.15, 0.3)
    color = params.get("color", [0.72, 0.58, 0.38, 1.0])
    tape = params.get("tape_color", [0.85, 0.75, 0.45, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="box_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "box_body", None)
    cb(f"{name}__tape", [x, y + depth * 0.45, z + height], [width, depth * 0.1, 0.004], tape, collection, "box_tape", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.04], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
