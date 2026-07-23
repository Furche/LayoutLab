# LayoutLab generator — see plant_basic.md for parameter reference.
GENERATOR_NAME = "plant_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Potted plant (pot + foliage box)."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "PLANT_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    pot = _clamp(params.get("pot", 0.14), 0.08, 0.14)
    height = _clamp(params.get("height", 0.4), 0.22, 0.4)
    pot_h = min(0.12, height * 0.35)
    foliage = _clamp(params.get("foliage", pot * 1.35), pot, pot * 1.6)
    foliage_h = max(height - pot_h, 0.08)
    pot_color = params.get("pot_color", [0.55, 0.4, 0.32, 1.0])
    leaf_color = params.get("leaf_color", [0.25, 0.48, 0.3, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="plant_body")
    cb(f"{name}__pot", [x, y, z], [pot, pot, pot_h], pot_color, collection, "plant_pot", None)
    fx = x + (pot - foliage) * 0.5
    fy = y + (pot - foliage) * 0.5
    cb(f"{name}__foliage", [fx, fy, z + pot_h], [foliage, foliage, foliage_h], leaf_color, collection, "plant_foliage", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + pot / 2, y + pot / 2, z + height + 0.03], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [max(pot, foliage), max(pot, foliage), height]}
