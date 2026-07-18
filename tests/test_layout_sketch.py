"""Top-down layout sketch for agent spatial feedback — no bpy."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestLayoutSketch(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")
        from layoutlab.runtime.session import RoomSession
        from layoutlab.runtime.tools import dispatch_tool

        self.dispatch = dispatch_tool
        self.session = RoomSession()
        fixture = ROOT / "tests" / "fixtures" / "reference_kids_room_commands.json"
        cmds = json.loads(fixture.read_text(encoding="utf-8"))["commands"]
        self.assertTrue(self.session.apply_commands(cmds)["ok"])

    def test_get_layout_sketch_has_ascii_and_furniture(self):
        out = self.dispatch(self.session, "get_layout_sketch", {})
        self.assertTrue(out["ok"])
        self.assertIn("#", out["ascii"])
        self.assertTrue(out["rooms"])
        furn = out["rooms"][0]["furniture"]
        gens = {f["generator"] for f in furn}
        self.assertIn("bed_basic", gens)
        self.assertTrue(out["legend"])

    def test_dry_run_includes_layout_sketch(self):
        out = self.dispatch(
            self.session,
            "dry_run_commands",
            {
                "commands": [
                    {"action": "delete_collection_objects", "collection": "layoutlab_room"},
                    {
                        "action": "create_room",
                        "params": {
                            "name": "R",
                            "width": 4,
                            "depth": 3,
                            "height": 2.5,
                            "collection": "layoutlab_room",
                        },
                    },
                    {
                        "action": "add_opening",
                        "params": {
                            "room": "R",
                            "kind": "door",
                            "wall_side": "east",
                            "offset": 0.4,
                            "width": 0.9,
                            "height": 2.0,
                        },
                    },
                    {
                        "action": "run_generator",
                        "generator": "bed_basic",
                        "params": {
                            "name": "BED",
                            "location": [1.0, 0.15, 0],
                            "length": 1.2,
                            "width": 2.0,
                            "head_side": "y_min",
                            "collection": "layoutlab_room",
                        },
                    },
                ],
                "analyze": True,
            },
        )
        self.assertTrue(out["ok"], out)
        sketch = out["layout_sketch"]
        self.assertIn("D", sketch["ascii"])
        self.assertTrue(any(f["generator"] == "bed_basic" for f in sketch["rooms"][0]["furniture"]))
        # Live session unchanged
        self.assertEqual(self.session.list_rooms()[0]["name"], "KIDS_ROOM")


if __name__ == "__main__":
    unittest.main()
