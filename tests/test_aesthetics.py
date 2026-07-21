"""DD-017 experimental aesthetic shortlist guardrails."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestAesthetics(unittest.TestCase):
    def test_enabled_by_each_explicit_flag(self):
        from layoutlab.runtime.planning.aesthetics import aesthetics_enabled

        self.assertTrue(aesthetics_enabled(env={"LAYOUTLAB_AI_AESTHETICS": "yes"}))
        self.assertTrue(aesthetics_enabled(params={"aesthetics": True}, env={}))
        self.assertTrue(aesthetics_enabled(llm_config={"aesthetics": True}, env={}))
        self.assertFalse(aesthetics_enabled(env={"LAYOUTLAB_AI_AESTHETICS": "0"}))

    def test_recommendation_switches_only_within_shortlist(self):
        from layoutlab.runtime.planning.aesthetics import apply_aesthetic_recommendation

        planned = {
            "selected_id": "a",
            "shortlist_ids": ["a", "b"],
            "candidates": [
                {"candidate_id": "a", "strategy": "first", "commands": [{"action": "one"}]},
                {"candidate_id": "b", "strategy": "second", "commands": [{"action": "two"}]},
            ],
            "commands": [{"action": "one"}],
            "selection_reason": "Core choice.",
        }
        changed = apply_aesthetic_recommendation(
            planned, {"recommended_id": "b", "summary_de": "B wirkt ruhiger."}
        )
        self.assertEqual(changed["selected_id"], "b")
        self.assertEqual(changed["commands"], [{"action": "two"}])
        self.assertTrue(changed["candidates"][1]["recommended"])
        self.assertIn("experimentell", changed["selection_reason"])

    def test_non_shortlist_recommendation_is_ignored(self):
        from layoutlab.runtime.planning.aesthetics import apply_aesthetic_recommendation

        planned = {"selected_id": "a", "shortlist_ids": ["a"], "commands": [{"action": "one"}]}
        unchanged = apply_aesthetic_recommendation(planned, {"recommended_id": "outside"})
        self.assertEqual(unchanged["selected_id"], "a")
        self.assertNotIn("aesthetic", unchanged)

    def test_blueprint_png_from_shortlist_preview(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.planning.blueprint_png import (
            evidence_from_candidate,
            render_blueprint_png,
        )
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        bad = {
            "ok": True,
            "reply": "x",
            "questions": [],
            "commands": [
                {
                    "action": "run_generator",
                    "params": {"generator": "bed_basic", "location": {"x": 0, "y": 0, "z": 0}},
                }
            ],
            "proposal": {"commands": [], "assumes": []},
            "tool_trace": [],
        }
        bad["proposal"]["commands"] = list(bad["commands"])
        out = ag._ensure_core_recipe_plan(
            session, bad, "schönes schlafzimmer", last_plan=None
        )
        row = (out.get("shortlist") or [])[0]
        png = render_blueprint_png(row.get("viewer_preview"))
        self.assertIsNotNone(png)
        self.assertTrue(png.startswith(b"\x89PNG"))
        ev = evidence_from_candidate(row)
        self.assertEqual(ev["evidence_kind"], "blueprint_png")
        self.assertTrue(ev["image_data_url"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
