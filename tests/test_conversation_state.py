"""FC-002/WP-03 conversation state — focus, preferences, reference resolution."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestConversationState(unittest.TestCase):
    def test_schema_normalize_and_preferences(self):
        from layoutlab.runtime.planning.conversation_state import (
            AGENT_STATE_SCHEMA,
            PROVENANCE_EXPLICIT,
            PROVENANCE_INFERRED,
            apply_preferences_from_message,
            normalize_agent_state,
        )

        legacy = {"schema": "0.2.0", "goal": "x", "requirements": {"windows": 2}}
        state = normalize_agent_state(legacy)
        self.assertEqual(state["schema"], AGENT_STATE_SCHEMA)
        self.assertIn("focus", state)
        self.assertIn("preferences", state)
        state = apply_preferences_from_message(state, "Ich möchte es lieber minimal.")
        self.assertTrue(
            any(
                p.get("key") == "style"
                and p.get("value") == "minimal"
                and p.get("provenance") == PROVENANCE_EXPLICIT
                for p in state["preferences"]
            )
        )
        state = apply_preferences_from_message(state, "Der Raum wirkt kühl.")
        warmth = next(p for p in state["preferences"] if p.get("key") == "warmth")
        self.assertEqual(warmth.get("provenance"), PROVENANCE_INFERRED)
        # inferred must not overwrite explicit style
        state = apply_preferences_from_message(state, "wirkt kühl")
        style = next(p for p in state["preferences"] if p.get("key") == "style")
        self.assertEqual(style.get("provenance"), PROVENANCE_EXPLICIT)

    def test_resolve_bed_and_ambiguous_pronoun(self):
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.planning.conversation_state import (
            push_focus,
            resolve_reference,
        )
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_commands.json"
        cmds = json.loads(fixture.read_text(encoding="utf-8"))["commands"]
        self.assertTrue(session.apply_commands(cmds)["ok"])

        out = run_agent_turn(session, "Ich finde den Raum noch etwas kühl.", llm_config=None)
        self.assertEqual(out.get("turn_kind"), "conversation")
        prefs = (session.agent_state.get("preferences") or [])
        self.assertTrue(any(p.get("key") == "warmth" for p in prefs))

        bed = resolve_reference(session, session.agent_state, "dreh das Bett")
        self.assertEqual(bed.get("status"), "resolved")
        self.assertTrue(bed.get("object_ids"))

        # Pronoun without focus + multiple furniture → ambiguous clarification
        empty_focus = push_focus({"schema": "0.3.0"}, object_ids=[])
        # clear focus
        session.agent_state["focus"] = {
            "object_ids": [],
            "labels": [],
            "candidate_id": None,
            "room_id": None,
            "stack": [],
        }
        amb = run_agent_turn(session, "verschiebe es bitte", llm_config=None)
        self.assertEqual(amb.get("turn_kind"), "clarification")
        self.assertEqual(amb.get("commands") or [], [])
        self.assertTrue(amb.get("open_question"))

        # After focusing one object, pronoun resolves
        oid = bed["object_ids"][0]
        session.agent_state = push_focus(session.agent_state, object_ids=[oid], labels=["bed"])
        resolved = resolve_reference(session, session.agent_state, "dreh es")
        self.assertEqual(resolved.get("status"), "resolved")
        self.assertEqual(resolved.get("object_ids"), [oid])

    def test_swap_on_empty_scene_still_action(self):
        from layoutlab.runtime.planning.turn_kind import TURN_ACTION, infer_turn_kind
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.session import RoomSession

        msg = "Bett und Schreibtisch austauschen"
        self.assertEqual(infer_turn_kind(msg), TURN_ACTION)
        # Empty scene: do not force clarification for missing labels
        out = run_agent_turn(RoomSession(), msg, llm_config=None)
        self.assertNotEqual(out.get("turn_kind"), "clarification")


if __name__ == "__main__":
    unittest.main()
