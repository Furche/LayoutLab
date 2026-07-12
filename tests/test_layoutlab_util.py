import importlib.util
import json
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_UTIL_PATH = _REPO_ROOT / "layoutlab" / "util.py"
_GENERATORS_DIR = _REPO_ROOT / "layoutlab" / "generators"


def _load_util():
    spec = importlib.util.spec_from_file_location("layoutlab_util", _UTIL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_util = _load_util()
sanitize_generator_name = _util.sanitize_generator_name
infer_generator_name_from_code = _util.infer_generator_name_from_code
infer_generator_meta_from_code = _util.infer_generator_meta_from_code
parse_commands_payload = _util.parse_commands_payload
merge_generator_params = _util.merge_generator_params
component_suffix_from_name = _util.component_suffix_from_name
generator_version_tuple = _util.generator_version_tuple


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
        code = (_GENERATORS_DIR / "bed_basic.py").read_text(encoding="utf-8")
        meta = infer_generator_meta_from_code(code, _GENERATORS_DIR / "bed_basic.py")
        self.assertEqual(meta["name"], "bed_basic")
        self.assertEqual(meta["category"], "Beds")
        self.assertEqual(meta["version"], "0.6.0")
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


class TestMergeGeneratorParams(unittest.TestCase):
    def test_overrides_win(self):
        merged = merge_generator_params({"length": 12, "width": 20}, {"length": 14})
        self.assertEqual(merged["length"], 14)
        self.assertEqual(merged["width"], 20)

    def test_empty_overrides(self):
        merged = merge_generator_params({"name": "BED"}, None)
        self.assertEqual(merged["name"], "BED")


class TestGeneratorVersionTuple(unittest.TestCase):
    def test_ordering(self):
        self.assertGreater(generator_version_tuple("0.2"), generator_version_tuple("0.1"))
        self.assertEqual(generator_version_tuple("0.2"), (0, 2))


class TestComponentSuffix(unittest.TestCase):
    def test_mattress(self):
        self.assertEqual(component_suffix_from_name("BED_120_mattress", "BED_120"), "mattress")

    def test_label(self):
        self.assertEqual(component_suffix_from_name("BED_120_label", "BED_120"), "label")

    def test_no_match(self):
        self.assertEqual(component_suffix_from_name("OTHER_mattress", "BED_120"), "")


if __name__ == "__main__":
    unittest.main()
