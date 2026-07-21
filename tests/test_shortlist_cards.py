"""Human shortlist labels + sketch cards (0.10.30)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestStrategyLabels(unittest.TestCase):
    def test_bedroom_labels(self):
        from layoutlab.runtime.planning.selection_surface import strategy_label_de

        self.assertEqual(
            strategy_label_de("bed_north__storage_south"),
            "Bett Nordwand, Stauraum Süd",
        )
        self.assertEqual(
            strategy_label_de("bed_south__storage_swapped"),
            "Bett Südwand, Schrank eher Ost",
        )


class TestShortlistCards(unittest.TestCase):
    def test_shortlist_has_label_and_sketch(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        bad = {
            "ok": True,
            "reply": "Schlafzimmer.",
            "questions": [],
            "commands": [
                {
                    "action": "run_generator",
                    "params": {
                        "generator": "bed_basic",
                        "location": {"x": 0, "y": 0, "z": 0},
                    },
                }
            ],
            "proposal": {"commands": [], "assumes": []},
            "tool_trace": [],
        }
        bad["proposal"]["commands"] = list(bad["commands"])
        out = ag._ensure_core_recipe_plan(
            session, bad, "schönes schlafzimmer einrichten", last_plan=None
        )
        self.assertTrue(out.get("plan_layout_enforced"))
        self.assertIn("Bett", out.get("reply") or "")
        self.assertNotIn("bed_north__", out.get("reply") or "")
        shortlist = out.get("shortlist") or []
        self.assertGreaterEqual(len(shortlist), 2)
        for row in shortlist:
            self.assertTrue(row.get("label_de"), row)
            self.assertIn("Bett", row["label_de"])
            self.assertTrue(row.get("sketch_ascii"), "expected top-down sketch on card")
            self.assertIn("room=", row["sketch_ascii"])


if __name__ == "__main__":
    unittest.main()
