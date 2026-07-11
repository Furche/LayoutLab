"""Layout constraint analysis (DD-008) — reads clearances, emits findings."""

import json

from ..util import aabb_intersects, requirement_to_severity
from .clearance_export import world_bounds_from_object

CONSTRAINT_TYPE_ZONE_MUST_BE_CLEAR = "zone_must_be_clear"


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


def _furniture_name_for_clearance(clearance_obj):
    parent = clearance_obj.parent
    if parent:
        raw_params = parent.get("layoutlab_params")
        if raw_params:
            try:
                params = json.loads(raw_params)
                name = params.get("name")
                if name:
                    return str(name)
            except (TypeError, json.JSONDecodeError):
                pass
        if parent.name.endswith("_body"):
            return parent.name[: -len("_body")]
        return parent.name
    if clearance_obj.name.endswith("_clearance_front_access"):
        return clearance_obj.name[: -len("_clearance_front_access")]
    return clearance_obj.name


def _violation_message(requirement, clearance_name, furniture_name):
    labels = {
        "required": "Required",
        "preferred": "Preferred",
        "informational": "Informational",
    }
    req = (requirement or "preferred").strip().lower()
    label = labels.get(req, "Clearance")
    return f"{label} clearance '{clearance_name}' on {furniture_name} is blocked"


def _is_clearance_object(obj):
    return bool(obj.get("layoutlab_clearance_name"))


def _is_blocker_mesh(obj):
    if getattr(obj, "type", None) != "MESH":
        return False
    if obj.get("layoutlab_clearance_name") or obj.get("layoutlab_role") == "clearance":
        return False
    return True


def _blocker_overlap_entry(obj):
    return {
        "object_name": obj.name,
        "object_id": obj.get("layoutlab_object_id", ""),
        "part": obj.get("layoutlab_part", ""),
    }


def analyze_layout(context, cmd):
    """Run zone_must_be_clear checks for clearances in scope (DD-008 v1)."""
    scope = cmd.get("scope", "scene")
    collection_name = cmd.get("collection")
    include = cmd.get("include", ["clearances"])
    if include != ["clearances"]:
        raise ValueError('analyze_layout v1 only supports include=["clearances"]')

    objects = collect_objects_for_scope(context, scope, collection_name)
    context.view_layer.update()

    clearances = [obj for obj in objects if _is_clearance_object(obj)]
    blockers = [obj for obj in objects if _is_blocker_mesh(obj)]

    findings = []
    for clearance in clearances:
        clearance_bounds = world_bounds_from_object(clearance)
        owner_id = clearance.get("layoutlab_object_id", "")
        clearance_name = clearance.get("layoutlab_clearance_name", "")
        requirement = clearance.get("layoutlab_clearance_requirement", "preferred")
        furniture_name = _furniture_name_for_clearance(clearance)

        overlaps = []
        for blocker in blockers:
            if blocker == clearance:
                continue
            blocker_id = blocker.get("layoutlab_object_id", "")
            if owner_id and blocker_id and blocker_id == owner_id:
                continue
            blocker_bounds = world_bounds_from_object(blocker)
            if aabb_intersects(clearance_bounds, blocker_bounds):
                overlaps.append(_blocker_overlap_entry(blocker))

        if overlaps:
            severity = requirement_to_severity(requirement)
            findings.append(
                {
                    "severity": severity,
                    "constraint_type": CONSTRAINT_TYPE_ZONE_MUST_BE_CLEAR,
                    "message": _violation_message(requirement, clearance_name, furniture_name),
                    "clearance_ref": {
                        "object_id": owner_id,
                        "clearance_id": clearance.get("layoutlab_clearance_id", ""),
                        "clearance_name": clearance_name,
                        "furniture_name": furniture_name,
                    },
                    "overlaps": overlaps,
                }
            )

    summary = {"errors": 0, "warnings": 0, "info": 0}
    for finding in findings:
        sev = finding.get("severity", "warning")
        if sev in summary:
            summary[sev] += 1

    return {
        "analyzed": True,
        "scope": scope,
        "object_count": len(objects),
        "clearance_count": len(clearances),
        "summary": summary,
        "findings": findings,
    }
