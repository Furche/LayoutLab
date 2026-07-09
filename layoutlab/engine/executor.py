import math

import bpy

from ..api import build_generator_api
from ..util import sanitize_generator_name
from . import registry


def execute_generator(name, params):
    name = sanitize_generator_name(name)
    gen_code = registry.read_generator_code(name)
    namespace = {"__name__": f"layoutlab_generator_{name}", "math": math, "bpy": bpy}
    exec(gen_code, namespace)
    generate = namespace.get("generate")
    if not callable(generate):
        raise ValueError(f"Generator '{name}' has no callable generate(params, api).")
    return generate(params or {}, build_generator_api())
