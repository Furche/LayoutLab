import bpy


def get_or_create_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def delete_collection_objects(collection_name):
    col = bpy.data.collections.get(collection_name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)


def delete_prefix(prefix):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix):
            bpy.data.objects.remove(obj, do_unlink=True)


def delete_by_object_id(object_id):
    if not object_id:
        return 0
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.get("layoutlab_object_id") == object_id:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def find_objects_by_object_id(object_id):
    return [o for o in bpy.data.objects if o.get("layoutlab_object_id") == object_id]
