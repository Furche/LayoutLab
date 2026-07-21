"""Shortlist user/AI selection (DD-017) — chat + Viewer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestShortlistResolve(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_ordinal_and_id(self):
        from layoutlab.runtime.planning.selection_surface import resolve_shortlist_selection

        shortlist = [
            {"candidate_id": "bed_north__storage_south", "commands": [{"action": "x"}]},
            {"candidate_id": "bed_south__storage_north", "commands": [{"action": "y"}]},
            {"candidate_id": "bed_south__storage_swapped", "commands": [{"action": "z"}]},
        ]
        self.assertEqual(
            resolve_shortlist_selection("nimm variante 2", shortlist),
            "bed_south__storage_north",
        )
        self.assertEqual(
            resolve_shortlist_selection("die dritte bitte", shortlist),
            "bed_south__storage_swapped",
        )
        self.assertEqual(
            resolve_shortlist_selection("bed_south__storage_north", shortlist),
            "bed_south__storage_north",
        )
        self.assertIsNone(resolve_shortlist_selection("bau ein schlafzimmer", shortlist))


class TestShortlistFlow(unittest.TestCase):
    def test_force_exposes_shortlist_then_chat_select(self):
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
        planned = ag._ensure_core_recipe_plan(
            session, bad, "schönes schlafzimmer einrichten", last_plan=None
        )
        self.assertTrue(planned.get("plan_layout_enforced"))
        shortlist = planned.get("shortlist") or []
        self.assertGreaterEqual(len(shortlist), 2, shortlist)
        for row in shortlist:
            self.assertTrue(row.get("commands"), row)
            self.assertTrue(row.get("candidate_id"))

        # Persist like finish would
        fp = ag._placement_fingerprint(planned.get("commands") or [])
        ag._update_agent_state(
            session, planned, "schönes schlafzimmer", last_plan=None, placement_fp=fp
        )
        self.assertTrue(session.agent_state.get("last_shortlist"))

        second_id = shortlist[1]["candidate_id"]
        selected = ag.run_agent_turn(session, f"nimm variante 2", llm_config={})
        self.assertTrue(selected.get("ok"), selected)
        self.assertEqual(selected.get("mode"), "select_candidate")
        self.assertEqual(selected.get("selected_id"), second_id)
        self.assertEqual(selected.get("commands"), shortlist[1]["commands"])
        self.assertIn("Gewählt:", selected.get("reply") or "")


if __name__ == "__main__":
    unittest.main()
