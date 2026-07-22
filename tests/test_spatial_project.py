"""FC-001/WP-06 — Spatial Project / independent rooms (DD-020)."""

from __future__ import annotations

import unittest

from layoutlab.runtime.session import RoomSession, export_viewer_scene
from layoutlab.runtime import furniture_ops
from layoutlab.protocol.viewer_export import VIEWER_SCHEMA


class SpatialProjectTests(unittest.TestCase):
    def setUp(self):
        self.session = RoomSession()

    def _create_room(self, name="ROOM_A", location=(0, 0, 0), width=4.0, depth=3.0):
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
        furniture_ops.ensure_semantic_defaults(self.session.mesh_store, self.session._rooms, oid)
        main = furniture_ops.main_part(self.session.mesh_store, oid)
        main["layoutlab_room_id"] = room_id
        for part in furniture_ops.objects_for_id(self.session.mesh_store, oid):
            part["layoutlab_room_id"] = room_id
        furniture_ops.refresh_validity(self.session.mesh_store, self.session._rooms, oid)
        return oid

    def test_export_has_project_wrapper(self):
        self._create_room()
        export = export_viewer_scene(self.session)
        self.assertEqual(export["viewer_schema"], VIEWER_SCHEMA)
        self.assertEqual(VIEWER_SCHEMA, "0.1.2")
        self.assertTrue(export["project_id"])
        self.assertEqual(export["project_id"], self.session.project_id)
        self.assertIn("project", export)
        self.assertEqual(export["project"]["project_id"], self.session.project_id)
        self.assertEqual(export["scene"], "SpatialProject")
        self.assertEqual(len(export["rooms"]), 1)
        room = export["rooms"][0]
        self.assertIn("transform", room)
        self.assertTrue(room["visible"])
        self.assertFalse(room["locked"])
        self.assertTrue(room["included_in_analysis"])
        self.assertFalse(room["protected_from_ai"])

    def test_two_independent_rooms(self):
        a = self._create_room("A", location=(0, 0, 0))
        b = self._create_room("B", location=(10, 0, 0), width=3.0, depth=3.0)
        self.assertEqual(len(self.session._rooms), 2)
        self.assertNotEqual(a["room_id"], b["room_id"])
        # Moving A must not mutate B fabric.
        self.session.apply_command(
            {"action": "move_room", "room_id": a["room_id"], "dx": 1.0, "dy": 0.5}
        )
        model_b = self.session.get_by_id(b["room_id"])
        self.assertEqual(model_b["origin"][0], 10.0)
        self.assertEqual(model_b["footprint"]["width"], 3.0)

    def test_move_room_valid_follows_invalid_stays(self):
        room = self._create_room(location=(0, 0, 0), width=4.0, depth=3.0)
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

        vx0 = furniture_ops.main_part(self.session.mesh_store, valid_id).location.x
        vy0 = furniture_ops.main_part(self.session.mesh_store, valid_id).location.y
        ix0 = furniture_ops.main_part(self.session.mesh_store, invalid_id).location.x

        result = self.session.apply_command(
            {"action": "move_room", "room_id": rid, "dx": 2.0, "dy": 1.0}
        )
        self.assertIn(valid_id, result["followed"])
        self.assertIn(invalid_id, result["left_behind"])
        self.assertAlmostEqual(
            furniture_ops.main_part(self.session.mesh_store, valid_id).location.x, vx0 + 2.0, places=4
        )
        self.assertAlmostEqual(
            furniture_ops.main_part(self.session.mesh_store, invalid_id).location.x, ix0, places=4
        )
        # Membership preserved for invalid.
        self.assertEqual(
            furniture_ops.main_part(self.session.mesh_store, invalid_id).get("layoutlab_room_id"),
            rid,
        )
        model = self.session.get_by_id(rid)
        self.assertAlmostEqual(model["origin"][0], 2.0, places=4)
        self.assertAlmostEqual(model["origin"][1], 1.0, places=4)

        # Local location for followed furniture equals pre-move world (origin started at 0).
        export = export_viewer_scene(self.session)
        main_export = None
        for o in export["objects"]:
            layoutlab = o.get("layoutlab") or {}
            if layoutlab.get("object_id") != valid_id:
                continue
            if layoutlab.get("part_type") == "main" or layoutlab.get("part") == "body":
                main_export = o
                break
        self.assertIsNotNone(main_export)
        local = main_export["local_location"]
        self.assertAlmostEqual(local[0], vx0, places=3)
        self.assertAlmostEqual(local[1], vy0, places=3)

    def test_duplicate_room_includes_invalid_and_inactive(self):
        room = self._create_room(width=4.0, depth=3.0)
        rid = room["room_id"]
        self.session.apply_command(
            {
                "action": "add_opening",
                "params": {
                    "room_id": rid,
                    "wall_side": "south",
                    "kind": "door",
                    "name": "door1",
                    "offset": 0.5,
                    "width": 0.9,
                    "height": 2.0,
                },
            }
        )
        # Shrink south via move_wall so opening may become inactive if offset out of range —
        # instead place opening near end then shrink width.
        invalid_id = self._spawn_furniture(rid, name="out", location=(50.0, 50.0, 0.0))
        valid_id = self._spawn_furniture(rid, name="in", location=(1.0, 1.0, 0.0))

        dup = self.session.apply_command(
            {
                "action": "duplicate_room",
                "room_id": rid,
                "offset": [5.0, 0.0, 0.0],
                "new_name": "ROOM_A_copy",
            }
        )
        self.assertEqual(len(self.session._rooms), 2)
        new_id = dup["room_id"]
        self.assertNotEqual(new_id, rid)
        self.assertEqual(dup["name"], "ROOM_A_copy")
        self.assertEqual(len(dup["duplicated_object_ids"]), 2)
        self.assertEqual(dup["opening_count"], 1)

        # Source room unchanged.
        src = self.session.get_by_id(rid)
        self.assertEqual(src["origin"][0], 0.0)
        self.assertEqual(len(src["openings"]), 1)

        clone = self.session.get_by_id(new_id)
        self.assertAlmostEqual(clone["origin"][0], 5.0, places=4)
        self.assertEqual(len(clone["openings"]), 1)
        self.assertNotEqual(clone["openings"][0]["opening_id"], src["openings"][0]["opening_id"])

        # Invalid membership copied to new room.
        new_invalid = [
            oid
            for oid in dup["duplicated_object_ids"]
            if furniture_ops.validity_of(furniture_ops.main_part(self.session.mesh_store, oid))
            == furniture_ops.VALIDITY_OUTSIDE
        ]
        self.assertEqual(len(new_invalid), 1)
        self.assertEqual(
            furniture_ops.main_part(self.session.mesh_store, new_invalid[0]).get(
                "layoutlab_room_id"
            ),
            new_id,
        )
        # Source invalid still on source room.
        self.assertEqual(
            furniture_ops.main_part(self.session.mesh_store, invalid_id).get("layoutlab_room_id"),
            rid,
        )
        self.assertEqual(
            furniture_ops.main_part(self.session.mesh_store, valid_id).get("layoutlab_room_id"),
            rid,
        )

    def test_room_flags_hide_and_lock(self):
        room = self._create_room()
        rid = room["room_id"]
        self.session.apply_command(
            {"action": "set_room_flags", "room_id": rid, "locked": True, "protected_from_ai": True}
        )
        model = self.session.get_by_id(rid)
        self.assertTrue(model["locked"])
        self.assertTrue(model["protected_from_ai"])
        with self.assertRaises(ValueError):
            self.session.apply_command({"action": "move_room", "room_id": rid, "dx": 1.0})

        self.session.apply_command(
            {"action": "set_room_flags", "room_id": rid, "locked": False}
        )
        self.session.apply_command({"action": "hide_room", "room_id": rid})
        export = export_viewer_scene(self.session)
        self.assertFalse(export["rooms"][0]["visible"])
        # Hidden rooms omit fabric meshes but remain in rooms[].
        roles = {o.get("layoutlab", {}).get("role") for o in export["objects"]}
        self.assertNotIn("room_floor", roles)

    def test_delete_room_removes_member_furniture(self):
        room = self._create_room()
        rid = room["room_id"]
        oid = self._spawn_furniture(rid)
        self.session.apply_command({"action": "delete_room", "room_id": rid})
        self.assertEqual(len(self.session._rooms), 0)
        self.assertIsNone(furniture_ops.main_part(self.session.mesh_store, oid))

    def test_commit_move_room_bumps_revision(self):
        room = self._create_room()
        out = self.session.commit_commands(
            [{"action": "move_room", "room_id": room["room_id"], "dx": 1.0, "dy": 0.0}],
            actor="user",
            action="move_room",
        )
        self.assertTrue(out["ok"])
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(out["export"]["project"]["revision"], 1)


if __name__ == "__main__":
    unittest.main()
