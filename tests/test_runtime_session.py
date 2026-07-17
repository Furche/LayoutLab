"""Headless RoomSession + viewer export (DD-014 Phase B) — no bpy."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert_no_bpy():
    if "bpy" in sys.modules:
        raise AssertionError("bpy must not be imported for headless room session tests")


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
        self.assertEqual(export["rooms"][0]["name"], "KIDS_ROOM")

        walls = [
            o
            for o in export["objects"]
            if (o.get("layoutlab") or {}).get("role") == "room_wall"
            or o.get("custom_properties", {}).get("layoutlab_role") == "room_wall"
        ]
        self.assertGreaterEqual(len(walls), 4)
        quad = walls[0].get("viewer") or {}
        self.assertEqual(quad.get("primitive"), "quad")
        self.assertEqual(len(quad.get("corners") or []), 4)
        _assert_no_bpy()

    def test_empty_kids_shell_commands(self):
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_shell_commands.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        result = self.session.apply_commands(payload["commands"])
        self.assertTrue(result["ok"], result.get("errors"))
        export = result["export"]
        self.assertEqual(len(export["rooms"]), 1)
        roles = {
            (o.get("layoutlab") or {}).get("role")
            or o.get("custom_properties", {}).get("layoutlab_role")
            for o in export["objects"]
        }
        self.assertIn("room_floor", roles)
        self.assertIn("room_wall", roles)
        self.assertIn("room_opening", roles)
        self.assertIn("room_fixed", roles)
        openings = [
            o
            for o in export["objects"]
            if (o.get("layoutlab") or {}).get("role") == "room_opening"
        ]
        self.assertEqual(len(openings), 2)
        self.assertEqual(openings[0]["viewer"].get("display"), "wire")
        # Collection clear then recreate works
        again = self.session.apply_commands(payload["commands"])
        self.assertTrue(again["ok"])
        self.assertEqual(len(again["export"]["rooms"]), 1)
        _assert_no_bpy()

    def test_unsupported_generator_rejected(self):
        with self.assertRaises(ValueError):
            self.session.apply_command(
                {"action": "run_generator", "generator": "bed_basic", "params": {}}
            )

    def test_session_module_loads_without_bpy(self):
        """Import path used by the HTTP server must not pull bpy."""
        # Fresh load check: package already imported in setUp; ensure bpy still absent.
        _assert_no_bpy()
        spec = importlib.util.find_spec("layoutlab.runtime.session")
        self.assertIsNotNone(spec)


if __name__ == "__main__":
    unittest.main()
