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

    def test_solid_wall_penetration_is_error(self):
        from layoutlab.core.solid_collision import CONSTRAINT_TYPE_SOLID_WALL

        # Wardrobe centered on west wall plane → solid penetration
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
                    "action": "run_generator",
                    "generator": "wardrobe_basic",
                    "params": {
                        "name": "WR",
                        "location": [-0.3, 1.0, 0],
                        "width": 1.2,
                        "depth": 0.6,
                        "height": 2.0,
                        "collection": "layoutlab_room",
                    },
                },
            ]
        )
        result = self.session.apply_command({"action": "analyze_layout", "scope": "scene"})
        solid = [f for f in result["findings"] if f.get("constraint_type") == CONSTRAINT_TYPE_SOLID_WALL]
        self.assertTrue(solid, result["findings"])
        self.assertEqual(solid[0]["severity"], "error")
        self.assertTrue(solid[0].get("non_negotiable"))


class TestObservationQueries(unittest.TestCase):
    def setUp(self):
        from layoutlab.runtime.session import RoomSession

        self.session = RoomSession()
        self.session.apply_commands(
            [
                {
                    "action": "create_room",
                    "params": {
                        "name": "BEDROOM",
                        "width": 4,
                        "depth": 3,
                        "height": 2.5,
                        "collection": "layoutlab_room",
                    },
                }
            ]
        )

    def test_observation_returns_no_commands(self):
        from layoutlab.runtime.agent import run_agent_turn

        out = run_agent_turn(
            self.session,
            "kannst du die aktuelle scene sehen?",
            llm_config=None,
        )
        self.assertEqual(out["mode"], "observe")
        self.assertEqual(out["commands"], [])
        self.assertIn("BEDROOM", out["reply"])
        tools = [t.get("tool") for t in out.get("tool_trace") or []]
        self.assertIn("get_analysis", tools)
        self.assertIn("get_layout_sketch", tools)
        self.assertTrue(out.get("quality"))
        self.assertIn("Top-down", out["reply"])


if __name__ == "__main__":
    unittest.main()
