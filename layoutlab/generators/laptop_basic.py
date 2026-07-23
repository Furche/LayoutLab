# LayoutLab generator — see laptop_basic.md for parameter reference.
GENERATOR_NAME = "laptop_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Open laptop (base + screen)."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "LAPTOP_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.32), 0.22, 0.32)
    depth = _clamp(params.get("depth", 0.22), 0.16, 0.22)
    height = _clamp(params.get("height", 0.02), 0.012, 0.02)
    screen_h = _clamp(params.get("screen_height", 0.2), 0.12, 0.2)
    body_color = params.get("body_color", [0.55, 0.55, 0.58, 1.0])
    screen_color = params.get("screen_color", [0.1, 0.12, 0.16, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="laptop_body")
    cb(f"{name}__base", [x, y, z], [width, depth, height], body_color, collection, "laptop_base", None)
    # screen as thin panel at back of base
    st = 0.01
    cb(f"{name}__screen", [x, y + depth - st, z + height], [width, st, screen_h], screen_color, collection, "laptop_screen", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + screen_h + 0.03], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height + screen_h]}
