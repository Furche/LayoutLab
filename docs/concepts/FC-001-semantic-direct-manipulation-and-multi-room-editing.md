# FC-001 — Semantic Direct Manipulation and Multi-Room Editing

**Status:** Active (WP-06 complete — Spatial Project `0.10.40`; WP-07 later)
**Date:** 2026-07-22
**Owner:** Product / Architecture
**Related:** [DD-009](../design_decisions/DD-009-ai-execution-boundary.md) · [DD-010](../design_decisions/DD-010-room-model.md) · [DD-014](../design_decisions/DD-014-standalone-runtime-path.md) · [DD-018](../design_decisions/DD-018-semantic-transactions-and-authority.md) (**Accepted**) · [DD-019](../design_decisions/DD-019-semantic-direct-manipulation.md) (**Accepted**) · [DD-020](../design_decisions/DD-020-spatial-project-independent-rooms.md) (**Accepted**) · [Room Model](../room_model.md) · [Spatial Project vision](../Future_Ideas.md#13-spatial-project-model)

------------------------------------------------------------------------

## 1. Purpose

LayoutLab must be directly editable without forcing every change through the AI
chat. Users should be able to select, move, resize, duplicate, hide and delete
rooms and furniture in the 3D viewport while preserving the semantic model used by
generators, analysis, planning candidates and AI proposals.

The viewport is therefore not an independent mesh editor. It is a visual editing
surface for authoritative LayoutLab domain state.

> Direct manipulation changes the semantic LayoutLab model. Runtime geometry is a
> deterministic projection of that model.

This concept also extends the current single-space Room Model toward a Spatial
Project containing multiple independently editable rooms.

------------------------------------------------------------------------

## 2. Product principles

### 2.1 Semantic edits, not raw mesh edits

Moving or resizing an element updates semantic properties such as position,
rotation, dimensions, generator parameters, room membership and support relation.
The runtime then updates or regenerates geometry.

### 2.2 Preserve user intent; expose consequences

Manual edits may create invalid states. LayoutLab must not silently repair,
relocate, resize or delete other elements. It preserves the requested change and
shows the resulting conflict.

### 2.3 Preserve data whenever possible

Elements that temporarily cannot be represented remain in domain state as invalid
or inactive. Restoring compatible geometry restores them automatically.

### 2.4 Every committed edit is reversible

One completed gesture equals one semantic transaction and one Undo step. An
applied AI candidate is also one transaction.

### 2.5 Manual editing and AI share one authority model

The user, AI, planner and imports must not maintain parallel versions of the room.
They operate through the same versioned command and transaction boundary.

------------------------------------------------------------------------

## 3. Direct room editing

### 3.1 Selection and tools

A room is a first-class selectable object with stable identity, geometry,
transform, walls, openings, fixed elements, furniture membership and validation
state.

The initial interaction can use explicit tools rather than a full modelling edit
mode:

```text
Select room
Move room
Move wall
Move corner
Add/edit opening
Numeric inspector
```

A dedicated Room Edit Mode may follow when polygonal footprints and wall graphs
make the tool set complex enough to justify it.

### 3.2 Moving a wall

Dragging a wall moves it parallel to itself:

- the opposite wall remains fixed;
- adjacent walls are lengthened or shortened;
- room dimensions update live;
- snapping may target grid, measures, other walls and alignment guides;
- the drag is preview-only until mouse release.

Corner handles move two adjacent walls together. Numeric input provides exact
dimensions alongside mouse editing.

------------------------------------------------------------------------

## 4. Furniture behaviour when room boundaries change

### 4.1 Resize preserves furniture world positions

When one room wall moves, all furniture remains at its existing world position.
This applies both when enlarging and shrinking the room.

Furniture is not automatically moved, scaled or rearranged.

If the edited boundary changes the room-local origin, LayoutLab recomputes each
furniture local transform from its preserved world transform. “Stays in place” is
therefore a spatial invariant, not an accident of one coordinate convention.

### 4.2 Invalid but still associated

If a boundary change leaves furniture intersecting a wall or outside its room, the
object remains assigned to that room but becomes invalid and is shown in red.

Illustrative states:

```text
VALID
INVALID_INTERSECTS_WALL
INVALID_OUTSIDE_ROOM
INVALID_COLLISION
INVALID_CLEARANCE
```

Membership and validity are separate facts:

```text
membership: the object still belongs to Room A
validity: the object is currently not valid within Room A
```

LayoutLab recalculates validity after relevant changes. If the object later lies
fully and validly inside its assigned room again, it automatically returns to
`VALID`.

------------------------------------------------------------------------

## 5. Moving a whole room

A room may be moved as one project object.

- Valid furniture assigned to the room moves with it and retains its local layout.
- Invalid furniture assigned to the room remains at its absolute world position.
- The invalid object's room membership remains until the user reassigns or deletes it.
- Once the object is validly inside its room again, it automatically participates
  in subsequent room moves.

To keep an invalid object fixed in world space while its assigned room moves,
LayoutLab recomputes that object's room-local transform using the inverse of the new
room transform. The object does not become world-owned merely because it is invalid.

This requires three distinct concepts:

```text
membership             -> which room owns the object semantically?
validity               -> is it currently valid in that room?
transform participation -> does it follow the room transform now?
```

The UI should make a left-behind object's membership visible through a warning,
inspector message, issue list or relationship marker.

------------------------------------------------------------------------

## 6. Walls, windows and doors

### 6.1 Openings belong to walls

Windows and doors attach semantically to a stable wall, for example through:

```text
wall_id
offset_along_wall
width
height
sill_height
opening_direction
state
```

### 6.2 Host-wall movement

When a wall moves parallel to itself, all windows and doors hosted by that wall
move with it. Their offset along the wall and other parameters remain unchanged.

### 6.3 Adjacent-wall shortening

Openings on adjacent walls keep their world position. LayoutLab does not slide
them inward merely to preserve visibility. If an adjacent wall endpoint moves,
`offset_along_wall` is recalculated against the updated wall segment.

If shortening a wall places an opening beyond the remaining wall segment:

- the opening is not deleted;
- its host relation and offset remain stored;
- its state becomes `INACTIVE_OUTSIDE_WALL`;
- it disappears from rendered geometry;
- extending the wall far enough restores it automatically at the same position.

Furniture remains visibly invalid because the user must be able to repair it.
An opening without host-wall surface becomes invisible because it has no currently
representable geometry. Both retain their data.

------------------------------------------------------------------------

## 7. Direct furniture editing

### 7.1 Move and rotate

Normal floor furniture moves in the room's XY plane and rotates around Z. It
remains attached to a semantic support surface rather than a hard-coded `z = 0`:

```text
support_ref = room_floor
```

This keeps a future extension open for:

```text
support_ref = table.surface_top
support_ref = shelf.surface
support_ref = wall
support_ref = ceiling
```

The MVP only needs floor support. Free vertical placement and stacking are later
work, not part of the first direct-manipulation slice.

### 7.2 Snapping and feedback

Optional snapping may target room grids, wall planes, corners, centres, furniture
edges, semantic anchor points and preferred clearances.

During manipulation the viewport should distinguish:

```text
green  -> valid
orange -> valid but functionally weak
red    -> invalid
```

The user may still commit a red position. It remains visible and invalid rather
than being rejected or silently repaired.

### 7.3 Resize through parameters

Furniture handles and numeric fields modify semantic generator parameters. The
object is regenerated instead of applying naive mesh scale.

Examples:

- widening a bed moves fixed-size posts, resizes frame and mattress, redistributes
  headboard/rails and may change one pillow into two;
- widening a wardrobe may add a door, redistribute compartments and reposition
  handles after defined thresholds.

Unusual user dimensions are accepted when technically constructible. Generators
use documented fallbacks and warnings rather than silently substituting standard
dimensions.

For responsive dragging, the viewport may show simplified preview geometry and run
full deterministic regeneration on release.

------------------------------------------------------------------------

## 8. Spatial Project and multiple rooms

The future authoring root is a Spatial Project rather than an implicit single
scene or single room:

```text
Spatial Project
|- Room A
|  |- Walls / openings / fixed elements
|  `- Furniture
|- Room B
`- Room C
```

Each room has a stable ID, transform, geometry, contents, visibility, lock state
and analysis state. Furniture normally uses room-local coordinates:

```text
world_transform = room_transform * furniture_local_transform
```

The invalid-object exception described in section 5 deliberately preserves world
position during a whole-room move.

The first multi-room implementation should support independent rooms. Shared-wall
ownership, coupled wall edits, passages and multi-floor buildings require a later
extension rather than being hidden inside the first version.

------------------------------------------------------------------------

## 9. Common project operations

Rooms and furniture should support:

- select and multi-select;
- move and rotate where applicable;
- duplicate with new stable IDs and rewritten internal references;
- delete through a reversible transaction;
- hide/show;
- include/exclude from analysis;
- lock against editing;
- protect from AI changes.

Visibility, analysis participation and editability are different properties:

```text
visible
included_in_analysis
locked
protected_from_ai
```

Duplicating a room copies its semantic fabric and valid contents. The product must
explicitly define whether invalid associated objects are included; it must not be
an accidental consequence of scene parenting.

------------------------------------------------------------------------

## 10. Transactions, Undo and Redo

All mutations become semantic transactions with actor and revision metadata:

```text
actor: user | ai | planner | system | import
action
base_revision
result_revision
operations
description
timestamp
```

For dragging:

```text
mouse down -> begin preview
mouse move -> update preview only
mouse up   -> commit one transaction
Escape     -> discard preview
```

Applying one AI candidate creates one Undo unit regardless of how many underlying
objects changed.

Redo reapplies the same committed semantic transaction. It must reproduce the same
result against the revision created by its corresponding Undo rather than invoking
an AI, generator decision or repair heuristic again.

------------------------------------------------------------------------

## 11. Protecting manual work from AI

AI proposals target a specific `base_revision`. If the project changed after the
proposal was produced, LayoutLab must revalidate or regenerate it rather than
blindly applying stale commands.

Users may lock an entire object or individual properties:

```text
position
rotation
dimensions
generator parameters
room geometry
```

`protected_from_ai` is a hard constraint. Provenance records whether a property was
last changed by user, AI, planner or import. Manual choices must not be silently
overwritten by later AI assumptions.

The AI continues to work on cloned candidate state:

```text
clone current revision
-> apply candidate internally
-> validate and analyze
-> discard invalid attempts
-> present viable proposal
-> explicit user Apply
-> commit one transaction
```

------------------------------------------------------------------------

## 12. Interaction details worth preserving

Later UI work may include:

- live dimensions and direct numeric entry;
- keyboard nudging and configurable grid increments;
- temporary snapping override;
- ghost display of the previous position;
- alignment and distribution tools;
- groups and multi-selection;
- issue list per room;
- before/after comparison;
- manual variants;
- targeted repair suggestions without automatic repair.

------------------------------------------------------------------------

## 13. Example

The user drags a bedroom's north wall southward.

1. The north-wall windows move with the wall.
2. East and west walls become shorter.
3. An east-wall window falls beyond its wall endpoint, becomes
   `INACTIVE_OUTSIDE_WALL` and disappears without data loss.
4. A wardrobe now intersects the north wall. It stays where it was, remains assigned
   to the bedroom, becomes invalid and is shown red.
5. Releasing the mouse commits one Undo step.
6. Extending the walls later restores the hidden window.
7. Once the wardrobe lies validly inside the room again, it returns to `VALID`.
8. If the entire room is then moved, the valid wardrobe moves with it.

------------------------------------------------------------------------

## 14. Architectural decomposition required before implementation

This concept deliberately spans several subsystems. It should not become one giant
DD or one giant implementation ticket. At minimum, implementation requires explicit
decisions for:

1. **Transactions, revisions, Undo/Redo and authority** — [DD-018](../design_decisions/DD-018-semantic-transactions-and-authority.md) (**Accepted**)
2. **Semantic direct manipulation** — [DD-019](../design_decisions/DD-019-semantic-direct-manipulation.md) (**Accepted**)
3. **Spatial Project / Multi-Room** — [DD-020](../design_decisions/DD-020-spatial-project-independent-rooms.md) (**Accepted**)

DD-010 remains the accepted single-space foundation. This concept extends it; it
does not rewrite it.

**WP-01…WP-06 status:** complete through Spatial Project / independent rooms (`0.10.40`).
Next optional: **FC-001/WP-07** (advanced supports / stacking — explicitly later).
Locked Accept defaults include: session Undo ≥ 50
with integer revision; duplicate includes invalid membership; fixed elements become inactive
not deleted; Spatial Project is the only durable format (`rooms[]`, n = 1 normal; no legacy
single-room export).

------------------------------------------------------------------------

## 15. Derived work packages

These identifiers are roadmap references, not implementation-ready tickets by
themselves.

| ID | Work package | Entry condition |
|---|---|---|
| **FC-001/WP-01** | Architecture package: define the three decisions above and resolve schema ownership | **Done** — DD-018/019/020 Accepted |
| **FC-001/WP-02** | Transaction/revision foundation with preview, commit, Undo/Redo and stale proposal protection | **Done** — `0.10.36` (DD-018) |
| **FC-001/WP-03** | Single-room furniture selection, XY move/Z rotation, floor support, duplicate/delete/hide/lock | **Done** — `0.10.37` (DD-019) |
| **FC-001/WP-04** | Parametric furniture resize through generator parameters and regeneration | **Done** — `0.10.38` (DD-019) |
| **FC-001/WP-05** | Wall/corner resize, opening host behaviour, inactive opening restoration and invalid furniture visualization | **Done** — `0.10.39` (DD-019) |
| **FC-001/WP-06** | Independent multi-room Spatial Project, local transforms and whole-room operations | **Done** — `0.10.40` (DD-020) |
| **FC-001/WP-07** | Advanced support surfaces and stacking | Explicitly later |

Each work package must update binding contracts and tests in the same change. No
work package may implement raw viewport-only state that bypasses Core.

WP-01 locked defaults (see DD-018/019/020 Acceptance notes):

- duplicate room includes invalid associated objects and inactive openings/fixed elements;
- wall-hosted fixed elements become inactive (not deleted) when swallowed, like openings;
- session Undo default ≥ 50; integer project revision;
- Spatial Project with `rooms[]` is the only durable format (no legacy single-room export).

------------------------------------------------------------------------

## 16. Non-goals for the first implementation

- freeform mesh editing;
- shared-wall topology between rooms;
- automatic repair after manual edits;
- arbitrary vertical placement and physics-based stacking;
- multi-floor buildings;
- full CAD constraint solver;
- allowing AI to apply stale or unvalidated changes.

------------------------------------------------------------------------

## 17. Guiding statement

> Users may edit LayoutLab directly and freely. The system preserves their data,
> exposes invalid states instead of repairing them silently, and keeps manual and
> AI changes on the same semantic, versioned and reversible model.
