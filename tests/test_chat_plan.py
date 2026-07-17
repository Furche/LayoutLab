"""Chat planning: demo intents + command sanitize (no network / no bpy)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestChatPlan(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")
        from layoutlab.runtime import chat

        self.chat = chat

    def test_demo_furnished(self):
        result = self.chat.plan_from_message("Bitte furnished kids room")
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "demo")
        self.assertTrue(result["commands"])
        self.assertTrue(any(c.get("action") == "run_generator" for c in result["commands"]))

    def test_demo_empty(self):
        result = self.chat.plan_from_message("empty kids room bitte")
        self.assertTrue(result["ok"])
        actions = [c.get("action") for c in result["commands"]]
        self.assertIn("create_room", actions)
        self.assertNotIn("run_generator", actions)

    def test_demo_analyze(self):
        result = self.chat.plan_from_message("analyze clearances")
        self.assertEqual(result["commands"][0]["action"], "analyze_layout")

    def test_sanitize_rejects_unknown(self):
        with self.assertRaises(ValueError):
            self.chat.sanitize_commands([{"action": "run_python", "code": "x"}])

    def test_help_without_key(self):
        result = self.chat.plan_from_message("was kannst du?")
        self.assertTrue(result["ok"])
        self.assertEqual(result["commands"], [])
        self.assertIn("OPENAI_API_KEY", result["reply"])


if __name__ == "__main__":
    unittest.main()
