import math
import uuid

import bpy

from ..api import build_generator_api
from ..api.metadata import activate_context, build_object_context, deactivate_context
from ..api.parts import PartSession, activate_session, deactivate_session
from ..util import infer_generator_meta_from_code, sanitize_generator_name
from . import registry


def execute_generator(name, params=None, object_id=None):
    name = sanitize_generator_name(name)
    params = dict(params or {})
    gen_code = registry.read_generator_code(name)
    gen_meta = infer_generator_meta_from_code(gen_code)
    if not object_id:
        object_id = str(uuid.uuid4())

    meta_context = build_object_context(
        name,
        gen_meta.get("version", ""),
        params,
        object_id,
    )
    furniture_prefix = params.get("name", "OBJ")
    collection = params.get("collection", "layout_tests")
    part_session = PartSession(furniture_prefix, collection)

    namespace = {"__name__": f"layoutlab_generator_{name}", "math": math, "bpy": bpy}
    exec(gen_code, namespace)
    generate = namespace.get("generate")
    if not callable(generate):
        raise ValueError(f"Generator '{name}' has no callable generate(params, api).")

    activate_context(meta_context)
    activate_session(part_session)
    try:
        result = generate(params, build_generator_api())
        part_summary = part_session.finish()
    finally:
        deactivate_session()
        deactivate_context()

    payload = {
        "object_id": object_id,
        "generator": name,
        "parts": part_summary.get("parts", []),
        "main_part": part_summary.get("main_part", ""),
        "part_object_count": part_summary.get("object_count", 0),
    }
    if isinstance(result, dict):
        return {**result, **payload}
    return payload
