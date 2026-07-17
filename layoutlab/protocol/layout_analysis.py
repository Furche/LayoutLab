"""Layout constraint analysis (DD-008) — Blender adapter + shared core."""

from ..core.analyze import (
    CONSTRAINT_TYPE_ZONE_MUST_BE_CLEAR,
    analyze_clearance_objects,
    blocker_overlap_entry,
    furniture_name_for_clearance,
    is_blocker_mesh,
    is_clearance_object,
    violation_message,
)
from .clearance_export import world_bounds_from_object

# Re-export helpers used by tests / callers
_furniture_name_for_clearance = furniture_name_for_clearance
_violation_message = violation_message
_is_clearance_object = is_clearance_object
_is_blocker_mesh = is_blocker_mesh
_blocker_overlap_entry = blocker_overlap_entry


def _objects_in_collection_recursive(coll):
    objects = list(coll.objects)
    for child in coll.children:
        objects.extend(_objects_in_collection_recursive(child))
    return objects


def collect_objects_for_scope(context, scope, collection_name=None):
    if scope == "selection":
        return list(context.selected_objects)
    if scope == "collection":
        if not collection_name:
            raise ValueError("analyze_layout with scope=collection requires collection")
        coll = context.blend_data.collections.get(collection_name)
        if not coll:
            raise ValueError(f"Collection not found: {collection_name}")
        return _objects_in_collection_recursive(coll)
    if scope == "scene":
        return _objects_in_collection_recursive(context.scene.collection)
    raise ValueError(f"Unknown analyze_layout scope: {scope!r}")


def analyze_layout(context, cmd):
    """Run zone_must_be_clear checks for clearances in scope (DD-008 v1)."""
    scope = cmd.get("scope", "scene")
    collection_name = cmd.get("collection")
    include = cmd.get("include", ["clearances"])
    if include != ["clearances"]:
        raise ValueError('analyze_layout v1 only supports include=["clearances"]')

    objects = collect_objects_for_scope(context, scope, collection_name)
    context.view_layer.update()

    return analyze_clearance_objects(
        objects,
        get_world_bounds=world_bounds_from_object,
        scope=scope,
    )
