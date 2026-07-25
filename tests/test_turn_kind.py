"""FC-002/WP-A conversational turn kinds — no bpy / no network."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestTurnKind(unittest.TestCase):
    def test_infer_conversation_and_observation(self):
        from layoutlab.runtime.planning.turn_kind import (
            TURN_ACTION,
            TURN_CLARIFY,
            TURN_CONVERSATION,
            TURN_OBSERVATION,
            TURN_STYLING,
            allows_commands,
            infer_turn_kind,
        )

        self.assertEqual(
            infer_turn_kind("Ich finde den Raum noch etwas kühl. Was meinst du?"),
            TURN_CONVERSATION,
        )
        self.assertFalse(
            allows_commands(
                infer_turn_kind("Ich finde den Raum noch etwas kühl. Was meinst du?")
            )
        )
        self.assertEqual(
            infer_turn_kind("kannst du die aktuelle scene sehen?"),
            TURN_OBSERVATION,
        )
        self.assertEqual(infer_turn_kind("So ungefähr?"), TURN_OBSERVATION)
        self.assertEqual(
            infer_turn_kind("Dekoriere den Arbeitsplatz bitte gemütlich"),
            TURN_STYLING,
        )
        self.assertEqual(
            infer_turn_kind("richte mir ein schönes schlafzimmer ein"),
            TURN_ACTION,
        )
        self.assertEqual(
            infer_turn_kind("vielleicht etwas gemütlicher?"),
            TURN_CLARIFY,
        )
        self.assertEqual(
            infer_turn_kind(
                "irgendwie finde ich das zimmer nicht besonders schön eingerichtet oder?"
            ),
            TURN_CONVERSATION,
        )
        self.assertEqual(infer_turn_kind("kannst du das tun?"), TURN_ACTION)
        self.assertEqual(infer_turn_kind("kann losgehen"), TURN_ACTION)
        self.assertTrue(allows_commands(infer_turn_kind("kann losgehen")))

    def test_accept_followup_not_blocked_without_llm(self):
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.planning.turn_kind import TURN_ACTION, infer_turn_kind
        from layoutlab.runtime.session import RoomSession

        self.assertEqual(infer_turn_kind("kannst du das tun?"), TURN_ACTION)
        session = RoomSession()
        # Without LLM, action may fall through to demo empty reply — but must NOT
        # be forced into the non-mutating converse path with a styling ack.
        out = run_agent_turn(session, "kann losgehen", llm_config=None)
        self.assertNotEqual(out.get("turn_kind"), "conversation")
        self.assertNotEqual(out.get("mode"), "converse")

    def test_conversation_returns_no_commands(self):
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_commands.json"
        cmds = json.loads(fixture.read_text(encoding="utf-8"))["commands"]
        self.assertTrue(session.apply_commands(cmds)["ok"])

        out = run_agent_turn(
            session,
            "Ich finde den Raum noch etwas kühl. Was meinst du?",
            llm_config=None,
        )
        self.assertEqual(out.get("turn_kind"), "conversation")
        self.assertEqual(out.get("commands") or [], [])
        self.assertEqual(out.get("proposal", {}).get("commands") or [], [])
        self.assertIsNotNone(out.get("observed_revision"))
        self.assertEqual(
            session.agent_state.get("last_observed_revision"),
            out.get("observed_revision"),
        )
        self.assertEqual(out.get("proposal", {}).get("title"), "Einschätzung")
        self.assertIn("ohne etwas zu ändern", out.get("reply") or "")

    def test_styling_acknowledged_without_commands(self):
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        out = run_agent_turn(
            session, "Dekoriere das Zimmer bitte gemütlich", llm_config=None
        )
        self.assertEqual(out.get("turn_kind"), "styling_request")
        self.assertEqual(out.get("commands") or [], [])

    def test_recipe_not_forced_on_conversation(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        session.agent_state = {
            "requirements": {"room_type": "bedroom", "width": 4, "depth": 3.5},
            "goal": "Schlafzimmer planen",
        }
        bad = {
            "ok": True,
            "turn_kind": "conversation",
            "reply": "Wirkt etwas kühl.",
            "questions": [],
            "commands": [
                {
                    "action": "create_room",
                    "params": {"width": 4, "depth": 3.5, "name": "BEDROOM"},
                }
            ],
            "proposal": {
                "commands": [
                    {
                        "action": "create_room",
                        "params": {"width": 4, "depth": 3.5, "name": "BEDROOM"},
                    }
                ],
                "assumes": [],
            },
        }
        guarded = ag._apply_turn_kind_guards(bad, "conversation")
        self.assertEqual(guarded.get("commands") or [], [])
        out = ag._ensure_core_recipe_plan(
            session,
            guarded,
            "Ich finde den Raum noch etwas kühl. Was meinst du?",
            last_plan=None,
        )
        self.assertFalse(out.get("plan_layout_enforced"))
        self.assertEqual(out.get("commands") or [], [])


if __name__ == "__main__":
    unittest.main()
