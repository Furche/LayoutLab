"""LayoutLab Blender API package.

Import concrete submodules (e.g. ``layoutlab.api.metadata``) for headless use.
``build_generator_api`` requires Blender.
"""

__all__ = ["build_generator_api"]


def __getattr__(name):
    if name == "build_generator_api":
        import math

        import bpy

        from . import collections, clearance, geometry, materials, parts

        def build_generator_api():
            return {
                "bpy": bpy,
                "math": math,
                "begin_part": parts.begin_part,
                "end_part": parts.end_part,
                "finish": parts.finish,
                "create_box": geometry.create_box,
                "create_clearance": clearance.create_clearance,
                "create_label": geometry.create_label,
                "delete_collection_objects": collections.delete_collection_objects,
                "delete_prefix": collections.delete_prefix,
                "get_or_create_collection": collections.get_or_create_collection,
                "ensure_material": materials.ensure_material,
            }

        return build_generator_api
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
