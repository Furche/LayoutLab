import importlib.util
import unittest
from pathlib import Path

_UTIL_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "util.py"


def _load_util():
    spec = importlib.util.spec_from_file_location("layoutlab_util", _UTIL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAabbIntersects(unittest.TestCase):
    def setUp(self):
        self.util = _load_util()

    def test_disjoint(self):
        a = {"min": [0, 0, 0], "max": [1, 1, 1]}
        b = {"min": [2, 0, 0], "max": [3, 1, 1]}
        self.assertFalse(self.util.aabb_intersects(a, b))

    def test_touching_face_not_overlap(self):
        a = {"min": [0, 0, 0], "max": [1, 1, 1]}
        b = {"min": [1, 0, 0], "max": [2, 1, 1]}
        self.assertFalse(self.util.aabb_intersects(a, b))

    def test_overlap(self):
        a = {"min": [0, 0, 0], "max": [2, 2, 2]}
        b = {"min": [1, 1, 1], "max": [3, 3, 3]}
        self.assertTrue(self.util.aabb_intersects(a, b))

    def test_contained(self):
        a = {"min": [0, 0, 0], "max": [10, 10, 10]}
        b = {"min": [2, 2, 2], "max": [4, 4, 4]}
        self.assertTrue(self.util.aabb_intersects(a, b))


class TestRequirementToSeverity(unittest.TestCase):
    def setUp(self):
        self.util = _load_util()

    def test_required(self):
        self.assertEqual(self.util.requirement_to_severity("required"), "error")

    def test_preferred(self):
        self.assertEqual(self.util.requirement_to_severity("preferred"), "warning")

    def test_informational(self):
        self.assertEqual(self.util.requirement_to_severity("informational"), "info")

    def test_default_warning(self):
        self.assertEqual(self.util.requirement_to_severity(None), "warning")


if __name__ == "__main__":
    unittest.main()
