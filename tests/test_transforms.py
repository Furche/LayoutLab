import unittest
from types import SimpleNamespace


def translations_close(a, b, tolerance=0.05):
    return all(abs(a[i] - b[i]) <= tolerance for i in range(3))


class _FakeTranslation:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __sub__(self, other):
        return _FakeTranslation(self.x - other.x, self.y - other.y, self.z - other.z)


class TestTranslationsClose(unittest.TestCase):
    def test_match(self):
        self.assertTrue(translations_close((0.45, 0.45, 3.1), (0.46, 0.44, 3.12), 0.05))

    def test_double_offset_detected(self):
        self.assertFalse(translations_close((0.45, 0.45, 3.1), (68.75, 197.95, 3.1), 0.05))


class TestRelativeTranslation(unittest.TestCase):
    def test_offset_independent_of_world_origin(self):
        import importlib.util
        from pathlib import Path

        util_path = Path(__file__).resolve().parent.parent / "layoutlab" / "util.py"
        spec = importlib.util.spec_from_file_location("layoutlab_util", util_path)
        util = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(util)

        child = SimpleNamespace(translation=_FakeTranslation(68.65, 197.95, 3.05))
        parent = SimpleNamespace(translation=_FakeTranslation(68.3, 197.7, 0.0))
        rel = util.relative_translation_from_world_matrices(child, parent)
        self.assertTrue(translations_close(rel, (0.35, 0.25, 3.05), 0.01))


if __name__ == "__main__":
    unittest.main()
