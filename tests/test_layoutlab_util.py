import json
import unittest
from pathlib import Path

from layoutlab_util import (
    infer_generator_meta_from_code,
    infer_generator_name_from_code,
    parse_commands_payload,
    sanitize_generator_name,
)


GENERATORS_DIR = Path(__file__).resolve().parent.parent / "generators"


class TestSanitizeGeneratorName(unittest.TestCase):
    def test_strips_py_suffix(self):
        self.assertEqual(sanitize_generator_name("bed_basic.py"), "bed_basic")

    def test_replaces_invalid_chars(self):
        self.assertEqual(sanitize_generator_name("my-bed v2"), "my_bed_v2")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            sanitize_generator_name("  ")


class TestGeneratorMetadata(unittest.TestCase):
    def test_bed_basic_from_repo_file(self):
        code = (GENERATORS_DIR / "bed_basic.py").read_text(encoding="utf-8")
        meta = infer_generator_meta_from_code(code, GENERATORS_DIR / "bed_basic.py")
        self.assertEqual(meta["name"], "bed_basic")
        self.assertEqual(meta["category"], "Beds")
        self.assertEqual(meta["version"], "0.1")
        self.assertEqual(meta["icon"], "BED")
        self.assertIn("Parametric low bed", meta["description"])

    def test_infer_name_from_code(self):
        code = 'GENERATOR_NAME = "wardrobe_basic"\ndef generate(params, api):\n    pass'
        self.assertEqual(infer_generator_name_from_code(code), "wardrobe_basic")


class TestParseCommandsPayload(unittest.TestCase):
    def test_object_envelope(self):
        text = json.dumps({"commands": [{"action": "move", "object": "A", "location": [1, 2, 3]}]})
        commands = parse_commands_payload(text)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["action"], "move")

    def test_bare_array(self):
        text = json.dumps([{"action": "delete", "object": "B"}])
        commands = parse_commands_payload(text)
        self.assertEqual(len(commands), 1)

    def test_invalid_structure_raises(self):
        with self.assertRaises(ValueError):
            parse_commands_payload(json.dumps({"commands": "not-a-list"}))

    def test_invalid_json_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_commands_payload("{not json")


if __name__ == "__main__":
    unittest.main()
