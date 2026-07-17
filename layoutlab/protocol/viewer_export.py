"""Viewer export hints (DD-014 Phase A / json_protocol §6.4)."""

VIEWER_SCHEMA = "0.1.0"

WIRE_ROLES = frozenset({"clearance", "room_opening"})
QUAD_ROLES = frozenset({"room_wall"})
BOX_ROLES = frozenset({"room_floor", "room_fixed", "room_opening", "clearance"})


def round_corner(corner):
    return [round(float(corner[0]), 4), round(float(corner[1]), 4), round(float(corner[2]), 4)]


def viewer_block_for_role(role, *, corners=None, display_type=None):
    """Build optional ``viewer`` hint dict for an exported object.

    Returns ``None`` when no hint is useful (unknown role without corners).
    """
    role = role or ""
    hint = {}

    if corners and len(corners) >= 4:
        hint["primitive"] = "quad"
        hint["corners"] = [round_corner(c) for c in corners[:4]]
    elif role in QUAD_ROLES:
        hint["primitive"] = "quad"
    elif role in BOX_ROLES or role:
        hint["primitive"] = "box"

    if role in WIRE_ROLES or (display_type and str(display_type).upper() == "WIRE"):
        hint["display"] = "wire"

    return hint or None


def parse_corners_json(raw):
    """Parse stamped ``layoutlab_viewer_corners`` JSON string → list or None."""
    if not raw:
        return None
    import json

    try:
        corners = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(corners, list) or len(corners) < 4:
        return None
    return corners
