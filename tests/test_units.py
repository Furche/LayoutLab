"""Unit tests for LayoutLab ↔ Blender unit conversion."""

import importlib.util
import unittest
from pathlib import Path

_UNITS_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "api" / "units.py"


def _load_units():
    spec = importlib.util.spec_from_file_location("layoutlab_api_units", _UNITS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestUnitConversion(unittest.TestCase):
    def setUp(self):
        self.units = _load_units()

    def test_default_scene_scale(self):
        # Fresh Blender: 1 BU = 1 m → 1 LL (10 cm) = 0.1 BU
        self.assertAlmostEqual(self.units.bu_per_ll_unit(scale_length=1.0), 0.1)
        self.assertAlmostEqual(self.units.to_bu(7.5, scale_length=1.0), 0.75)
        self.assertAlmostEqual(self.units.from_bu(0.75, scale_length=1.0), 7.5)

    def test_ten_cm_scene_scale(self):
        # Reference-style: 1 BU = 0.1 m → LL and BU match
        self.assertAlmostEqual(self.units.bu_per_ll_unit(scale_length=0.1), 1.0)
        self.assertAlmostEqual(self.units.to_bu(7.5, scale_length=0.1), 7.5)
        self.assertAlmostEqual(self.units.from_bu(7.5, scale_length=0.1), 7.5)

    def test_vec_roundtrip(self):
        src = [42.0, 21.8, 7.5]
        bu = self.units.to_bu_vec(src, scale_length=1.0)
        back = self.units.from_bu_vec(bu, scale_length=1.0)
        for a, b in zip(src, back):
            self.assertAlmostEqual(a, b, places=6)

    def test_constants(self):
        self.assertAlmostEqual(self.units.LAYOUTLAB_METERS_PER_UNIT, 0.1)
        self.assertEqual(self.units.SCALE_CONVENTION, "1_unit_equals_10cm")


if __name__ == "__main__":
    unittest.main()
