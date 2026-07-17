"""Pure clearance overlap analysis (DD-008) — no bpy / mathutils."""

from __future__ import annotations

import json

from ..util import aabb_intersects, is_analyze_blocker, requirement_to_severity

CONSTRAINT_TYPE_ZONE_MUST_BE_CLEAR = "zone_must_be_clear"


def furniture_name_for_clearance(clearance_obj):
    parent = getattr(clearance_obj, "parent", None)
    if parent is not None:
        raw_params = parent.get("layoutlab_params") if hasattr(parent, "get") else None
        if raw_params:
            try:
                params = json.loads(raw_params)
                name = params.get("name")
                if name:
                    return str(name)
            except (TypeError, json.JSONDecodeError):
                pass
        pname = getattr(parent, "name", "") or ""
        if pname.endswith("_body"):
            return pname[: -len("_body")]
        return pname or clearance_obj.name
    name = clearance_obj.name
    if name.endswith("_clearance_front_access"):
        return name[: -len("_clearance_front_access")]
    return name


def violation_message(requirement, clearance_name, furniture_name):
    labels = {
        "required": "Required",
        "preferred": "Preferred",
        "informational": "Informational",
    }
    req = (requirement or "preferred").strip().lower()
    label = labels.get(req, "Clearance")
    return f"{label} clearance '{clearance_name}' on {furniture_name} is blocked"


def is_clearance_object(obj):
    return bool(obj.get("layoutlab_clearance_name"))


def is_blocker_mesh(obj):
    return is_analyze_blocker(
        getattr(obj, "type", None),
        role=obj.get("layoutlab_role", "") or "",
        has_clearance_name=bool(obj.get("layoutlab_clearance_name")),
    )


def blocker_overlap_entry(obj):
    return {
        "object_name": obj.name,
        "object_id": obj.get("layoutlab_object_id", ""),
        "part": obj.get("layoutlab_part", ""),
        "role": obj.get("layoutlab_role", ""),
    }


def analyze_clearance_objects(objects, *, get_world_bounds, scope="scene"):
    """Run zone_must_be_clear on a list of duck-typed objects.

    Each object needs: ``name``, ``type``, ``get(key)``, optional ``parent``.
    ``get_world_bounds(obj)`` → ``{"min": [...], "max": [...]}``.
    """
    clearances = [obj for obj in objects if is_clearance_object(obj)]
    blockers = [obj for obj in objects if is_blocker_mesh(obj)]

    findings = []
    for clearance in clearances:
        clearance_bounds = get_world_bounds(clearance)
        owner_id = clearance.get("layoutlab_object_id", "")
        clearance_name = clearance.get("layoutlab_clearance_name", "")
        requirement = clearance.get("layoutlab_clearance_requirement", "preferred")
        furniture_name = furniture_name_for_clearance(clearance)

        overlaps = []
        for blocker in blockers:
            if blocker is clearance:
                continue
            blocker_id = blocker.get("layoutlab_object_id", "")
            if owner_id and blocker_id and blocker_id == owner_id:
                continue
            blocker_bounds = get_world_bounds(blocker)
            if aabb_intersects(clearance_bounds, blocker_bounds):
                overlaps.append(blocker_overlap_entry(blocker))

        if overlaps:
            severity = requirement_to_severity(requirement)
            findings.append(
                {
                    "severity": severity,
                    "constraint_type": CONSTRAINT_TYPE_ZONE_MUST_BE_CLEAR,
                    "message": violation_message(requirement, clearance_name, furniture_name),
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
    severity_to_summary = {"error": "errors", "warning": "warnings", "info": "info"}
    for finding in findings:
        key = severity_to_summary.get(finding.get("severity", "warning"), "warnings")
        summary[key] += 1

    return {
        "analyzed": True,
        "scope": scope,
        "object_count": len(objects),
        "clearance_count": len(clearances),
        "summary": summary,
        "findings": findings,
    }
