"""LayoutLab units ↔ Blender scene units.

Protocol / JSON / generator params use LayoutLab units:
    1 LL unit = 10 cm = 0.1 m

Blender mesh coordinates use scene Blender Units (BU). For METRIC/NONE:
    1 BU = scale_length meters
    bu = ll * 0.1 / scale_length
"""

from __future__ import annotations

LAYOUTLAB_METERS_PER_UNIT = 0.1
SCALE_CONVENTION = "1_unit_equals_10cm"


def scene_scale_length(scene=None):
    """Return Blender ``unit_settings.scale_length`` (meters per BU for metric)."""
    if scene is None:
        import bpy

        scene = bpy.context.scene
    try:
        return float(scene.unit_settings.scale_length) or 1.0
    except Exception:
        return 1.0


def bu_per_ll_unit(scale_length=None, scene=None):
    """How many Blender units equal one LayoutLab unit."""
    if scale_length is None:
        scale_length = scene_scale_length(scene)
    scale_length = float(scale_length) or 1.0
    return LAYOUTLAB_METERS_PER_UNIT / scale_length


def to_bu(value, scale_length=None, scene=None):
    return float(value) * bu_per_ll_unit(scale_length=scale_length, scene=scene)


def from_bu(value, scale_length=None, scene=None):
    factor = bu_per_ll_unit(scale_length=scale_length, scene=scene)
    if factor == 0:
        return float(value)
    return float(value) / factor


def to_bu_vec(values, scale_length=None, scene=None):
    factor = bu_per_ll_unit(scale_length=scale_length, scene=scene)
    return [float(v) * factor for v in values]


def from_bu_vec(values, scale_length=None, scene=None):
    factor = bu_per_ll_unit(scale_length=scale_length, scene=scene)
    if factor == 0:
        return [float(v) for v in values]
    return [float(v) / factor for v in values]


def unit_export_fields(scene=None):
    """Top-level export metadata for scene JSON."""
    scale_length = scene_scale_length(scene)
    factor = bu_per_ll_unit(scale_length=scale_length)
    system = "NONE"
    if scene is not None:
        try:
            system = scene.unit_settings.system
        except Exception:
            pass
    else:
        try:
            import bpy

            system = bpy.context.scene.unit_settings.system
        except Exception:
            pass
    return {
        "unit": system,
        "unit_scale": scale_length,
        "scale_convention": SCALE_CONVENTION,
        "bu_per_ll_unit": factor,
        "note": (
            "Coordinates/dimensions are LayoutLab units (1 unit = 10 cm). "
            f"Scene Blender units: multiply by bu_per_ll_unit ({factor})."
        ),
    }
