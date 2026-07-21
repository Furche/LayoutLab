"""DD-016 bedroom_basic recipe + plan_layout tool."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestBedroomBasicRecipe(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_plan_layout_tool_returns_commands(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "recipe": "bedroom_basic",
                "width": 4.0,
                "depth": 3.5,
                "include_desk": True,
                "include_wardrobe": True,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["recipe"], "bedroom_basic")
        actions = [c.get("action") for c in out["commands"]]
        self.assertIn("create_room", actions)
        self.assertIn("add_opening", actions)
        self.assertIn("run_generator", actions)
        gens = [
            c.get("generator")
            for c in out["commands"]
            if c.get("action") == "run_generator"
        ]
        self.assertEqual(set(gens), {"bed_basic", "wardrobe_basic", "desk_basic"})
        # Live session unchanged
        summary = dispatch_tool(session, "get_scene_summary", {})
        self.assertEqual(len(summary.get("rooms") or []), 0)

    def test_bedroom_basic_dry_run_no_hard_errors_4x35(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        plan = dispatch_tool(
            session,
            "plan_layout",
            {"recipe": "bedroom_basic", "width": 4.0, "depth": 3.5},
        )
        dry = dispatch_tool(
            session,
            "dry_run_commands",
            {"commands": plan["commands"], "analyze": True},
        )
        self.assertTrue(dry.get("apply_ok"), dry.get("errors"))
        summary = (dry.get("analysis") or {}).get("summary") or {}
        self.assertEqual(int(summary.get("errors") or 0), 0, dry.get("analysis"))
        bed = next(
            c
            for c in plan["commands"]
            if c.get("generator") == "bed_basic"
        )
        self.assertEqual(bed["params"]["head_side"], "y_min")
        self.assertLess(float(bed["params"]["location"][1]), 0.2)
        # 120×200 human: along wall 1.2 (length/X), into room 2.0 (width/Y)
        self.assertAlmostEqual(float(bed["params"]["length"]), 1.2, places=2)
        self.assertAlmostEqual(float(bed["params"]["width"]), 2.0, places=2)

    def test_bedroom_basic_dry_run_no_hard_errors_4x4(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        plan = dispatch_tool(
            session,
            "plan_layout",
            {"recipe": "bedroom_basic", "width": 4.0, "depth": 4.0},
        )
        dry = dispatch_tool(
            session,
            "dry_run_commands",
            {"commands": plan["commands"], "analyze": True},
        )
        self.assertTrue(dry.get("apply_ok"), dry.get("errors"))
        summary = (dry.get("analysis") or {}).get("summary") or {}
        self.assertEqual(int(summary.get("errors") or 0), 0, dry.get("analysis"))

    def test_window_count_two_no_overlap_apply(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        plan = dispatch_tool(
            session,
            "plan_layout",
            {
                "recipe": "bedroom_basic",
                "width": 3.0,
                "depth": 5.0,
                "window_count": 2,
            },
        )
        self.assertTrue(plan["ok"], plan)
        wins = [
            c
            for c in plan["commands"]
            if c.get("action") == "add_opening"
            and (c.get("params") or {}).get("kind") == "window"
        ]
        self.assertEqual(len(wins), 2)
        applied = session.apply_commands(plan["commands"])
        self.assertTrue(applied["ok"], applied.get("errors"))

    def test_plan_layout_baseline_overrides_bad_llm_windows(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        planned = dispatch_tool(
            session,
            "plan_layout",
            {"recipe": "bedroom_basic", "width": 3.0, "depth": 5.0, "window_count": 1},
        )
        last_plan = {
            "arguments": {
                "recipe": "bedroom_basic",
                "width": 3.0,
                "depth": 5.0,
                "window_count": 1,
            },
            "commands": planned["commands"],
            "assumes": planned.get("assumes") or [],
        }
        # Simulate LLM inventing four overlapping windows
        bad = {
            "reply": "Schlafzimmer mit 2 Fenstern",
            "questions": [],
            "commands": [
                {"action": "create_room", "params": {"width": 5, "depth": 3}},
                {
                    "action": "add_opening",
                    "params": {"kind": "door", "wall_side": "east", "width": 0.9},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "window", "wall_side": "north", "width": 1.2},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "window", "wall_side": "north", "width": 1.2},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "window", "wall_side": "south", "width": 1.2},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "window", "wall_side": "south", "width": 1.2},
                },
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {"location": [0, 0, 0], "length": 2, "width": 1.2},
                },
            ],
            "proposal": {"commands": [], "assumes": []},
        }
        bad["proposal"]["commands"] = bad["commands"]
        fixed = ag._apply_plan_layout_baseline(
            session,
            bad,
            "3x 5m groß, 2 fenster, eine tür",
            last_plan,
        )
        self.assertTrue(fixed.get("plan_layout_enforced"))
        wins = [
            c
            for c in fixed["commands"]
            if c.get("action") == "add_opening"
            and (c.get("params") or {}).get("kind") == "window"
        ]
        self.assertEqual(len(wins), 2, wins)
        applied = session.clone().apply_commands(fixed["commands"])
        self.assertTrue(applied["ok"], applied.get("errors"))
        self.assertIn("Core-Vorschlag:", fixed["reply"])
        self.assertTrue(fixed.get("selected_id") or fixed.get("planning"))

    def test_parse_room_size(self):
        from layoutlab.runtime import agent as ag

        self.assertEqual(ag._parse_room_size_m("3x 5m groß, 2 fenster"), (3.0, 5.0))
        self.assertEqual(ag._parse_room_size_m("raum 4.0 x 3.5 m"), (4.0, 3.5))
        self.assertIsNone(ag._parse_room_size_m("bett auf 120x200"))
