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


class TestIsAnalyzeBlocker(unittest.TestCase):
    def setUp(self):
        self.util = _load_util()

    def test_furniture_mesh_is_blocker(self):
        self.assertTrue(self.util.is_analyze_blocker("MESH", role="bed_frame"))

    def test_room_wall_is_blocker(self):
        self.assertTrue(self.util.is_analyze_blocker("MESH", role="room_wall"))

    def test_room_fixed_is_blocker(self):
        self.assertTrue(self.util.is_analyze_blocker("MESH", role="room_fixed"))

    def test_room_floor_excluded(self):
        self.assertFalse(self.util.is_analyze_blocker("MESH", role="room_floor"))

    def test_room_opening_excluded(self):
        self.assertFalse(self.util.is_analyze_blocker("MESH", role="room_opening"))

    def test_clearance_excluded(self):
        self.assertFalse(self.util.is_analyze_blocker("MESH", role="clearance", has_clearance_name=True))

    def test_curve_excluded(self):
        self.assertFalse(self.util.is_analyze_blocker("CURVE", role="label"))


if __name__ == "__main__":
    unittest.main()
