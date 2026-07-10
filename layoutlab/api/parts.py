"""Part-based generator session: Furniture → Parts → Meshes → finalized Blender objects."""

import bpy

from .collections import get_or_create_collection
from .metadata import apply_layoutlab_metadata, get_active_context
from .transforms import parent_preserve_world_transform

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


class PartSession:
    def __init__(self, furniture_prefix, collection):
        self.furniture_prefix = furniture_prefix
        self.collection = collection
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
        obj = finalize_part_objects(draft.objects, final_name, self.collection)
        if obj:
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
                parent_preserve_world_transform(obj, main_obj)

        view_layer = bpy.context.view_layer
        if view_layer:
            view_layer.update()

        self.summary = {
            "parts": [p.part_id for p in self.parts],
            "main_part": main_obj.name if main_obj else "",
            "object_count": len(self.parts),
        }
        self.finished = True
        return self.summary


def finalize_part_objects(objects, result_name, collection):
    meshes = [o for o in objects if o.type == "MESH"]
    others = [o for o in objects if o.type != "MESH"]

    if not meshes and len(others) == 1:
        others[0].name = result_name
        return others[0]

    if len(meshes) == 1 and not others:
        meshes[0].name = result_name
        return meshes[0]

    if not meshes:
        return None

    meshes = sorted(meshes, key=lambda o: (o.location.x, o.location.y, o.location.z))

    view_layer = bpy.context.view_layer
    for obj in bpy.context.scene.objects:
        obj.select_set(False)

    for obj in meshes:
        obj.select_set(True)
    view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    joined = view_layer.objects.active
    joined.name = result_name

    for obj in others:
        bpy.data.objects.remove(obj, do_unlink=True)

    col = get_or_create_collection(collection)
    if joined.name not in col.objects:
        col.objects.link(joined)

    return joined


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
        raise RuntimeError("Part session not active — generate() must run via execute_generator().")
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


def register_created_object(obj):
    session = get_active_session()
    if session and session.current:
        session.add_object(obj)
        return True
    return False
