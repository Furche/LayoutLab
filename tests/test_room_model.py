import importlib.util
import unittest
from pathlib import Path

_ROOM_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "core" / "room.py"


def _load_room():
    spec = importlib.util.spec_from_file_location("layoutlab_core_room", _ROOM_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRoomModelRectangle(unittest.TestCase):
    def setUp(self):
        self.room_core = _load_room()

    def test_create_derives_four_walls(self):
        model = self.room_core.create_room_model(
            {"name": "KIDS", "location": [65.3, 196.8, 0], "width": 42, "depth": 21.8, "height": 26}
        )
        self.assertEqual(model["footprint"]["kind"], "rectangle")
        self.assertEqual(len(model["walls"]), 4)
        sides = {w["side"] for w in model["walls"]}
        self.assertEqual(sides, {"south", "east", "north", "west"})
        west = self.room_core.find_wall(model, "west")
        self.assertAlmostEqual(west["length"], 21.8)

    def test_wall_ids_stable_on_update(self):
        model = self.room_core.create_room_model({"name": "R", "width": 10, "depth": 8, "height": 25})
        ids_before = {w["side"]: w["wall_id"] for w in model["walls"]}
        self.room_core.update_room_model(model, {"width": 12})
        ids_after = {w["side"]: w["wall_id"] for w in model["walls"]}
        self.assertEqual(ids_before, ids_after)
        self.assertEqual(model["footprint"]["width"], 12.0)

    def test_add_opening_and_fixed(self):
        model = self.room_core.create_room_model(
            {"name": "KIDS", "location": [65.3444, 196.8293, 0], "width": 42, "depth": 21.8, "height": 26}
        )
        window = self.room_core.add_opening(
            model,
            {
                "name": "window_west",
                "kind": "window",
                "wall_side": "west",
                "offset": 4.8,
                "width": 12.3,
                "height": 14.7,
                "sill_height": 8.8,
            },
        )
        door = self.room_core.add_opening(
            model,
            {
                "name": "door_east",
                "kind": "door",
                "wall_side": "east",
                "offset": 2.5,
                "width": 7.08,
                "height": 18.45,
            },
        )
        rad = self.room_core.add_fixed_element(
            model,
            {
                "name": "heizung",
                "kind": "radiator",
                "wall_side": "west",
                "offset": 5.65,
                "width": 11.0,
                "depth": 1.0,
                "height": 7.5,
            },
        )
        self.assertEqual(len(model["openings"]), 2)
        self.assertEqual(window["wall_side"], "west")
        self.assertEqual(door["wall_side"], "east")
        self.assertEqual(rad["kind"], "radiator")
        block = self.room_core.export_room_block(model)
        self.assertEqual(block["footprint"]["width"], 42.0)
        self.assertIn("world_bounds", block)

    def test_opening_out_of_range_raises(self):
        model = self.room_core.create_room_model({"name": "R", "width": 10, "depth": 8, "height": 25})
        with self.assertRaises(ValueError):
            self.room_core.add_opening(
                model, {"kind": "door", "wall_side": "south", "offset": 8, "width": 5, "height": 20}
            )

    def test_polygon_rejected(self):
        with self.assertRaises(ValueError):
            self.room_core.create_room_model(
                {"name": "R", "footprint": {"kind": "polygon", "width": 10, "depth": 8}}
            )

    def test_west_opening_box(self):
        model = self.room_core.create_room_model(
            {"name": "R", "location": [0, 0, 0], "width": 40, "depth": 20, "height": 25, "wall_thickness": 0.2}
        )
        opening = self.room_core.add_opening(
            model, {"kind": "window", "wall_side": "west", "offset": 5, "width": 10, "height": 12, "sill": 8}
        )
        loc, dims = self.room_core.opening_world_box(model, opening)
        self.assertAlmostEqual(loc[1], 5.0)
        self.assertAlmostEqual(dims[1], 10.0)
        self.assertAlmostEqual(loc[2], 8.0)


if __name__ == "__main__":
    unittest.main()
