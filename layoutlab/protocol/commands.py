import json
import math
import traceback

import bpy

from ..api.geometry import create_box
from ..api.collections import delete_collection_objects, delete_prefix
from ..engine.executor import execute_generator
from ..engine.registry import generator_path, save_generator_code
from ..util import parse_commands_payload, sanitize_generator_name
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
        return create_box(cmd["name"], cmd.get("location", [0,0,0]), cmd.get("dimensions", [1,1,0.1]),
                          color=cmd.get("color", [0.2,0.8,1.0,0.22]), collection=cmd.get("collection", "layout_tests"),
                          role="clearance", display_type=cmd.get("display_type", "WIRE"))
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
