import bpy

from mathutils import Matrix


def _world_matrix_delta(a, b, tolerance=1e-3):
    return matrix_max_abs_delta(a, b) <= tolerance


def parent_preserve_world_transform(child, parent):
    """Parent *child* to *parent* without changing its world matrix.

    Generators place build meshes in absolute world coordinates (from params.location).
    After join, child Parts must keep the same world position when parented to the
    Main Part.

    Uses Blender's ``parent_set(keep_transform=True)`` when possible — more reliable
    than assigning ``matrix_world`` after parenting inside ``exec()`` / operators.
    Falls back to explicit ``matrix_local`` assignment.
    """
    if child is None or parent is None or child == parent:
        return child

    world = child.matrix_world.copy()
    view_layer = bpy.context.view_layer

    if _parent_with_operator(child, parent, view_layer):
        view_layer.update()
        if _world_matrix_delta(child.matrix_world, world):
            return child

    parent_world = parent.matrix_world.copy()
    child.parent = None
    child.matrix_world = world
    child.parent = parent
    child.parent_type = "OBJECT"
    child.matrix_local = parent_world.inverted() @ world
    if view_layer:
        view_layer.update()
    return child


def _parent_with_operator(child, parent, view_layer):
    try:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        return False

    try:
        for obj in view_layer.objects:
            obj.select_set(False)
        child.select_set(True)
        parent.select_set(True)
        view_layer.objects.active = parent
        bpy.ops.object.parent_set(type="OBJECT", keep_transform=True)
        return True
    except RuntimeError:
        return False


def matrix_max_abs_delta(a, b):
    """Largest absolute element difference between two 4×4 matrices."""
    return max(abs(float(a[i][j]) - float(b[i][j])) for i in range(4) for j in range(4))


def parenting_local_matches_world(child, parent, tolerance=1e-4):
    """Return True if child.matrix_local == parent⁻¹ @ child.matrix_world."""
    expected = parent.matrix_world.inverted() @ child.matrix_world
    return matrix_max_abs_delta(child.matrix_local, expected) <= tolerance


def world_translation_tuple(obj):
    t = obj.matrix_world.translation
    return (float(t.x), float(t.y), float(t.z))


def relative_translation_tuple(child, parent):
    cw = child.matrix_world.translation
    pw = parent.matrix_world.translation
    return (float(cw.x - pw.x), float(cw.y - pw.y), float(cw.z - pw.z))


def translations_close(a, b, tolerance=0.05):
    return all(abs(a[i] - b[i]) <= tolerance for i in range(3))
