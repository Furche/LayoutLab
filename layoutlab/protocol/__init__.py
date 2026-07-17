"""LayoutLab protocol package.

Import submodules explicitly (e.g. ``layoutlab.protocol.viewer_export``) so
headless Core can load without Blender. ``commands`` / ``export`` need bpy.
"""

__all__ = ["apply_commands_json", "get_commands_text", "layout_export_json"]


def __getattr__(name):
    if name == "apply_commands_json":
        from .commands import apply_commands_json

        return apply_commands_json
    if name == "get_commands_text":
        from .commands import get_commands_text

        return get_commands_text
    if name == "layout_export_json":
        from .export import layout_export_json

        return layout_export_json
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
