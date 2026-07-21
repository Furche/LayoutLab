"""Generic recipe routing + Core force path for furnished-room planning."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestRecipeRouting(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_resolve_schlafzimmer(self):
        from layoutlab.runtime.planning import resolve_recipe_id

        self.assertEqual(
            resolve_recipe_id(conversation="schönes schlafzimmer"),
            "bedroom_basic",
        )

    def test_resolve_buero_unmapped(self):
        from layoutlab.runtime.planning import resolve_recipe_id, wants_layout_planning

        self.assertTrue(wants_layout_planning("bau ein büro"))
        self.assertIsNone(resolve_recipe_id(conversation="bau ein büro"))

    def test_resolve_from_requirements(self):
        from layoutlab.runtime.planning import resolve_recipe_id

        self.assertEqual(
            resolve_recipe_id(
                conversation="mach was schönes",
                requirements={"room_type": "bedroom"},
            ),
            "bedroom_basic",
        )

    def test_observation_not_forced(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        session.agent_state = {
            "requirements": {"room_type": "bedroom", "width": 4, "depth": 3.5},
            "goal": "Schlafzimmer planen",
        }
        bad = {
            "ok": True,
            "reply": "Im Raum steht ein Bett.",
            "questions": [],
            "commands": [],
            "proposal": {"commands": [], "assumes": []},
        }
        out = ag._ensure_core_recipe_plan(
            session, bad, "was siehst du gerade im raum?", last_plan=None
        )
        self.assertFalse(out.get("plan_layout_enforced"))
        self.assertEqual(out.get("commands") or [], [])


class TestCoreRecipeForcePath(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")

    def test_force_replaces_free_llm_geometry(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        bad = {
            "ok": True,
            "reply": "Hier ein Schlafzimmer.",
            "questions": [],
            "commands": [
                {
                    "action": "create_room",
                    "params": {"width": 4, "depth": 3.5, "name": "ROOM"},
                },
                {
                    "action": "add_opening",
                    "params": {"kind": "door", "offset": 1.0, "width": 0.9},
                },
                {
                    "action": "run_generator",
                    "params": {
                        "generator": "bed_basic",
                        "location": {"x": 1.2, "y": 0.8, "z": 0},
                        "length": 2,
                        "width": 1.2,
                    },
                },
            ],
            "proposal": {"commands": [], "assumes": []},
        }
        bad["proposal"]["commands"] = bad["commands"]

        fixed = ag._ensure_core_recipe_plan(
            session,
            bad,
            "richte mir ein schönes schlafzimmer ein",
            last_plan=None,
        )
        self.assertTrue(fixed.get("plan_layout_enforced"))
        cmds = fixed["commands"]
        rooms = [c for c in cmds if c.get("action") == "create_room"]
        self.assertTrue(rooms)
        self.assertEqual((rooms[0].get("params") or {}).get("name"), "BEDROOM")

        beds = [
            c
            for c in cmds
            if c.get("action") == "run_generator"
            and (c.get("generator") or (c.get("params") or {}).get("generator")) == "bed_basic"
        ]
        self.assertTrue(beds, cmds)
        bed = beds[0]
        self.assertEqual(bed.get("generator"), "bed_basic")
        loc = (bed.get("params") or {}).get("location")
        self.assertIsInstance(loc, (list, tuple), loc)
        self.assertNotIsInstance(loc, dict)

        openings = [c for c in cmds if c.get("action") == "add_opening"]
        self.assertTrue(openings)
        for op in openings:
            params = op.get("params") or {}
            self.assertIn(params.get("wall_side"), ("north", "south", "east", "west"), params)
            self.assertEqual(params.get("room"), "BEDROOM")

        applied = session.clone().apply_commands(cmds)
        self.assertTrue(applied["ok"], applied.get("errors"))

    def test_finish_skips_placement_fixes_when_enforced(self):
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
            "proposal": {"commands": [], "assumes": [], "requirements": {"room_type": "bedroom"}},
        }
        bad["proposal"]["commands"] = list(bad["commands"])
        # Minimal finish path: ensure + baseline + placement gate
        out = ag._ensure_core_recipe_plan(
            session, bad, "schlafzimmer mit bett", last_plan=None
        )
        self.assertTrue(out.get("plan_layout_enforced"))
        # Simulate finish gate
        if not out.get("plan_layout_enforced"):
            out = ag._apply_deterministic_placement_fixes("schlafzimmer mit bett", out)
        gens = [c for c in out["commands"] if c.get("action") == "run_generator"]
        self.assertTrue(any(c.get("generator") == "bed_basic" for c in gens))


if __name__ == "__main__":
    unittest.main()
