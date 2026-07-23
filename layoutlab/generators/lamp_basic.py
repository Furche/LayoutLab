# LayoutLab generator — see lamp_basic.md for parameter reference.
GENERATOR_NAME = "lamp_basic"
GENERATOR_CATEGORY = "Decor"
GENERATOR_DESCRIPTION = "Minimal table lamp (base + stem + shade) for support-surface demos."
GENERATOR_VERSION = "0.1.0"
GENERATOR_ICON = "MESH_CUBE"

MIN_BASE = 0.08
DEFAULT_BASE = 0.12
DEFAULT_HEIGHT = 0.38
DEFAULT_SHADE = 0.16


def _clamp(value, minimum, fallback):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(value, minimum)


def generate(params, api):
    name = params.get("name", "LAMP_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")

    base = _clamp(params.get("base", DEFAULT_BASE), MIN_BASE, DEFAULT_BASE)
    height = _clamp(params.get("height", DEFAULT_HEIGHT), 0.2, DEFAULT_HEIGHT)
    shade = _clamp(params.get("shade", DEFAULT_SHADE), MIN_BASE, DEFAULT_SHADE)

    base_h = min(0.03, height * 0.12)
    shade_h = min(0.08, height * 0.25)
    stem_h = max(height - base_h - shade_h, 0.05)
    stem_t = min(0.02, base * 0.2)

    base_color = params.get("base_color", [0.25, 0.25, 0.28, 1.0])
    stem_color = params.get("stem_color", [0.55, 0.55, 0.58, 1.0])
    shade_color = params.get("shade_color", [0.92, 0.88, 0.75, 1.0])

    cb = api["create_box"]
    cl = api["create_label"]
    bp = api["begin_part"]
    ep = api["end_part"]

    bp("body", main=True, role="lamp_body")
    cb(
        f"{name}__body_base",
        [x, y, z],
        [base, base, base_h],
        base_color,
        collection,
        "lamp_base",
        None,
    )
    stem_x = x + (base - stem_t) * 0.5
    stem_y = y + (base - stem_t) * 0.5
    cb(
        f"{name}__body_stem",
        [stem_x, stem_y, z + base_h],
        [stem_t, stem_t, stem_h],
        stem_color,
        collection,
        "lamp_stem",
        None,
    )
    shade_x = x + (base - shade) * 0.5
    shade_y = y + (base - shade) * 0.5
    cb(
        f"{name}__body_shade",
        [shade_x, shade_y, z + base_h + stem_h],
        [shade, shade, shade_h],
        shade_color,
        collection,
        "lamp_shade",
        None,
    )
    ep()

    bp("label", role="label")
    cl(
        f"{name}__label",
        [x + base / 2, y + base / 2, z + height + 0.04],
        name,
        collection,
        0.025,
    )
    ep()

    return {
        "created": name,
        "type": GENERATOR_NAME,
        "size": [base, base, height],
    }
