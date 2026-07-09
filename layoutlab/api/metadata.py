"""Semantic object metadata on Blender meshes (Phase D)."""

import json

_active_context = None


class GeneratorObjectContext:
    __slots__ = ("object_id", "generator", "generator_version", "params_json", "name_prefix")

    def __init__(self, object_id, generator, generator_version, params_json, name_prefix):
        self.object_id = object_id
        self.generator = generator
        self.generator_version = generator_version
        self.params_json = params_json
        self.name_prefix = name_prefix


def activate_context(context):
    global _active_context
    _active_context = context


def deactivate_context():
    global _active_context
    _active_context = None


def get_active_context():
    return _active_context


def apply_layoutlab_metadata(obj, context, *, component=None, role=None):
    if context is None:
        return
    obj["layoutlab_object_id"] = context.object_id
    obj["layoutlab_generator"] = context.generator
    obj["layoutlab_generator_version"] = context.generator_version
    obj["layoutlab_params"] = context.params_json
    if component:
        obj["layoutlab_component"] = component
    if role:
        obj["layoutlab_role"] = role


def build_object_context(generator, generator_version, params, object_id):
    params = dict(params or {})
    name_prefix = params.get("name", "OBJ")
    params_json = json.dumps(params, ensure_ascii=False, sort_keys=True)
    return GeneratorObjectContext(
        object_id=object_id,
        generator=generator,
        generator_version=generator_version or "",
        params_json=params_json,
        name_prefix=name_prefix,
    )


def component_for_object_name(object_name, name_prefix):
    from ..util import component_suffix_from_name

    return component_suffix_from_name(object_name, name_prefix)
