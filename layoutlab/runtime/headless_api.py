"""Headless generator API + PartSession (DD-014 Phase B2) — no bpy."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

from ..api.metadata import (
    activate_context,
    apply_layoutlab_metadata,
    build_object_context,
    deactivate_context,
    get_active_context,
)
from ..util import (
    infer_generator_meta_from_code,
    relative_translation_from_locations,
    resolve_clearance_locations,
    sanitize_generator_name,
    validate_clearance_requirement,
)
from .mesh_store import BOX_FACES, MeshObject, MeshStore, box_local_verts, join_mesh_objects

DEFAULT_CLEARANCE_COLOR = (0.2, 0.8, 1.0, 0.22)

_active_session = None


class PartDraft:
    __slots__ = ("part_id", "main", "dynamic", "role", "objects")

    def __init__(self, part_id, main, dynamic, role):
        self.part_id = part_id
        self.main = bool(main)
        self.dynamic = bool(dynamic)
        self.role = role
        self.objects = []


class FinalizedPart:
    __slots__ = ("part_id", "main", "dynamic", "role", "object")

    def __init__(self, part_id, main, dynamic, role, obj):
        self.part_id = part_id
        self.main = main
        self.dynamic = dynamic
        self.role = role
        self.object = obj


class HeadlessPartSession:
    def __init__(self, furniture_prefix, collection, store: MeshStore):
        self.furniture_prefix = furniture_prefix
        self.collection = collection
        self.store = store
        self.current = None
        self.parts = []
        self.finished = False
        self.summary = {}

    def part_object_name(self, part_id):
        return f"{self.furniture_prefix}_{part_id}"

    def begin_part(self, part_id, main=False, dynamic=False, role=None):
        if self.current and self.current.objects:
            self.end_part()
        elif self.current:
            self.current = None
        self.current = PartDraft(part_id, main, dynamic, role)

    def add_object(self, obj):
        if not self.current:
            raise RuntimeError("create_box/create_label called without begin_part() — start a part first.")
        self.current.objects.append(obj)

    def end_part(self):
        if not self.current:
            return None
        draft = self.current
        self.current = None
        if not draft.objects:
            return None
        final_name = self.part_object_name(draft.part_id)
        # Remove draft pieces from store; joined result is re-added
        for obj in draft.objects:
            self.store.remove(obj)
        obj = join_mesh_objects(draft.objects, final_name, self.collection)
        if obj:
            self.store.add(obj)
            self.parts.append(FinalizedPart(draft.part_id, draft.main, draft.dynamic, draft.role, obj))
        return obj

    def finish(self):
        if self.finished:
            return self.summary
        if self.current and self.current.objects:
            self.end_part()

        main_obj = None
        for part in self.parts:
            if part.main:
                main_obj = part.object
                break
        if main_obj is None and self.parts:
            main_obj = self.parts[0].object

        for part in self.parts:
            obj = part.object
            meta = get_active_context()
            part_type = "main" if part.main else ("dynamic" if part.dynamic else "static")
            if meta:
                apply_layoutlab_metadata(
                    obj,
                    meta,
                    component=part.part_id,
                    role=part.role or obj.get("layoutlab_role"),
                    part=part.part_id,
                    part_type=part_type,
                )
            else:
                obj["layoutlab_part"] = part.part_id
                obj["layoutlab_part_type"] = part_type
                if part.role:
                    obj["layoutlab_role"] = part.role

            if main_obj and obj != main_obj:
                rel = relative_translation_from_locations(obj.location, main_obj.location)
                obj.parent = main_obj
                obj.location.x, obj.location.y, obj.location.z = rel

            if obj.get("layoutlab_clearance_name") or part.role == "clearance":
                obj.display_type = "WIRE"
                obj.show_in_front = True

        self.summary = {
            "parts": [p.part_id for p in self.parts],
            "main_part": main_obj.name if main_obj else "",
            "object_count": len(self.parts),
        }
        self.finished = True
        return self.summary


def activate_session(session):
    global _active_session
    _active_session = session


def deactivate_session():
    global _active_session
    _active_session = None


def get_active_session():
    return _active_session


def begin_part(part_id, main=False, dynamic=False, role=None):
    session = get_active_session()
    if session is None:
        raise RuntimeError("Part session not active — generate() must run via execute_generator_headless().")
    session.begin_part(part_id, main=main, dynamic=dynamic, role=role)
    return part_id


def end_part():
    session = get_active_session()
    if session is None:
        raise RuntimeError("Part session not active.")
    return session.end_part()


def finish():
    session = get_active_session()
    if session is None:
        raise RuntimeError("Part session not active.")
    return session.finish()


def _register(obj):
    session = get_active_session()
    if session and session.current:
        session.add_object(obj)
        return True
    return False


def create_box(name, location, dimensions, color=(0.8, 0.8, 0.8, 1), collection="layout_tests", role=None, display_type=None, component=None):
    lx, ly, lz = [float(v) for v in location]
    dx, dy, dz = [float(v) for v in dimensions]
    obj = MeshObject(
        name,
        location=(lx, ly, lz),
        vertices=box_local_verts(dx, dy, dz),
        faces=list(BOX_FACES),
        collection=collection,
        display_type=display_type,
        color=color,
    )
    if role and not get_active_context():
        obj["layoutlab_role"] = role
    session = get_active_session()
    store = session.store if session else None
    if store is not None:
        store.add(obj)
    if _register(obj):
        return obj
    if get_active_context() and role:
        obj["layoutlab_role"] = role
    return obj


def create_label(name, location, text, collection="layout_tests", size=0.35, component=None):
    obj = MeshObject(
        name,
        location=location,
        obj_type="FONT",
        collection=collection,
        text=str(text),
    )
    obj["layoutlab_role"] = "label"
    session = get_active_session()
    if session is not None:
        session.store.add(obj)
    if _register(obj):
        return obj
    return obj


def _main_part_location():
    session = get_active_session()
    if not session:
        return None
    for part in session.parts:
        if part.main and part.object:
            loc = part.object.location
            return (float(loc.x), float(loc.y), float(loc.z))
    return None


def create_clearance(
    name,
    dimensions,
    *,
    location=None,
    local_location=None,
    clearance_name,
    purpose="",
    requirement="preferred",
    priority=0,
    params=None,
    color=DEFAULT_CLEARANCE_COLOR,
    collection="layout_tests",
    display_type="WIRE",
):
    if not clearance_name or not str(clearance_name).strip():
        raise ValueError("create_clearance requires clearance_name")

    requirement = validate_clearance_requirement(requirement)
    dims = tuple(float(v) for v in dimensions)
    world, local = resolve_clearance_locations(
        local_location=local_location,
        world_location=location,
        main_location=_main_part_location(),
    )
    clearance_id = str(uuid.uuid4())

    obj = create_box(
        name,
        world,
        dims,
        color=color,
        collection=collection,
        role="clearance",
        display_type=display_type,
    )
    obj.show_in_front = True
    obj["layoutlab_role"] = "clearance"
    obj["layoutlab_clearance_id"] = clearance_id
    obj["layoutlab_clearance_name"] = str(clearance_name).strip()
    if purpose:
        obj["layoutlab_clearance_purpose"] = str(purpose).strip()
    obj["layoutlab_clearance_requirement"] = requirement
    obj["layoutlab_clearance_priority"] = int(priority)
    payload = dict(params or {})
    payload["local_transform"] = {
        "location": [float(v) for v in local],
        "rotation": [0.0, 0.0, 0.0],
        "dimensions": [float(v) for v in dims],
        "shape": "box",
    }
    obj["layoutlab_clearance_params"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return obj


def get_or_create_collection(name):
    return name


def delete_collection_objects(collection_name):
    session = get_active_session()
    if session is None:
        return {"deleted": 0}
    n = session.store.delete_collection(collection_name)
    return {"deleted": n, "collection": collection_name}


def delete_prefix(prefix):
    session = get_active_session()
    if session is None:
        return {"deleted": 0}
    n = session.store.delete_prefix(prefix)
    return {"deleted": n, "prefix": prefix}


def ensure_material(name, color, backface_culling=False):
    return name


def build_headless_api():
    return {
        "bpy": None,
        "math": math,
        "begin_part": begin_part,
        "end_part": end_part,
        "finish": finish,
        "create_box": create_box,
        "create_clearance": create_clearance,
        "create_label": create_label,
        "delete_collection_objects": delete_collection_objects,
        "delete_prefix": delete_prefix,
        "get_or_create_collection": get_or_create_collection,
        "ensure_material": ensure_material,
    }


def bundled_generators_dir():
    return Path(__file__).resolve().parent.parent / "generators"


def load_bundled_generator_source(name):
    path = bundled_generators_dir() / f"{sanitize_generator_name(name)}.py"
    if not path.exists():
        raise FileNotFoundError(f"Bundled generator not found: {name}")
    return path.read_text(encoding="utf-8")


def execute_generator_headless(name, params=None, object_id=None, store: MeshStore | None = None):
    """Run a bundled generator against a MeshStore (no bpy)."""
    name = sanitize_generator_name(name)
    params = dict(params or {})
    gen_code = load_bundled_generator_source(name)
    gen_meta = infer_generator_meta_from_code(gen_code)
    if not object_id:
        object_id = str(uuid.uuid4())

    if store is None:
        store = MeshStore()

    meta_context = build_object_context(
        name,
        gen_meta.get("version", ""),
        params,
        object_id,
    )
    furniture_prefix = params.get("name", "OBJ")
    collection = params.get("collection", "layout_tests")
    part_session = HeadlessPartSession(furniture_prefix, collection, store)

    namespace = {"__name__": f"layoutlab_generator_{name}", "math": math}
    exec(gen_code, namespace)
    generate = namespace.get("generate")
    if not callable(generate):
        raise ValueError(f"Generator '{name}' has no callable generate(params, api).")

    activate_context(meta_context)
    activate_session(part_session)
    try:
        result = generate(params, build_headless_api())
        part_summary = part_session.finish()
    finally:
        deactivate_session()
        deactivate_context()

    payload = {
        "object_id": object_id,
        "generator": name,
        "parts": part_summary.get("parts", []),
        "main_part": part_summary.get("main_part", ""),
        "part_object_count": part_summary.get("object_count", 0),
    }
    if isinstance(result, dict):
        return {**result, **payload}
    return payload
