"""lamp_basic join anchor must be the base (foot), not an overhanging shade."""

from __future__ import annotations

import unittest

from layoutlab.runtime.furniture_ops import main_part
from layoutlab.runtime.session import RoomSession


class TestLampAnchor(unittest.TestCase):
    def test_main_location_is_base_foot(self):
        session = RoomSession()
        session.apply_command(
            {
                "action": "create_room",
                "params": {
                    "name": "R",
                    "location": [0, 0, 0],
                    "width": 4,
                    "depth": 3,
                    "collection": "c_lamp",
                },
            }
        )
        # Shade wider than base → old XY-sort made shade the join anchor.
        result = session.apply_command(
            {
                "action": "run_generator",
                "generator": "lamp_basic",
                "params": {
                    "name": "LAMP",
                    "location": [1.0, 1.0, 0.0],
                    "base": 0.12,
                    "shade": 0.2,
                    "height": 0.4,
                    "collection": "c_lamp",
                },
            }
        )
        main = main_part(session.mesh_store, result["object_id"])
        self.assertIsNotNone(main)
        self.assertAlmostEqual(float(main.location.x), 1.0, places=4)
        self.assertAlmostEqual(float(main.location.y), 1.0, places=4)
        self.assertAlmostEqual(float(main.location.z), 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
