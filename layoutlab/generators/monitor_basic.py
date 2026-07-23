# LayoutLab generator — see monitor_basic.md for parameter reference.
GENERATOR_NAME = "monitor_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Desk monitor with stand and screen."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)

def generate(params, api):
    name = params.get("name", "MONITOR_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    width = _clamp(params.get("width", 0.52), 0.3, 0.52)
    depth = _clamp(params.get("depth", 0.18), 0.12, 0.18)
    height = _clamp(params.get("height", 0.42), 0.28, 0.42)
    stand_color = params.get("stand_color", [0.22, 0.22, 0.24, 1.0])
    screen_color = params.get("screen_color", [0.12, 0.14, 0.18, 1.0])
    cb, cl, bp, ep = api["create_box"], api["create_label"], api["begin_part"], api["end_part"]
    base_h, base_d = 0.02, depth
    base_w = min(width * 0.45, 0.22)
    neck_w, neck_d, neck_h = 0.04, 0.04, height * 0.28
    screen_t = 0.03
    screen_h = height - base_h - 0.04
    bp("body", main=True, role="monitor_body")
    bx = x + (width - base_w) * 0.5
    cb(f"{name}__base", [bx, y, z], [base_w, base_d, base_h], stand_color, collection, "monitor_base", None)
    nx = x + (width - neck_w) * 0.5
    ny = y + (depth - neck_d) * 0.55
    cb(f"{name}__neck", [nx, ny, z + base_h], [neck_w, neck_d, neck_h], stand_color, collection, "monitor_neck", None)
    sy = y + depth - screen_t
    cb(f"{name}__screen", [x, sy, z + base_h + neck_h * 0.35], [width, screen_t, screen_h], screen_color, collection, "monitor_screen", None)
    ep()
    bp("label", role="label")
    cl(f"{name}__label", [x + width / 2, y + depth / 2, z + height + 0.04], name, collection, 0.02)
    ep()
    return {"created": name, "type": GENERATOR_NAME, "size": [width, depth, height]}
