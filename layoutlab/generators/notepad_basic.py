# LayoutLab generator — see notepad_basic.md for parameter reference.
GENERATOR_NAME = "notepad_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Notepad / paper pad."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "NOTEPAD_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.15), 0.1, 0.15)
    depth = _clamp(params.get("depth", 0.21), 0.14, 0.21)
    height = _clamp(params.get("height", 0.015), 0.008, 0.015)
    color = params.get("color", [0.95, 0.93, 0.88, 1.0])
    binding = params.get("binding_color", [0.75, 0.2, 0.2, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    bp("body", main=True, role="notepad_body")
    cb(f"{name}__pad", [x, y, z], [width, depth, height], color, collection, "notepad_pad", None)
    cb(f"{name}__bind", [x, y, z + height], [width, 0.012, 0.003], binding, collection, "notepad_binding", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.03], name, collection, 0.016)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
