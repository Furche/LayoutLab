"""FC-001/WP-03 semantic furniture manipulation — no bpy."""

from __future__ import annotations

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
            "width": 4.0,
            "depth": 3.0,
            "height": 2.6,
            "wall_thickness": 0.02,
            "collection": "layoutlab_room",
        },
    }


def _desk(location=(1.0, 1.0, 0.0), name="DESK"):
    return {
        "action": "run_generator",
        "generator": "desk_basic",
        "params": {
            "name": name,
            "location": list(location),
            "width": 1.2,
            "depth": 0.6,
            "height": 0.75,
            "show_clearance": False,
            "collection": "layoutlab_room",
        },
    }


class TestFurnitureManipulation(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.session import RoomSession

        self.session = RoomSession()
        self.session.commit_commands([_room()], actor="user")
        placed = self.session.commit_commands([_desk()], actor="user")
        self.assertTrue(placed["ok"], placed)
        self.object_id = placed["results"][0]["result"]["object_id"]

    def test_semantic_defaults_on_create(self):
        from layoutlab.runtime import furniture_ops as fo

        main = fo.main_part(self.session.mesh_store, self.object_id)
        self.assertIsNotNone(main)
        self.assertEqual(main.get("layoutlab_support_ref"), fo.SUPPORT_ROOM_FLOOR)
        self.assertEqual(main.get("layoutlab_validity"), fo.VALIDITY_VALID)
        self.assertTrue(main.get("layoutlab_room_id"))
        self.assertFalse(main.get("locked"))
        export = self.session.apply_commands([])["export"]
        furniture = [
            o
            for o in export["objects"]
            if (o.get("layoutlab") or {}).get("object_id") == self.object_id
            and (o.get("layoutlab") or {}).get("part_type") == "main"
        ]
        self.assertTrue(furniture)
        self.assertEqual(furniture[0]["layoutlab"]["support_ref"], "room_floor")
        _assert_no_bpy()

    def test_select_is_ephemeral(self):
        rev = self.session.revision
        result = self.session.commit_commands(
            [{"action": "select_object", "object_id": self.object_id}],
            actor="user",
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result.get("ephemeral"))
        self.assertEqual(self.session.revision, rev)
        self.assertNotIn("transaction", result)
        self.assertEqual(self.session.selected_object_id, self.object_id)
        self.assertEqual(result["export"]["selected_object_id"], self.object_id)

    def test_move_xy_and_undo(self):
        moved = self.session.commit_commands(
            [{"action": "move", "object_id": self.object_id, "location": [2.0, 1.5, 0]}],
            actor="user",
            action="gesture",
            description="move desk",
        )
        self.assertTrue(moved["ok"], moved)
        loc = moved["results"][0]["result"]["location"]
        self.assertAlmostEqual(loc[0], 2.0, places=3)
        self.assertAlmostEqual(loc[1], 1.5, places=3)
        self.assertEqual(moved["results"][0]["result"]["support_ref"], "room_floor")

        self.session.undo()
        from layoutlab.runtime import furniture_ops as fo

        summary = fo.semantic_summary(self.session.mesh_store, self.object_id)
        self.assertAlmostEqual(summary["location"][0], 1.0, places=3)

    def test_rotate_z_updates_export(self):
        rotated = self.session.commit_commands(
            [{"action": "rotate_z", "object_id": self.object_id, "degrees": 90}],
            actor="user",
        )
        self.assertTrue(rotated["ok"], rotated)
        self.assertAlmostEqual(rotated["results"][0]["result"]["rotation_z_deg"], 90.0, places=3)
        export = rotated["export"]
        main = next(
            o
            for o in export["objects"]
            if (o.get("layoutlab") or {}).get("object_id") == self.object_id
            and (o.get("layoutlab") or {}).get("part_type") == "main"
        )
        self.assertAlmostEqual(main["rotation_euler_deg"][2], 90.0, places=3)

    def test_rotate_z_preserves_footprint_center(self):
        from layoutlab.runtime import furniture_ops as fo

        main = fo.main_part(self.session.mesh_store, self.object_id)
        params = fo._parse_params(main)
        hx, hy = fo.footprint_half_xy(params, main.get("layoutlab_generator"))
        loc0 = [main.location.x, main.location.y, main.location.z]
        center0 = fo.corner_to_center(loc0, hx, hy, main.rotation_z_deg)

        self.session.commit_commands(
            [{"action": "rotate_z", "object_id": self.object_id, "degrees": 90}],
            actor="user",
        )
        main = fo.main_part(self.session.mesh_store, self.object_id)
        loc1 = [main.location.x, main.location.y, main.location.z]
        center1 = fo.corner_to_center(loc1, hx, hy, main.rotation_z_deg)
        self.assertAlmostEqual(center1[0], center0[0], places=4)
        self.assertAlmostEqual(center1[1], center0[1], places=4)

    def test_clearance_export_keeps_oriented_mesh_after_rotate(self):
        """Clearance viewer hint must keep mesh verts (not AABB) so rotation is visible."""
        from layoutlab.runtime.session import export_viewer_scene

        placed = self.session.commit_commands(
            [
                {
                    "action": "run_generator",
                    "generator": "desk_basic",
                    "params": {
                        "name": "DESK_CL",
                        "location": [2.0, 1.0, 0.0],
                        "width": 1.2,
                        "depth": 0.6,
                        "height": 0.75,
                        "show_clearance": True,
                        "collection": "layoutlab_room",
                    },
                }
            ],
            actor="user",
        )
        self.assertTrue(placed["ok"], placed)
        oid = placed["results"][0]["result"]["object_id"]

        def _clearances(export):
            out = []
            for o in export["objects"]:
                props = o.get("custom_properties") or {}
                role = (o.get("layoutlab") or {}).get("role") or props.get("layoutlab_role")
                if role == "clearance" or props.get("layoutlab_clearance_name"):
                    if (o.get("layoutlab") or {}).get("object_id") == oid:
                        out.append(o)
            return out

        before = export_viewer_scene(self.session)
        clearances = _clearances(before)
        self.assertTrue(clearances, "desk should export a clearance")
        cl0 = clearances[0]
        viewer0 = cl0.get("viewer") or {}
        self.assertEqual(viewer0.get("primitive"), "mesh")
        self.assertEqual(viewer0.get("display"), "wire")
        verts0 = viewer0.get("vertices") or []
        self.assertGreaterEqual(len(verts0), 8)

        self.session.commit_commands(
            [{"action": "rotate_z", "object_id": oid, "degrees": 45}],
            actor="user",
        )
        after = export_viewer_scene(self.session)
        cl1 = _clearances(after)[0]
        viewer1 = cl1.get("viewer") or {}
        self.assertEqual(viewer1.get("primitive"), "mesh")
        verts1 = viewer1.get("vertices") or []
        self.assertEqual(len(verts1), len(verts0))
        moved = any(
            abs(a[0] - b[0]) > 1e-3 or abs(a[1] - b[1]) > 1e-3 for a, b in zip(verts0, verts1)
        )
        self.assertTrue(moved, "clearance verts should change after rotate_z")
        span_x = max(v[0] for v in verts1) - min(v[0] for v in verts1)
        span_y = max(v[1] for v in verts1) - min(v[1] for v in verts1)
        self.assertGreater(span_x, 0.7)
        self.assertGreater(span_y, 0.7)

    def test_invalid_outside_room_still_assigned(self):
        from layoutlab.runtime import furniture_ops as fo

        result = self.session.commit_commands(
            [{"action": "move", "object_id": self.object_id, "location": [10.0, 10.0, 0]}],
            actor="user",
        )
        self.assertTrue(result["ok"], result)
        summary = result["results"][0]["result"]
        self.assertEqual(summary["validity"], fo.VALIDITY_OUTSIDE)
        self.assertTrue(summary["room_id"])
        # Still present in store / membership preserved.
        self.assertIsNotNone(fo.main_part(self.session.mesh_store, self.object_id))

    def test_duplicate_delete_hide_lock(self):
        from layoutlab.runtime import furniture_ops as fo

        dup = self.session.commit_commands(
            [{"action": "duplicate", "object_id": self.object_id, "offset": [0.5, 0, 0]}],
            actor="user",
        )
        self.assertTrue(dup["ok"], dup)
        new_id = dup["results"][0]["result"]["object_id"]
        self.assertNotEqual(new_id, self.object_id)
        self.assertIsNotNone(fo.main_part(self.session.mesh_store, new_id))

        hidden = self.session.commit_commands(
            [{"action": "hide", "object_id": new_id}],
            actor="user",
        )
        self.assertTrue(hidden["ok"])
        self.assertFalse(hidden["results"][0]["result"]["visible"])

        locked = self.session.commit_commands(
            [{"action": "set_locked", "object_id": new_id, "locked": True}],
            actor="user",
        )
        self.assertTrue(locked["ok"])
        blocked = self.session.commit_commands(
            [{"action": "move", "object_id": new_id, "location": [0.5, 0.5, 0]}],
            actor="user",
        )
        self.assertFalse(blocked["ok"])

        # Unlock then delete
        self.session.commit_commands(
            [{"action": "set_locked", "object_id": new_id, "locked": False}],
            actor="user",
        )
        deleted = self.session.commit_commands(
            [{"action": "delete", "object_id": new_id}],
            actor="user",
        )
        self.assertTrue(deleted["ok"], deleted)
        self.assertIsNone(fo.main_part(self.session.mesh_store, new_id))

    def test_preview_move_then_commit(self):
        begun = self.session.begin_preview(
            [{"action": "move", "object_id": self.object_id, "location": [2.5, 1.0, 0]}],
            actor="user",
        )
        self.assertTrue(begun["ok"])
        self.assertEqual(self.session.revision, 2)  # room + desk commits
        self.assertFalse(self.session.can_undo)  # preview blocks undo property... actually can_undo is False when preview active
        committed = self.session.commit_preview(action="gesture")
        self.assertTrue(committed["ok"], committed)
        self.assertEqual(self.session.revision, 3)
        from layoutlab.runtime import furniture_ops as fo

        summary = fo.semantic_summary(self.session.mesh_store, self.object_id)
        self.assertAlmostEqual(summary["location"][0], 2.5, places=3)


if __name__ == "__main__":
    unittest.main()
