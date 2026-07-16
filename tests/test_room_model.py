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
            {"name": "KIDS", "location": [6.53, 19.68, 0], "width": 4.2, "depth": 2.18, "height": 2.6}
        )
        self.assertEqual(model["footprint"]["kind"], "rectangle")
        self.assertEqual(len(model["walls"]), 4)
        sides = {w["side"] for w in model["walls"]}
        self.assertEqual(sides, {"south", "east", "north", "west"})
        west = self.room_core.find_wall(model, "west")
        self.assertAlmostEqual(west["length"], 2.18)

    def test_wall_ids_stable_on_update(self):
        model = self.room_core.create_room_model({"name": "R", "width": 1.0, "depth": 0.8, "height": 2.5})
        ids_before = {w["side"]: w["wall_id"] for w in model["walls"]}
        self.room_core.update_room_model(model, {"width": 1.2})
        ids_after = {w["side"]: w["wall_id"] for w in model["walls"]}
        self.assertEqual(ids_before, ids_after)
        self.assertEqual(model["footprint"]["width"], 1.2)

    def test_add_opening_and_fixed(self):
        model = self.room_core.create_room_model(
            {"name": "KIDS", "location": [0, 0, 0], "width": 4.2, "depth": 2.18, "height": 2.6}
        )
        window = self.room_core.add_opening(
            model,
            {
                "name": "window_west",
                "kind": "window",
                "wall_side": "west",
                "offset": 0.48,
                "width": 1.23,
                "height": 1.47,
                "sill_height": 0.88,
            },
        )
        door = self.room_core.add_opening(
            model,
            {
                "name": "door_east",
                "kind": "door",
                "wall_side": "east",
                "offset": 0.25,
                "width": 0.708,
                "height": 1.845,
            },
        )
        rad = self.room_core.add_fixed_element(
            model,
            {
                "name": "heizung",
                "kind": "radiator",
                "wall_side": "west",
                "offset": 0.565,
                "width": 1.1,
                "depth": 0.1,
                "height": 0.75,
            },
        )
        self.assertEqual(len(model["openings"]), 2)
        self.assertEqual(window["wall_side"], "west")
        self.assertEqual(door["wall_side"], "east")
        self.assertEqual(rad["kind"], "radiator")
        block = self.room_core.export_room_block(model)
        self.assertEqual(block["footprint"]["width"], 4.2)
        self.assertIn("world_bounds", block)

    def test_opening_out_of_range_raises(self):
        model = self.room_core.create_room_model({"name": "R", "width": 1.0, "depth": 0.8, "height": 2.5})
        with self.assertRaises(ValueError):
            self.room_core.add_opening(
                model, {"kind": "door", "wall_side": "south", "offset": 0.8, "width": 0.5, "height": 2.0}
            )

    def test_polygon_rejected(self):
        with self.assertRaises(ValueError):
            self.room_core.create_room_model(
                {"name": "R", "footprint": {"kind": "polygon", "width": 1.0, "depth": 0.8}}
            )

    def test_west_opening_box(self):
        model = self.room_core.create_room_model(
            {"name": "R", "location": [0, 0, 0], "width": 4.0, "depth": 2.0, "height": 2.5, "wall_thickness": 0.02}
        )
        opening = self.room_core.add_opening(
            model, {"kind": "window", "wall_side": "west", "offset": 0.5, "width": 1.0, "height": 1.2, "sill": 0.8}
        )
        loc, dims = self.room_core.opening_world_box(model, opening)
        self.assertAlmostEqual(loc[1], 0.5)
        self.assertAlmostEqual(dims[1], 1.0)
        self.assertAlmostEqual(loc[2], 0.8)

    def test_default_origin_zero(self):
        model = self.room_core.create_room_model({"name": "R", "width": 1.0, "depth": 0.8, "height": 2.5})
        self.assertEqual(model["origin"], [0.0, 0.0, 0.0])

    def test_inward_wall_normals(self):
        model = self.room_core.create_room_model({"name": "R", "width": 1.0, "depth": 0.8, "height": 2.5})
        expected = {
            "south": (0.0, 1.0, 0.0),
            "north": (0.0, -1.0, 0.0),
            "west": (1.0, 0.0, 0.0),
            "east": (-1.0, 0.0, 0.0),
        }
        for wall in model["walls"]:
            c = self.room_core.wall_plane_corners(model, wall)
            u = [c[1][i] - c[0][i] for i in range(3)]
            v = [c[3][i] - c[0][i] for i in range(3)]
            n = (
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            )
            length = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
            n = tuple(x / length for x in n)
            exp = expected[wall["side"]]
            for a, b in zip(n, exp):
                self.assertAlmostEqual(a, b, places=5, msg=wall["side"])


if __name__ == "__main__":
    unittest.main()
