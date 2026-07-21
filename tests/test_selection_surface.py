"""Planning selection surfacing in reply + session log."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestSelectionSurface(unittest.TestCase):
    def test_reply_note_includes_shortlist(self):
        from layoutlab.runtime.planning.selection_surface import (
            format_planning_reply_note,
            merge_planning_into_result,
        )

        planned = {
            "mode": "candidates",
            "recipe": "bedroom_basic",
            "selected_id": "bed_west__storage_south",
            "strategy": "bed_west",
            "selection_reason": "Shortlist 2 ohne Veto.",
            "shortlist_ids": ["bed_west__storage_south", "bed_south__storage_north"],
            "candidates": [
                {"candidate_id": "bed_west__storage_south", "strategy": "bed_west"},
                {"candidate_id": "bed_south__storage_north", "strategy": "bed_south"},
                {"candidate_id": "bed_north__storage_east", "strategy": "bed_north"},
            ],
            "revision_rounds": 0,
        }
        note = format_planning_reply_note(
            {
                "selected_id": planned["selected_id"],
                "shortlist_ids": planned["shortlist_ids"],
                "candidate_count": 3,
                "selection_reason": planned["selection_reason"],
                "revision_rounds": 0,
            },
            enforced=True,
        )
        self.assertIn("Core-Vorschlag: bed_west__storage_south", note)
        self.assertIn("Shortlist 2/3", note)

        out = merge_planning_into_result(
            {"reply": "Schlafzimmer eingerichtet.", "commands": []},
            planned,
            enforced=True,
        )
        self.assertTrue(out.get("plan_layout_enforced"))
        self.assertIn("Core-Vorschlag:", out["reply"])
        self.assertNotIn("plan_layout/mode=candidates", out["reply"])
        self.assertEqual(out["planning"]["selected_id"], "bed_west__storage_south")
        self.assertEqual(len(out["planning"]["candidates"]), 3)


class TestForcePathSurfacesPlanning(unittest.TestCase):
    def test_ensure_attaches_planning_and_trace(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        bad = {
            "ok": True,
            "reply": "Hier ein Schlafzimmer.",
            "questions": [],
            "commands": [
                {
                    "action": "run_generator",
                    "params": {
                        "generator": "bed_basic",
                        "location": {"x": 1, "y": 1, "z": 0},
                    },
                }
            ],
            "proposal": {"commands": [], "assumes": []},
            "tool_trace": [{"tool": "get_scene_summary"}],
        }
        bad["proposal"]["commands"] = list(bad["commands"])
        fixed = ag._ensure_core_recipe_plan(
            session,
            bad,
            "richte mir ein schönes schlafzimmer ein",
            last_plan=None,
        )
        self.assertTrue(fixed.get("plan_layout_enforced"))
        self.assertTrue(fixed.get("selected_id"))
        self.assertTrue(fixed.get("shortlist_ids"))
        self.assertIn("planning", fixed)
        self.assertIn("Core-Vorschlag:", fixed.get("reply") or "")
        tools = [t.get("tool") for t in (fixed.get("tool_trace") or [])]
        self.assertIn("plan_layout", tools)


class TestSessionLogPlanning(unittest.TestCase):
    def test_markdown_includes_planning_block(self):
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
                sl.start_session(label="test")
                sl.log_agent_turn(
                    message="schlafzimmer bitte",
                    history_len=0,
                    result={
                        "ok": True,
                        "mode": "agent",
                        "reply": "Fertig. — Core-Vorschlag: bed_west (Shortlist 2/3).",
                        "commands": [],
                        "proposal": {"title": "SZ", "commands": []},
                        "tool_trace": [{"tool": "plan_layout"}],
                        "plan_layout_enforced": True,
                        "planning": {
                            "recipe": "bedroom_basic",
                            "selected_id": "bed_west",
                            "strategy": "bed_west",
                            "selection_reason": "Shortlist 2 ohne Veto.",
                            "shortlist_ids": ["bed_west", "bed_south"],
                            "candidate_count": 3,
                            "candidates": [
                                {"candidate_id": "bed_west", "strategy": "bed_west"},
                                {"candidate_id": "bed_south", "strategy": "bed_south"},
                            ],
                            "revision_rounds": 0,
                        },
                    },
                )
                text = md.read_text(encoding="utf-8")
                self.assertIn("**Planning:**", text)
                self.assertIn("selected: `bed_west`", text)
                self.assertIn("shortlist (2):", text)
                self.assertIn("plan_layout", text)


if __name__ == "__main__":
    unittest.main()
