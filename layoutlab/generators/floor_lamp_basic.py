# LayoutLab generator — see floor_lamp_basic.md for parameter reference.
GENERATOR_NAME = "floor_lamp_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Tall floor lamp (base + stem + shade)."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "FLOOR_LAMP_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    base = _clamp(params.get("base", 0.28), 0.18, 0.28)
    height = _clamp(params.get("height", 1.55), 1.0, 1.55)
    shade = _clamp(params.get("shade", 0.35), 0.22, 0.35)
    base_h = 0.04
    shade_h = min(0.22, height * 0.16)
    stem_h = max(height - base_h - shade_h, 0.5)
    stem_t = 0.03
    base_color = params.get("base_color", [0.22, 0.22, 0.24, 1.0])
    stem_color = params.get("stem_color", [0.5, 0.5, 0.52, 1.0])
    shade_color = params.get("shade_color", [0.92, 0.88, 0.78, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="floor_lamp_body")
    cb(f"{name}__base", [x, y, z], [base, base, base_h], base_color, collection, "floor_lamp_base", None)
    sx = x + (base - stem_t) * 0.5
    sy = y + (base - stem_t) * 0.5
    cb(f"{name}__stem", [sx, sy, z + base_h], [stem_t, stem_t, stem_h], stem_color, collection, "floor_lamp_stem", None)
    shx = x + (base - shade) * 0.5
    shy = y + (base - shade) * 0.5
    cb(f"{name}__shade", [shx, shy, z + base_h + stem_h], [shade, shade, shade_h], shade_color, collection, "floor_lamp_shade", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + base / 2, y + base / 2, z + height + 0.04], name, collection, 0.025)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [max(base, shade), max(base, shade), height]}
