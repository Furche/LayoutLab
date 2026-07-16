"""Clearance zone creation (DD-007)."""

import json
import uuid

from ..util import resolve_clearance_locations, validate_clearance_requirement
from .geometry import create_box
from .parts import get_active_session
from .units import from_bu_vec

DEFAULT_CLEARANCE_COLOR = (0.2, 0.8, 1.0, 0.22)


def _main_part_location():
    session = get_active_session()
    if not session:
        return None
    for part in session.parts:
        if part.main and part.object:
            loc = part.object.location
            return (float(loc.x), float(loc.y), float(loc.z))
    return None


def apply_clearance_metadata(
    obj,
    *,
    clearance_id,
    clearance_name,
    purpose,
    requirement,
    priority,
    params,
    local_location,
    dimensions,
):
    obj["layoutlab_role"] = "clearance"
    obj["layoutlab_clearance_id"] = clearance_id
    obj["layoutlab_clearance_name"] = clearance_name
    if purpose:
        obj["layoutlab_clearance_purpose"] = purpose
    obj["layoutlab_clearance_requirement"] = requirement
    obj["layoutlab_clearance_priority"] = int(priority)

    payload = dict(params or {})
    payload["local_transform"] = {
        "location": [float(v) for v in local_location],
        "rotation": [0.0, 0.0, 0.0],
        "dimensions": [float(v) for v in dimensions],
        "shape": "box",
    }
    obj["layoutlab_clearance_params"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)


def create_clearance(
    name,
    dimensions,
    *,
    location=None,
    local_location=None,
    clearance_name,
    purpose="",
    requirement="preferred",
    priority=0,
    params=None,
    color=DEFAULT_CLEARANCE_COLOR,
    collection="layout_tests",
    display_type="WIRE",
):
    """Create a wireframe clearance zone mesh with DD-007 metadata."""
    if not clearance_name or not str(clearance_name).strip():
        raise ValueError("create_clearance requires clearance_name")

    requirement = validate_clearance_requirement(requirement)
    dims = tuple(float(v) for v in dimensions)
    # Main part is already in Blender units; clearance inputs are LayoutLab units.
    main_bu = _main_part_location()
    main_ll = from_bu_vec(main_bu) if main_bu is not None else None
    world, local = resolve_clearance_locations(
        local_location=local_location,
        world_location=location,
        main_location=main_ll,
    )
    clearance_id = str(uuid.uuid4())

    obj = create_box(
        name,
        world,
        dims,
        color=color,
        collection=collection,
        role="clearance",
        display_type=display_type,
    )
    obj.show_in_front = True

    apply_clearance_metadata(
        obj,
        clearance_id=clearance_id,
        clearance_name=str(clearance_name).strip(),
        purpose=str(purpose or "").strip(),
        requirement=requirement,
        priority=priority,
        params=params,
        local_location=local,
        dimensions=dims,
    )
    return obj
