"""FC-002/WP-04 semantic change summaries from transaction ops."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestChangeSummary(unittest.TestCase):
    def test_summarize_move_between_observations(self):
        from layoutlab.runtime.agent import run_agent_turn
        from layoutlab.runtime.planning.change_summary import describe_operation
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        self.assertIn(
            "verschoben",
            describe_operation(
                {
                    "action": "move",
                    "object_id": "bed-1",
                    "params": {"location": [1.2, 0.5, 0]},
                }
            ),
        )

        session = RoomSession()
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_commands.json"
        import json

        cmds = json.loads(fixture.read_text(encoding="utf-8"))["commands"]
        created = session.commit_commands(cmds, actor="user", description="setup")
        self.assertTrue(created.get("ok"), created)
        desk_id = None
        for obj in session.mesh_store.objects:
            props = getattr(obj, "props", None) or {}
            gen = props.get("layoutlab_generator") or ""
            if "desk" in gen:
                desk_id = props.get("layoutlab_object_id")
                break
        self.assertTrue(desk_id, "expected a desk in fixture")

        # Baseline observation stamps last_observed_revision
        obs1 = run_agent_turn(session, "kannst du die aktuelle scene sehen?", llm_config=None)
        self.assertEqual(obs1.get("turn_kind"), "observation_request")
        base_rev = session.agent_state.get("last_observed_revision")
        self.assertEqual(base_rev, session.revision)

        moved = session.commit_commands(
            [
                {
                    "action": "move",
                    "object_id": desk_id,
                    "params": {"location": [2.0, 1.5, 0]},
                }
            ],
            actor="user",
            description="user moved desk",
        )
        self.assertTrue(moved.get("ok"), moved)
        self.assertGreater(session.revision, base_rev)

        summary = dispatch_tool(
            session,
            "summarize_changes",
            {"from_revision": base_rev, "to_revision": session.revision},
        )
        self.assertTrue(summary.get("ok"), summary)
        self.assertTrue(summary.get("history_available"))
        self.assertTrue(summary.get("lines"), summary)
        self.assertTrue(any("verschoben" in ln for ln in summary["lines"]))

        obs2 = run_agent_turn(
            session, "Hast du dir das so ungefähr vorgestellt?", llm_config=None
        )
        self.assertEqual(obs2.get("turn_kind"), "observation_request")
        self.assertEqual(obs2.get("commands") or [], [])
        cs = obs2.get("change_summary") or {}
        self.assertTrue(cs.get("lines"), cs)
        self.assertIn("verschoben", obs2.get("reply") or "")

    def test_history_unavailable_outside_window(self):
        from layoutlab.runtime.session import RoomSession

        session = RoomSession(undo_depth=2)
        for i in range(4):
            out = session.commit_commands(
                [
                    {
                        "action": "create_room",
                        "params": {
                            "name": f"R{i}",
                            "width": 3 + i * 0.1,
                            "depth": 3,
                            "height": 2.5,
                        },
                    }
                ],
                actor="user",
            )
            self.assertTrue(out.get("ok"), out)
        # from_revision 0 is older than oldest undo base
        summary = session.summarize_changes(from_revision=0, to_revision=session.revision)
        self.assertTrue(summary.get("ok"))
        self.assertFalse(summary.get("history_available"))


if __name__ == "__main__":
    unittest.main()
