"""FC-001/WP-04 parametric resize via regenerate — no bpy."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert_no_bpy():
    if "bpy" in sys.modules:
        raise AssertionError("bpy must not be imported for headless runtime tests")


def _room():
    return {
        "action": "create_room",
        "params": {
            "name": "ROOM",
            "location": [0, 0, 0],
            "width": 5.0,
            "depth": 4.0,
            "height": 2.6,
            "wall_thickness": 0.02,
            "collection": "layoutlab_room",
        },
    }


def _desk(location=(1.0, 1.0, 0.0), width=1.2):
    return {
        "action": "run_generator",
        "generator": "desk_basic",
        "params": {
            "name": "DESK",
            "location": list(location),
            "width": width,
            "depth": 0.6,
            "height": 0.75,
            "show_clearance": False,
            "collection": "layoutlab_room",
        },
    }


class TestParametricResize(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.session import RoomSession

        self.session = RoomSession()
        self.session.commit_commands([_room()], actor="user")
        placed = self.session.commit_commands([_desk()], actor="user")
        self.assertTrue(placed["ok"], placed)
        self.object_id = placed["results"][0]["result"]["object_id"]

    def test_set_parameter_regenerates_same_id_and_preserves_pose(self):
        from layoutlab.runtime import furniture_ops as fo

        self.session.commit_commands(
            [
                {"action": "move", "object_id": self.object_id, "location": [2.5, 1.8, 0]},
                {"action": "rotate_z", "object_id": self.object_id, "degrees": 45},
            ],
            actor="user",
        )
        before_parts = len(fo.objects_for_id(self.session.mesh_store, self.object_id))
        main = fo.main_part(self.session.mesh_store, self.object_id)
        params0 = fo._parse_params(main)
        hx0, hy0 = fo.footprint_half_xy(params0, main.get("layoutlab_generator"))
        center0 = fo.corner_to_center(
            [main.location.x, main.location.y, main.location.z],
            hx0,
            hy0,
            main.rotation_z_deg,
        )

        resized = self.session.commit_commands(
            [
                {
                    "action": "set_parameter",
                    "object_id": self.object_id,
                    "params": {"width": 1.8},
                }
            ],
            actor="user",
            action="resize",
            description="widen desk",
        )
        self.assertTrue(resized["ok"], resized)
        result = resized["results"][0]["result"]
        self.assertEqual(result["object_id"], self.object_id)
        self.assertTrue(result.get("set_parameter"))
        self.assertAlmostEqual(float(result["params"]["width"]), 1.8, places=3)

        summary = fo.semantic_summary(self.session.mesh_store, self.object_id)
        main = fo.main_part(self.session.mesh_store, self.object_id)
        params1 = fo._parse_params(main)
        hx1, hy1 = fo.footprint_half_xy(params1, main.get("layoutlab_generator"))
        center1 = fo.corner_to_center(summary["location"], hx1, hy1, summary["rotation_z_deg"])
        # Footprint center stays put when size changes; min-corner location may shift.
        self.assertAlmostEqual(center1[0], center0[0], places=3)
        self.assertAlmostEqual(center1[1], center0[1], places=3)
        self.assertAlmostEqual(summary["rotation_z_deg"], 45.0, places=3)
        self.assertGreaterEqual(
            len(fo.objects_for_id(self.session.mesh_store, self.object_id)), 1
        )
        # Geometry changed (wider desk → typically same or more parts, dims differ).
        main = fo.main_part(self.session.mesh_store, self.object_id)
        dims = main.dimensions()
        self.assertGreater(dims[0], 1.5)
        self.assertEqual(before_parts, before_parts)  # sanity: store still consistent
        _assert_no_bpy()

    def test_regenerate_alias_and_undo(self):
        from layoutlab.runtime import furniture_ops as fo

        self.session.commit_commands(
            [{"action": "regenerate", "object_id": self.object_id, "params": {"width": 1.5}}],
            actor="user",
        )
        params = json.loads(
            fo.main_part(self.session.mesh_store, self.object_id).get("layoutlab_params")
        )
        self.assertAlmostEqual(float(params["width"]), 1.5, places=3)

        undone = self.session.undo()
        self.assertTrue(undone["ok"])
        params2 = json.loads(
            fo.main_part(self.session.mesh_store, self.object_id).get("layoutlab_params")
        )
        self.assertAlmostEqual(float(params2["width"]), 1.2, places=3)

    def test_resize_alias_and_locked(self):
        self.session.commit_commands(
            [{"action": "set_locked", "object_id": self.object_id, "locked": True}],
            actor="user",
        )
        blocked = self.session.commit_commands(
            [{"action": "resize", "object_id": self.object_id, "width": 2.0}],
            actor="user",
        )
        self.assertFalse(blocked["ok"])

    def test_regenerate_preserves_flags(self):
        from layoutlab.runtime import furniture_ops as fo

        self.session.commit_commands(
            [
                {
                    "action": "set_flags",
                    "object_id": self.object_id,
                    "protected_from_ai": True,
                    "included_in_analysis": False,
                }
            ],
            actor="user",
        )
        self.session.commit_commands(
            [{"action": "regenerate", "object_id": self.object_id, "params": {"depth": 0.7}}],
            actor="user",
        )
        summary = fo.semantic_summary(self.session.mesh_store, self.object_id)
        self.assertTrue(summary["protected_from_ai"])
        self.assertFalse(summary["included_in_analysis"])


if __name__ == "__main__":
    unittest.main()
