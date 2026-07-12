import importlib.util
import json
import unittest
from pathlib import Path

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "reference_kids_room_commands.json"
_DESK_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "generators" / "desk_basic.py"


def _load_desk_basic():
    spec = importlib.util.spec_from_file_location("desk_basic", _DESK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDeskChairZone(unittest.TestCase):
    def setUp(self):
        self.desk_mod = _load_desk_basic()

    def test_chair_zone_at_front(self):
        loc, dims = self.desk_mod._chair_zone_local(12.0, 6.0, 6.0, 7.0)
        self.assertEqual(loc, [0.0, -6.0, 0.0])
        self.assertEqual(dims, [12.0, 6.0, 7.0])

    def test_chair_zone_minimum_depth(self):
        _, dims = self.desk_mod._chair_zone_local(10.0, 5.0, 0.0, 7.0)
        self.assertEqual(dims[1], 0.1)


class TestReferenceKidsRoomFixture(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_loads(self):
        self.assertIn("commands", self.fixture)
        self.assertGreaterEqual(len(self.fixture["commands"]), 3)

    def test_generators_present(self):
        gens = {
            c["generator"]
            for c in self.fixture["commands"]
            if c.get("action") == "run_generator"
        }
        self.assertEqual(gens, {"bed_basic", "wardrobe_basic", "desk_basic"})

    def test_desk_has_chair_clearance(self):
        desk_cmds = [
            c
            for c in self.fixture["commands"]
            if c.get("action") == "run_generator" and c.get("generator") == "desk_basic"
        ]
        self.assertEqual(len(desk_cmds), 1)
        self.assertTrue(desk_cmds[0]["params"].get("show_clearance"))

    def test_expected_clearances_include_desk(self):
        names = {e["clearance_name"] for e in self.fixture["expected_clearances"]}
        self.assertIn("chair_access", names)

    def test_reference_collection_consistent(self):
        collection = self.fixture["collection"]
        for cmd in self.fixture["commands"]:
            if cmd.get("action") == "run_generator":
                self.assertEqual(cmd["params"].get("collection"), collection)


if __name__ == "__main__":
    unittest.main()
