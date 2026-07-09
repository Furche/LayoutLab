import json
import traceback

import bpy

from ..engine.executor import execute_generator
from ..engine.registry import (
    addon_user_dir,
    default_generator_template,
    generator_path,
    list_generators_meta,
    load_bundled_generator_source,
    read_generator_code,
    save_generator_code,
)
from ..protocol.commands import apply_commands_json, get_commands_text
from ..protocol.export import layout_export_json
from .properties import refresh_browser_items


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


class LAYOUTLAB_OT_run_diagnostics(bpy.types.Operator):
    bl_idname = "layoutlab.run_diagnostics"
    bl_label = "Run Console Checks"

    def execute(self, context):
        from ..diagnostics import run_console_checks

        try:
            report = run_console_checks(context)
            context.window_manager.clipboard = report
            self.report({"INFO"}, "Diagnostics complete — report copied to clipboard.")
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


operator_classes = (
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
    LAYOUTLAB_OT_run_diagnostics,
)
