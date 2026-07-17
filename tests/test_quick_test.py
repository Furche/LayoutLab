"""Unit tests for Quick Test profiles (no bpy)."""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "plugin" / "quick_test.py"


def _load():
    spec = importlib.util.spec_from_file_location("layoutlab_quick_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load()


class QuickTestMetricDefaultsTests(unittest.TestCase):
    def test_bed_defaults_are_meters(self):
        d = _mod.QUICK_TEST_PROFILES["bed_basic"]["defaults"]
        self.assertEqual(d["layoutlab_test_length"], 1.2)
        self.assertEqual(d["layoutlab_test_width"], 2.0)

    def test_desk_profile_exists(self):
        d = _mod.QUICK_TEST_PROFILES["desk_basic"]["defaults"]
        self.assertEqual(d["layoutlab_test_width"], 1.2)
        self.assertEqual(d["layoutlab_test_depth"], 0.6)
        self.assertEqual(d["layoutlab_test_height"], 0.75)

    def test_wardrobe_defaults_are_meters(self):
        d = _mod.QUICK_TEST_PROFILES["wardrobe_basic"]["defaults"]
        self.assertLess(d["layoutlab_test_width"], 5.0)
        self.assertEqual(d["layoutlab_test_height"], 1.5)

    def test_pre_metric_heuristic(self):
        scene = SimpleNamespace(
            layoutlab_test_length=12.0,
            layoutlab_test_width=20.0,
        )
        self.assertTrue(_mod.quick_test_values_look_pre_metric(scene, "bed_basic"))
        scene.layoutlab_test_length = 1.2
        scene.layoutlab_test_width = 2.0
        self.assertFalse(_mod.quick_test_values_look_pre_metric(scene, "bed_basic"))

    def test_desk_params(self):
        scene = SimpleNamespace(
            layoutlab_test_object_name="TEST_DESK",
            layoutlab_test_location=(0.0, 0.0, 0.0),
            layoutlab_test_width=1.2,
            layoutlab_test_depth=0.6,
            layoutlab_test_height=0.75,
        )
        params = _mod.build_quick_test_params(scene, "desk_basic")
        self.assertEqual(params["width"], 1.2)
        self.assertEqual(params["depth"], 0.6)
        self.assertNotIn("length", params)


if __name__ == "__main__":
    unittest.main()
