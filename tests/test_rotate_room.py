"""Core rotate_room (Z) — fabric + VALID furniture participation."""

from __future__ import annotations

import unittest

from layoutlab.core import room as room_core
from layoutlab.runtime import furniture_ops
from layoutlab.runtime.session import RoomSession, export_viewer_scene


class TestRotateRoom(unittest.TestCase):
    def setUp(self):
        self.session = RoomSession()

    def _create_room(self, name="R1", location=(0, 0, 0), width=4.0, depth=3.0):
        return self.session.apply_command(
            {
                "action": "create_room",
                "params": {
                    "name": name,
                    "location": list(location),
                    "width": width,
                    "depth": depth,
                    "collection": f"coll_{name}",
                },
            }
        )

    def _spawn_furniture(self, room_id, name="bed", location=(1.0, 1.0, 0.0)):
        result = self.session.apply_command(
            {
                "action": "run_generator",
                "generator": "bed_basic",
                "params": {
                    "name": name,
                    "location": list(location),
                    "collection": self.session.get_by_id(room_id)["collection"],
                },
            }
        )
        oid = result["object_id"]
        furniture_ops.ensure_semantic_defaults(
            self.session.mesh_store, self.session._rooms, oid
        )
        main = furniture_ops.main_part(self.session.mesh_store, oid)
        main["layoutlab_room_id"] = room_id
        for part in furniture_ops.objects_for_id(self.session.mesh_store, oid):
            part["layoutlab_room_id"] = room_id
        furniture_ops.refresh_validity(self.session.mesh_store, self.session._rooms, oid)
        return oid

    def test_rotate_90_keeps_center_and_updates_rz(self):
        room = self._create_room()
        rid = room["room_id"]
        model = self.session.get_by_id(rid)
        c0 = room_core.room_footprint_center(model)
        self.session.apply_command({"action": "rotate_room", "room_id": rid, "degrees": 90})
        model = self.session.get_by_id(rid)
        self.assertAlmostEqual(float(model["rotation_z_deg"]), 90.0, places=3)
        c1 = room_core.room_footprint_center(model)
        self.assertAlmostEqual(c1[0], c0[0], places=4)
        self.assertAlmostEqual(c1[1], c0[1], places=4)

    def test_rotate_openings_follow_wall(self):
        room = self._create_room()
        rid = room["room_id"]
        self.session.apply_command(
            {
                "action": "add_opening",
                "params": {
                    "room_id": rid,
                    "wall_side": "west",
                    "kind": "window",
                    "opening_name": "win_west",
                    "offset": 0.8,
                    "width": 1.2,
                    "height": 1.4,
                    "sill_height": 0.9,
                },
            }
        )
        model = self.session.get_by_id(rid)
        win = next(o for o in model["openings"] if o["name"] == "win_west")
        off0 = float(win["offset"])
        wall = room_core.find_wall(model, win["wall_id"])
        pt0 = room_core._attachment_world_xy(model, wall, win["offset"])
        center0 = room_core.room_footprint_center(model)

        self.session.apply_command({"action": "rotate_room", "room_id": rid, "degrees": 90})
        model = self.session.get_by_id(rid)
        win = next(o for o in model["openings"] if o["name"] == "win_west")
        self.assertAlmostEqual(float(win["offset"]), off0, places=5)
        wall = room_core.find_wall(model, win["wall_id"])
        pt1 = room_core._attachment_world_xy(model, wall, win["offset"])
        dx0, dy0 = pt0[0] - center0[0], pt0[1] - center0[1]
        exp_x = center0[0] - dy0
        exp_y = center0[1] + dx0
        self.assertAlmostEqual(pt1[0], exp_x, places=3)
        self.assertAlmostEqual(pt1[1], exp_y, places=3)

    def test_valid_furniture_follows_invalid_stays(self):
        room = self._create_room(width=4.0, depth=3.0)
        rid = room["room_id"]
        valid_id = self._spawn_furniture(rid, name="valid_bed", location=(1.0, 1.0, 0.0))
        invalid_id = self._spawn_furniture(rid, name="outside_bed", location=(20.0, 20.0, 0.0))
        self.assertEqual(
            furniture_ops.validity_of(furniture_ops.main_part(self.session.mesh_store, valid_id)),
            furniture_ops.VALIDITY_VALID,
        )
        self.assertEqual(
            furniture_ops.validity_of(furniture_ops.main_part(self.session.mesh_store, invalid_id)),
            furniture_ops.VALIDITY_OUTSIDE,
        )

        v0 = furniture_ops.main_part(self.session.mesh_store, valid_id)
        i0 = furniture_ops.main_part(self.session.mesh_store, invalid_id)
        params0 = furniture_ops._parse_params(v0)
        hx, hy = furniture_ops.footprint_half_xy(params0, v0.get("layoutlab_generator"))
        loc0 = [float(v0.location.x), float(v0.location.y), float(v0.location.z)]
        c_furn0 = furniture_ops.corner_to_center(loc0, hx, hy, float(v0.rotation_z_deg or 0.0))
        ix0, iy0 = float(i0.location.x), float(i0.location.y)
        rz0 = float(v0.rotation_z_deg or 0.0)
        center = room_core.room_footprint_center(self.session.get_by_id(rid))

        self.session.apply_command({"action": "rotate_room", "room_id": rid, "degrees": 90})

        v1 = furniture_ops.main_part(self.session.mesh_store, valid_id)
        i1 = furniture_ops.main_part(self.session.mesh_store, invalid_id)
        self.assertAlmostEqual(float(i1.location.x), ix0, places=4)
        self.assertAlmostEqual(float(i1.location.y), iy0, places=4)

        params1 = furniture_ops._parse_params(v1)
        hx1, hy1 = furniture_ops.footprint_half_xy(params1, v1.get("layoutlab_generator"))
        loc1 = [float(v1.location.x), float(v1.location.y), float(v1.location.z)]
        c_furn1 = furniture_ops.corner_to_center(loc1, hx1, hy1, float(v1.rotation_z_deg or 0.0))
        dx, dy = c_furn0[0] - center[0], c_furn0[1] - center[1]
        exp_x, exp_y = center[0] - dy, center[1] + dx
        self.assertAlmostEqual(c_furn1[0], exp_x, places=3)
        self.assertAlmostEqual(c_furn1[1], exp_y, places=3)
        self.assertAlmostEqual(float(v1.rotation_z_deg), rz0 + 90.0, places=2)

    def test_export_floor_quad_rotated(self):
        room = self._create_room()
        rid = room["room_id"]
        self.session.apply_command({"action": "rotate_room", "room_id": rid, "degrees": 45})
        export = export_viewer_scene(self.session)
        floor = next(o for o in export["objects"] if str(o.get("name", "")).endswith("_floor"))
        viewer = floor.get("viewer") or {}
        self.assertEqual(viewer.get("primitive"), "quad")
        corners = viewer.get("corners") or []
        self.assertEqual(len(corners), 4)
        xs = [c[0] for c in corners]
        self.assertGreater(max(xs) - min(xs), 4.0)

    def test_export_opening_and_fixed_oriented_after_rotate(self):
        room = self._create_room()
        rid = room["room_id"]
        self.session.apply_command(
            {
                "action": "add_opening",
                "params": {
                    "room_id": rid,
                    "wall_side": "west",
                    "kind": "window",
                    "opening_name": "win",
                    "offset": 0.5,
                    "width": 1.2,
                    "height": 1.4,
                    "sill_height": 0.9,
                },
            }
        )
        self.session.apply_command(
            {
                "action": "add_fixed_element",
                "params": {
                    "room_id": rid,
                    "wall_side": "north",
                    "kind": "radiator",
                    "name": "rad",
                    "offset": 1.0,
                    "width": 1.0,
                    "depth": 0.12,
                    "height": 0.6,
                },
            }
        )
        self.session.apply_command({"action": "rotate_room", "room_id": rid, "degrees": 45})
        export = export_viewer_scene(self.session)
        model = self.session.get_by_id(rid)
        opening = next(o for o in export["objects"] if "opening_win" in o["name"])
        fixed = next(o for o in export["objects"] if "fixed_rad" in o["name"])

        ov = opening.get("viewer") or {}
        self.assertEqual(ov.get("primitive"), "mesh")
        self.assertEqual(ov.get("display"), "wire")
        overts = ov.get("vertices") or []
        self.assertEqual(len(overts), 8)
        local_o = [room_core.room_world_to_local(model, v) for v in overts]
        ox = [c[0] for c in local_o]
        oy = [c[1] for c in local_o]
        # West opening: thin in local X, span along local Y
        self.assertLess(max(ox) - min(ox), 0.1)
        self.assertGreater(max(oy) - min(oy), 1.0)

        fv = fixed.get("viewer") or {}
        self.assertEqual(fv.get("primitive"), "mesh")
        fverts = fv.get("vertices") or []
        self.assertEqual(len(fverts), 8)
        local_f = [room_core.room_world_to_local(model, v) for v in fverts]
        fx = [c[0] for c in local_f]
        fy = [c[1] for c in local_f]
        # North radiator: span along local X, thin in local Y
        self.assertGreater(max(fx) - min(fx), 0.8)
        self.assertLess(max(fy) - min(fy), 0.25)

    def test_locked_room_rejects_rotate(self):
        room = self._create_room()
        rid = room["room_id"]
        self.session.apply_command(
            {"action": "set_room_locked", "room_id": rid, "locked": True}
        )
        with self.assertRaises(ValueError):
            self.session.apply_command({"action": "rotate_room", "room_id": rid, "degrees": 15})


if __name__ == "__main__":
    unittest.main()
