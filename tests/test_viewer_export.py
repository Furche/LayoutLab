"""Unit tests for viewer export hints (no bpy)."""

import importlib.util
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "layoutlab" / "protocol" / "viewer_export.py"


def _load():
    spec = importlib.util.spec_from_file_location("layoutlab_viewer_export", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load()


class ViewerExportTests(unittest.TestCase):
    def test_schema_version(self):
        self.assertEqual(_mod.VIEWER_SCHEMA, "0.1.2")

    def test_clearance_wire(self):
        hint = _mod.viewer_block_for_role("clearance")
        self.assertEqual(hint["primitive"], "box")
        self.assertEqual(hint["display"], "wire")

    def test_opening_wire(self):
        hint = _mod.viewer_block_for_role("room_opening", display_type="WIRE")
        self.assertEqual(hint["display"], "wire")

    def test_wall_quad_corners(self):
        corners = [[0, 0, 0], [0, 0, 2], [1, 0, 2], [1, 0, 0]]
        hint = _mod.viewer_block_for_role("room_wall", corners=corners)
        self.assertEqual(hint["primitive"], "quad")
        self.assertEqual(hint["corners"][2], [1.0, 0.0, 2.0])

    def test_furniture_box(self):
        hint = _mod.viewer_block_for_role("bed_frame")
        self.assertEqual(hint, {"primitive": "box"})

    def test_parse_corners_json(self):
        raw = "[[0,0,0],[0,0,1],[1,0,1],[1,0,0]]"
        corners = _mod.parse_corners_json(raw)
        self.assertEqual(len(corners), 4)
        self.assertIsNone(_mod.parse_corners_json("not-json"))
        self.assertIsNone(_mod.parse_corners_json("[]"))


if __name__ == "__main__":
    unittest.main()
