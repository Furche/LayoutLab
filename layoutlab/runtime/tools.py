"""Deterministic agent read tools over RoomSession (agent_tools 0.1) — no bpy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..util import axis_aligned_bounds_from_points, infer_generator_meta_from_code
from .analyze import analyze_session, world_bounds_for_target
from .headless_api import bundled_generators_dir
from .mesh_store import MeshObject
from .session import SESSION_ACTIONS

TOOL_NAMES = frozenset(
    {
        "get_scene_summary",
        "get_room",
        "list_objects",
        "get_object",
        "get_analysis",
        "list_generators",
        "list_supported_actions",
    }
)

GENERATOR_KEY_PARAMS = {
    "bed_basic": ["name", "location", "length", "width", "head_side", "clearances", "collection"],
    "desk_basic": [
        "name",
        "location",
        "width",
        "depth",
        "height",
        "show_clearance",
        "clearance_depth",
        "collection",
    ],
    "wardrobe_basic": [
        "name",
        "location",
        "width",
        "depth",
        "height",
        "front_side",
        "show_clearance",
        "collection",
    ],
}


def _r(values):
    return [round(float(v), 4) for v in values]


def _bounds_dict(bounds):
    return {
        "min": _r(bounds.get("min", [0, 0, 0])),
        "max": _r(bounds.get("max", [0, 0, 0])),
    }


def _mesh_entry(obj: MeshObject):
    bounds = world_bounds_for_target(obj)
    dims = obj.dimensions()
    entry = {
        "name": obj.name,
        "object_id": obj.get("layoutlab_object_id") or "",
        "role": obj.get("layoutlab_role") or "",
        "part": obj.get("layoutlab_part") or "",
        "generator": obj.get("layoutlab_generator") or "",
        "collection": obj.collection or "",
        "world_bounds": _bounds_dict(bounds),
        "dimensions": _r(dims),
    }
    if obj.get("layoutlab_clearance_name"):
        entry["clearance_name"] = obj.get("layoutlab_clearance_name")
        entry["requirement"] = obj.get("layoutlab_clearance_requirement") or "preferred"
    return entry


def _parse_params_json(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def get_scene_summary(session, params=None):
    params = params or {}
    collection = params.get("collection")
    rooms_out = []
    for model in session._rooms.values():
        coll = model.get("collection") or "layoutlab_room"
        if collection and coll != collection:
            continue
        fp = model.get("footprint") or {}
        rooms_out.append(
            {
                "room_id": model.get("room_id"),
                "name": model.get("name"),
                "collection": coll,
                "width": fp.get("width"),
                "depth": fp.get("depth"),
                "height": model.get("height"),
                "opening_count": len(model.get("openings") or []),
                "fixed_count": len(model.get("fixed_elements") or []),
            }
        )

    furniture = clearances = walls = other = 0
    generators = set()
    for obj in session.mesh_store.objects:
        if collection and obj.collection != collection:
            continue
        role = obj.get("layoutlab_role") or ""
        if role == "clearance" or obj.get("layoutlab_clearance_name"):
            clearances += 1
        elif obj.get("layoutlab_generator"):
            furniture += 1
            generators.add(obj.get("layoutlab_generator"))
        elif role == "room_wall":
            walls += 1
        elif obj.type == "FONT" or role == "label":
            other += 1
        else:
            other += 1

    # Wall panels are not mesh_store objects — count from rooms for summary honesty
    if not walls:
        for model in session._rooms.values():
            coll = model.get("collection") or "layoutlab_room"
            if collection and coll != collection:
                continue
            walls += len(model.get("walls") or [])

    analysis = analyze_session(
        session,
        {
            "scope": "collection" if collection else "scene",
            "collection": collection,
            "include": ["clearances"],
        },
    )
    return {
        "ok": True,
        "unit": "METRIC",
        "unit_scale": 1.0,
        "rooms": rooms_out,
        "object_counts": {
            "furniture": furniture,
            "clearances": clearances,
            "walls": walls,
            "other": other,
        },
        "generators_present": sorted(generators),
        "analysis": {
            "analyzed": analysis.get("analyzed"),
            "summary": analysis.get("summary"),
            "findings_count": len(analysis.get("findings") or []),
        },
    }


def get_room(session, params=None):
    params = params or {}
    room_ref = params.get("room") or params.get("room_id") or params.get("name")
    if not room_ref:
        raise ValueError("get_room requires room (name or room_id)")
    include = set(params.get("include") or ["openings", "fixed", "walls_meta"])

    model = None
    if room_ref in session._rooms:
        model = session._rooms[room_ref]
    else:
        model = session.get_by_name(str(room_ref))
    if not model:
        raise ValueError(f"room not found: {room_ref}")

    from ..core.room import room_world_bounds

    room = {
        "room_id": model["room_id"],
        "name": model["name"],
        "origin": list(model.get("origin") or [0, 0, 0]),
        "height": model.get("height"),
        "wall_thickness": model.get("wall_thickness"),
        "footprint": dict(model.get("footprint") or {}),
        "collection": model.get("collection") or "layoutlab_room",
        "world_bounds": room_world_bounds(model),
    }
    if "walls_meta" in include:
        room["walls_meta"] = [
            {
                "side": w.get("side"),
                "length": w.get("length"),
                "wall_id": w.get("wall_id"),
                "height": w.get("height"),
            }
            for w in model.get("walls") or []
        ]
    if "openings" in include:
        room["openings"] = [
            {
                "name": o.get("name"),
                "kind": o.get("kind"),
                "wall_side": o.get("wall_side"),
                "wall_id": o.get("wall_id"),
                "offset": o.get("offset"),
                "width": o.get("width"),
                "height": o.get("height"),
                "sill_height": o.get("sill_height", 0.0),
            }
            for o in model.get("openings") or []
        ]
    if "fixed" in include:
        room["fixed_elements"] = [
            {
                "name": f.get("name"),
                "kind": f.get("kind"),
                "wall_side": f.get("wall_side"),
                "wall_id": f.get("wall_id"),
                "offset": f.get("offset"),
                "width": f.get("width"),
                "depth": f.get("depth"),
                "height": f.get("height"),
            }
            for f in model.get("fixed_elements") or []
        ]
    return {"ok": True, "room": room}


def list_objects(session, params=None):
    params = params or {}
    collection = params.get("collection")
    roles = set(params.get("roles") or [])
    generators = set(params.get("generators") or [])
    limit = int(params.get("limit") or 50)
    limit = max(1, min(limit, 200))

    out = []
    for obj in session.mesh_store.objects:
        if obj.type == "FONT" or (obj.get("layoutlab_role") or "") == "label":
            continue
        if collection and obj.collection != collection:
            continue
        role = obj.get("layoutlab_role") or ""
        gen = obj.get("layoutlab_generator") or ""
        if roles and role not in roles and not (
            "clearance" in roles and obj.get("layoutlab_clearance_name")
        ):
            continue
        if generators and gen not in generators:
            continue
        out.append(_mesh_entry(obj))
        if len(out) >= limit:
            break
    return {"ok": True, "objects": out, "count": len(out)}


def get_object(session, params=None):
    params = params or {}
    object_id = params.get("object_id")
    name = params.get("name")
    if not object_id and not name:
        raise ValueError("get_object requires object_id or name")

    found = None
    for obj in session.mesh_store.objects:
        if object_id and obj.get("layoutlab_object_id") == object_id:
            # Prefer main/body if multiple share id — return exact name match first later
            if name and obj.name != name:
                if found is None:
                    found = obj
                continue
            found = obj
            if not name or obj.name == name:
                break
        elif name and obj.name == name:
            found = obj
            break
    if not found and object_id:
        for obj in session.mesh_store.objects:
            if obj.get("layoutlab_object_id") == object_id:
                found = obj
                break
    if not found:
        raise ValueError(f"object not found: {object_id or name}")

    entry = _mesh_entry(found)
    entry["params"] = _parse_params_json(found.get("layoutlab_params"))
    clearances = []
    oid = found.get("layoutlab_object_id")
    for obj in session.mesh_store.objects:
        if not obj.get("layoutlab_clearance_name"):
            continue
        if oid and obj.get("layoutlab_object_id") == oid:
            clearances.append(
                {
                    "clearance_name": obj.get("layoutlab_clearance_name"),
                    "requirement": obj.get("layoutlab_clearance_requirement") or "preferred",
                    "world_bounds": _bounds_dict(world_bounds_for_target(obj)),
                    "name": obj.name,
                }
            )
    entry["clearances"] = clearances
    parent = found.parent
    entry["parent_object_id"] = parent.get("layoutlab_object_id") if parent else None
    entry["parent_name"] = parent.name if parent else None
    return {"ok": True, "object": entry}


def get_analysis(session, params=None):
    params = params or {}
    scope = params.get("scope") or "scene"
    collection = params.get("collection")
    # refresh ignored for now — always live on headless session
    result = analyze_session(
        session,
        {"scope": scope, "collection": collection, "include": ["clearances"]},
    )
    result["ok"] = True
    return result


def list_generators(session, params=None):
    params = params or {}
    names_filter = params.get("names")
    names_filter = set(names_filter) if names_filter else None
    gens = []
    root = bundled_generators_dir()
    if root.is_dir():
        for path in sorted(root.glob("*.py")):
            if names_filter and path.stem not in names_filter:
                continue
            code = path.read_text(encoding="utf-8")
            meta = infer_generator_meta_from_code(code, path)
            name = meta.get("name") or path.stem
            gens.append(
                {
                    "name": name,
                    "category": meta.get("category") or "",
                    "description": meta.get("description") or "",
                    "version": meta.get("version") or "",
                    "key_params": GENERATOR_KEY_PARAMS.get(name, ["name", "location", "collection"]),
                }
            )
    return {"ok": True, "generators": gens}


def list_supported_actions(session, params=None):
    return {
        "ok": True,
        "actions": sorted(SESSION_ACTIONS),
        "note": "Mutating actions must go through proposal.commands → Apply (/v1/commands).",
    }


TOOL_HANDLERS = {
    "get_scene_summary": get_scene_summary,
    "get_room": get_room,
    "list_objects": list_objects,
    "get_object": get_object,
    "get_analysis": get_analysis,
    "list_generators": list_generators,
    "list_supported_actions": list_supported_actions,
}


def openai_tool_definitions():
    """OpenAI-compatible tool schemas for agent turn."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_scene_summary",
                "description": "Cheap scene seed: rooms, object counts, analysis summary. Call first.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "Optional collection filter"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_room",
                "description": "Room footprint, openings, fixed elements, wall meta (no meshes).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "room": {"type": "string", "description": "Room name or room_id"},
                        "include": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "openings | fixed | walls_meta",
                        },
                    },
                    "required": ["room"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_objects",
                "description": "List furniture/clearance objects with world bounds.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "roles": {"type": "array", "items": {"type": "string"}},
                        "generators": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_object",
                "description": "One object with params and related clearances.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "object_id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_analysis",
                "description": "Run or return clearance analysis findings (DD-008).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string", "enum": ["scene", "collection"]},
                        "collection": {"type": "string"},
                        "refresh": {"type": "boolean"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_generators",
                "description": "Bundled generators and key params (no source code).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "names": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_supported_actions",
                "description": "Allowlisted LayoutLab command actions for proposals.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


def dispatch_tool(session, name: str, params: dict | None = None) -> dict:
    if name not in TOOL_HANDLERS:
        raise ValueError(f"unknown tool: {name!r}")
    return TOOL_HANDLERS[name](session, params or {})
