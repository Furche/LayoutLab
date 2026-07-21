"""Human shortlist labels + sketch cards (0.10.30)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestStrategyLabels(unittest.TestCase):
    def test_bedroom_labels(self):
        from layoutlab.runtime.planning.selection_surface import strategy_label_de

        self.assertEqual(
            strategy_label_de("bed_north__storage_south"),
            "Bett Nordwand, Stauraum Süd",
        )
        self.assertEqual(
            strategy_label_de("bed_south__storage_swapped"),
            "Bett Südwand, Schrank eher Ost",
        )


class TestShortlistCards(unittest.TestCase):
    def test_shortlist_has_label_and_sketch(self):
        from layoutlab.runtime import agent as ag
        from layoutlab.runtime.session import RoomSession

        session = RoomSession()
        bad = {
            "ok": True,
            "reply": "Schlafzimmer.",
            "questions": [],
            "commands": [
                {
                    "action": "run_generator",
                    "params": {
                        "generator": "bed_basic",
                        "location": {"x": 0, "y": 0, "z": 0},
                    },
                }
            ],
            "proposal": {"commands": [], "assumes": []},
            "tool_trace": [],
        }
        bad["proposal"]["commands"] = list(bad["commands"])
        out = ag._ensure_core_recipe_plan(
            session, bad, "schönes schlafzimmer einrichten", last_plan=None
        )
        self.assertTrue(out.get("plan_layout_enforced"))
        self.assertIn("Bett", out.get("reply") or "")
        self.assertNotIn("bed_north__", out.get("reply") or "")
        shortlist = out.get("shortlist") or []
        self.assertGreaterEqual(len(shortlist), 2)
        for row in shortlist:
            self.assertTrue(row.get("label_de"), row)
            self.assertIn("Bett", row["label_de"])
            self.assertTrue(row.get("sketch_ascii"), "expected top-down sketch on card")
            self.assertIn("room=", row["sketch_ascii"])
            preview = row.get("viewer_preview")
            self.assertIsInstance(preview, dict, row.get("candidate_id"))
            self.assertTrue(preview.get("rooms") or preview.get("objects"))
            for obj in preview.get("objects") or []:
                viewer = obj.get("viewer") or {}
                self.assertNotIn("vertices", viewer)
                self.assertNotIn("faces", viewer)


class TestSlimViewerPreview(unittest.TestCase):
    def test_drops_mesh_and_clearances(self):
        from layoutlab.runtime.planning.viewer_preview import slim_viewer_preview

        raw = {
            "viewer_schema": "0.1.1",
            "rooms": [{"name": "BEDROOM", "footprint": {"width": 4, "depth": 3.5}}],
            "objects": [
                {
                    "name": "BED",
                    "layoutlab": {"role": "bed_mattress"},
                    "world_bbox_corners": [[0, 0, 0], [1, 0, 0], [1, 2, 0], [0, 2, 0], [0, 0, 0.5], [1, 0, 0.5], [1, 2, 0.5], [0, 2, 0.5]],
                    "viewer": {"primitive": "mesh", "vertices": [[0, 0, 0]], "faces": [[0, 0, 0]]},
                },
                {
                    "name": "CLR",
                    "layoutlab": {"role": "clearance"},
                    "viewer": {"primitive": "box", "display": "wire"},
                },
            ],
            "analysis": {"summary": {"errors": 0}},
        }
        slim = slim_viewer_preview(raw)
        self.assertEqual(len(slim["objects"]), 1)
        self.assertEqual(slim["objects"][0]["viewer"]["primitive"], "box")
        self.assertNotIn("vertices", slim["objects"][0]["viewer"])
        self.assertNotIn("analysis", slim)


if __name__ == "__main__":
    unittest.main()
