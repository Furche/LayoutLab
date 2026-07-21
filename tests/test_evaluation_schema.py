"""DD-017 Evaluation schema v0.1 — profiles, roles, soft→components, shortlist."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestEvaluationSchema(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_resolve_profile_bed_basic(self):
        from layoutlab.runtime.planning.schema import resolve_profile_id

        self.assertEqual(resolve_profile_id("bed_basic"), "bed")
        self.assertEqual(resolve_profile_id("bed"), "bed")

    def test_resolve_profile_unknown(self):
        from layoutlab.runtime.planning.schema import resolve_profile_id

        self.assertEqual(resolve_profile_id("totally_made_up"), "unknown")
        self.assertEqual(resolve_profile_id(""), "unknown")
        self.assertEqual(resolve_profile_id(None), "unknown")

    def test_normalize_role_rejects_invented(self):
        from layoutlab.runtime.planning.schema import normalize_role

        self.assertEqual(normalize_role("primary_sleeping_place"), "primary_sleeping_place")
        self.assertIsNone(normalize_role("super_comfy_corner"))
        self.assertIsNone(normalize_role(""))
        self.assertIsNone(normalize_role(None))

    def test_opening_access_to_signed_component(self):
        from layoutlab.runtime.planning.schema import soft_findings_to_components

        findings = [
            {
                "severity": "warning",
                "constraint_type": "opening_access",
                "message": "Door 'door_01' access zone is blocked",
            }
        ]
        comps = soft_findings_to_components({"findings": findings}, findings=findings)
        self.assertEqual(len(comps), 1)
        c = comps[0]
        self.assertEqual(c["id"], "opening_access")
        self.assertEqual(c["category"], "accessibility")
        self.assertEqual(c["value"], -40)
        self.assertEqual(c["severity"], "severe")
        self.assertLess(c["value"], 0)

    def test_candidates_include_schema_and_shortlist(self):
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
        self.assertEqual(out.get("schema_version"), "0.1.0")
        self.assertEqual(out.get("evaluation_schema"), "0.1.0")
        shortlist = out.get("shortlist_ids") or []
        self.assertIsInstance(shortlist, list)
        self.assertTrue(shortlist, "expected non-empty shortlist on 4x3.5")
        self.assertIn(out["selected_id"], shortlist)
        for c in out.get("candidates") or []:
            ev = c.get("evaluation") or {}
            self.assertIn(ev.get("state"), {
                "invalid",
                "valid_with_severe_penalty",
                "valid_but_suboptimal",
                "preferred",
            }, c)
            self.assertIn("severe_veto", ev)
            self.assertIn("functional", ev)
            self.assertIn("category_vector", ev)


if __name__ == "__main__":
    unittest.main()
