# Room Model (DD-010)

**Status:** Accepted · Plugin **0.10.1**  
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

- Floor; **inward-facing wall panels** (opaque from inside, see-through from outside via backface culling)
- **Constructive openings:** wall quads are split around doors/windows (no Boolean) — portable to standalone later
- Opening wire placeholders (semantic markers); fixed boxes
- Default room origin **`[0, 0, 0]`**; sizes in Blender units (Metric: 1 = 1 m)

------------------------------------------------------------------------

## MVP commands

| Action | Purpose |
|---|---|
| `create_room` | Rectangle room + four walls |
| `update_room` | Size / height / origin (wall ids preserved; attachments reconciled) |
| `move_wall` | Parallel wall move (`delta`, outward-positive) — FC-001/WP-05 |
| `move_corner` | Corner `sw\|se\|nw\|ne` with `dx`/`dy` — FC-001/WP-05 |
| `delete_room` | Remove all meshes for `room_id` |
| `add_opening` / `update_opening` / `remove_opening` | Door or window (cuts wall panels) |
| `add_fixed_element` / `update_fixed_element` / `remove_fixed_element` | e.g. radiator |

Wall reference: `wall_side` (`south`\|`east`\|`north`\|`west`) or `wall_id`.  
Room reference on mutate: `room` / `room_id` (not the opening name).

Overlapping openings on the same wall raise an error at sync/panel build.
------------------------------------------------------------------------

## Reference kids room shell

Shell only: `tests/fixtures/reference_kids_room_shell_commands.json` — footprint ≈ 4.2 × 2.18 m at `[0, 0, 0]`.

Full layout (shell + bed + desk): `tests/fixtures/reference_kids_room_commands.json`.
------------------------------------------------------------------------

## Export

Scene export includes top-level `rooms[]` with `layoutlab.room`-equivalent fields (`room_id`, footprint, walls, openings, fixed_elements, `world_bounds`).

------------------------------------------------------------------------

## Not in MVP

Polygon footprints, free `add_wall`/`move_wall`, multi-room (follow-up).
Boolean modifiers are intentionally unused — openings use constructive panel splits.
`analyze_layout` treats `room_wall` / `room_fixed` as blockers; floor/opening wires are excluded.