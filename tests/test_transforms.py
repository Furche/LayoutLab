import unittest


def translations_close(a, b, tolerance=0.05):
    return all(abs(a[i] - b[i]) <= tolerance for i in range(3))


class TestTranslationsClose(unittest.TestCase):
    def test_match(self):
        self.assertTrue(translations_close((0.45, 0.45, 3.1), (0.46, 0.44, 3.12), 0.05))

    def test_double_offset_detected(self):
        self.assertFalse(translations_close((0.45, 0.45, 3.1), (68.75, 197.95, 3.1), 0.05))


if __name__ == "__main__":
    unittest.main()
