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
        self.assertTrue(any("door" in m for m in missing))
        self.assertTrue(any("bed_basic" in m for m in missing))

    def test_proposal_missing_detects_windows_even_with_door(self):
        from layoutlab.runtime import agent as ag

        conv = "raum mit 2 fenstern, einer tür und einem bett"
        cmds = [
            {"action": "create_room", "params": {"width": 4, "depth": 5}},
            {
                "action": "add_opening",
                "params": {"room": "R", "kind": "door", "wall_side": "east", "offset": 0.3},
            },
            {"action": "run_generator", "generator": "bed_basic", "params": {"location": [0, 0, 0]}},
        ]
        missing = ag._proposal_missing_requested(conv, cmds)
        self.assertTrue(any("window" in m for m in missing), missing)
        self.assertEqual(ag._requested_window_count(conv), 2)
        # Door alone must not satisfy window requirement
        self.assertFalse(any("door" in m for m in missing), missing)

    def test_requested_window_count_words(self):
        from layoutlab.runtime import agent as ag

        self.assertEqual(ag._requested_window_count("zwei fenster bitte"), 2)
        self.assertEqual(ag._requested_window_count("ein fenster"), 1)
        self.assertEqual(ag._requested_window_count("nur bett"), 0)

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

    def test_validate_accepts_params_collection(self):
        out = self.dispatch(
            self.session,
            "validate_commands",
            {
                "commands": [
                    {
                        "action": "delete_collection_objects",
                        "params": {"collection": "layoutlab_room"},
                    }
                ]
            },
        )
        self.assertTrue(out["ok"], out)

    def test_deterministic_bed_head_and_wardrobe_nudge(self):
        from layoutlab.runtime import agent as ag

        result = {
            "reply": "ok",
            "commands": [
                {
                    "action": "create_room",
                    "params": {"width": 4.0, "depth": 3.0, "collection": "layoutlab_room"},
                },
                {
                    "action": "add_opening",
                    "params": {"room": "ROOM", "kind": "door", "wall_side": "east", "width": 0.9},
                },
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [1.0, 0.15, 0],
                        "length": 2.0,
                        "width": 1.2,
                        "head_side": "y_max",
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "wardrobe_basic",
                    "params": {
                        "name": "WARDROBE",
                        "location": [2.5, 0.15, 0],
                        "width": 1.0,
                        "depth": 0.6,
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": [], "expected_risks": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes(
            "das bett steht mit dem kopfende in den raum", result
        )
        bed = next(c for c in fixed["commands"] if c.get("generator") == "bed_basic")
        wardrobe = next(c for c in fixed["commands"] if c.get("generator") == "wardrobe_basic")
        self.assertEqual(bed["params"]["head_side"], "y_min")
        self.assertLess(float(bed["params"]["location"][1]), 0.2)
        self.assertLess(float(wardrobe["params"]["location"][0]), 1.0)

    def test_floating_bed_snaps_to_wall(self):
        from layoutlab.runtime import agent as ag

        result = {
            "reply": "ok",
            "commands": [
                {"action": "create_room", "params": {"width": 4.0, "depth": 3.5}},
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [1.0, 1.15, 0],
                        "length": 2.0,
                        "width": 1.2,
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes("bau ein schlafzimmer", result)
        bed = next(c for c in fixed["commands"] if c.get("generator") == "bed_basic")
        self.assertEqual(bed["params"]["head_side"], "y_min")
        self.assertLess(float(bed["params"]["location"][1]), 0.2)

    def test_better_layout_moves_furniture(self):
        from layoutlab.runtime import agent as ag

        ag._LAST_PLACEMENT_FP = (
            ("bed_basic", (2.0, 1.0, 0.0), None, None),
            ("wardrobe_basic", (0.5, 1.5, 0.0), None, None),
            ("desk_basic", (1.5, 0.5, 0.0), None, None),
        )
        result = {
            "reply": "besser",
            "commands": [
                {"action": "create_room", "params": {"width": 4.0, "depth": 3.5}},
                {
                    "action": "add_opening",
                    "params": {"room": "ROOM", "kind": "door", "wall_side": "east", "width": 0.9},
                },
                {
                    "action": "add_opening",
                    "params": {"room": "ROOM", "kind": "window", "wall_side": "south", "width": 1.2},
                },
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [2.0, 1.0, 0],
                        "length": 2.0,
                        "width": 1.2,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "wardrobe_basic",
                    "params": {
                        "name": "WARDROBE",
                        "location": [0.5, 1.5, 0],
                        "width": 1.0,
                        "depth": 0.6,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "desk_basic",
                    "params": {
                        "name": "DESK",
                        "location": [1.5, 0.5, 0],
                        "width": 1.2,
                        "depth": 0.6,
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes(
            "glaubst du du findest eine bessere lösung", result
        )
        bed = next(c for c in fixed["commands"] if c.get("generator") == "bed_basic")
        desk = next(c for c in fixed["commands"] if c.get("generator") == "desk_basic")
        self.assertEqual(bed["params"]["head_side"], "y_max")
        self.assertNotEqual(tuple(bed["params"]["location"]), (2.0, 1.0, 0))
        self.assertLess(float(desk["params"]["location"][0]), 1.0)
        ag._LAST_PLACEMENT_FP = None


    def test_desk_bed_overlap_separated(self):
        from layoutlab.runtime import agent as ag

        result = {
            "reply": "ok",
            "commands": [
                {"action": "create_room", "params": {"width": 4.0, "depth": 3.5}},
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [1.4, 0.08, 0],
                        "length": 1.2,
                        "width": 2.0,
                        "head_side": "y_min",
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "desk_basic",
                    "params": {
                        "name": "DESK",
                        "location": [1.4, 0.5, 0],
                        "width": 1.5,
                        "depth": 0.7,
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes("schlafzimmer", result)
        bed = next(c for c in fixed["commands"] if c.get("generator") == "bed_basic")
        desk = next(c for c in fixed["commands"] if c.get("generator") == "desk_basic")
        # South-wall bed: sleep along Y → width (Y) is mattress length, length (X) is mattress width
        self.assertGreaterEqual(float(bed["params"]["width"]), float(bed["params"]["length"]))
        bed_box = ag._gen_xy_aabb("bed_basic", bed["params"])
        desk_box = ag._gen_xy_aabb("desk_basic", desk["params"])
        self.assertFalse(ag._aabb_overlap_tuple(bed_box, desk_box), (bed_box, desk_box))

    def test_parse_bed_size_and_apply(self):
        from layoutlab.runtime import agent as ag

        self.assertEqual(ag._parse_bed_size_m("bett auf 120x200 machen"), (1.2, 2.0))
        self.assertEqual(ag._parse_bed_size_m("bett 1.4 × 2.0 m"), (1.4, 2.0))
        self.assertIsNone(ag._parse_bed_size_m("3x 5m groß"))
        self.assertEqual(ag._mattress_to_bed_axes("y_min", 1.2, 2.0), (1.2, 2.0))
        self.assertEqual(ag._mattress_to_bed_axes("x_max", 1.2, 2.0), (2.0, 1.2))

        result = {
            "reply": "angepasst",
            "commands": [
                {"action": "create_room", "params": {"width": 4.0, "depth": 3.5}},
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [0.08, 0.08, 0],
                        "length": 1.0,
                        "width": 1.8,
                        "head_side": "y_min",
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes(
            "kannst du das bett auf 120x200 machen?", result
        )
        bed = next(c for c in fixed["commands"] if c.get("generator") == "bed_basic")
        self.assertAlmostEqual(float(bed["params"]["length"]), 1.2, places=2)
        self.assertAlmostEqual(float(bed["params"]["width"]), 2.0, places=2)
        self.assertIn("120×200", fixed["reply"])

    def test_bed_size_noop_no_false_wall_note(self):
        from layoutlab.runtime import agent as ag

        result = {
            "reply": "Ich habe das Bett angepasst.",
            "commands": [
                {"action": "create_room", "params": {"width": 4.0, "depth": 3.5}},
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [0.08, 0.08, 0],
                        "length": 1.2,
                        "width": 2.0,
                        "head_side": "y_min",
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes(
            "kannst du das bett auf 120x200 machen?", result
        )
        self.assertIn("bereits", fixed["reply"].lower())
        self.assertNotIn("Layout-Korrektur", fixed["reply"])

    def test_good_recipe_bed_no_wall_spam(self):
        from layoutlab.runtime import agent as ag

        result = {
            "reply": "Schlafzimmer geplant.",
            "commands": [
                {"action": "create_room", "params": {"width": 4.0, "depth": 3.5}},
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [0.08, 0.08, 0],
                        "length": 1.2,
                        "width": 2.0,
                        "head_side": "y_min",
                        "collection": "layoutlab_room",
                    },
                },
            ],
            "proposal": {"commands": []},
        }
        result["proposal"]["commands"] = result["commands"]
        fixed = ag._apply_deterministic_placement_fixes("bau ein schlafzimmer", result)
        self.assertNotIn("Layout-Korrektur", fixed.get("reply") or "")

    def test_observation_detects_problems_phrase(self):
        from layoutlab.runtime import agent as ag

        self.assertTrue(ag._is_observation_query("siehst du was eventuell problematisch sein könnte?"))
        self.assertTrue(ag._is_observation_query("siehst du auch, dass der tisch im bett drin steht?"))
        self.assertFalse(ag._is_observation_query("kannst du mir ein layout bauen welches physikalisch möglich ist"))


if __name__ == "__main__":
    unittest.main()
