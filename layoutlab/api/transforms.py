"""Matrix helpers for Part finalization — preserve world transforms on parenting."""

from mathutils import Matrix


def parent_preserve_world_transform(child, parent):
    """Parent *child* to *parent* without changing its world matrix.

    Generators place build meshes in absolute world coordinates (from params.location).
    After join, child Parts must keep the same world position when parented to the
    Main Part. Setting ``child.matrix_world`` after ``child.parent = parent`` is
    unreliable in all Blender contexts; explicit ``matrix_local`` is required.
    """
    if child is None or parent is None or child == parent:
        return child

    world = child.matrix_world.copy()
    parent_world = parent.matrix_world.copy()
    child.parent = parent
    child.parent_type = "OBJECT"
    child.matrix_local = parent_world.inverted() @ world
    return child


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
