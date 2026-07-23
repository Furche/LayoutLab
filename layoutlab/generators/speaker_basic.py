# LayoutLab generator — see speaker_basic.md for parameter reference.
GENERATOR_NAME = "speaker_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Compact desk speaker."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "SPEAKER_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.12), 0.08, 0.12)
    depth = _clamp(params.get("depth", 0.14), 0.1, 0.14)
    height = _clamp(params.get("height", 0.22), 0.14, 0.22)
    color = params.get("color", [0.15, 0.15, 0.16, 1.0])
    grill = params.get("grill_color", [0.3, 0.3, 0.32, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="speaker_body")
    cb(f"{name}__body", [x, y, z], [width, depth, height], color, collection, "speaker_body", None)
    cb(f"{name}__grill", [x + width * 0.15, y + depth - 0.008, z + height * 0.2], [width * 0.7, 0.008, height * 0.55], grill, collection, "speaker_grill", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.016)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
