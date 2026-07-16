import importlib.util
import unittest
from pathlib import Path

_WARDROBE_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "generators" / "wardrobe_basic.py"


def _load_wardrobe_basic():
    spec = importlib.util.spec_from_file_location("wardrobe_basic", _WARDROBE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestWardrobeFrontSide(unittest.TestCase):
    def setUp(self):
        self.mod = _load_wardrobe_basic()

    def test_y_min_clearance(self):
        loc, dims = self.mod._clearance_spec("y_min", 0.8, 0.4, 1.5, 0.018, 0.6)
        self.assertEqual(loc, [0.0, -0.618, 0.0])
        self.assertEqual(dims, [0.8, 0.6, 1.5])

    def test_y_max_clearance(self):
        loc, dims = self.mod._clearance_spec("y_max", 0.8, 0.4, 1.5, 0.018, 0.6)
        self.assertAlmostEqual(loc[1], 0.418)
        self.assertEqual(dims, [0.8, 0.6, 1.5])

    def test_unknown_front_side_raises(self):
        with self.assertRaises(ValueError):
            self.mod._normalize_front_side("x_max")


if __name__ == "__main__":
    unittest.main()
