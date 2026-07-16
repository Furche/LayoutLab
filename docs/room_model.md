# Room Model (DD-010)

**Status:** Accepted · Plugin **0.9.1**  
**Source of truth:** editable Room Model — not a furniture generator.

Related: [DD-010](design_decisions/DD-010-room-model.md) · [json_protocol.md](json_protocol.md) · [object_model.md](object_model.md)

------------------------------------------------------------------------

## Concept

```
Room Model (Core JSON)
  ├── footprint (kind: rectangle | later polygon)
  ├── walls (derived ids, stable across size updates)
  ├── openings (door / window on a wall)
  └── fixed_elements (radiator, …)
        ↓ sync
Blender meshes (adapter)
```

- Floor; **inward-facing wall planes** (opaque from inside, see-through from outside via backface culling)
- Opening placeholders; fixed boxes
- Default room origin **`[0, 0, 0]`**

------------------------------------------------------------------------

## MVP commands

| Action | Purpose |
|---|---|
| `create_room` | Rectangle room + four walls |
| `update_room` | Size / height / origin (wall ids preserved) |
| `delete_room` | Remove all meshes for `room_id` |
| `add_opening` / `update_opening` / `remove_opening` | Door or window |
| `add_fixed_element` / `update_fixed_element` / `remove_fixed_element` | e.g. radiator |

Wall reference: `wall_side` (`south`\|`east`\|`north`\|`west`) or `wall_id`.  
Room reference on mutate: `room` / `room_id` (not the opening name).

------------------------------------------------------------------------

## Reference kids room shell

See `tests/fixtures/reference_kids_room_shell_commands.json` — footprint ≈ 4.2 × 2.18 m at `[0, 0, 0]`.

------------------------------------------------------------------------

## Export

Scene export includes top-level `rooms[]` with `layoutlab.room`-equivalent fields (`room_id`, footprint, walls, openings, fixed_elements, `world_bounds`).

------------------------------------------------------------------------

## Not in MVP

Polygon footprints, free `add_wall`/`move_wall`, boolean door cuts, multi-room, analyze room-as-blocker (follow-up).
