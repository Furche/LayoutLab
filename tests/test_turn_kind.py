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
    def test_table_planning_and_action(self):
        from layoutlab.runtime.planning.turn_kind import (
            TURN_ACTION,
            TURN_PLANNING,
            allows_commands,
            infer_turn_kind,
        )

        cases = [
            ("Schlafzimmer mit zwei Fenstern", TURN_PLANNING),
            ("Schlafzimmer mit 2 Fenstern", TURN_PLANNING),
            ("Bitte gestalte ein Schlafzimmer mit Möbeln", TURN_PLANNING),
            (
                "bitte einmal ein Schlafzimmer gestalten mit 2 Fenstern und Möbeln",
                TURN_PLANNING,
            ),
            ("Ich brauche ein Kinderzimmer für zwei Kinder", TURN_PLANNING),
            ("Ich brauche ein eingerichtetes Kinderzimmer", TURN_PLANNING),
            ("Gestalte ein Schlafzimmer", TURN_PLANNING),
            ("Bett und Schreibtisch austauschen", TURN_ACTION),
            ("kannst du mal bett und schreibtisch austauschen?", TURN_ACTION),
            ("Kannst du das ausprobieren?", TURN_ACTION),
            ("Nochmal versuchen", TURN_ACTION),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                kind = infer_turn_kind(message)
                self.assertEqual(kind, expected, message)
                self.assertTrue(allows_commands(kind), message)

    def test_table_conversation_and_observation(self):
        from layoutlab.runtime.planning.turn_kind import (
            TURN_CONVERSATION,
            TURN_OBSERVATION,
            allows_commands,
            infer_turn_kind,
        )

        cases = [
            ("Wie findest du das eingerichtete Schlafzimmer?", TURN_CONVERSATION),
            ("Ich finde den Raum etwas kühl.", TURN_CONVERSATION),
            ("Ich finde den Raum noch etwas kühl. Was meinst du?", TURN_CONVERSATION),
            ("Sieht das für dich stimmig aus?", TURN_OBSERVATION),
            ("Hast du dir das so ungefähr vorgestellt?", TURN_OBSERVATION),
            ("So ungefähr?", TURN_OBSERVATION),
            ("kannst du die aktuelle scene sehen?", TURN_OBSERVATION),
            # Bare room label alone is not a plan request
            ("Schlafzimmer", TURN_CONVERSATION),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                kind = infer_turn_kind(message)
                self.assertEqual(kind, expected, message)
                self.assertFalse(allows_commands(kind), message)

    def test_table_styling_wp_a_no_commands(self):
        from layoutlab.runtime.planning.turn_kind import (
            TURN_STYLING,
            allows_commands,
            infer_turn_kind,
        )
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.session import RoomSession

        cases = [
            "Dekoriere den Arbeitsplatz gemütlich.",
            "Dekoriere den Arbeitsplatz bitte gemütlich",
            "Mach den Raum etwas wohnlicher.",
        ]
        for message in cases:
            with self.subTest(message=message):
                kind = infer_turn_kind(message)
                self.assertEqual(kind, TURN_STYLING, message)
                self.assertFalse(allows_commands(kind), message)
                out = run_agent_turn(RoomSession(), message, llm_config=None)
                self.assertEqual(out.get("turn_kind"), TURN_STYLING, message)
                self.assertEqual(out.get("commands") or [], [], message)

    def test_bedroom_plan_then_retry_keeps_requirements(self):
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        first = run_agent_turn(
            session, "Schlafzimmer mit zwei Fenstern", llm_config=None
        )
        self.assertTrue(first["ok"], first)
        self.assertEqual(first.get("mode"), "agent_fallback")
        self.assertEqual(first.get("turn_kind"), "planning_request")
        self.assertTrue(first.get("commands"))
        self.assertEqual(session.agent_state["requirements"]["windows"], 2)

        second = run_agent_turn(session, "Nochmal versuchen", llm_config=None)
        self.assertTrue(second["ok"], second)
        self.assertEqual(second.get("mode"), "agent_fallback")
        wins = [
            c
            for c in second.get("commands") or []
            if c.get("action") == "add_opening"
            and str((c.get("params") or {}).get("kind") or c.get("kind") or "").lower()
            == "window"
        ]
        self.assertGreaterEqual(len(wins), 2)

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
