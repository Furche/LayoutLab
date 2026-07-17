bl_info = {
    "name": "LayoutLab",
    "author": "ChatGPT / Alexander",
    "version": (0, 10, 8),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > LayoutLab",
    "description": "Room layout JSON exchange with an asset-browser-like generator browser.",
    "category": "3D View",
}

import bpy

from .engine.registry import addon_user_dir, sync_bundled_generators
from .engine import (
    addon_bundled_generators_dir,
    addon_root_dir,
    default_generator_template,
    execute_generator,
    generator_path,
    list_generators_meta,
    load_bundled_generator_source,
    read_generator_code,
    save_generator_code,
)
from .plugin import classes, LayoutLabGeneratorItem
from .plugin.properties import _on_generator_index_changed
from .protocol.commands import apply_commands_json, get_commands_text
from .protocol.export import layout_export_json

__all__ = [
    "addon_bundled_generators_dir",
    "addon_root_dir",
    "addon_user_dir",
    "apply_commands_json",
    "bl_info",
    "default_generator_template",
    "execute_generator",
    "generator_path",
    "get_commands_text",
    "layout_export_json",
    "load_bundled_generator_source",
    "read_generator_code",
    "save_generator_code",
]


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
    bpy.types.Scene.layoutlab_generator_index = bpy.props.IntProperty(default=0, update=_on_generator_index_changed)
    bpy.types.Scene.layoutlab_generator_filter = bpy.props.StringProperty(name="Search", default="")
    bpy.types.Scene.layoutlab_category_filter = bpy.props.StringProperty(name="Category", default="All")
    bpy.types.Scene.layoutlab_quick_test_profile_gen = bpy.props.StringProperty(name="Quick Test Profile", default="")
    bpy.types.Scene.layoutlab_test_object_name = bpy.props.StringProperty(name="Object Name", default="TEST_BED")
    bpy.types.Scene.layoutlab_test_location = bpy.props.FloatVectorProperty(name="Location", size=3, default=(0.0, 0.0, 0.0))
    bpy.types.Scene.layoutlab_test_length = bpy.props.FloatProperty(name="Length", default=1.2)
    bpy.types.Scene.layoutlab_test_width = bpy.props.FloatProperty(name="Width", default=2.0)
    bpy.types.Scene.layoutlab_test_depth = bpy.props.FloatProperty(name="Depth", default=0.6)
    bpy.types.Scene.layoutlab_test_height = bpy.props.FloatProperty(name="Height", default=0.75)
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
    del bpy.types.Scene.layoutlab_quick_test_profile_gen
    del bpy.types.Scene.layoutlab_test_object_name
    del bpy.types.Scene.layoutlab_test_location
    del bpy.types.Scene.layoutlab_test_length
    del bpy.types.Scene.layoutlab_test_width
    del bpy.types.Scene.layoutlab_test_depth
    del bpy.types.Scene.layoutlab_test_height


if __name__ == "__main__":
    register()
