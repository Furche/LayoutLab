import math

import bpy

from . import collections, geometry, materials, parts


def build_generator_api():
    return {
        "bpy": bpy,
        "math": math,
        "begin_part": parts.begin_part,
        "end_part": parts.end_part,
        "finish": parts.finish,
        "create_box": geometry.create_box,
        "create_label": geometry.create_label,
        "delete_collection_objects": collections.delete_collection_objects,
        "delete_prefix": collections.delete_prefix,
        "get_or_create_collection": collections.get_or_create_collection,
        "ensure_material": materials.ensure_material,
    }
