# DD-002: Generators Rebuild Mesh (No Blind Scaling)

Status: **Accepted**  
Date: 2026-07-09  
Version: 1.0

------------------------------------------------------------------------

## Problem

Scaling a bed mesh by 1.5× on the X axis makes everything wider — including
leg thickness, rail width, and pillow size. Real furniture does not behave
this way: legs stay the same diameter, spacing grows, pillow count may increase,
extra centre supports appear at extreme sizes.

Blind `object.scale` or uniform box scaling produces incorrect planning geometry
and teaches the AI the wrong model of how objects work.

## Decision

Generators **always rebuild geometry from parameters** using rules.

- Never scale an existing mesh as the primary parametric mechanism.
- Apply domain rules per component (posts capped relative to size, pillow count
  thresholds, minimum dimensions).
- Use fallbacks for unusual inputs instead of raising errors when possible.
- Regeneration means: delete old components → run generator again with new params.

Scaling via Blender's `object.scale` on generated objects is discouraged and
not part of the LayoutLab workflow.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Scale base mesh** | Violates furniture physics; unusable for planning |
| **Modifier stack (Array, Mirror)** | Hard to serialize params; Blender-specific; poor JSON round-trip |
| **Linked duplicates with scale** | Same scaling problem; no rule expression |
| **Hybrid: base mesh + selective rebuild** | Complexity without clear benefit at current scale |

## Consequences

**Positive**

- Geometry always matches semantic intent at any parameter value.
- Generators encode real-world expertise (see `bed_basic` pillow count rule).
- AI receives honest dimensions in scene export.
- Enables reliable regeneration once params are stored on objects `[PLANNED]`.

**Negative / trade-offs**

- Every parameter change requires full rebuild (performance cost at scale).
- Generators are more code than a static mesh.
- Requires `delete_prefix` / `delete_collection_objects` before re-run in v0.5 `[IMPLEMENTED]`.

## Example (bed_basic, v0.5)

```
width >= 13  →  2 pillows
width < 13   →  1 pillow

post_size = min(requested, width * 0.25, length * 0.25)
```

Not: `scale_x = width / default_width`

## Implementation Status

| Aspect | Status |
|---|---|
| Rule-based component placement in `bed_basic` | `[IMPLEMENTED]` |
| `regenerate` command (update params in place) | `[PLANNED]` |
| Undo integration for rebuild | `[PLANNED]` |

## References

- `LayoutLab_Generator_Specification.md` §6 Parametrik, §7 Fallbacks
- `docs/json_protocol.md` §4.1 `run_generator`
