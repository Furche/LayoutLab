import json

from ..util import merge_generator_params

__all__ = ["layoutlab_block_from_object", "merge_generator_params"]


def layoutlab_block_from_object(obj):
    object_id = obj.get("layoutlab_object_id")
    if not object_id:
        return None

    params = {}
    raw_params = obj.get("layoutlab_params")
    if raw_params:
        try:
            params = json.loads(raw_params)
        except (TypeError, json.JSONDecodeError):
            params = raw_params

    return {
        "object_id": object_id,
        "generator": obj.get("layoutlab_generator", ""),
        "generator_version": obj.get("layoutlab_generator_version", ""),
        "params": params,
        "component": obj.get("layoutlab_component", ""),
        "role": obj.get("layoutlab_role", ""),
    }
