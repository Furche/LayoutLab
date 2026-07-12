import importlib.util
import unittest
from pathlib import Path

_BED_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "generators" / "bed_basic.py"


def _load_bed_basic():
    spec = importlib.util.spec_from_file_location("bed_basic", _BED_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBedClearanceZones(unittest.TestCase):
    def setUp(self):
        self.bed_mod = _load_bed_basic()
        self.BedConstruction = self.bed_mod.BedConstruction

    def _bed(self, head_side="y_max"):
        return self.BedConstruction(
            x=0,
            y=0,
            floor_z=0,
            length=12,
            width=20,
            leg_height=2.5,
            frame_height=1.0,
            rail=0.35,
            post=0.45,
            headboard_rise=3.2,
            head_side=head_side,
        )

    def test_foot_entry_y_max(self):
        bed = self._bed("y_max")
        loc, dims = self.bed_mod._zone_for_side(bed, "foot", 6.0, 2.0)
        self.assertEqual(loc, [0.0, -6.0, 0.0])
        self.assertEqual(dims[0], 12.0)
        self.assertEqual(dims[1], 6.0)

    def test_left_entry_y_max(self):
        bed = self._bed("y_max")
        loc, dims = self.bed_mod._zone_for_side(bed, "left", 5.0, 2.0)
        self.assertEqual(loc, [-5.0, 0.0, 0.0])
        self.assertEqual(dims[0], 5.0)
        self.assertEqual(dims[1], 20.0)

    def test_unknown_side_raises(self):
        bed = self._bed("y_max")
        with self.assertRaises(ValueError):
            self.bed_mod._zone_for_side(bed, "diagonal", 6.0, 2.0)

    def test_iter_clearance_specs_empty(self):
        self.assertEqual(self.bed_mod._iter_clearance_specs({}), [])
        self.assertEqual(self.bed_mod._iter_clearance_specs({"clearances": "nope"}), [])


if __name__ == "__main__":
    unittest.main()
