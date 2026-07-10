import bpy


def _world_matrix_delta(a, b, tolerance=1e-3):
    return matrix_max_abs_delta(a, b) <= tolerance


def _parent_has_identity_rotation(parent, tolerance=1e-5):
    return all(abs(float(r)) <= tolerance for r in parent.rotation_euler)


def parent_preserve_world_transform(child, parent, world=None):
    """Parent *child* to *parent* without changing its world matrix.

    LayoutLab generators are axis-aligned (no rotation). For that common case we
    set ``child.location`` to the world-space offset — more reliable inside
    ``exec()`` than assigning ``matrix_world`` / ``matrix_local`` after parenting.
    """
    if child is None or parent is None or child == parent:
        return child

    target_world = (world or child.matrix_world).copy()
    target_loc = target_world.translation.copy()
    view_layer = bpy.context.view_layer

    if child.parent:
        child.parent = None
        if view_layer:
            view_layer.update()

    child.parent = parent
    child.parent_type = "OBJECT"

    if _parent_has_identity_rotation(parent):
        parent_loc = parent.matrix_world.translation
        offset = target_loc - parent_loc
        child.location = (float(offset.x), float(offset.y), float(offset.z))
        child.rotation_euler = (0.0, 0.0, 0.0)
        child.scale = (1.0, 1.0, 1.0)
    else:
        child.matrix_local = parent.matrix_world.inverted() @ target_world

    if view_layer:
        view_layer.update()

    if not _world_matrix_delta(child.matrix_world, target_world, tolerance=1e-2):
        child.parent = None
        child.matrix_world = target_world
        child.parent = parent
        child.parent_type = "OBJECT"
        child.matrix_local = parent.matrix_world.inverted() @ target_world
        if view_layer:
            view_layer.update()

    return child


def matrix_max_abs_delta(a, b):
    """Largest absolute element difference between two 4×4 matrices."""
    return max(abs(float(a[i][j]) - float(b[i][j])) for i in range(4) for j in range(4))


def parenting_local_matches_world(child, parent, tolerance=1e-4):
    """Return True if child.matrix_local == parent⁻¹ @ child.matrix_world."""
    expected = parent.matrix_world.inverted() @ child.matrix_world
    return matrix_max_abs_delta(child.matrix_local, expected) <= tolerance


def child_local_looks_like_world_coords(child, max_local=15.0):
    """Heuristic: failed parenting often leaves local coords equal to world coords."""
    loc = child.location
    return abs(float(loc.x)) > max_local or abs(float(loc.y)) > max_local


def world_translation_tuple(obj):
    t = obj.matrix_world.translation
    return (float(t.x), float(t.y), float(t.z))


def relative_translation_tuple(child, parent):
    cw = child.matrix_world.translation
    pw = parent.matrix_world.translation
    return (float(cw.x - pw.x), float(cw.y - pw.y), float(cw.z - pw.z))


def translations_close(a, b, tolerance=0.05):
    return all(abs(a[i] - b[i]) <= tolerance for i in range(3))
