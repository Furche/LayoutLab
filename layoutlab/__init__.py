bl_info = {
    "name": "LayoutLab",
    "author": "ChatGPT / Alexander",
    "version": (0, 5, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > LayoutLab",
    "description": "Room layout JSON exchange with an asset-browser-like generator browser.",
    "category": "3D View",
}

import bpy
import json
import math
import traceback
from pathlib import Path
from mathutils import Vector

from .util import (
    infer_generator_meta_from_code,
    infer_generator_name_from_code,
    parse_commands_payload,
    sanitize_generator_name,
)


def addon_root_dir():
    return Path(__file__).resolve().parent


def addon_bundled_generators_dir():
    return addon_root_dir() / "generators"


def load_bundled_generator_source(name):
    path = addon_bundled_generators_dir() / f"{sanitize_generator_name(name)}.py"
    if not path.exists():
        raise FileNotFoundError(f"Bundled generator not found: {name}")
    return path.read_text(encoding="utf-8")


def default_generator_template():
    return load_bundled_generator_source("bed_basic")


def sync_bundled_generators():
    bundled_dir = addon_bundled_generators_dir()
    if not bundled_dir.is_dir():
        return
    for src in sorted(bundled_dir.glob("*.py")):
        dest = generator_path(src.stem)
        if not dest.exists():
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def addon_user_dir():
    base = Path(bpy.utils.user_resource("SCRIPTS", path="addons"))
    d = base / "layoutlab_generators"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generator_path(name):
    return addon_user_dir() / f"{sanitize_generator_name(name)}.py"


def list_generator_files():
    return sorted(addon_user_dir().glob("*.py"))


def list_generators_meta():
    metas = []
    for p in list_generator_files():
        try:
            metas.append(infer_generator_meta_from_code(p.read_text(encoding="utf-8"), p))
        except Exception:
            metas.append({"name": p.stem, "category": "Broken", "description": "Could not parse generator metadata.", "version": "", "icon": "ERROR", "path": str(p)})
    metas.sort(key=lambda m: (m["category"].lower(), m["name"].lower()))
    return metas


def read_generator_code(name):
    p = generator_path(name)
    if not p.exists():
        raise ValueError(f"Generator not found: {name}")
    return p.read_text(encoding="utf-8")


def save_generator_code(code):
    name = infer_generator_name_from_code(code)
    p = generator_path(name)
    p.write_text(code, encoding="utf-8")
    return name, p


def get_or_create_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def ensure_material(name, color):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    if len(color) == 4 and color[3] < 1.0:
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        mat.show_transparent_back = True
        try:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            bsdf.inputs["Alpha"].default_value = color[3]
        except Exception:
            pass
    return mat


def create_box(name, location, dimensions, color=(0.8, 0.8, 0.8, 1), collection="layout_tests", role=None, display_type=None):
    lx, ly, lz = [float(v) for v in location]
    dx, dy, dz = [float(v) for v in dimensions]
    mesh = bpy.data.meshes.new(name + "_mesh")
    verts = [(0,0,0),(dx,0,0),(dx,dy,0),(0,dy,0),(0,0,dz),(dx,0,dz),(dx,dy,dz),(0,dy,dz)]
    faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (lx, ly, lz)
    if color:
        obj.data.materials.append(ensure_material(f"MAT_{name}", color))
    if role:
        obj["layoutlab_role"] = role
    if display_type:
        obj.display_type = display_type
    get_or_create_collection(collection).objects.link(obj)
    return obj


def create_label(name, location, text, collection="layout_tests", size=0.35):
    curve = bpy.data.curves.new(name + "_curve", type="FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj["layoutlab_role"] = "label"
    get_or_create_collection(collection).objects.link(obj)
    return obj


def delete_collection_objects(collection_name):
    col = bpy.data.collections.get(collection_name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)


def delete_prefix(prefix):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix):
            bpy.data.objects.remove(obj, do_unlink=True)


def execute_generator(name, params):
    name = sanitize_generator_name(name)
    gen_code = read_generator_code(name)
    namespace = {"__name__": f"layoutlab_generator_{name}", "math": math, "bpy": bpy}
    exec(gen_code, namespace)
    generate = namespace.get("generate")
    if not callable(generate):
        raise ValueError(f"Generator '{name}' has no callable generate(params, api).")
    api = {
        "bpy": bpy,
        "math": math,
        "create_box": create_box,
        "create_label": create_label,
        "delete_collection_objects": delete_collection_objects,
        "delete_prefix": delete_prefix,
        "get_or_create_collection": get_or_create_collection,
        "ensure_material": ensure_material,
    }
    return generate(params or {}, api)


def v3(values):
    return [round(float(values[0]), 4), round(float(values[1]), 4), round(float(values[2]), 4)]


def object_to_dict(obj):
    world_corners = []
    if hasattr(obj, "bound_box"):
        world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "name": obj.name,
        "type": obj.type,
        "collection": obj.users_collection[0].name if obj.users_collection else "",
        "location": v3(obj.location),
        "rotation_euler_deg": [
            round(math.degrees(obj.rotation_euler.x), 3),
            round(math.degrees(obj.rotation_euler.y), 3),
            round(math.degrees(obj.rotation_euler.z), 3),
        ],
        "scale": v3(obj.scale),
        "dimensions": v3(obj.dimensions) if hasattr(obj, "dimensions") else [0, 0, 0],
        "visible": bool(obj.visible_get()),
        "world_bbox_corners": [v3(c) for c in world_corners],
        "custom_properties": {k: obj[k] for k in obj.keys() if isinstance(obj[k], (str, int, float, bool))},
    }


