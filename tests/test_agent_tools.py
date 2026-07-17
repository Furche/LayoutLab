"""Agent read tools over RoomSession — no bpy / no network."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestAgentTools(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        self.dispatch = dispatch_tool
        self.session = RoomSession()
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_commands.json"
        cmds = json.loads(fixture.read_text(encoding="utf-8"))["commands"]
        result = self.session.apply_commands(cmds)
        self.assertTrue(result["ok"], result.get("errors"))

    def test_scene_summary(self):
        out = self.dispatch(self.session, "get_scene_summary", {})
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["rooms"]), 1)
        self.assertEqual(out["rooms"][0]["name"], "KIDS_ROOM")
        self.assertIn("bed_basic", out["generators_present"])
        self.assertTrue(out["analysis"]["analyzed"])

    def test_get_room(self):
        out = self.dispatch(self.session, "get_room", {"room": "KIDS_ROOM"})
        self.assertEqual(out["room"]["footprint"]["width"], 4.2)
        self.assertGreaterEqual(len(out["room"]["openings"]), 2)
        self.assertNotIn("corners", json.dumps(out))

    def test_list_and_get_object(self):
        listed = self.dispatch(self.session, "list_objects", {"generators": ["desk_basic"]})
        self.assertGreaterEqual(listed["count"], 1)
        name = listed["objects"][0]["name"]
        got = self.dispatch(self.session, "get_object", {"name": name})
        self.assertEqual(got["object"]["name"], name)
        self.assertIn("params", got["object"])

    def test_analysis_and_actions(self):
        analysis = self.dispatch(self.session, "get_analysis", {"scope": "scene"})
        self.assertTrue(analysis["analyzed"])
        actions = self.dispatch(self.session, "list_supported_actions", {})
        self.assertIn("run_generator", actions["actions"])

    def test_list_generators(self):
        gens = self.dispatch(self.session, "list_generators", {})
        names = {g["name"] for g in gens["generators"]}
        self.assertIn("bed_basic", names)
        self.assertIn("wardrobe_basic", names)

    def test_unknown_tool(self):
        with self.assertRaises(ValueError):
            self.dispatch(self.session, "explode_room", {})

    def test_agent_demo_turn(self):
        from layoutlab.runtime.agent import run_agent_turn

        out = run_agent_turn(self.session, "lösche den raum", llm_config=None)
        self.assertTrue(out["ok"])
        self.assertEqual(out["mode"], "demo")
        self.assertEqual(out["proposal"]["commands"][0]["action"], "delete_collection_objects")


if __name__ == "__main__":
    unittest.main()
