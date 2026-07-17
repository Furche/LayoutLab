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

    def test_proposal_missing_detects_bed_and_door(self):
        from layoutlab.runtime import agent as ag

        conv = "neuer raum mit bett vor der tür\n3x5 meter"
        missing = ag._proposal_missing_requested(
            conv,
            [{"action": "create_room", "params": {"width": 3, "depth": 5}}],
        )
        self.assertTrue(any("add_opening" in m for m in missing))
        self.assertTrue(any("bed_basic" in m for m in missing))

    def test_validate_commands(self):
        good = self.dispatch(
            self.session,
            "validate_commands",
            {
                "commands": [
                    {"action": "delete_collection_objects", "collection": "layoutlab_room"},
                    {
                        "action": "create_room",
                        "params": {"name": "R", "width": 3, "depth": 5, "height": 2.5},
                    },
                    {
                        "action": "add_opening",
                        "params": {
                            "room": "R",
                            "kind": "door",
                            "wall_side": "east",
                            "offset": 0.3,
                            "width": 0.9,
                            "height": 2.0,
                        },
                    },
                    {
                        "action": "run_generator",
                        "generator": "bed_basic",
                        "params": {"name": "BED", "location": [0.5, 0.2, 0]},
                    },
                ]
            },
        )
        self.assertTrue(good["ok"], good)

        bad = self.dispatch(
            self.session,
            "validate_commands",
            {
                "commands": [
                    {"action": "create_room", "params": {"name": "R"}},
                    {"action": "run_generator", "generator": "sofa_basic", "params": {}},
                    {"action": "explode"},
                ]
            },
        )
        self.assertFalse(bad["ok"])
        codes = {e["code"] for e in bad["errors"]}
        self.assertIn("missing_size", codes)
        self.assertIn("unknown_generator", codes)
        self.assertIn("unknown_action", codes)

    def test_dry_run_does_not_mutate_live_session(self):
        before_rooms = len(self.session.list_rooms())
        before_meshes = len(self.session.mesh_store.objects)
        out = self.dispatch(
            self.session,
            "dry_run_commands",
            {
                "commands": [
                    {"action": "delete_collection_objects", "collection": "layoutlab_room"},
                    {
                        "action": "create_room",
                        "params": {
                            "name": "DRY_ROOM",
                            "width": 3,
                            "depth": 4,
                            "height": 2.5,
                            "collection": "layoutlab_room",
                        },
                    },
                    {
                        "action": "add_opening",
                        "params": {
                            "room": "DRY_ROOM",
                            "opening_name": "door_east",
                            "kind": "door",
                            "wall_side": "east",
                            "offset": 0.4,
                            "width": 0.9,
                            "height": 2.0,
                        },
                    },
                    {
                        "action": "run_generator",
                        "generator": "bed_basic",
                        "params": {
                            "name": "DRY_BED",
                            "location": [0.4, 0.15, 0],
                            "length": 1.2,
                            "width": 2.0,
                            "collection": "layoutlab_room",
                        },
                    },
                ],
                "analyze": True,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertTrue(out["applied"])
        self.assertEqual(out["scene_after"]["rooms"][0]["name"], "DRY_ROOM")
        self.assertIn("bed_basic", out["scene_after"]["generators_present"])
        self.assertIn("analysis", out)
        # Live session unchanged
        self.assertEqual(len(self.session.list_rooms()), before_rooms)
        self.assertEqual(len(self.session.mesh_store.objects), before_meshes)
        self.assertEqual(self.session.list_rooms()[0]["name"], "KIDS_ROOM")

    def test_session_clone_independence(self):
        clone = self.session.clone()
        clone.apply_commands(
            [{"action": "delete_collection_objects", "collection": "layoutlab_room"}]
        )
        self.assertEqual(len(clone.list_rooms()), 0)
        self.assertEqual(self.session.list_rooms()[0]["name"], "KIDS_ROOM")


if __name__ == "__main__":
    unittest.main()
