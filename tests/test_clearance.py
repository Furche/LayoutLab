import importlib.util
import unittest
from pathlib import Path

_UTIL_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "util.py"


def _load_util():
    spec = importlib.util.spec_from_file_location("layoutlab_util", _UTIL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestClearanceRequirement(unittest.TestCase):
    def setUp(self):
        self.util = _load_util()

    def test_required(self):
        self.assertEqual(self.util.validate_clearance_requirement("required"), "required")

    def test_preferred_default(self):
        self.assertEqual(self.util.validate_clearance_requirement("preferred"), "preferred")

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.util.validate_clearance_requirement("hard")


class TestClearanceLocations(unittest.TestCase):
    def setUp(self):
        self.util = _load_util()

    def test_local_to_world_with_main(self):
        world, local = self.util.resolve_clearance_locations(
            local_location=[0, -6, 0],
            main_location=(68.3, 197.7, 0),
        )
        self.assertEqual(world, (68.3, 191.7, 0.0))
        self.assertEqual(local, (0.0, -6.0, 0.0))

    def test_world_to_local_with_main(self):
        world, local = self.util.resolve_clearance_locations(
            world_location=(68.3, 191.7, 0),
            main_location=(68.3, 197.7, 0),
        )
        self.assertEqual(local, (0.0, -6.0, 0.0))
        self.assertEqual(world, (68.3, 191.7, 0.0))

    def test_standalone_world_equals_local(self):
        world, local = self.util.resolve_clearance_locations(world_location=(10, 5, 0))
        self.assertEqual(world, local)


class TestClearanceBounds(unittest.TestCase):
    def setUp(self):
        self.util = _load_util()

    def test_box_bounds(self):
        bounds = self.util.box_bounds_from_corner_and_dimensions([0, -0.6, 0], [0.8, 0.6, 1.5])
        self.assertEqual(bounds["min"], [0.0, -0.6, 0.0])
        self.assertEqual(bounds["max"], [0.8, 0.0, 1.5])

    def test_axis_aligned_bounds(self):
        bounds = self.util.axis_aligned_bounds_from_points([[0, -0.6, 0], [0.8, 0.0, 1.5], [0.1, -0.2, 0.3]])
        self.assertEqual(bounds["min"], [0.0, -0.6, 0.0])
        self.assertEqual(bounds["max"], [0.8, 0.0, 1.5])


if __name__ == "__main__":
    unittest.main()
