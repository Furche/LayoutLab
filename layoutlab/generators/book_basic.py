# LayoutLab generator — see book_basic.md for parameter reference.
GENERATOR_NAME = "book_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Small book or short book stack."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "BOOK_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.16), 0.1, 0.16)
    depth = _clamp(params.get("depth", 0.12), 0.08, 0.12)
    height = _clamp(params.get("height", 0.04), 0.02, 0.04)
    count = int(max(1, min(4, int(params.get("count", 2) or 2))))
    colors = params.get("colors") or [
        [0.55, 0.2, 0.18, 1.0],
        [0.2, 0.35, 0.5, 1.0],
        [0.75, 0.65, 0.35, 1.0],
        [0.25, 0.4, 0.28, 1.0],
    ]
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="book_body")
    layer = height / count
    for i in range(count):
        c = colors[i % len(colors)]
        # slight offset for stack look
        ox = 0.004 * (i % 2)
        cb(f"{name}__book_{i}", [x + ox, y, z + i * layer], [width - ox, depth, max(layer * 0.92, 0.008)], c, collection, "book_volume", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.018)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
