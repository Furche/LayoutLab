"""Pure-Python helpers shared by the LayoutLab addon and unit tests."""

import json
import re
from pathlib import Path


def relative_translation_from_world_matrices(child_world, parent_world):
    """World-space offset from *parent_world* origin to *child_world* origin."""
    ct = child_world.translation
    pt = parent_world.translation
    return (float(ct.x - pt.x), float(ct.y - pt.y), float(ct.z - pt.z))


def relative_translation_from_locations(child_loc, parent_loc):
    """World-space offset using Blender object ``location`` vectors (pre-parenting)."""
    return (
        float(child_loc.x - parent_loc.x),
        float(child_loc.y - parent_loc.y),
        float(child_loc.z - parent_loc.z),
    )


CLEARANCE_REQUIREMENTS = frozenset({"required", "preferred"})

# Mesh roles that must not count as obstacles in analyze_layout
ANALYZE_NON_BLOCKER_ROLES = frozenset({
    "clearance",
    "room_floor",
    "room_opening",
    "label",
})


def is_analyze_blocker(obj_type, role="", has_clearance_name=False):
    """True if an object should be treated as an obstacle for zone_must_be_clear."""
    if obj_type != "MESH":
        return False
    if has_clearance_name or role == "clearance":
        return False
    if role in ANALYZE_NON_BLOCKER_ROLES:
        return False
    return True


def validate_clearance_requirement(requirement):
    req = (requirement or "preferred").strip().lower()
    if req not in CLEARANCE_REQUIREMENTS:
        raise ValueError(
            f"clearance requirement must be one of {sorted(CLEARANCE_REQUIREMENTS)}, got {requirement!r}"
        )
    return req


def resolve_clearance_locations(local_location=None, world_location=None, main_location=None):
    """Return (world_location, local_location) for axis-aligned clearance boxes."""
    main = main_location

    if local_location is not None:
        local = tuple(float(v) for v in local_location)
        if main is not None:
            world = (main[0] + local[0], main[1] + local[1], main[2] + local[2])
        else:
            world = local
        return world, local

    if world_location is not None:
        world = tuple(float(v) for v in world_location)
        if main is not None:
            local = (world[0] - main[0], world[1] - main[1], world[2] - main[2])
        else:
            local = world
        return world, local

    raise ValueError("create_clearance requires location or local_location")


def box_bounds_from_corner_and_dimensions(location, dimensions):
    """Axis-aligned bounds for a box anchored at *location* with positive *dimensions*."""
    loc = [float(v) for v in location]
    dim = [float(v) for v in dimensions]
    return {
        "min": [round(loc[i], 4) for i in range(3)],
        "max": [round(loc[i] + dim[i], 4) for i in range(3)],
    }


def axis_aligned_bounds_from_points(points):
    """Min/max bounds for a list of [x, y, z] points."""
    if not points:
        return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}
    xs, ys, zs = zip(*[(float(p[0]), float(p[1]), float(p[2])) for p in points])
    return {
        "min": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
        "max": [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
    }


def aabb_intersects(bounds_a, bounds_b):
    """True if two axis-aligned boxes overlap with volume > 0 (DD-008 v1)."""
    a_min = bounds_a.get("min", [0, 0, 0])
    a_max = bounds_a.get("max", [0, 0, 0])
    b_min = bounds_b.get("min", [0, 0, 0])
    b_max = bounds_b.get("max", [0, 0, 0])
    for i in range(3):
        if float(a_max[i]) <= float(b_min[i]) or float(b_max[i]) <= float(a_min[i]):
            return False
    return True


def requirement_to_severity(requirement):
    """Map clearance requirement to analysis severity (DD-008)."""
    req = (requirement or "preferred").strip().lower()
    if req == "required":
        return "error"
    if req == "informational":
        return "info"
    return "warning"


def parse_clearance_params_json(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