def layout_export_json(context, selected_only=False):
    scene = context.scene
    objs = context.selected_objects if selected_only else scene.objects
    data = {
        "layoutlab_version": "0.5.0",
        "unit": scene.unit_settings.system,
        "unit_scale": scene.unit_settings.scale_length,
        "scene": scene.name,
        "generator_dir": str(addon_user_dir()),
        "generators": list_generators_meta(),
        "note": "Coordinates/dimensions are Blender units. In Alexander's room: 1 unit ≈ 10 cm.",
        "objects": [object_to_dict(o) for o in objs if o.type in {"MESH", "EMPTY", "CURVE", "FONT"}],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def get_commands_text(context):
    scene = context.scene
    if scene.layoutlab_command_source == "TEXT":
        txt = bpy.data.texts.get(scene.layoutlab_text_block_name)
        if not txt:
            raise ValueError(f"Text block not found: {scene.layoutlab_text_block_name}")
        return txt.as_string()
    return context.window_manager.clipboard


def apply_single_command(context, cmd):
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


class LayoutLabGeneratorItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    category: bpy.props.StringProperty()
    description: bpy.props.StringProperty()
    version: bpy.props.StringProperty()
    icon_name: bpy.props.StringProperty()
    path: bpy.props.StringProperty()


def refresh_browser_items(context):
    scene = context.scene
    scene.layoutlab_generator_items.clear()
    filter_text = scene.layoutlab_generator_filter.lower().strip()
    category_filter = scene.layoutlab_category_filter.lower().strip()

    for meta in list_generators_meta():
        hay = f'{meta["name"]} {meta["category"]} {meta["description"]}'.lower()
        if filter_text and filter_text not in hay:
            continue
        if category_filter and category_filter != "all" and category_filter != meta["category"].lower():
            continue
        item = scene.layoutlab_generator_items.add()
        item.name = meta["name"]
        item.category = meta["category"]
        item.description = meta["description"]
        item.version = meta["version"]
        item.icon_name = meta["icon"]
        item.path = meta["path"]

    if scene.layoutlab_generator_index >= len(scene.layoutlab_generator_items):
        scene.layoutlab_generator_index = max(0, len(scene.layoutlab_generator_items) - 1)


class LAYOUTLAB_OT_copy_scene(bpy.types.Operator):
    bl_idname = "layoutlab.copy_scene"
    bl_label = "Copy Scene Layout"
    selected_only: bpy.props.BoolProperty(default=False)
    def execute(self, context):
        context.window_manager.clipboard = layout_export_json(context, self.selected_only)
        self.report({"INFO"}, "Layout JSON copied to clipboard.")
        return {"FINISHED"}


class LAYOUTLAB_OT_apply_commands(bpy.types.Operator):
    bl_idname = "layoutlab.apply_commands"
    bl_label = "Apply Commands"
    def execute(self, context):
        try:
            results, errors = apply_commands_json(context, get_commands_text(context))
            if results:
                print("LayoutLab results:")
                print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
            if errors:
                print("LayoutLab errors:")
                for e in errors: print(e)
                self.report({"WARNING"}, "Some commands failed. See console.")
            else:
                self.report({"INFO"}, "Commands applied.")
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class LAYOUTLAB_OT_create_command_text_block(bpy.types.Operator):
    bl_idname = "layoutlab.create_command_text_block"
    bl_label = "Create Command Text"
    def execute(self, context):
        name = context.scene.layoutlab_text_block_name
        txt = bpy.data.texts.get(name) or bpy.data.texts.new(name)
        if not txt.as_string().strip():
            txt.write('{\n  "commands": [\n    {"action":"delete_collection_objects", "collection":"layout_tests"},\n    {\n      "action":"run_generator",\n      "generator":"bed_basic",\n      "params":{\n        "name":"BED_120x200",\n        "location":[68.3,197.7,0],\n        "length":12,\n        "width":20,\n        "head_side":"y_max",\n        "collection":"layout_tests"\n      }\n    }\n  ]\n}\n')
        self.report({"INFO"}, f"Text block ready: {name}")
        return {"FINISHED"}


class LAYOUTLAB_OT_install_default_generator(bpy.types.Operator):
    bl_idname = "layoutlab.install_default_generator"
    bl_label = "Install bed_basic"
    def execute(self, context):
        gen_name, p = save_generator_code(load_bundled_generator_source("bed_basic"))
        context.scene.layoutlab_selected_generator = gen_name
        refresh_browser_items(context)
        self.report({"INFO"}, f"Installed: {gen_name}")
        return {"FINISHED"}


class LAYOUTLAB_OT_open_generator_browser(bpy.types.Operator):
    bl_idname = "layoutlab.open_generator_browser"
    bl_label = "Generator Browser"
    bl_options = {"REGISTER"}
    def execute(self, context):
        refresh_browser_items(context)
        return context.window_manager.invoke_popup(self, width=760)
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        header = layout.row(align=True)
        header.label(text="LayoutLab Generator Browser", icon="ASSET_MANAGER")
        header.operator("layoutlab.refresh_generator_browser", text="", icon="FILE_REFRESH")
        header.operator("layoutlab.install_default_generator", text="", icon="IMPORT")
        filters = layout.row(align=True)
        filters.prop(scene, "layoutlab_generator_filter", text="", icon="VIEWZOOM")
        filters.prop(scene, "layoutlab_category_filter", text="Category")
        filters.operator("layoutlab.refresh_generator_browser", text="Refresh")
        layout.separator()
        split = layout.split(factor=0.45)
        left = split.column()
        right = split.column()
        left.template_list("LAYOUTLAB_UL_generator_list", "", scene, "layoutlab_generator_items", scene, "layoutlab_generator_index", rows=12)
        row = left.row(align=True)
        row.operator("layoutlab.new_generator", text="New", icon="ADD")
        row.operator("layoutlab.load_selected_generator", text="Edit", icon="TEXT")
        row.operator("layoutlab.delete_selected_generator", text="Delete", icon="TRASH")
        if scene.layoutlab_generator_items:
            idx = min(max(scene.layoutlab_generator_index, 0), len(scene.layoutlab_generator_items) - 1)
            item = scene.layoutlab_generator_items[idx]
            right.label(text=item.name, icon="SCRIPT")
            right.label(text=f"Category: {item.category}")
            if item.version:
                right.label(text=f"Version: {item.version}")
            if item.description:
                box = right.box()
                box.label(text="Description")
                box.label(text=item.description)
            right.separator()
            right.label(text="Quick Test")
            right.prop(scene, "layoutlab_test_object_name", text="Name")
            right.prop(scene, "layoutlab_test_location", text="Location")
            right.prop(scene, "layoutlab_test_length", text="Length")
            right.prop(scene, "layoutlab_test_width", text="Width")
            right.operator("layoutlab.run_selected_generator", text="Create Test Object", icon="PLAY")
            right.separator()
            right.label(text="File")
            right.label(text=item.path)
        else:
            right.label(text="No generators found.")


class LAYOUTLAB_OT_refresh_generator_browser(bpy.types.Operator):
    bl_idname = "layoutlab.refresh_generator_browser"
    bl_label = "Refresh Generators"
    def execute(self, context):
        refresh_browser_items(context)
        return {"FINISHED"}


class LAYOUTLAB_OT_new_generator(bpy.types.Operator):
    bl_idname = "layoutlab.new_generator"
    bl_label = "New Generator"
    def execute(self, context):
        txt_name = context.scene.layoutlab_generator_text_block_name
        txt = bpy.data.texts.get(txt_name) or bpy.data.texts.new(txt_name)
        txt.clear()
        txt.write(default_generator_template().replace('GENERATOR_NAME = "bed_basic"', 'GENERATOR_NAME = "new_generator"'))
        context.scene.layoutlab_selected_generator = "new_generator"
        self.report({"INFO"}, f"Created editable text block: {txt_name}")
        return {"FINISHED"}


class LAYOUTLAB_OT_load_selected_generator(bpy.types.Operator):
    bl_idname = "layoutlab.load_selected_generator"
    bl_label = "Edit Generator"
    def execute(self, context):
        try:
            scene = context.scene
            gen = scene.layoutlab_generator_items[scene.layoutlab_generator_index].name if scene.layoutlab_generator_items else scene.layoutlab_selected_generator
            code = read_generator_code(gen)
            txt_name = scene.layoutlab_generator_text_block_name
            txt = bpy.data.texts.get(txt_name) or bpy.data.texts.new(txt_name)
            txt.clear()
            txt.write(code)
            scene.layoutlab_selected_generator = gen
            self.report({"INFO"}, f"Loaded generator into Text Editor: {gen}")
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class LAYOUTLAB_OT_save_generator_from_text(bpy.types.Operator):
    bl_idname = "layoutlab.save_generator_from_text"
    bl_label = "Save Current Generator Code"
    def execute(self, context):
        try:
            txt = bpy.data.texts.get(context.scene.layoutlab_generator_text_block_name)
            if not txt:
                raise ValueError("Generator text block not found.")
            gen_name, p = save_generator_code(txt.as_string())
            context.scene.layoutlab_selected_generator = gen_name
            refresh_browser_items(context)
            self.report({"INFO"}, f"Saved generator: {gen_name}")
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class LAYOUTLAB_OT_delete_selected_generator(bpy.types.Operator):
    bl_idname = "layoutlab.delete_selected_generator"
    bl_label = "Delete Generator"
    def execute(self, context):
        try:
            scene = context.scene
            gen = scene.layoutlab_generator_items[scene.layoutlab_generator_index].name if scene.layoutlab_generator_items else scene.layoutlab_selected_generator
            p = generator_path(gen)
            if p.exists(): p.unlink()
            refresh_browser_items(context)
            self.report({"INFO"}, f"Deleted generator: {gen}")
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class LAYOUTLAB_OT_copy_generator_list(bpy.types.Operator):
    bl_idname = "layoutlab.copy_generator_list"
    bl_label = "Copy Generator List"
    def execute(self, context):
        data = {"generator_dir": str(addon_user_dir()), "generators": list_generators_meta()}
        context.window_manager.clipboard = json.dumps(data, indent=2, ensure_ascii=False)
        self.report({"INFO"}, "Generator list copied.")
        return {"FINISHED"}


class LAYOUTLAB_OT_run_selected_generator(bpy.types.Operator):
    bl_idname = "layoutlab.run_selected_generator"
    bl_label = "Run Selected Generator"
    def execute(self, context):
        try:
            scene = context.scene
            gen = scene.layoutlab_generator_items[scene.layoutlab_generator_index].name if scene.layoutlab_generator_items else scene.layoutlab_selected_generator
            params = {
                "name": scene.layoutlab_test_object_name or f"TEST_{gen}",
                "location": list(scene.layoutlab_test_location),
                "length": scene.layoutlab_test_length,
                "width": scene.layoutlab_test_width,
                "head_side": "y_max",
                "collection": "layout_tests",
            }
            result = execute_generator(gen, params)
            print("LayoutLab generator result:")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            self.report({"INFO"}, f"Generated: {gen}")
        except Exception as e:
            print(traceback.format_exc())
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class LAYOUTLAB_UL_generator_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text=item.name, icon="SCRIPT")
        row.label(text=item.category)


