# LayoutLab generator — see keyboard_basic.md for parameter reference.
GENERATOR_NAME = "keyboard_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Flat computer keyboard for desk styling."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "KEYBOARD_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.45), 0.2, 0.45)
    depth = _clamp(params.get("depth", 0.15), 0.08, 0.15)
    height = _clamp(params.get("height", 0.025), 0.01, 0.025)
    color = params.get("color", [0.18, 0.18, 0.2, 1.0])
    key_color = params.get("key_color", [0.28, 0.28, 0.3, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="keyboard_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "keyboard_body", None)
    # shallow key deck inset
    inset = 0.012
    cb(
        f"{name}__keys",
        [x + inset, y + inset, z + height],
        [max(width - 2 * inset, 0.05), max(depth - 2 * inset, 0.04), 0.006],
        key_color,
        collection,
        "keyboard_keys",
        None,
    )
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.04], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height + 0.006]}
