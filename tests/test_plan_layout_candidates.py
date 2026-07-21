"""DD-011 plan_layout mode=candidates — expand, soft-rank, select."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestPlanLayoutCandidates(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_candidates_mode_returns_distinct_ids(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "mode": "candidates",
                "recipe": "bedroom_basic",
                "width": 4.0,
                "depth": 3.5,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertEqual(out.get("mode"), "candidates")
        cands = out.get("candidates") or []
        self.assertGreaterEqual(len(cands), 2)
        ids = [c["candidate_id"] for c in cands]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(out["selected_id"], ids)
        self.assertTrue(out.get("commands"))
        self.assertEqual(out.get("recipe"), "bedroom_basic")
        self.assertEqual(out.get("recipe_kind"), "room_use")
        self.assertEqual(list(out.get("recipe_goals") or []), ["sleep", "storage"])
        self.assertTrue(out.get("selection_reason"))

    def test_selected_has_zero_hard_errors_4x35(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "mode": "candidates",
                "recipe": "bedroom_basic",
                "width": 4.0,
                "depth": 3.5,
            },
        )
        self.assertTrue(out["ok"], out)
        selected = next(c for c in out["candidates"] if c["candidate_id"] == out["selected_id"])
        q = selected.get("quality") or {}
        self.assertFalse(q.get("has_hard_errors"), q)
        self.assertEqual(int(q.get("hard_errors") or 0), 0, q)
        dry = dispatch_tool(
            session,
            "dry_run_commands",
            {"commands": out["commands"], "analyze": True},
        )
        self.assertTrue(dry.get("apply_ok"), dry.get("errors"))
        summary = (dry.get("analysis") or {}).get("summary") or {}
        self.assertEqual(int(summary.get("errors") or 0), 0, dry.get("analysis"))

    def test_selected_id_stable(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        params = {
            "mode": "candidates",
            "recipe": "bedroom_basic",
            "width": 4.0,
            "depth": 3.5,
        }
        a = dispatch_tool(RoomSession(), "plan_layout", params)
        b = dispatch_tool(RoomSession(), "plan_layout", params)
        self.assertEqual(a["selected_id"], b["selected_id"])
        self.assertEqual(
            [c["candidate_id"] for c in a["candidates"]],
            [c["candidate_id"] for c in b["candidates"]],
        )

    def test_live_session_unchanged(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        dispatch_tool(
            session,
            "plan_layout",
            {
                "mode": "candidates",
                "recipe": "bedroom_basic",
                "width": 4.0,
                "depth": 3.5,
            },
        )
        summary = dispatch_tool(session, "get_scene_summary", {})
        self.assertEqual(len(summary.get("rooms") or []), 0)

    def test_single_mode_still_works(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "mode": "single",
                "recipe": "bedroom_basic",
                "width": 4.0,
                "depth": 3.5,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertEqual(out.get("mode"), "single")
        self.assertNotIn("candidates", out)
        self.assertEqual(out.get("recipe_kind"), "room_use")
        bed = next(c for c in out["commands"] if c.get("generator") == "bed_basic")
        self.assertEqual(bed["params"]["head_side"], "y_min")

    def test_strategies_visibly_differ(self):
        from layoutlab.runtime.planning.bedroom_basic import enumerate_bedroom_candidates

        cands = enumerate_bedroom_candidates({"width": 4.0, "depth": 3.5})
        self.assertGreaterEqual(len(cands), 2)
        beds = []
        for c in cands:
            bed = next(x for x in c["commands"] if x.get("generator") == "bed_basic")
            beds.append((bed["params"]["head_side"], tuple(bed["params"]["location"])))
        # At least south vs north head walls among candidates
        heads = {h for h, _loc in beds}
        self.assertIn("y_min", heads)
        self.assertIn("y_max", heads)


if __name__ == "__main__":
    unittest.main()
