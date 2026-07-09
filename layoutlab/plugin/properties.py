import bpy

from ..engine.registry import list_generators_meta


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
