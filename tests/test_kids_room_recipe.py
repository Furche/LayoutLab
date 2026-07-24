"""DD-016 kids_room_basic recipe + routing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestKidsRoomRecipe(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_resolve_kinderzimmer(self):
        from layoutlab.runtime.planning import resolve_recipe_id

        self.assertEqual(
            resolve_recipe_id(conversation="richt ein kinderzimmer ein"),
            "kids_room_basic",
        )
        self.assertEqual(
            resolve_recipe_id(requirements={"room_type": "kids_room"}),
            "kids_room_basic",
        )

    def test_kinderzimmer_not_bedroom(self):
        from layoutlab.runtime.planning import resolve_recipe_id

        self.assertEqual(
            resolve_recipe_id(conversation="kinderzimmer mit bett und schreibtisch"),
            "kids_room_basic",
        )

    def test_plan_layout_kids_room(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "recipe": "kids_room_basic",
                "width": 4.0,
                "depth": 3.0,
                "include_desk": True,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["recipe"], "kids_room_basic")
        self.assertIn("play", out.get("recipe_goals") or [])
        gens = [
            c.get("generator")
            for c in out["commands"]
            if c.get("action") == "run_generator"
        ]
        self.assertIn("bed_basic", gens)
        self.assertIn("desk_basic", gens)
        self.assertNotIn("wardrobe_basic", gens)

    def test_kids_candidates_shortlist(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "mode": "candidates",
                "recipe": "kids_room_basic",
                "width": 4.0,
                "depth": 3.0,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["recipe"], "kids_room_basic")
        self.assertTrue(out.get("shortlist_ids"), out)
        self.assertIn(out["selected_id"], out["shortlist_ids"])
        self.assertGreaterEqual(len(out.get("candidates") or []), 2)

    def test_kids_fixture_size_dry_run(self):
        """Reference-like shallow kids room should still produce a usable plan."""
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        planned = dispatch_tool(
            session,
            "plan_layout",
            {
                "recipe": "kids_room_basic",
                "width": 4.2,
                "depth": 2.18,
                "bed_width": 1.2,
                "bed_length": 2.0,
                "include_desk": True,
                "strategy": "bed_west__desk_north",
            },
        )
        self.assertTrue(planned["ok"], planned)
        dry = dispatch_tool(
            session,
            "dry_run_commands",
            {"commands": planned["commands"], "analyze": True},
        )
        summary = (dry.get("analysis") or {}).get("summary") or {}
        self.assertEqual(int(summary.get("errors") or 0), 0, dry.get("analysis"))

    def test_list_recipes_includes_kids(self):
        from layoutlab.runtime.planning import list_recipes

        self.assertIn("bedroom_basic", list_recipes())
        self.assertIn("kids_room_basic", list_recipes())


if __name__ == "__main__":
    unittest.main()
