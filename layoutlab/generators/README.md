# Reference Generators

Version-controlled parametric generators. Bundled copies sync to the Blender
user directory on addon register (if missing).

| Generator | Description | Docs |
|---|---|---|
| `bed_basic` | Parametric low bed | [bed_basic.md](bed_basic.md) |
| `wardrobe_basic` | Parametric wardrobe with doors, shelves, clearance | [wardrobe_basic.md](wardrobe_basic.md) |

## Authoring Checklist

Every new generator must:

1. Define all five metadata constants (`GENERATOR_NAME`, …, `GENERATOR_ICON`)
2. Implement `generate(params, api)` using only the LayoutLab API
3. Set `layoutlab_role` on every component mesh
4. Apply rules and fallbacks — no blind scaling
5. Include a `{name}.md` reference document (params, components, examples, limits)
6. Be listed in this README

Pattern reference: **`bed_basic`**, **`wardrobe_basic`** — review before creating generator #3.  
Full guide: **[docs/how_to_write_generators.md](../../docs/how_to_write_generators.md)**
