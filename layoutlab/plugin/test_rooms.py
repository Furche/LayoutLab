"""Built-in kids-room test layouts for the Sidebar (metric, 1 unit = 1 m).

Mirrors tests/fixtures/reference_kids_room_commands.json.
"""

COLLECTION = "layoutlab_room"
ROOM_NAME = "KIDS_ROOM"

_CLEAR_COLLECTION = {
    "action": "delete_collection_objects",
    "collection": COLLECTION,
}

_ROOM_SHELL = [
    {
        "action": "create_room",
        "params": {
            "name": ROOM_NAME,
            "location": [0, 0, 0],
            "width": 4.2,
            "depth": 2.18,
            "height": 2.6,
            "wall_thickness": 0.02,
            "collection": COLLECTION,
        },
    },
    {
        "action": "add_opening",
        "params": {
            "room": ROOM_NAME,
            "opening_name": "window_west",
            "kind": "window",
            "wall_side": "west",
            "offset": 0.48054,
            "width": 1.22946,
            "height": 1.47,
            "sill_height": 0.88,
        },
    },
    {
        "action": "add_opening",
        "params": {
            "room": ROOM_NAME,
            "opening_name": "door_east",
            "kind": "door",
            "wall_side": "east",
            "offset": 0.24866,
            "width": 0.70801,
            "height": 1.84453,
        },
    },
    {
        "action": "add_fixed_element",
        "params": {
            "room": ROOM_NAME,
            "fixed_name": "heizung",
            "kind": "radiator",
            "wall_side": "west",
            "offset": 0.56494,
            "width": 1.1,
            "depth": 0.1,
            "height": 0.75,
        },
    },
]

_FURNITURE = [
    {
        "action": "run_generator",
        "generator": "bed_basic",
        "params": {
            "name": "BED_120x200",
            "location": [0.15, 0.09, 0],
            "length": 1.2,
            "width": 2.0,
            "head_side": "y_max",
            "clearances": [
                {
                    "clearance_name": "bed_entry",
                    "side": "right",
                    "depth": 0.5,
                    "requirement": "preferred",
                }
            ],
            "collection": COLLECTION,
        },
    },
    {
        "action": "run_generator",
        "generator": "desk_basic",
        "params": {
            "name": "DESK_120x60",
            "location": [2.7, 1.58, 0],
            "width": 1.2,
            "depth": 0.6,
            "height": 0.75,
            "show_clearance": True,
            "collection": COLLECTION,
        },
    },
]


def empty_test_room_commands():
    return {"commands": [_CLEAR_COLLECTION, *_ROOM_SHELL]}


def furnished_test_room_commands():
    return {"commands": [_CLEAR_COLLECTION, *_ROOM_SHELL, *_FURNITURE]}
