# DD-005: Generators Carry Metadata Constants

Status: **Accepted**  
Date: 2026-07-09  
Version: 1.0

------------------------------------------------------------------------

## Problem

Without standard metadata, generators are anonymous Python files. The browser
cannot show categories, the AI cannot describe available tools, and users
cannot distinguish versions or understand purpose before running code.

## Decision

Every generator **must** declare metadata as module-level string constants:

```python
GENERATOR_NAME = "bed_basic"
GENERATOR_CATEGORY = "Beds"
GENERATOR_DESCRIPTION = "Parametric low bed with legs, frame, mattress..."
GENERATOR_VERSION = "0.1"
GENERATOR_ICON = "BED"
```

Rules:

- `GENERATOR_NAME` is the unique identifier and filename stem (sanitized).
- Metadata is parsed from source without executing the generator `[IMPLEMENTED]`.
- Browser, scene export, and generator list export all use the same metadata.
- Icons use Blender icon names (e.g. `BED`, `SCRIPT`, `HOME`).

Optional future fields `[PLANNED]`: author, license, tags, thumbnail path, examples.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Metadata in JSON sidecar** | Two files per generator; sync risk |
| **Metadata only in docstring** | Hard to parse reliably; not structured |
| **Metadata in Blender custom properties** | Wrong layer; generators exist before scene |
| **Infer everything from function name** | Fragile; no category or description |

## Consequences

**Positive**

- Browser can list and filter without running generator code.
- Scene export includes full generator catalog for AI context.
- Version field enables compatibility checks `[PLANNED]`.
- New generators are self-describing for both humans and AI.

**Negative / trade-offs**

- Regex parsing of constants is fragile if formatting is unusual `[IMPLEMENTED]`.
- Broken generators show category `"Broken"` with error icon — acceptable fallback.
- No schema validation on save yet `[PLANNED]`.

## Required Metadata (v0.5)

| Constant | Required | Default if missing |
|---|---|---|
| `GENERATOR_NAME` | yes | filename stem |
| `GENERATOR_CATEGORY` | no | `"Uncategorized"` |
| `GENERATOR_DESCRIPTION` | no | `""` |
| `GENERATOR_VERSION` | no | `""` |
| `GENERATOR_ICON` | no | `"SCRIPT"` |

## Implementation Status

| Aspect | Status |
|---|---|
| Metadata constants in generator source | `[IMPLEMENTED]` |
| Regex inference (`infer_generator_meta_from_code`) | `[IMPLEMENTED]` |
| Browser display | `[IMPLEMENTED]` |
| Export in scene JSON and generator list | `[IMPLEMENTED]` |
| Validation on `save_generator` | `[PLANNED]` |
| Thumbnail / tags / author fields | `[PLANNED]` |

## References

- `LayoutLab_Generator_Specification.md` §3, §11
- `docs/json_protocol.md` §5.2 Generator metadata entry
- `layoutlab_chatgpt_helper_v05.py` — `infer_generator_meta_from_code`
