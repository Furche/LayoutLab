"""FC-001/WP-07 / DD-021 — support surfaces + lamp on desk."""

from __future__ import annotations

import unittest

from layoutlab.runtime import furniture_ops as fo
from layoutlab.runtime.session import RoomSession
from layoutlab.runtime import support_surfaces as supports


class TestSupportSurfaces(unittest.TestCase):
    def setUp(self):
        self.session = RoomSession()
        room = self.session.apply_command(
            {
                "action": "create_room",
                "params": {
                    "name": "R",
                    "location": [0, 0, 0],
                    "width": 5.0,
                    "depth": 4.0,
                    "collection": "coll_support",
                },
            }
        )
        self.room_id = room["room_id"]
        desk = self.session.apply_command(
            {
                "action": "run_generator",
                "generator": "desk_basic",
                "params": {
                    "name": "DESK",
                    "location": [1.0, 1.0, 0.0],
                    "width": 1.2,
                    "depth": 0.6,
                    "height": 0.75,
                    "show_clearance": False,
                    "collection": "coll_support",
                },
            }
        )
        self.desk_id = desk["object_id"]
        lamp = self.session.apply_command(
            {
                "action": "run_generator",
                "generator": "lamp_basic",
                "params": {
                    "name": "LAMP",
                    "location": [0.2, 0.2, 0.0],
                    "collection": "coll_support",
                },
            }
        )
        self.lamp_id = lamp["object_id"]

    def test_desk_stamps_surface_top(self):
        main = fo.main_part(self.session.mesh_store, self.desk_id)
        surfaces = supports.surfaces_of(main)
        self.assertEqual(len(surfaces), 1)
        self.assertEqual(surfaces[0]["id"], "surface_top")
        self.assertAlmostEqual(float(surfaces[0]["local_z"]), 0.75, places=3)

    def test_place_on_sets_z_and_valid(self):
        out = self.session.apply_command(
            {
                "action": "place_on",
                "object_id": self.lamp_id,
                "host_object_id": self.desk_id,
                "surface_id": "surface_top",
            }
        )
        self.assertEqual(out.get("validity") or out["results"][0]["result"]["validity"], fo.VALIDITY_VALID)
        # apply_command wraps differently — normalize
        result = out if "support_ref" in out else out["results"][0]["result"]
        self.assertTrue(str(result["support_ref"]).startswith(f"object:{self.desk_id}#"))
        lamp = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertAlmostEqual(float(lamp.location.z), 0.75, places=2)

    def test_host_move_follows_child(self):
        self.session.apply_command(
            {
                "action": "place_on",
                "object_id": self.lamp_id,
                "host_object_id": self.desk_id,
            }
        )
        lamp0 = fo.main_part(self.session.mesh_store, self.lamp_id)
        x0, y0, z0 = float(lamp0.location.x), float(lamp0.location.y), float(lamp0.location.z)
        self.session.apply_command(
            {
                "action": "move",
                "object_id": self.desk_id,
                "location": [1.5, 1.2, 0.0],
            }
        )
        lamp1 = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertAlmostEqual(float(lamp1.location.x) - x0, 0.5, places=2)
        self.assertAlmostEqual(float(lamp1.location.y) - y0, 0.2, places=2)
        self.assertAlmostEqual(float(lamp1.location.z), z0, places=2)

    def test_host_delete_dangling_no_support(self):
        self.session.apply_command(
            {
                "action": "place_on",
                "object_id": self.lamp_id,
                "host_object_id": self.desk_id,
            }
        )
        self.session.apply_command({"action": "delete", "object_id": self.desk_id})
        lamp = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertEqual(fo.validity_of(lamp), fo.VALIDITY_NO_SUPPORT)
        self.assertIn(self.desk_id, fo.support_ref(lamp))

    def test_host_shrink_detaches_to_floor(self):
        # Place lamp near the edge of a wide desk, then shrink width so centre falls off.
        self.session.apply_command(
            {
                "action": "place_on",
                "object_id": self.lamp_id,
                "host_object_id": self.desk_id,
                "location": [2.05, 1.25],  # near east edge of desk at 1.0..2.2 x
            }
        )
        lamp = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertEqual(fo.validity_of(lamp), fo.VALIDITY_VALID)
        lx = float(lamp.location.x)
        ly = float(lamp.location.y)
        self.session.apply_command(
            {
                "action": "set_parameter",
                "object_id": self.desk_id,
                "parameter": "width",
                "value": 0.5,
            }
        )
        lamp = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertEqual(fo.support_ref(lamp), fo.SUPPORT_ROOM_FLOOR)
        self.assertAlmostEqual(float(lamp.location.z), 0.0, places=2)
        self.assertAlmostEqual(float(lamp.location.x), lx, places=2)
        self.assertAlmostEqual(float(lamp.location.y), ly, places=2)

    def test_host_grow_reattaches_floor_lamp(self):
        self.session.apply_command(
            {
                "action": "place_on",
                "object_id": self.lamp_id,
                "host_object_id": self.desk_id,
                "location": [2.05, 1.25],
            }
        )
        self.session.apply_command(
            {
                "action": "set_parameter",
                "object_id": self.desk_id,
                "parameter": "width",
                "value": 0.5,
            }
        )
        lamp = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertEqual(fo.support_ref(lamp), fo.SUPPORT_ROOM_FLOOR)
        # Grow desk back under the lamp.
        self.session.apply_command(
            {
                "action": "set_parameter",
                "object_id": self.desk_id,
                "parameter": "width",
                "value": 1.4,
            }
        )
        lamp = fo.main_part(self.session.mesh_store, self.lamp_id)
        self.assertTrue(fo.support_ref(lamp).startswith(f"object:{self.desk_id}#"))
        self.assertAlmostEqual(float(lamp.location.z), 0.75, places=2)
        self.assertEqual(fo.validity_of(lamp), fo.VALIDITY_VALID)


if __name__ == "__main__":
    unittest.main()
