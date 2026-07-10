"""Pure-Python helpers shared by the LayoutLab addon and unit tests."""

import json
import re
from pathlib import Path


def sanitize_generator_name(name):
    name = (name or "").strip()
    name = re.sub(r"\.py$", "", name)
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", name)
    name = name.strip("_")
    if not name:
        raise ValueError("Generator name is empty.")
    return name


def infer_generator_name_from_code(code):
    m = re.search(r'GENERATOR_NAME\s*=\s*[\'"]([^\'"]+)[\'"]', code)
    if m:
        return sanitize_generator_name(m.group(1))
    m = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)
    if m and m.group(1) != "generate":
        return sanitize_generator_name(m.group(1))
    raise ValueError('Generator code needs GENERATOR_NAME = "name"')


def generator_version_tuple(version_str):
    """Parse GENERATOR_VERSION strings like '0.2' into comparable tuples."""
    parts = []
    for piece in str(version_str or "0").split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            break
    return tuple(parts) or (0,)


def infer_generator_meta_from_code(code, filepath=None):
    def val(key, default=""):
        m = re.search(rf'{key}\s*=\s*[\'"]([^\'"]*)[\'"]', code)
        return m.group(1).strip() if m else default

    name = val("GENERATOR_NAME")
    if not name and filepath:
        name = Path(filepath).stem

    return {
        "name": sanitize_generator_name(name),
        "category": val("GENERATOR_CATEGORY", "Uncategorized") or "Uncategorized",
        "description": val("GENERATOR_DESCRIPTION", ""),
        "version": val("GENERATOR_VERSION", ""),
        "icon": val("GENERATOR_ICON", "SCRIPT") or "SCRIPT",
        "path": str(filepath) if filepath else "",
    }


def parse_commands_payload(text):
    """Parse JSON command input into a list of command dicts."""
    payload = json.loads(text)
    if isinstance(payload, list):
        commands = payload
    elif isinstance(payload, dict):
        commands = payload.get("commands", [])
    else:
        raise ValueError("Expected JSON with {'commands': [...]} or a list.")
    if not isinstance(commands, list):
        raise ValueError("Expected JSON with {'commands': [...]} or a list.")
    return commands


def merge_generator_params(stored, overrides):
    """Merge stored generator params with command overrides (regenerate)."""
    merged = dict(stored or {})
    merged.update(overrides or {})
    return merged


def component_suffix_from_name(object_name, name_prefix):
    """Derive layoutlab_component from object name and params.name prefix."""
    if not object_name or not name_prefix:
        return ""
    if object_name == name_prefix:
        return ""
    prefix = f"{name_prefix}_"
    if object_name.startswith(prefix):
        return object_name[len(prefix):]
    return ""
