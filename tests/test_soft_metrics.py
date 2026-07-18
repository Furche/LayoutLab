"""Soft metrics (DD-015) — packing + opening access."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestSoftMetrics(unittest.TestCase):
    def setUp(self):
        if "bpy" in sys.modules:
            raise AssertionError("bpy must not be imported")
        from layoutlab.runtime.session import RoomSession

        self.session = RoomSession()

    def test_packing_warns_when_dense(self):
        from layoutlab.core.soft_metrics import CONSTRAINT_TYPE_SOFT_PACKING

        # Tiny room + large bed → high packing
        self.session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "TINY",
                        "width": 2.0,
                        "depth": 2.0,
                        "height": 2.5,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [0.1, 0.1, 0],
                        "length": 1.8,
                        "width": 1.6,
                        "collection": "layoutlab_room",
                    },
                },
            ]
        )
        result = self.session.apply_command({"action": "analyze_layout", "scope": "scene"})
        soft = [f for f in result["findings"] if f.get("constraint_type") == CONSTRAINT_TYPE_SOFT_PACKING]
        self.assertTrue(soft, result["findings"])
        self.assertIn(soft[0]["severity"], ("info", "warning"))
        self.assertIn("soft_summary", result)

    def test_opening_access_when_bed_blocks_door(self):
        from layoutlab.core.soft_metrics import CONSTRAINT_TYPE_OPENING_ACCESS

        self.session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "R",
                        "width": 4.0,
                        "depth": 3.0,
                        "height": 2.5,
                        "collection": "layoutlab_room",
                    },
                },
                {
                    "action": "add_opening",
                    "params": {
                        "room": "R",
                        "opening_name": "door_south",
                        "kind": "door",
                        "wall_side": "south",
                        "offset": 1.5,
                        "width": 0.9,
                        "height": 2.0,
                    },
                },
                {
                    "action": "run_generator",
                    "generator": "bed_basic",
                    "params": {
                        "name": "BED",
                        "location": [1.2, 0.05, 0],
                        "length": 1.2,
                        "width": 2.0,
                        "head_side": "y_max",
                        "collection": "layoutlab_room",
                    },
                },
            ]
        )
        result = self.session.apply_command({"action": "analyze_layout", "scope": "scene"})
        access = [
            f for f in result["findings"] if f.get("constraint_type") == CONSTRAINT_TYPE_OPENING_ACCESS
        ]
        self.assertTrue(access, json.dumps(result["findings"], indent=2))

    def test_dry_run_includes_soft_summary(self):
        from layoutlab.runtime.tools import dispatch_tool

        out = dispatch_tool(
            self.session,
            "dry_run_commands",
            {
                "commands": [
                    {
                        "action": "create_room",
                        "params": {
                            "name": "R",
                            "width": 3,
                            "depth": 3,
                            "height": 2.5,
                            "collection": "layoutlab_room",
                        },
                    }
                ],
                "analyze": True,
            },
        )
        self.assertTrue(out["ok"], out)
        self.assertIn("soft_summary", out)
        self.assertIn("soft_summary", out.get("analysis") or {})


if __name__ == "__main__":
    unittest.main()
