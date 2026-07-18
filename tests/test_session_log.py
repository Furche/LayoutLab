"""Session interaction log writes LAST_SESSION.md + session.jsonl."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestSessionLog(unittest.TestCase):
    def test_agent_and_apply_roundtrip(self):
        from layoutlab.runtime import session_log as sl

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            jsonl = tmp_path / "session.jsonl"
            md = tmp_path / "LAST_SESSION.md"
            with mock.patch.object(sl, "LOG_DIR", tmp_path), mock.patch.object(
                sl, "JSONL_PATH", jsonl
            ), mock.patch.object(sl, "MARKDOWN_PATH", md), mock.patch.object(
                sl, "_ROOT", tmp_path
            ):
                sid = sl.start_session(label="test")
                self.assertTrue(sid.startswith("test-"))
                sl.log_agent_turn(
                    message="kannst du die aktuelle scene sehen?",
                    history_len=0,
                    result={
                        "ok": True,
                        "mode": "observe",
                        "reply": "Scene ist leer.",
                        "questions": [],
                        "commands": [],
                        "proposal": {"title": "Scene-Status", "commands": [], "expected_risks": []},
                        "tool_trace": [{"tool": "get_scene_summary"}],
                        "quality": None,
                    },
                )
                sl.log_apply(
                    commands=[{"action": "create_room", "params": {"name": "R", "width": 3, "depth": 4}}],
                    result={
                        "ok": True,
                        "errors": [],
                        "export": {
                            "rooms": [{"name": "R"}],
                            "objects": [{}, {}],
                            "analysis": {
                                "summary": {"errors": 0, "warnings": 1, "info": 0},
                                "soft_summary": {"count": 1},
                                "findings": [
                                    {
                                        "severity": "warning",
                                        "constraint_type": "opening_access",
                                        "message": "door blocked",
                                    }
                                ],
                            },
                        },
                    },
                )
                text = md.read_text(encoding="utf-8")
                self.assertIn("agent turn", text)
                self.assertIn("kannst du die aktuelle scene sehen?", text)
                self.assertIn("apply", text)
                self.assertIn("opening_access", text)
                summary = sl.latest_summary()
                self.assertEqual(summary["event_count"], 3)
                self.assertTrue(jsonl.is_file())


if __name__ == "__main__":
    unittest.main()
