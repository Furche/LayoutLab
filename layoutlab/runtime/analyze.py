"""Headless analyze_layout over RoomSession (DD-014) — no bpy."""

from __future__ import annotations

from ..core import room as room_core
from ..core.analyze import analyze_clearance_objects
from ..util import axis_aligned_bounds_from_points
from .mesh_store import MeshObject


def _round_corner(corner):
    return [round(float(corner[0]), 4), round(float(corner[1]), 4), round(float(corner[2]), 4)]


class RoomProxy:
    """Duck-typed analyze target for room display geometry."""

    __slots__ = ("name", "type", "collection", "props", "bounds", "parent")

    def __init__(self, name, role, room_id, collection, bounds, entity_id=None):
        self.name = name
        self.type = "MESH"
        self.collection = collection
        self.parent = None
        self.bounds = bounds
        self.props = {
            "layoutlab_role": role,
            "layoutlab_object_id": room_id,
            "layoutlab_room_id": room_id,
        }
        if entity_id:
            self.props["layoutlab_room_entity_id"] = entity_id

    def get(self, key, default=None):
        return self.props.get(key, default)


def world_bounds_for_target(obj):
    if isinstance(obj, RoomProxy):
        return obj.bounds
    if isinstance(obj, MeshObject):
        return axis_aligned_bounds_from_points(
            [_round_corner(c) for c in obj.world_bbox_corners()]
        )
    raise TypeError(f"unsupported analyze target: {type(obj)!r}")


def _bounds_from_loc_dims(loc, dims):
    x, y, z = (float(v) for v in loc)
    dx, dy, dz = (float(v) for v in dims)
    return {
        "min": _round_corner([x, y, z]),
        "max": _round_corner([x + dx, y + dy, z + dz]),
    }


def room_analyze_proxies(model):
    """Wall panels + fixed elements as blockers; floor/openings omitted via role."""
    collection = model.get("collection") or "layoutlab_room"
    room_id = model["room_id"]
    prefix = f"{model['name']}_"
    proxies = []

    for wall in model.get("walls", []):
        panels = room_core.wall_display_panels(model, wall)
        for index, panel in enumerate(panels):
            corners = [_round_corner(c) for c in panel["corners"]]
            name = (
                f"{prefix}wall_{wall['side']}"
                if len(panels) == 1
                else f"{prefix}wall_{wall['side']}_p{index}"
            )
            proxies.append(
                RoomProxy(
                    name,
                    "room_wall",
                    room_id,
                    collection,
                    axis_aligned_bounds_from_points(corners),
                    entity_id=wall.get("wall_id"),
                )
            )

    for fixed in model.get("fixed_elements", []):
        loc, dims = room_core.fixed_element_world_box(model, fixed)
        proxies.append(
            RoomProxy(
                f"{prefix}fixed_{fixed['name']}",
                "room_fixed",
                room_id,
                collection,
                _bounds_from_loc_dims(loc, dims),
                entity_id=fixed.get("fixed_element_id"),
            )
        )

    return proxies


def collect_session_objects(session, scope="scene", collection_name=None):
    if scope == "selection":
        raise ValueError("analyze_layout scope=selection is not supported headless")
    if scope not in ("scene", "collection"):
        raise ValueError(f"Unknown analyze_layout scope: {scope!r}")

    objects = []
    for model in session._rooms.values():
        if not bool(model.get("included_in_analysis", True)):
            continue
        coll = model.get("collection") or "layoutlab_room"
        if scope == "collection" and coll != collection_name:
            continue
        objects.extend(room_analyze_proxies(model))

    for obj in session.mesh_store.objects:
        if scope == "collection" and obj.collection != collection_name:
            continue
        # Skip furniture whose room opted out of analysis.
        rid = obj.get("layoutlab_room_id") if hasattr(obj, "get") else None
        if rid and rid in session._rooms:
            if not bool(session._rooms[rid].get("included_in_analysis", True)):
                continue
        objects.append(obj)

    if scope == "collection" and not collection_name:
        raise ValueError("analyze_layout with scope=collection requires collection")

    return objects


def analyze_session(session, cmd=None):
    cmd = cmd or {}
    scope = cmd.get("scope", "scene")
    collection_name = cmd.get("collection")
    include = cmd.get("include")
    if include is None:
        include_set = {"clearances", "soft"}
    else:
        include_set = set(include)
    unknown = include_set - {"clearances", "soft"}
    if unknown:
        raise ValueError(f"analyze_layout unknown include entries: {sorted(unknown)}")

    from ..core.soft_metrics import analyze_soft_metrics, soft_summary_from_findings
    from ..core.solid_collision import analyze_solid_wall_collisions

    findings = []
    clearance_count = 0
    object_count = 0

    if "clearances" in include_set:
        objects = collect_session_objects(session, scope=scope, collection_name=collection_name)
        object_count = len(objects)
        clearance_result = analyze_clearance_objects(
            objects,
            get_world_bounds=world_bounds_for_target,
            scope=scope,
        )
        findings.extend(clearance_result.get("findings") or [])
        clearance_count = clearance_result.get("clearance_count") or 0

    # Always run solid wall checks when analyzing a scene (hard, non-negotiable).
    if scope in ("scene", "collection"):
        solid = analyze_solid_wall_collisions(session)
        if scope == "collection" and collection_name:
            solid = [
                f
                for f in solid
                if any(
                    (m.get("collection") or "layoutlab_room") == collection_name
                    for m in session._rooms.values()
                )
            ]
        findings.extend(solid)

    if "soft" in include_set and scope in ("scene", "collection"):
        soft_findings = analyze_soft_metrics(session)
        if scope == "collection" and collection_name:
            soft_findings = [
                f
                for f in soft_findings
                if (
                    (f.get("metrics") or {}).get("room")
                    and any(
                        m.get("name") == (f.get("metrics") or {}).get("room")
                        and (m.get("collection") or "layoutlab_room") == collection_name
                        for m in session._rooms.values()
                    )
                )
                or (
                    f.get("constraint_type") == "opening_access"
                    and (f.get("opening_ref") or {}).get("collection") == collection_name
                )
            ]
        findings.extend(soft_findings)

    summary = {"errors": 0, "warnings": 0, "info": 0}
    severity_to_summary = {"error": "errors", "warning": "warnings", "info": "info"}
    for finding in findings:
        key = severity_to_summary.get(finding.get("severity", "warning"), "warnings")
        summary[key] += 1

    # Alias for viewers that expect overlaps[].name
    for finding in findings:
        for overlap in finding.get("overlaps") or []:
            if "name" not in overlap and overlap.get("object_name"):
                overlap["name"] = overlap["object_name"]

    result = {
        "analyzed": True,
        "scope": scope,
        "object_count": object_count,
        "clearance_count": clearance_count,
        "summary": summary,
        "findings": findings,
        "soft_summary": soft_summary_from_findings(findings),
        "include": sorted(include_set),
    }
    return result
