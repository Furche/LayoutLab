# LayoutLab generator — see laundry_basket_basic.md for parameter reference.
GENERATOR_NAME = "laundry_basket_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Laundry basket (open box)."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "BASKET_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.4), 0.28, 0.4)
    depth = _clamp(params.get("depth", 0.4), 0.28, 0.4)
    height = _clamp(params.get("height", 0.5), 0.35, 0.5)
    wall = 0.02
    color = params.get("color", [0.75, 0.72, 0.68, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="basket_body")
    # floor
    cb(f"{name}__floor", [x, y, z], [width, depth, wall], color, collection, "basket_floor", None)
    # four walls
    cb(f"{name}__w_s", [x, y, z + wall], [width, wall, height - wall], color, collection, "basket_wall", None)
    cb(f"{name}__w_n", [x, y + depth - wall, z + wall], [width, wall, height - wall], color, collection, "basket_wall", None)
    cb(f"{name}__w_w", [x, y + wall, z + wall], [wall, depth - 2 * wall, height - wall], color, collection, "basket_wall", None)
    cb(f"{name}__w_e", [x + width - wall, y + wall, z + wall], [wall, depth - 2 * wall, height - wall], color, collection, "basket_wall", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
