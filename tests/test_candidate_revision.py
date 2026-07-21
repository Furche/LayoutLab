"""DD-017 bounded internal revision for plan_layout candidates."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _cand(cid: str, *, hard: bool = False, veto: bool = False) -> dict:
    return {
        "candidate_id": cid,
        "strategy": cid,
        "commands": [],
        "quality": {
            "has_hard_errors": hard,
            "hard_errors": 1 if hard else 0,
            "apply_ok": not hard,
            "soft_warnings": 0,
            "soft_info": 0,
        },
        "evaluation": {"severe_veto": veto},
    }


class TestCandidateRevision(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_happy_path_no_revision(self):
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
        self.assertEqual(out.get("revision_rounds"), 0)
        self.assertEqual(out.get("revision_trace"), [])
        self.assertTrue(out.get("shortlist_ids"), "expected non-empty shortlist")

    def test_needs_revision_helpers(self):
        from layoutlab.runtime.planning.candidates import (
            MAX_REVISION_ROUNDS,
            _majority_failing_bed_wall,
            _needs_revision,
            _revision_overlay,
        )

        self.assertEqual(MAX_REVISION_ROUNDS, 2)

        clean = [_cand("bed_south__storage_north")]
        self.assertFalse(_needs_revision(clean, clean))

        hard = [
            _cand("bed_south__storage_north", hard=True),
            _cand("bed_north__storage_south", hard=True),
        ]
        self.assertTrue(_needs_revision([], hard))

        veto_only = [
            _cand("bed_south__storage_north", veto=True),
            _cand("bed_north__storage_south", veto=True),
        ]
        self.assertTrue(_needs_revision([], veto_only))

        self.assertFalse(_needs_revision([], []))

        self.assertEqual(_majority_failing_bed_wall(hard), "south")
        overlay, intention = _revision_overlay(1, hard)
        self.assertEqual(overlay.get("prefer_bed_wall"), "north")
        self.assertEqual(overlay.get("bed_wall"), "north")
        self.assertEqual(intention, "prefer_bed_wall_north")

        north_fail = [
            _cand("bed_north__storage_south", hard=True),
            _cand("bed_north__storage_swapped", hard=True),
        ]
        overlay2, intention2 = _revision_overlay(1, north_fail)
        self.assertEqual(intention2, "prefer_bed_wall_south")
        self.assertEqual(overlay2.get("bed_wall"), "south")

        desk_overlay, desk_intention = _revision_overlay(2, hard)
        self.assertEqual(desk_overlay, {"include_desk": False})
        self.assertEqual(desk_intention, "omit_desk")

    def test_omit_desk_intention_allowlisted(self):
        from layoutlab.runtime.planning.schema import validate_intention

        self.assertTrue(validate_intention("omit_desk"))
        self.assertTrue(validate_intention("prefer_bed_wall_north"))
        self.assertFalse(validate_intention("invent_free_xy"))
        self.assertFalse(validate_intention("random_intention"))

    def test_reconcile_defaults_mode_candidates(self):
        from layoutlab.runtime.planning import reconcile_plan_layout_params

        out = reconcile_plan_layout_params(
            {},
            requirements={"room_type": "bedroom", "width": 4, "depth": 3.5},
        )
        self.assertEqual(out.get("mode"), "candidates")
        self.assertEqual(out.get("recipe"), "bedroom_basic")


if __name__ == "__main__":
    unittest.main()
