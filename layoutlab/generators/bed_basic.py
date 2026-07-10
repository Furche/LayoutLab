# LayoutLab generator — see bed_basic.md for parameter reference.
GENERATOR_NAME = "bed_basic"
GENERATOR_CATEGORY = "Beds"
GENERATOR_DESCRIPTION = "Parametric low bed with legs, frame, mattress, headboard and fallback sizing."
GENERATOR_VERSION = "0.4.1"
GENERATOR_ICON = "BED"

# Fallback thresholds (Blender units; 1 unit ≈ 10 cm in reference room)
MIN_BED_DIMENSION = 3
PILLOW_COUNT_WIDTH_THRESHOLD = 13  # width >= 13 → two pillows
PILLOW_HEIGHT = 0.45
PILLOW_GAP = 0.2
MATTRESS_Z_INSET_FACTOR = 0.55  # mattress sits above lower rail within frame


def generate(params, api):
    name = params.get("name", "BED_basic")
    x, y, z = params.get("location", [0, 0, 0])
    length = max(params.get("length", 20), MIN_BED_DIMENSION)
    width = max(params.get("width", 12), MIN_BED_DIMENSION)
    collection = params.get("collection", "layout_tests")

    leg_height = params.get("leg_height", 2.5)
    frame_height = params.get("frame_height", 1.0)
    mattress_height = params.get("mattress_height", 2.0)
    rail = min(params.get("rail_thickness", 0.35), width * 0.2, length * 0.2)
    post = min(params.get("post_size", 0.45), width * 0.25, length * 0.25)
    inset = min(params.get("mattress_inset", 0.45), width * 0.2, length * 0.2)
    head_side = params.get("head_side", "y_max")

    frame_color = params.get("frame_color", [0.72, 0.55, 0.35, 1])
    mattress_color = params.get("mattress_color", [0.86, 0.86, 0.82, 0.65])
    pillow_color = params.get("pillow_color", [0.95, 0.95, 0.92, 1])

    cb = api["create_box"]
    cl = api["create_label"]
    bp = api["begin_part"]
    ep = api["end_part"]

    frame_z = z + leg_height
    mattress_x = x + rail
    mattress_y = y + rail
    mattress_l = max(length - 2 * rail, 1)
    mattress_w = max(width - 2 * rail, 1)
    mattress_z = frame_z + frame_height * MATTRESS_Z_INSET_FACTOR

    bp("body", main=True, role="bed_frame")
    for sx, sy, suffix in [
        (0, 0, "post_xmin_ymin"),
        (length - post, 0, "post_xmax_ymin"),
        (0, width - post, "post_xmin_ymax"),
        (length - post, width - post, "post_xmax_ymax"),
    ]:
        cb(
            f"{name}__body_{suffix}",
            [x + sx, y + sy, z],
            [post, post, leg_height + frame_height],
            frame_color,
            collection,
            "bed_post",
            None,
        )

    cb(f"{name}__body_rail_y_min", [x, y, frame_z], [length, rail, frame_height], frame_color, collection, "bed_frame", None)
    cb(f"{name}__body_rail_y_max", [x, y + width - rail, frame_z], [length, rail, frame_height], frame_color, collection, "bed_frame", None)
    cb(f"{name}__body_rail_x_min", [x, y, frame_z], [rail, width, frame_height], frame_color, collection, "bed_frame", None)
    cb(f"{name}__body_rail_x_max", [x + length - rail, y, frame_z], [rail, width, frame_height], frame_color, collection, "bed_frame", None)

    head_h = params.get("headboard_height", 4.2)
    foot_h = params.get("footboard_height", 2.2)
    if head_side == "y_max":
        cb(f"{name}__body_headboard", [x, y + width - rail, z], [length, rail, head_h], frame_color, collection, "bed_headboard", None)
        cb(f"{name}__body_footboard", [x, y, z], [length, rail, foot_h], frame_color, collection, "bed_footboard", None)
        pillow_y = y + width - rail - 2.1
    elif head_side == "y_min":
        cb(f"{name}__body_headboard", [x, y, z], [length, rail, head_h], frame_color, collection, "bed_headboard", None)
        cb(f"{name}__body_footboard", [x, y + width - rail, z], [length, rail, foot_h], frame_color, collection, "bed_footboard", None)
        pillow_y = y + rail + 0.25
    elif head_side == "x_max":
        cb(f"{name}__body_headboard", [x + length - rail, y, z], [rail, width, head_h], frame_color, collection, "bed_headboard", None)
        cb(f"{name}__body_footboard", [x, y, z], [rail, width, foot_h], frame_color, collection, "bed_footboard", None)
        pillow_y = mattress_y + mattress_w - 2.0
    else:
        cb(f"{name}__body_headboard", [x, y, z], [rail, width, head_h], frame_color, collection, "bed_headboard", None)
        cb(f"{name}__body_footboard", [x + length - rail, y, z], [rail, width, foot_h], frame_color, collection, "bed_footboard", None)
        pillow_y = mattress_y + 0.2

    ep()

    bp("mattress", role="bed_mattress")
    cb(
        f"{name}__mattress",
        [mattress_x, mattress_y, mattress_z],
        [mattress_l, mattress_w, mattress_height],
        mattress_color,
        collection,
        "bed_mattress",
        None,
    )
    ep()

    pillow_count = 2 if width >= PILLOW_COUNT_WIDTH_THRESHOLD else 1
    pillow_w = max((mattress_w - 0.4) / pillow_count, 0.8)
    for i in range(pillow_count):
        px = mattress_x + PILLOW_GAP + i * pillow_w
        py = max(min(pillow_y, mattress_y + mattress_w - 1.2), mattress_y + 0.2)
        bp(f"pillow_{i + 1}", role="bed_pillow")
        cb(
            f"{name}__pillow_{i + 1}",
            [px, py, mattress_z + mattress_height + 0.05],
            [pillow_w - PILLOW_GAP, min(1.8, mattress_w * 0.35), PILLOW_HEIGHT],
            pillow_color,
            collection,
            "bed_pillow",
            None,
        )
        ep()

    bp("label", role="label")
    cl(f"{name}__label", [x + length / 2, y + width / 2, mattress_z + mattress_height + 0.7], name, collection)
    ep()

    return {"created": name, "type": "bed_basic", "size": [length, width]}
