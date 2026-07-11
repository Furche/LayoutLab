# DD-003: Communication Exclusively via JSON

Status: **Accepted**  
Date: 2026-07-09  
Version: 1.0

------------------------------------------------------------------------

## Problem

If ChatGPT sends Python code that calls `bpy.ops` directly, several failures
occur:

- Tight coupling to Blender version and operator names
- No validation layer between AI and scene
- Security risk (`exec` of arbitrary code in Blender context)
- Impossible to log, replay, or diff AI actions
- Plugin and AI evolve independently and break silently

## Decision

All AI → plugin communication uses **JSON commands** only.

- AI sends `{"commands": [...]}` with declarative `action` fields.
- Plugin validates and dispatches each command sequentially.
- Scene state returns to AI as JSON export (clipboard).
- The only exception: `save_generator` carries Python source as a string field
  — this is generator *authorship*, not scene manipulation.

AI must not instruct users to paste Python into Blender's scripting panel for
LayoutLab workflows.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Python snippets for AI** | No schema, no validation, breaks on Blender updates |
| **Natural language → direct bpy** | Requires NLP inside plugin; wrong layer |
| **Custom binary protocol** | Not human-readable; bad for AI and debugging |
| **MCP / REST API to Blender** | Possible future frontend `[PLANNED]`; JSON remains the semantic layer |

## Consequences

**Positive**

- Plugin and AI are decoupled — either side can version independently.
- Commands are replayable, loggable, and testable.
- Full specification possible (`docs/json_protocol.md`).
- Multiple AI agents (ChatGPT, Cursor, scripts) can use the same interface.

**Negative / trade-offs**

- JSON is verbose for complex geometry (generators preferred over raw boxes).
- No structured error response yet — failures go to Blender console only `[PLANNED]`.
- `protocol_version` field not yet enforced `[PLANNED]`.

## Rules for Agents

1. Use `run_generator` when a generator exists — not manual `create_box` chains.
2. Check exported `generators` list before calling unknown generator names.
3. Prefer batch commands in one `commands` array for atomic layout operations.
4. Do not send Python for direct Blender execution.

## Implementation Status

| Aspect | Status |
|---|---|
| JSON command input (clipboard / text block) | `[IMPLEMENTED]` v0.5 |
| Scene JSON export | `[IMPLEMENTED]` v0.5 |
| Full protocol spec | `[IMPLEMENTED]` `docs/json_protocol.md` |
| Structured error response | `[PLANNED]` |
| `protocol_version` field | `[PLANNED]` |

## References

- `docs/json_protocol.md`
- `00_READ_THIS_FIRST.md` — AI agent rules
- `LayoutLab_Master_Design_Document.md` §11
- [DD-009](DD-009-ai-execution-boundary.md) — why plugin execution layer exists (broader than JSON transport)