class LAYOUTLAB_PT_panel(bpy.types.Panel):
    bl_label = "LayoutLab"
    bl_idname = "LAYOUTLAB_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LayoutLab"
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box = layout.box()
        box.label(text="Scene Exchange", icon="FILE_REFRESH")
        row = box.row(align=True)
        op = row.operator("layoutlab.copy_scene", text="Copy Scene"); op.selected_only = False
        op = row.operator("layoutlab.copy_scene", text="Copy Selected"); op.selected_only = True
        box.separator()
        box.label(text="Apply ChatGPT Commands", icon="CONSOLE")
        box.prop(scene, "layoutlab_command_source", text="")
        if scene.layoutlab_command_source == "TEXT":
            box.prop(scene, "layoutlab_text_block_name", text="Text")
            box.operator("layoutlab.create_command_text_block", text="Create Command Text")
        box.operator("layoutlab.apply_commands", text="Apply Commands", icon="PLAY")
        layout.separator()
        box = layout.box()
        box.label(text="Generator Library", icon="ASSET_MANAGER")
        box.operator("layoutlab.open_generator_browser", text="Open Generator Browser", icon="ASSET_MANAGER")
        row = box.row(align=True)
        row.operator("layoutlab.install_default_generator", text="Install Default")
        row.operator("layoutlab.copy_generator_list", text="Copy List")
        box.separator()
        box.label(text="Generator Code Workbench", icon="TEXT")
        box.prop(scene, "layoutlab_generator_text_block_name", text="Text")
        row = box.row(align=True)
        row.operator("layoutlab.new_generator", text="New")
        row.operator("layoutlab.save_generator_from_text", text="Save")
        row.operator("layoutlab.load_selected_generator", text="Load")


