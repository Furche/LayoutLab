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

    def test_unknown_recipe(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        out = dispatch_tool(RoomSession(), "plan_layout", {"recipe": "spaceship"})
        self.assertFalse(out["ok"])
        self.assertIn("bedroom_basic", out["known_recipes"])


if __name__ == "__main__":
    unittest.main()
