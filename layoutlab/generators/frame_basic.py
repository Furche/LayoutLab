# LayoutLab generator — see frame_basic.md for parameter reference.
GENERATOR_NAME = "frame_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Standing picture frame."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "FRAME_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.22), 0.12, 0.22)
    depth = _clamp(params.get("depth", 0.08), 0.05, 0.08)
    height = _clamp(params.get("height", 0.3), 0.16, 0.3)
    frame_color = params.get("frame_color", [0.35, 0.28, 0.22, 1.0])
    art_color = params.get("art_color", [0.7, 0.75, 0.8, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    base_h = 0.015
    frame_t = 0.02
    bp("body", main=True, role="frame_body")
    cb(f"{name}__base", [x, y, z], [width, depth, base_h], frame_color, collection, "frame_base", None)
    # upright panel near back of base
    cb(f"{name}__frame", [x, y + depth - frame_t, z + base_h], [width, frame_t, height - base_h], frame_color, collection, "frame_border", None)
    inset = 0.02
    cb(
        f"{name}__art",
        [x + inset, y + depth - frame_t - 0.005, z + base_h + inset],
        [max(width - 2 * inset, 0.05), 0.008, max(height - base_h - 2 * inset, 0.08)],
        art_color,
        collection,
        "frame_art",
        None,
    )
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.018)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
