"""Semantic transactions / revision / Undo (DD-018 / FC-001/WP-02) — no bpy."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert_no_bpy():
    if "bpy" in sys.modules:
        raise AssertionError("bpy must not be imported for headless runtime tests")


def _room_cmd(name="ROOM_A", width=4.0, depth=3.0):
    return {
        "action": "create_room",
        "params": {
            "name": name,
            "location": [0, 0, 0],
            "width": width,
            "depth": depth,
            "height": 2.6,
            "wall_thickness": 0.02,
            "collection": "layoutlab_room",
        },
    }


class TestSemanticTransactions(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime import transactions as tx

        self.RoomSession = RoomSession
        self.tx = tx
        self.session = RoomSession()

    def test_apply_commands_does_not_bump_revision(self):
        result = self.session.apply_commands([_room_cmd()])
        self.assertTrue(result["ok"])
        self.assertEqual(self.session.revision, 0)
        self.assertFalse(self.session.can_undo)
        _assert_no_bpy()

    def test_commit_commands_bumps_revision_and_undo(self):
        result = self.session.commit_commands(
            [_room_cmd()],
            actor="user",
            action="commands",
            description="create room",
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(result["result_revision"], 1)
        self.assertEqual(result["base_revision"], 0)
        self.assertEqual(result["export"]["revision"], 1)
        self.assertTrue(self.session.can_undo)
        self.assertEqual(len(self.session.list_rooms()), 1)

        undone = self.session.undo()
        self.assertTrue(undone["ok"])
        self.assertEqual(self.session.revision, 0)
        self.assertEqual(len(self.session.list_rooms()), 0)
        self.assertTrue(self.session.can_redo)

        redone = self.session.redo()
        self.assertTrue(redone["ok"])
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(len(self.session.list_rooms()), 1)
        self.assertFalse(self.session.can_redo)
        _assert_no_bpy()

    def test_preview_does_not_create_undo_until_commit(self):
        begun = self.session.begin_preview([_room_cmd()], actor="user", description="drag")
        self.assertTrue(begun["ok"])
        self.assertEqual(self.session.revision, 0)
        self.assertFalse(self.session.can_undo)
        self.assertEqual(len(self.session.list_rooms()), 1)

        cancelled = self.session.cancel_preview()
        self.assertTrue(cancelled["ok"])
        self.assertTrue(cancelled["cancelled"])
        self.assertEqual(len(self.session.list_rooms()), 0)
        self.assertEqual(self.session.revision, 0)

        begun = self.session.begin_preview([_room_cmd(name="ROOM_B")])
        self.assertTrue(begun["ok"])
        committed = self.session.commit_preview(action="gesture", description="release")
        self.assertTrue(committed["ok"], committed)
        self.assertEqual(self.session.revision, 1)
        self.assertTrue(self.session.can_undo)
        self.assertEqual(committed["transaction"]["action"], "gesture")
        _assert_no_bpy()

    def test_preview_update_replaces_ops(self):
        self.session.begin_preview([_room_cmd(name="A")])
        updated = self.session.update_preview([_room_cmd(name="B", width=5.0)])
        self.assertTrue(updated["ok"])
        rooms = self.session.list_rooms()
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["name"], "B")
        self.assertEqual(rooms[0]["footprint"]["width"], 5.0)
        self.session.cancel_preview()
        self.assertEqual(len(self.session.list_rooms()), 0)

    def test_stale_base_revision_rejects_ai_apply(self):
        self.session.commit_commands([_room_cmd()], actor="user")
        self.assertEqual(self.session.revision, 1)

        stale = self.session.commit_commands(
            [_room_cmd(name="OTHER")],
            actor="ai",
            base_revision=0,
            description="stale proposal",
        )
        self.assertFalse(stale["ok"])
        self.assertEqual(stale["error_code"], self.tx.ERROR_STALE_BASE_REVISION)
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(len(self.session.list_rooms()), 1)
        self.assertEqual(self.session.list_rooms()[0]["name"], "ROOM_A")

        missing = self.session.commit_commands([_room_cmd(name="X")], actor="ai")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error_code"], self.tx.ERROR_MISSING_BASE_REVISION)

        ok = self.session.commit_commands(
            [{"action": "delete_room", "params": {"name": "ROOM_A"}}],
            actor="ai",
            base_revision=1,
        )
        self.assertTrue(ok["ok"], ok)
        self.assertEqual(self.session.revision, 2)
        self.assertEqual(len(self.session.list_rooms()), 0)

    def test_protected_from_ai_blocks_apply(self):
        self.session.commit_commands([_room_cmd()], actor="user")
        room = self.session.get_by_name("ROOM_A")
        room["protected_from_ai"] = True

        blocked = self.session.commit_commands(
            [{"action": "update_room", "params": {"name": "ROOM_A", "width": 5.0}}],
            actor="ai",
            base_revision=1,
        )
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error_code"], self.tx.ERROR_PROTECTED_FROM_AI)
        self.assertEqual(self.session.list_rooms()[0]["footprint"]["width"], 4.0)

    def test_failed_commit_restores_and_does_not_bump(self):
        self.session.commit_commands([_room_cmd()], actor="user")
        failed = self.session.commit_commands(
            [{"action": "delete_room", "params": {"name": "MISSING"}}],
            actor="user",
        )
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["error_code"], self.tx.ERROR_COMMIT_FAILED)
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(len(self.session.list_rooms()), 1)

    def test_undo_depth_default_at_least_50(self):
        self.assertGreaterEqual(self.session.undo_depth, 50)
        small = self.RoomSession(undo_depth=3)
        for i in range(5):
            small.commit_commands([_room_cmd(name=f"R{i}")], actor="user")
        self.assertEqual(small.undo_len, 3)
        self.assertEqual(small.revision, 5)

    def test_import_actor_one_transaction(self):
        result = self.session.commit_commands(
            [_room_cmd(), _room_cmd(name="ROOM_B")],
            actor="import",
            action="import",
            description="full scene",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(result["transaction"]["actor"], "import")
        self.assertEqual(self.session.undo_len, 1)

    def test_clone_keeps_revision_without_undo_history(self):
        self.session.commit_commands([_room_cmd()], actor="user")
        clone = self.session.clone()
        self.assertEqual(clone.revision, 1)
        self.assertFalse(clone.can_undo)
        clone.apply_commands([{"action": "delete_room", "params": {"name": "ROOM_A"}}])
        self.assertEqual(len(self.session.list_rooms()), 1)
        self.assertEqual(self.session.revision, 1)


class TestProposalBaseRevision(unittest.TestCase):
    def setUp(self):
        _assert_no_bpy()
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.agent import _stamp_base_revision, run_agent_turn

        self.session = RoomSession()
        self._stamp = _stamp_base_revision
        self.run_agent_turn = run_agent_turn

    def test_stamp_and_agent_turn_include_base_revision(self):
        self.session.commit_commands([_room_cmd()], actor="user")
        stamped = self._stamp(self.session, {"ok": True, "proposal": {"commands": []}})
        self.assertEqual(stamped["base_revision"], 1)
        self.assertEqual(stamped["proposal"]["base_revision"], 1)

        result = self.run_agent_turn(self.session, "was ist im raum?")
        self.assertIn("base_revision", result)
        self.assertEqual(result["base_revision"], 1)
        self.assertEqual(result["proposal"]["base_revision"], 1)


if __name__ == "__main__":
    unittest.main()
