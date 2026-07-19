"""Mini requirements → plan_layout mapping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestRequirements(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_normalize_and_plan_via_requirements(self):
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        out = dispatch_tool(
            session,
            "plan_layout",
            {
                "requirements": {
                    "room_type": "bedroom",
                    "width": 4.0,
                    "depth": 3.5,
                    "doors": 1,
                    "windows": 2,
                    "furniture": ["bed", "wardrobe", "desk"],
                    "door_wall": "east",
                    "assumes": ["defaults ok"],
                }
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertIn("requirements", out)
        self.assertEqual(out["requirements"]["windows"], 2)
        wins = [
            c
            for c in out["commands"]
            if c.get("action") == "add_opening"
            and (c.get("params") or {}).get("kind") == "window"
        ]
        self.assertEqual(len(wins), 2)
        sides = {(c.get("params") or {}).get("wall_side") for c in wins}
        self.assertNotIn("east", sides)  # door wall avoided
        applied = session.apply_commands(out["commands"])
        self.assertTrue(applied["ok"], applied.get("errors"))

    def test_baseline_uses_proposal_requirements_not_bad_windows(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        session = RoomSession()
        planned = dispatch_tool(
            session,
            "plan_layout",
            {
                "requirements": {
                    "room_type": "bedroom",
                    "width": 4,
                    "depth": 3.5,
                    "windows": 1,
                    "doors": 1,
                }
            },
        )
        last_plan = {
            "arguments": {"requirements": planned["requirements"]},
            "commands": planned["commands"],
            "assumes": [],
            "requirements": planned["requirements"],
        }
        bad = {
            "reply": "mit zwei fenstern",
            "questions": [],
            "commands": [
                {"action": "create_room", "params": {"width": 4, "depth": 3.5}},
                {
                    "action": "add_opening",
                    "params": {"kind": "door", "wall_side": "east", "width": 0.9},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "window", "wall_side": "east", "width": 1.2},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "window", "wall_side": "east", "width": 1.2},
                },
            ],
            "proposal": {
                "commands": [],
                "requirements": {
                    "room_type": "bedroom",
                    "width": 4,
                    "depth": 3.5,
                    "windows": 2,
                    "doors": 1,
                    "door_wall": "east",
                    "furniture": ["bed", "wardrobe", "desk"],
                },
            },
        }
        bad["proposal"]["commands"] = bad["commands"]
        fixed = ag._apply_plan_layout_baseline(
            session,
            bad,
            "schlafzimmer mit 2 fenstern",
            last_plan,
        )
        wins = [
            c
            for c in fixed["commands"]
            if c.get("action") == "add_opening"
            and (c.get("params") or {}).get("kind") == "window"
        ]
        self.assertEqual(len(wins), 2)
        sides = {(c.get("params") or {}).get("wall_side") for c in wins}
        self.assertNotIn("east", sides)
        self.assertEqual(fixed["proposal"]["requirements"]["windows"], 2)
        applied = session.clone().apply_commands(fixed["commands"])
        self.assertTrue(applied["ok"], applied.get("errors"))

    def test_fenstern_count(self):
        from layoutlab.runtime import agent as ag

        self.assertEqual(
            ag._requested_window_count(
                "kannst du mir einen raum erstellen mit 2 fenstern und möbeln?"
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
