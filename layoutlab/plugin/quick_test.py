"""Generator-specific Quick Test fields and params for the browser popup.

Defaults are Blender scene units (Metric: 1 unit = 1 meter).
"""

QUICK_TEST_PROFILES = {
    "bed_basic": {
        "object_name": "TEST_BED",
        "fields": (
            ("layoutlab_test_length", "Length"),
            ("layoutlab_test_width", "Width"),
        ),
        "defaults": {
            "layoutlab_test_length": 1.2,
            "layoutlab_test_width": 2.0,
        },
    },
    "wardrobe_basic": {
        "object_name": "TEST_WARDROBE",
        "fields": (
            ("layoutlab_test_width", "Width"),
            ("layoutlab_test_depth", "Depth"),
            ("layoutlab_test_height", "Height"),
        ),
        "defaults": {
            "layoutlab_test_width": 0.8,
            "layoutlab_test_depth": 0.4,
            "layoutlab_test_height": 1.5,
        },
    },
    "desk_basic": {
        "object_name": "TEST_DESK",
        "fields": (
            ("layoutlab_test_width", "Width"),
            ("layoutlab_test_depth", "Depth"),
            ("layoutlab_test_height", "Height"),
        ),
        "defaults": {
            "layoutlab_test_width": 1.2,
            "layoutlab_test_depth": 0.6,
            "layoutlab_test_height": 0.75,
        },
    },
}

GENERIC_QUICK_TEST = {
    "object_name": None,
    "fields": (
        ("layoutlab_test_length", "Length"),
        ("layoutlab_test_width", "Width"),
    ),
    "defaults": {
        "layoutlab_test_length": 1.0,
        "layoutlab_test_width": 1.0,
    },
}

# Furniture in meters rarely exceeds this; old Quick Test used 8–20 (pre-metric).
_PRE_METRIC_DIM_THRESHOLD = 5.0


def quick_test_profile(generator_name):
    return QUICK_TEST_PROFILES.get(generator_name, GENERIC_QUICK_TEST)


def default_quick_test_object_name(generator_name):
    profile = quick_test_profile(generator_name)
    if profile.get("object_name"):
        return profile["object_name"]
    safe = (generator_name or "generator").upper().replace(".", "_")
    return f"TEST_{safe}"


def quick_test_values_look_pre_metric(scene, generator_name):
    """True if scene Quick Test dims still look like the old ÷10 / cm-era defaults."""
    profile = quick_test_profile(generator_name)
    for prop_name in profile.get("defaults", {}):
        try:
            if float(getattr(scene, prop_name)) > _PRE_METRIC_DIM_THRESHOLD:
                return True
        except (TypeError, ValueError, AttributeError):
            continue
    return False


def apply_quick_test_profile(scene, generator_name):
    profile = quick_test_profile(generator_name)
    for prop_name, value in profile["defaults"].items():
        setattr(scene, prop_name, value)
    scene.layoutlab_test_object_name = default_quick_test_object_name(generator_name)


def draw_quick_test_fields(layout, scene, generator_name):
    profile = quick_test_profile(generator_name)
    layout.prop(scene, "layoutlab_test_object_name", text="Name")
    layout.prop(scene, "layoutlab_test_location", text="Location")
    for prop_name, label in profile["fields"]:
        layout.prop(scene, prop_name, text=label)


def build_quick_test_params(scene, generator_name):
    name = (scene.layoutlab_test_object_name or "").strip()
    if not name:
        name = default_quick_test_object_name(generator_name)

    params = {
        "name": name,
        "location": list(scene.layoutlab_test_location),
        "collection": "layout_tests",
    }

    if generator_name == "bed_basic":
        params.update({
            "length": scene.layoutlab_test_length,
            "width": scene.layoutlab_test_width,
            "head_side": "y_max",
        })
    elif generator_name == "wardrobe_basic":
        params.update({
            "width": scene.layoutlab_test_width,
            "depth": scene.layoutlab_test_depth,
            "height": scene.layoutlab_test_height,
            "show_clearance": True,
        })
    elif generator_name == "desk_basic":
        params.update({
            "width": scene.layoutlab_test_width,
            "depth": scene.layoutlab_test_depth,
            "height": scene.layoutlab_test_height,
            "show_clearance": True,
        })
    else:
        params.update({
            "length": scene.layoutlab_test_length,
            "width": scene.layoutlab_test_width,
        })

    return params
