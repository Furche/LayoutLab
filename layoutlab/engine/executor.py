import math
import uuid

import bpy

from ..api import build_generator_api
from ..api.metadata import activate_context, build_object_context, deactivate_context
from ..util import infer_generator_meta_from_code, sanitize_generator_name
from . import registry


def execute_generator(name, params=None, object_id=None):
    name = sanitize_generator_name(name)
    params = dict(params or {})
    gen_code = registry.read_generator_code(name)
    gen_meta = infer_generator_meta_from_code(gen_code)
    if not object_id:
        object_id = str(uuid.uuid4())

    context = build_object_context(
        name,
        gen_meta.get("version", ""),
        params,
        object_id,
    )
    namespace = {"__name__": f"layoutlab_generator_{name}", "math": math, "bpy": bpy}
    exec(gen_code, namespace)
    generate = namespace.get("generate")
    if not callable(generate):
        raise ValueError(f"Generator '{name}' has no callable generate(params, api).")

    activate_context(context)
    try:
        result = generate(params, build_generator_api())
    finally:
        deactivate_context()

    if isinstance(result, dict):
        return {**result, "object_id": object_id, "generator": name}
    return {"object_id": object_id, "generator": name, "result": result}
