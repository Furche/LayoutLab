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


if __name__ == "__main__":
    unittest.main()
