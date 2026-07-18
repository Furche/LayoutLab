"""Headless RoomSession + generators (DD-014 Phase B2) — no bpy."""

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


class TestRuntimeSession(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.session import RoomSession

        self.RoomSession = RoomSession
        self.session = RoomSession()

    def test_create_room_export_has_rooms_and_wall_quad(self):
        result = self.session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "KIDS_ROOM",
                        "location": [0, 0, 0],
                        "width": 4.2,
                        "depth": 2.18,
                        "height": 2.6,
                        "wall_thickness": 0.02,
                        "collection": "layoutlab_room",
                    },
                }
            ]
        )
        self.assertTrue(result["ok"])
        export = result["export"]
        self.assertIn("viewer_schema", export)
        self.assertEqual(len(export["rooms"]), 1)
        walls = [
            o
            for o in export["objects"]
            if (o.get("layoutlab") or {}).get("role") == "room_wall"
        ]
        self.assertGreaterEqual(len(walls), 4)
        self.assertEqual(walls[0]["viewer"].get("primitive"), "quad")
        _assert_no_bpy()

    def test_empty_kids_shell_commands(self):
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_shell_commands.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        result = self.session.apply_commands(payload["commands"])
        self.assertTrue(result["ok"], result.get("errors"))
        roles = {(o.get("layoutlab") or {}).get("role") for o in result["export"]["objects"]}
        self.assertIn("room_floor", roles)
        self.assertIn("room_opening", roles)
        self.assertIn("room_fixed", roles)
        _assert_no_bpy()

    def test_analyze_layout_empty_scene(self):
        result = self.session.apply_command({"action": "analyze_layout", "scope": "scene"})
        self.assertTrue(result["analyzed"])
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["findings"], [])


class TestHeadlessGenerators(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.headless_api import execute_generator_headless
        from layoutlab.runtime.mesh_store import MeshStore
        from layoutlab.runtime.session import RoomSession

        self.execute = execute_generator_headless
        self.MeshStore = MeshStore
        self.RoomSession = RoomSession

    def test_desk_basic_export_has_mesh_and_wire_clearance(self):
        store = self.MeshStore()
        result = self.execute(
            "desk_basic",
            {
                "name": "DESK_120x60",
                "location": [2.7, 1.58, 0],
                "width": 1.2,
                "depth": 0.6,
                "height": 0.75,
                "show_clearance": True,
                "collection": "layoutlab_room",
            },
            store=store,
        )
        self.assertEqual(result["generator"], "desk_basic")
        self.assertIn("body", result["parts"])
        self.assertIn("clearance_chair_access", result["parts"])

        session = self.RoomSession()
        session.mesh_store = store
        export = session.apply_commands([])["export"]
        # Re-export from store via empty apply — use export_viewer_scene directly
        from layoutlab.runtime.session import export_viewer_scene

        export = export_viewer_scene(session)
        body = next(o for o in export["objects"] if o["name"].endswith("_body"))
        self.assertEqual(body["viewer"].get("primitive"), "mesh")
        self.assertGreaterEqual(len(body["viewer"]["vertices"]), 8)
        self.assertTrue(body["viewer"]["faces"])

        clearance = next(o for o in export["objects"] if "clearance" in o["name"])
        self.assertEqual(clearance["viewer"].get("display"), "wire")
        # Desk AABB should span legs (width ~1.2)
        self.assertGreater(body["dimensions"][0], 1.0)
        _assert_no_bpy()

    def test_furnished_kids_room_commands(self):
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_commands.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        session = self.RoomSession()
        result = session.apply_commands(payload["commands"])
        self.assertTrue(result["ok"], result.get("errors"))
        export = result["export"]
        self.assertEqual(len(export["rooms"]), 1)
        names = {o["name"] for o in export["objects"]}
        self.assertTrue(any("BED" in n for n in names))
        self.assertTrue(any("DESK" in n for n in names))
        meshes = [o for o in export["objects"] if (o.get("viewer") or {}).get("primitive") == "mesh"]
        self.assertGreaterEqual(len(meshes), 2)
        analysis = export.get("analysis") or {}
        self.assertTrue(analysis.get("analyzed"))
        _assert_no_bpy()

    def test_analyze_detects_blocked_clearance(self):
        """Desk chair zone overlapping a wall should yield a finding."""
        session = self.RoomSession()
        # Narrow room; desk with chair clearance extending past south wall into… wall itself
        result = session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "TINY",
                        "location": [0, 0, 0],
                        "width": 1.5,
                        "depth": 1.0,
                        "height": 2.6,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "desk_basic",
                    "params": {
                        "name": "DESK",
                        "location": [0.1, 0.05, 0],
                        "width": 1.2,
                        "depth": 0.6,
                        "height": 0.75,
                        "show_clearance": True,
                        "clearance_depth": 0.5,
                        "collection": "layoutlab_room",
                    },
                },
                {"action": "analyze_layout", "scope": "scene"},
            ]
        )
        self.assertTrue(result["ok"], result.get("errors"))
        analysis = result["results"][-1]["result"]
        self.assertTrue(analysis["analyzed"])
        # Chair clearance at y=-0.5..0 overlaps south wall at y=0
        self.assertGreaterEqual(analysis["summary"]["errors"] + analysis["summary"]["warnings"], 1)
        self.assertTrue(analysis["findings"])
        export = result["export"]
        self.assertTrue(export["analysis"]["analyzed"])
        self.assertGreaterEqual(len(export["analysis"]["findings"]), 1)
        _assert_no_bpy()

    def test_delete_collection_accepts_params_collection(self):
        session = self.RoomSession()
        session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "R",
                        "width": 3,
                        "depth": 3,
                        "height": 2.5,
                        "collection": "layoutlab_room",
                    },
                }
            ]
        )
        self.assertEqual(len(session.list_rooms()), 1)
        result = session.apply_commands(
            [
                {
                    "action": "delete_collection_objects",
                    "params": {"collection": "layoutlab_room"},
                }
            ]
        )
        self.assertTrue(result["ok"], result.get("errors"))
        self.assertEqual(len(session.list_rooms()), 0)

    def test_flat_run_generator_uses_location(self):
        session = self.RoomSession()
        result = session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "R",
                        "width": 4,
                        "depth": 3,
                        "height": 2.5,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "name": "BED",
                    "location": [1.0, 0.15, 0],
                    "width": 2.0,
                    "length": 1.2,
                    "head_side": "y_min",
                    "collection": "layoutlab_room",
                },
            ]
        )
        self.assertTrue(result["ok"], result.get("errors"))
        beds = [o for o in result["export"]["objects"] if o["name"].startswith("BED")]
        self.assertTrue(beds)
        # Flat location must be honored (defaults would place near origin differently).
        locs = [o.get("location") or [0, 0, 0] for o in beds]
        self.assertTrue(any(abs(float(loc[1]) - 0.15) < 0.05 for loc in locs), locs)


if __name__ == "__main__":
    unittest.main()
