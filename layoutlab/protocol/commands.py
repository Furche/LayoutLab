import json
import math
import traceback

import bpy

from ..api.clearance import create_clearance
from ..api.collections import delete_collection_objects, delete_prefix, delete_by_object_id, find_objects_by_object_id
from ..api.geometry import create_box
from ..engine.executor import execute_generator
from ..engine.registry import generator_path, save_generator_code
from ..protocol.semantic import merge_generator_params
from ..util import parse_commands_payload, sanitize_generator_name


def _resolve_object_id(cmd):
    object_id = cmd.get("object_id")
    if object_id:
        return object_id
    ref_name = cmd.get("object") or cmd.get("name")
    if not ref_name:
        return None
    ref = bpy.data.objects.get(ref_name)
    if not ref:
        raise ValueError(f"Object not found: {ref_name}")
    object_id = ref.get("layoutlab_object_id")
    if not object_id:
        raise ValueError(
            f"Object '{ref_name}' has no layoutlab_object_id (legacy object — use delete_prefix + run_generator)"
        )
    return object_id


def _regenerate_object(cmd):
    object_id = _resolve_object_id(cmd)
    if not object_id:
        raise ValueError("regenerate requires object_id or object with layoutlab_object_id")

    components = find_objects_by_object_id(object_id)
    if not components:
        raise ValueError(f"No objects found for object_id: {object_id}")

    first = components[0]
    generator = first.get("layoutlab_generator")
    if not generator:
        raise ValueError("Object has no layoutlab_generator metadata")

    raw_params = first.get("layoutlab_params") or "{}"
    try:
        stored = json.loads(raw_params)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid layoutlab_params on object: {exc}") from exc

    merged = merge_generator_params(stored, cmd.get("params", {}))
    delete_by_object_id(object_id)
    result = execute_generator(generator, merged, object_id=object_id)
    return {
        "regenerated": merged.get("name", ""),
        "object_id": object_id,
        "generator": generator,
        "params": merged,
        **(result if isinstance(result, dict) else {}),
    }


def get_commands_text(context):
    scene = context.scene
    if scene.layoutlab_command_source == "TEXT":
        txt = bpy.data.texts.get(scene.layoutlab_text_block_name)
        if not txt:
            raise ValueError(f"Text block not found: {scene.layoutlab_text_block_name}")
        return txt.as_string()
    return context.window_manager.clipboard


def apply_single_command(context, cmd):
    from ..plugin.properties import refresh_browser_items

    action = cmd.get("action")
    name = cmd.get("object") or cmd.get("name")

    if action == "run_generator":
        return execute_generator(cmd["generator"], cmd.get("params", {}))
    if action == "regenerate":
        return _regenerate_object(cmd)
    if action == "save_generator":
        gen_name, p = save_generator_code(cmd.get("code", ""))
        return {"saved_generator": gen_name, "path": str(p)}
    if action == "delete_generator":
        gen_name = sanitize_generator_name(cmd["generator"])
        p = generator_path(gen_name)
        if p.exists():
            p.unlink()
        refresh_browser_items(bpy.context)
        return {"deleted_generator": gen_name}
    if action == "create_box":
        return create_box(cmd["name"], cmd.get("location", [0,0,0]), cmd.get("dimensions", [1,1,1]),
                          color=cmd.get("color", [0.8,0.8,0.8,1]), collection=cmd.get("collection", "layout_tests"),
                          role=cmd.get("role"), display_type=cmd.get("display_type"))
    if action == "create_clearance":
        dims = cmd.get("dimensions", [1, 1, 0.1])
        loc = cmd.get("location", [0, 0, 0])
        return create_clearance(
            cmd["name"],
            dims,
            location=loc,
            clearance_name=cmd.get("clearance_name", cmd.get("name", "zone")),
            purpose=cmd.get("purpose", ""),
            requirement=cmd.get("requirement", "preferred"),
            priority=cmd.get("priority", 0),
            params=cmd.get("params"),
            color=tuple(cmd.get("color", [0.2, 0.8, 1.0, 0.22])),
            collection=cmd.get("collection", "layout_tests"),
            display_type=cmd.get("display_type", "WIRE"),
        )
    if action == "delete_collection_objects":
        return delete_collection_objects(cmd["collection"])
    if action == "delete_prefix":
        return delete_prefix(cmd["prefix"])

    obj = bpy.data.objects.get(name) if name else None
    if action == "move":
        if not obj: raise ValueError(f"Object not found: {name}")
        obj.location = cmd["location"]
    elif action == "rotate_z":
        if not obj: raise ValueError(f"Object not found: {name}")
        obj.rotation_euler.z = math.radians(float(cmd["degrees"]))
    elif action == "delete":
        if obj: bpy.data.objects.remove(obj, do_unlink=True)
    elif action == "hide":
        if not obj: raise ValueError(f"Object not found: {name}")
        obj.hide_viewport = True
        obj.hide_render = True
    elif action == "show":
        if not obj: raise ValueError(f"Object not found: {name}")
        obj.hide_viewport = False
        obj.hide_render = False
    else:
        raise ValueError(f"Unknown action: {action}")


def apply_commands_json(context, text):
    commands = parse_commands_payload(text)
    results = []
    errors = []
    for i, cmd in enumerate(commands):
        try:
            result = apply_single_command(context, cmd)
            if result is not None:
                results.append(result)
        except Exception as e:
            errors.append(f"Command {i}: {e}\n{traceback.format_exc()}")
    return results, errors
