import bpy


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
        box.label(text="Test Rooms", icon="HOME")
        row = box.row(align=True)
        row.operator("layoutlab.create_empty_test_room", text="Empty", icon="MESH_PLANE")
        row.operator("layoutlab.create_furnished_test_room", text="Furnished", icon="MOD_BUILD")
        layout.separator()
        box = layout.box()
        box.label(text="Generator Library", icon="ASSET_MANAGER")
        row = box.row(align=True)
        row.operator("layoutlab.open_generator_browser", text="Open Generator Browser", icon="ASSET_MANAGER")
        row.operator("layoutlab.paste_generator", text="Paste Generator", icon="PASTEFLIPDOWN")
        layout.separator()
        box = layout.box()
        box.label(text="Diagnostics", icon="CONSOLE")
        box.operator("layoutlab.run_diagnostics", text="Run Console Checks", icon="FILE_TEXT")


ui_classes = (
    LAYOUTLAB_UL_generator_list,
    LAYOUTLAB_PT_panel,
)
