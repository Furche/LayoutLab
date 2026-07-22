"""FC-001/WP-05 wall/corner resize + inactive openings — no bpy."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert_no_bpy():
    if "bpy" in sys.modules:
        raise AssertionError("bpy must not be imported")


class TestMoveWallCore(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.core import room as room_core

        self.room = room_core
        self.model = room_core.create_room_model(
            {"name": "R", "location": [0, 0, 0], "width": 4.0, "depth": 3.0, "height": 2.6}
        )
        self.room.add_opening(
            self.model,
            {
                "name": "win_west",
                "kind": "window",
                "wall_side": "west",
                "offset": 2.2,
                "width": 0.6,
                "height": 1.2,
                "sill_height": 0.9,
            },
        )
        self.room.add_fixed_element(
            self.model,
            {
                "name": "rad_west",
                "kind": "radiator",
                "wall_side": "west",
                "offset": 2.3,
                "width": 0.5,
                "depth": 0.1,
                "height": 0.6,
            },
        )

    def test_move_north_inward_makes_west_opening_inactive(self):
        # West opening ends at 2.8; shrink depth to 2.0 → inactive
        self.room.move_wall(self.model, "north", -1.0)
        self.assertAlmostEqual(self.model["footprint"]["depth"], 2.0, places=3)
        win = self.model["openings"][0]
        rad = self.model["fixed_elements"][0]
        self.assertEqual(win["state"], self.room.ATTACHMENT_INACTIVE_OUTSIDE_WALL)
        self.assertEqual(rad["state"], self.room.ATTACHMENT_INACTIVE_OUTSIDE_WALL)
        # Data preserved
        self.assertAlmostEqual(win["width"], 0.6, places=3)
        self.assertEqual(len(self.model["openings"]), 1)

    def test_expand_restores_inactive_opening(self):
        self.room.move_wall(self.model, "north", -1.0)
        self.assertEqual(
            self.model["openings"][0]["state"], self.room.ATTACHMENT_INACTIVE_OUTSIDE_WALL
        )
        self.room.move_wall(self.model, "north", 1.0)
        self.assertEqual(self.model["openings"][0]["state"], self.room.ATTACHMENT_ACTIVE)
        self.assertEqual(self.model["fixed_elements"][0]["state"], self.room.ATTACHMENT_ACTIVE)

    def test_south_move_preserves_west_opening_world_y(self):
        win = self.model["openings"][0]
        world_y_before = self.model["origin"][1] + win["offset"]
        # Move south outward by 0.5 → origin.y -= 0.5, depth += 0.5
        self.room.move_wall(self.model, "south", 0.5)
        win = self.model["openings"][0]
        world_y_after = self.model["origin"][1] + win["offset"]
        self.assertAlmostEqual(world_y_before, world_y_after, places=4)
        self.assertEqual(win["state"], self.room.ATTACHMENT_ACTIVE)

    def test_move_corner_ne(self):
        self.room.move_corner(self.model, "ne", dx=0.5, dy=0.25)
        self.assertAlmostEqual(self.model["footprint"]["width"], 4.5, places=3)
        self.assertAlmostEqual(self.model["footprint"]["depth"], 3.25, places=3)


class TestMoveWallSession(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.session import RoomSession

        self.session = RoomSession()
        self.session.commit_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "ROOM",
                        "location": [0, 0, 0],
                        "width": 4.0,
                        "depth": 3.0,
                        "height": 2.6,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "add_opening",
                    "params": {
                        "name": "ROOM",
                        "opening_name": "win_n",
                        "kind": "window",
                        "wall_side": "north",
                        "offset": 1.0,
                        "width": 1.0,
                        "height": 1.2,
                        "sill_height": 0.9,
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "desk_basic",
                    "params": {
                        "name": "DESK",
                        "location": [1.0, 1.2, 0],
                        "width": 1.0,
                        "depth": 0.5,
                        "height": 0.75,
                        "show_clearance": False,
                        "collection": "layoutlab_room",
                    },
                },
            ],
            actor="user",
        )
        from layoutlab.runtime import furniture_ops as fo

        self.fo = fo
        oid = None
        for o in self.session.mesh_store.objects:
            if o.get("layoutlab_object_id") and o.get("layoutlab_part_type") == "main":
                oid = o.get("layoutlab_object_id")
                break
        self.object_id = oid

    def test_move_wall_keeps_furniture_world_and_marks_invalid(self):
        before = self.fo.semantic_summary(self.session.mesh_store, self.object_id)
        self.assertEqual(before["validity"], self.fo.VALIDITY_VALID)

        # Shrink from north until desk (y≈1.2–1.7) is outside / intersecting.
        result = self.session.commit_commands(
            [{"action": "move_wall", "params": {"name": "ROOM", "wall_side": "north", "delta": -1.8}}],
            actor="user",
        )
        self.assertTrue(result["ok"], result)
        after = self.fo.semantic_summary(self.session.mesh_store, self.object_id)
        self.assertAlmostEqual(after["location"][0], before["location"][0], places=3)
        self.assertAlmostEqual(after["location"][1], before["location"][1], places=3)
        self.assertIn(
            after["validity"],
            (self.fo.VALIDITY_OUTSIDE, self.fo.VALIDITY_WALL),
        )
        model = self.session.get_by_name("ROOM")
        self.assertEqual(model["openings"][0]["state"], "ACTIVE")
        export = result["export"]
        opening_objs = [
            o
            for o in export["objects"]
            if (o.get("layoutlab") or {}).get("role") == "room_opening"
        ]
        self.assertEqual(len(opening_objs), 1)


if __name__ == "__main__":
    unittest.main()
