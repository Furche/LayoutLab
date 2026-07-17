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

    def test_analyze_layout_rejected(self):
        with self.assertRaises(ValueError):
            self.session.apply_command({"action": "analyze_layout", "scope": "scene"})


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
        _assert_no_bpy()


if __name__ == "__main__":
    unittest.main()
