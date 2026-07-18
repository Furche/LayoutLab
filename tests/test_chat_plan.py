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

    def test_demo_wardrobe(self):
        result = self.chat.plan_from_message("bau ein zimmer mit einem schrank")
        self.assertTrue(result["ok"])
        gens = [c.get("generator") for c in result["commands"] if c.get("action") == "run_generator"]
        self.assertIn("wardrobe_basic", gens)

    def test_demo_delete_room(self):
        result = self.chat.plan_from_message("lösche den raum")
        self.assertTrue(result["ok"])
        self.assertEqual(result["commands"][0]["action"], "delete_collection_objects")
        self.assertEqual(result["commands"][0]["collection"], "layoutlab_room")

    def test_demo_analyze(self):
        result = self.chat.plan_from_message("analyze clearances")
        self.assertEqual(result["commands"][0]["action"], "analyze_layout")

    def test_sanitize_rejects_unknown(self):
        with self.assertRaises(ValueError):
            self.chat.sanitize_commands([{"action": "run_python", "code": "x"}])

    def test_sanitize_hoists_delete_collection_from_params(self):
        out = self.chat.sanitize_commands(
            [{"action": "delete_collection_objects", "params": {"collection": "layoutlab_room"}}]
        )
        self.assertEqual(out[0]["collection"], "layoutlab_room")
        self.assertNotIn("params", out[0])

    def test_sanitize_wraps_flat_run_generator(self):
        out = self.chat.sanitize_commands(
            [
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "name": "BED",
                    "location": [1.0, 0.15, 0],
                    "head_side": "y_min",
                    "collection": "layoutlab_room",
                }
            ]
        )
        params = out[0]["params"]
        self.assertEqual(params["location"], [1.0, 0.15, 0])
        self.assertEqual(params["head_side"], "y_min")
        self.assertNotIn("location", out[0])

    def test_help_without_key(self):
        result = self.chat.plan_from_message("was kannst du?")
        self.assertTrue(result["ok"])
        self.assertEqual(result["commands"], [])
        self.assertIn("LLM", result["reply"])

    def test_resolve_llm_settings_prefers_request_key(self):
        settings = self.chat.resolve_llm_settings(
            {"api_key": "sk-test", "model": "gpt-test", "base_url": "https://example.com/v1/"}
        )
        self.assertEqual(settings["api_key"], "sk-test")
        self.assertEqual(settings["model"], "gpt-test")
        self.assertEqual(settings["base_url"], "https://example.com/v1")

    def test_llm_configured_from_request(self):
        self.assertTrue(self.chat.llm_configured({"api_key": "sk-x"}))
        self.assertFalse(self.chat.llm_configured({"api_key": "  "}))

if __name__ == "__main__":
    unittest.main()