classes = (
    LayoutLabGeneratorItem,
    LAYOUTLAB_OT_copy_scene,
    LAYOUTLAB_OT_apply_commands,
    LAYOUTLAB_OT_create_command_text_block,
    LAYOUTLAB_OT_install_default_generator,
    LAYOUTLAB_OT_open_generator_browser,
    LAYOUTLAB_OT_refresh_generator_browser,
    LAYOUTLAB_OT_new_generator,
    LAYOUTLAB_OT_load_selected_generator,
    LAYOUTLAB_OT_save_generator_from_text,
    LAYOUTLAB_OT_delete_selected_generator,
    LAYOUTLAB_OT_copy_generator_list,
    LAYOUTLAB_OT_run_selected_generator,
    LAYOUTLAB_UL_generator_list,
    LAYOUTLAB_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.layoutlab_command_source = bpy.props.EnumProperty(
        name="Command Source",
        items=[("CLIPBOARD", "Clipboard", "Read JSON commands from clipboard"), ("TEXT", "Text Block", "Read JSON commands from a Blender text block")],
        default="CLIPBOARD",
    )
    bpy.types.Scene.layoutlab_text_block_name = bpy.props.StringProperty(name="Command Text Block", default="LayoutLab_Commands")
    bpy.types.Scene.layoutlab_generator_text_block_name = bpy.props.StringProperty(name="Generator Text Block", default="LayoutLab_Generator_Code")
    bpy.types.Scene.layoutlab_selected_generator = bpy.props.StringProperty(name="Selected Generator", default="bed_basic")
    bpy.types.Scene.layoutlab_generator_items = bpy.props.CollectionProperty(type=LayoutLabGeneratorItem)
    bpy.types.Scene.layoutlab_generator_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.layoutlab_generator_filter = bpy.props.StringProperty(name="Search", default="")
    bpy.types.Scene.layoutlab_category_filter = bpy.props.StringProperty(name="Category", default="All")
    bpy.types.Scene.layoutlab_test_object_name = bpy.props.StringProperty(name="Object Name", default="TEST_BED")
    bpy.types.Scene.layoutlab_test_location = bpy.props.FloatVectorProperty(name="Location", size=3, default=(68.3, 197.7, 0.0))
    bpy.types.Scene.layoutlab_test_length = bpy.props.FloatProperty(name="Length", default=12.0)
    bpy.types.Scene.layoutlab_test_width = bpy.props.FloatProperty(name="Width", default=20.0)
    addon_user_dir()
    sync_bundled_generators()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.layoutlab_command_source
    del bpy.types.Scene.layoutlab_text_block_name
    del bpy.types.Scene.layoutlab_generator_text_block_name
    del bpy.types.Scene.layoutlab_selected_generator
    del bpy.types.Scene.layoutlab_generator_items
    del bpy.types.Scene.layoutlab_generator_index
    del bpy.types.Scene.layoutlab_generator_filter
    del bpy.types.Scene.layoutlab_category_filter
    del bpy.types.Scene.layoutlab_test_object_name
    del bpy.types.Scene.layoutlab_test_location
    del bpy.types.Scene.layoutlab_test_length
    del bpy.types.Scene.layoutlab_test_width


if __name__ == "__main__":
    register()
