"""Smoke-test Decor / Deko generators (lamp-style minimal props)."""

from __future__ import annotations

import unittest

from layoutlab.runtime import furniture_ops as fo
from layoutlab.runtime.session import RoomSession

DECOR = [
    "lamp_basic",
    "floor_lamp_basic",
    "keyboard_basic",
    "monitor_basic",
    "laptop_basic",
    "mouse_basic",
    "tablet_basic",
    "notepad_basic",
    "book_basic",
    "mug_basic",
    "plant_basic",
    "frame_basic",
    "speaker_basic",
    "pillow_basic",
    "blanket_basic",
    "rug_basic",
    "doormat_basic",
    "box_basic",
    "laundry_basket_basic",
]


class TestDecorGenerators(unittest.TestCase):
    def test_all_decor_generators_place_main(self):
        session = RoomSession()
        session.apply_command(
            {
                "action": "create_room",
                "params": {
                    "name": "R",
                    "location": [0, 0, 0],
                    "width": 8,
                    "depth": 6,
                    "collection": "c_decor",
                },
            }
        )
        for i, gen in enumerate(DECOR):
            out = session.apply_command(
                {
                    "action": "run_generator",
                    "generator": gen,
                    "params": {
                        "name": f"D_{i}",
                        "location": [0.2 + (i % 5) * 0.9, 0.2 + (i // 5) * 0.9, 0.0],
                        "collection": "c_decor",
                    },
                }
            )
            oid = out["object_id"]
            main = fo.main_part(session.mesh_store, oid)
            self.assertIsNotNone(main, msg=f"{gen} has no main part")
            self.assertEqual(main.get("layoutlab_generator"), gen)


if __name__ == "__main__":
    unittest.main()
