"""Slim viewer payloads for shortlist 3D thumbnails (DD-017)."""

from __future__ import annotations

from typing import Any

from ...protocol.viewer_export import VIEWER_SCHEMA


def slim_viewer_preview(export: dict | None) -> dict[str, Any] | None:
    """AABB/quad-only export for card thumbnails — drop mesh verts/faces + analysis."""
    if not isinstance(export, dict):
        return None
    rooms_out = []
    for room in export.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        rooms_out.append(
            {
                "room_id": room.get("room_id"),
                "name": room.get("name"),
                "height": room.get("height"),
                "footprint": room.get("footprint"),
                "walls": room.get("walls") or [],
                "openings": room.get("openings") or [],
                "fixed_elements": room.get("fixed_elements") or [],
            }
        )
    objects_out = []
    for obj in export.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        role = (
            (obj.get("layoutlab") or {}).get("role")
            if isinstance(obj.get("layoutlab"), dict)
            else None
        ) or (obj.get("custom_properties") or {}).get("layoutlab_role")
        if role in ("label", "clearance"):
            continue
        viewer = obj.get("viewer") if isinstance(obj.get("viewer"), dict) else {}
        slim_viewer: dict[str, Any] = {}
        prim = viewer.get("primitive")
        if prim == "quad" and viewer.get("corners"):
            slim_viewer = {"primitive": "quad", "corners": viewer.get("corners")}
        elif prim == "mesh" or prim == "box" or not prim:
            # Prefer AABB box for furniture; keep wire display for clearances/openings
            slim_viewer = {"primitive": "box"}
        if viewer.get("display") == "wire":
            slim_viewer["display"] = "wire"
            slim_viewer["primitive"] = slim_viewer.get("primitive") or "box"
            slim_viewer.pop("corners", None)
        entry: dict[str, Any] = {
            "name": obj.get("name"),
            "type": obj.get("type") or "MESH",
            "location": obj.get("location"),
            "dimensions": obj.get("dimensions"),
            "world_bbox_corners": obj.get("world_bbox_corners"),
        }
        if isinstance(obj.get("layoutlab"), dict):
            entry["layoutlab"] = {
                k: obj["layoutlab"].get(k)
                for k in ("role", "object_id", "generator", "collection")
                if obj["layoutlab"].get(k) is not None
            }
        if slim_viewer:
            entry["viewer"] = slim_viewer
        objects_out.append(entry)
    if not rooms_out and not objects_out:
        return None
    return {
        "viewer_schema": export.get("viewer_schema") or VIEWER_SCHEMA,
        "rooms": rooms_out,
        "objects": objects_out,
    }
