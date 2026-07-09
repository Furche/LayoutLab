# LayoutLab — Generator Developer Guide

Version: 1.0

> **Zielgruppe:** Menschen und KI, die neue LayoutLab-Generatoren schreiben.  
> **Charakter:** Praktischer Leitfaden mit Beispielen und Workflows.

Verwandte Dokumente (nicht duplizieren — dort nachschlagen):

| Dokument | Inhalt |
|---|---|
| [LayoutLab_Generator_Specification.md](../LayoutLab_Generator_Specification.md) | **Normativer Standard** — Pflichtregeln, Qualitätsbar |
| [docs/generator_api.md](generator_api.md) | **API-Referenz** — Signaturen und Verhalten der `api`-Funktionen |
| [docs/object_model.md](object_model.md) | Semantische Objekt-Metadaten auf Meshes |
| [docs/units_and_coordinates.md](units_and_coordinates.md) | Achsen, Maßstab (1 Unit ≈ 10 cm) |
| [layoutlab/generators/bed_basic.md](../layoutlab/generators/bed_basic.md) | Referenz-Instanz: vollständige Parameterliste |

**Dokumentationspflicht:** Wenn sich Generator-API, -struktur, -regeln, Parameter oder Best Practices ändern, **muss dieses Dokument mitaktualisiert werden** (siehe [docs/documentation_map.md](documentation_map.md)).

------------------------------------------------------------------------

# 1. Was ist ein Generator?

Ein Generator ist **kein Mesh** und **kein Blender-Asset**. Er ist ein **Regelwerk**, das aus Parametern Geometrie erzeugt.

```
Parameter  →  Generator (Regeln)  →  Komponenten  →  Meshes in der Szene
```

Ein Generator beschreibt **Wissen über einen Objekttyp** — z. B. wie ein Bett bei anderer Breite seine Pfosten, Matratze und Kissen neu platziert.

Der Engine-Aufruf (`run_generator` / `regenerate`) kümmert sich um:

- Laden und Ausführen des Python-Codes
- Injektion der LayoutLab-API (`api`-Dict)
- Automatisches Setzen von `layoutlab_object_id`, `layoutlab_params`, … auf erzeugte Meshes (v0.5.1+)

Der Generator selbst enthält **nur Möbel-Logik**.

------------------------------------------------------------------------

# 2. Wann einen neuen Generator erstellen?

| Situation | Empfehlung |
|---|---|
| Neuer **Objekttyp** (Schrank, Tisch, Tür) | Neuer Generator |
| Variante desselben Typs (Hochbett vs. Niedrigbett) | Neuer Generator **oder** Parameter an bestehendem (wenn Regeln sich teilen) |
| Einmalige Box in der Szene | **Kein** Generator — JSON `create_box` |
| Gleiche Logik in zwei Generatoren | Später: gemeinsame Komponenten extrahieren (noch nicht im Core) |
| Nur Farbe/Material ändern | Parameter des bestehenden Generators |

**Faustregel:** Wenn es eine **wiederholbare Regel** gibt („so funktioniert ein Bett"), gehört sie in einen Generator. Wenn es eine **Einmal-Aktion** ist, reicht ein JSON-Command.

------------------------------------------------------------------------

# 3. Verantwortung

## 3.1 Was ein Generator tut

- Geometrie über die LayoutLab-API erzeugen
- Parameter interpretieren, Defaults und Fallbacks anwenden
- Komponenten logisch trennen (Pfosten, Matratze, …)
- `layoutlab_role` auf jeder Komponente setzen
- Sinnvolles Return-Dict liefern (`created`, `type`, …)
- Optional: `{name}.md` mit Parametern und Beispielen dokumentieren

## 3.2 Was ein Generator ausdrücklich NICHT tut

| Verboten | Warum |
|---|---|
| UI (Panels, Operatoren) | UI gehört in `layoutlab/plugin/` |
| Szenen analysieren (andere Objekte lesen) | Generatoren sind zustandslos pro Aufruf |
| Andere Generatoren aufrufen oder ändern | Engine orchestriert; keine Generator-zu-Generator-Kopplung |
| Globale Blender-Einstellungen ändern | Seiteneffekte brechen Batch-Commands |
| Blind skalieren statt neu bauen | Verstößt gegen DD-002 |
| Direktes `bpy` wenn API reicht | Untestbar, bricht Architektur-Grenze |

Ausnahme: `api["bpy"]` ist technisch verfügbar — nur nutzen, wenn **keine** API-Funktion existiert, und in `{name}.md` begründen.

------------------------------------------------------------------------

# 4. Aufbau eines Generators

## 4.1 Dateistruktur

```
layoutlab/generators/
├── my_generator.py      # Code (Pflicht)
├── my_generator.md      # Referenz-Doku (Pflicht für bundled Generators)
└── README.md            # Index — Eintrag ergänzen
```

Runtime-Kopie (automatisch beim ersten Register, wenn fehlend):

```
…/scripts/addons/layoutlab_generators/my_generator.py
```

## 4.2 Pflicht-Metadaten

Am Dateianfang — **exakt diese Konstantennamen** (Browser liest sie per Regex):

```python
GENERATOR_NAME = "my_generator"
GENERATOR_CATEGORY = "Furniture"
GENERATOR_DESCRIPTION = "Kurze, verständliche Beschreibung für den Browser."
GENERATOR_VERSION = "0.1"
GENERATOR_ICON = "MESH_CUBE"   # Blender icon name
```

## 4.3 Pflicht-Funktion

```python
def generate(params, api):
    # … Geometrie erzeugen …
    return {"created": name, "type": GENERATOR_NAME, ...}
```

- **`params`:** Dict aus JSON (`run_generator`) oder gemergte Params (`regenerate`)
- **`api`:** LayoutLab-API — siehe [generator_api.md](generator_api.md)
- **Return:** Dict; mindestens `created` (Name-Präfix) und `type` (Generator-Name)

------------------------------------------------------------------------

# 5. Parameter

## 5.1 Konventionen

| Parameter | Typische Bedeutung |
|---|---|
| `name` | Präfix für **alle** Objektnamen (`BED_120x200_mattress`) |
| `location` | `[x, y, z]` — Min-Ecke des Footprints auf dem Boden |
| `collection` | Blender-Collection (Default: `"layout_tests"`) |
| `length`, `width`, `height` | Ausdehnung in Blender-Units entlang Achsen |

Achsen und Maßstab: [units_and_coordinates.md](units_and_coordinates.md)

## 5.2 Lesen mit Defaults

```python
name = params.get("name", "MY_default")
x, y, z = params.get("location", [0, 0, 0])
length = max(params.get("length", 10), MIN_LENGTH)
collection = params.get("collection", "layout_tests")
```

Niemals auf fehlende Keys mit `KeyError` reagieren, wenn ein sinnvoller Default existiert.

## 5.3 Validierung

- **Clamp** numerische Werte (Mindestmaße, Maximalanteile)
- **Fallback** für unbekannte Enums (z. B. `head_side` → `y_max`)
- Nur **Exception**, wenn die Eingabe wirklich nicht interpretierbar ist

------------------------------------------------------------------------

# 6. Collections

Generatoren platzieren Objekte über die API — nicht manuell in die Szene verlinken:

```python
collection = params.get("collection", "layout_tests")
cb = api["create_box"]
cb(f"{name}_part", [x, y, z], [dx, dy, dz], color, collection, "my_role", None)
```

`get_or_create_collection` wird intern von `create_box` / `create_label` aufgerufen.

**Regel:** Alle Komponenten eines logischen Objekts in dieselbe `collection`, sofern der Aufrufer nichts anderes verlangt.

------------------------------------------------------------------------

# 7. LayoutLab API (Kurzüberblick)

Vollständige Signaturen: **[generator_api.md](generator_api.md)**

| Funktion | Zweck |
|---|---|
| `create_box(name, loc, dims, color, collection, role, display_type)` | Axis-aligned Box |
| `create_label(name, loc, text, collection, size)` | Text-Label |
| `ensure_material(name, color)` | Material (meist via `create_box`) |
| `get_or_create_collection(name)` | Collection holen/erzeugen |
| `delete_collection_objects(name)` | Collection leeren |
| `delete_prefix(prefix)` | Objekte nach Namenspräfix löschen |
| `math` | Standard-math-Modul |
| `bpy` | Nur wenn nötig — siehe oben |

### Automatische Metadaten (v0.5.1+)

Während `execute_generator()` läuft, taggt die Engine **automatisch** jede via API erzeugte Komponente mit:

- `layoutlab_object_id`, `layoutlab_generator`, `layoutlab_params`, `layoutlab_component`

Generatoren müssen das **nicht manuell** setzen. Komponenten-Suffix wird aus `{name}_{suffix}` abgeleitet.

------------------------------------------------------------------------

# 8. Komponenten

## 8.1 Benennung

```
{params.name}_{component_suffix}
```

Beispiele: `BED_120_mattress`, `BED_120_post_xmin_ymin`, `BED_120_label`

Suffixe sind **generator-spezifisch**, müssen aber **stabil und dokumentiert** sein.

## 8.2 Rollen (`layoutlab_role`)

Jede Mesh-Komponente braucht eine Rolle — feingranular, generator-spezifisch:

```python
cb(..., role="bed_mattress", ...)
cb(..., role="bed_post", ...)
```

Export und KI nutzen Rollen zur Semantik. Liste in `{name}.md` pflegen.

## 8.3 Komponenten statt Monolith

Schlecht: ein riesiger Box für das ganze Bett.  
Gut: Pfosten, Rahmen, Matratze, Kopfteil — getrennt erzeugt, gemeinsame `object_id` via Engine.

------------------------------------------------------------------------

# 9. Fallbacks

Generatoren müssen **robust** sein:

| Eingabe | Verhalten |
|---|---|
| Bett sehr schmal | Mindestmaße clampen; ggf. weniger Kissen |
| Bett sehr breit | Zwei Kissen; ggf. dickere Schwellenwerte |
| Unbekannter `head_side` | Bekannter Default (`y_max`) |
| Fehlende Farbe | Default-RGBA |

**Keine Exception**, wenn das Problem durch Clamp/Defaults lösbar ist.

Konstanten für Schwellenwerte **oben im File benennen** (siehe `bed_basic.py`: `PILLOW_COUNT_WIDTH_THRESHOLD`).

------------------------------------------------------------------------

# 10. Fehlerbehandlung

| Fall | Vorgehen |
|---|---|
| Ungültige Parameter (negativ, NaN) | Clamps / Defaults |
| Geometrie unmöglich (Hochbett unter Mindesthöhe) | Mindesthöhe erzwingen **oder** klare `ValueError` mit Message |
| API-Fehler | Durchreichen — Engine/Command-Layer loggt Traceback |
| Teilweise fehlgeschlagene Komponente | Vermeiden — Generator soll atomar pro Aufruf konsistent sein |

Bei `ValueError`: kurze, actionable Message — sie erscheint in der Blender-Konsole unter `LayoutLab errors:`.

------------------------------------------------------------------------

# 11. Logging

Generatoren nutzen **kein** eigenes Logging-Framework.

- **Debug während Entwicklung:** temporäre `print()` — vor Commit entfernen
- **Ergebnis:** Return-Dict; Engine druckt es bei Quick Test / `run_generator` in die Konsole
- **Fehler:** Exceptions; Command-Layer fängt und protokolliert

Return-Dict sinnvoll füllen — hilft bei Diagnose:

```python
return {
    "created": name,
    "type": "bed_basic",
    "size": [length, width],
    "pillow_count": pillow_count,
}
```

------------------------------------------------------------------------

# 12. Namenskonventionen

| Was | Konvention | Beispiel |
|---|---|---|
| Generator-Datei | `snake_case.py` | `bed_basic.py` |
| `GENERATOR_NAME` | = Dateiname ohne `.py` | `"bed_basic"` |
| Objekt-Präfix | `params.name`, sprechend | `"BED_120x200"` |
| Komponenten-Suffix | `snake_case`, stabil | `_mattress`, `_post_xmin_ymin` |
| Rollen | `{typ}_{teil}` | `bed_mattress`, `wardrobe_door` |
| Konstanten | `UPPER_SNAKE` | `MIN_BED_DIMENSION` |

------------------------------------------------------------------------

# 13. Beispiele

## 13.1 Minimaler Generator

Ein Würfel + Label — zum Testen der Infrastruktur.

```python
GENERATOR_NAME = "demo_cube"
GENERATOR_CATEGORY = "Demo"
GENERATOR_DESCRIPTION = "Minimal example: one box and a label."
GENERATOR_VERSION = "0.1"
GENERATOR_ICON = "CUBE"

def generate(params, api):
    name = params.get("name", "DEMO_cube")
    x, y, z = params.get("location", [0, 0, 0])
    size = float(params.get("size", 1))
    collection = params.get("collection", "layout_tests")

    api["create_box"](
        f"{name}_box",
        [x, y, z],
        [size, size, size],
        [0.7, 0.7, 0.7, 1],
        collection,
        "demo_box",
        None,
    )
    api["create_label"](
        f"{name}_label",
        [x + size / 2, y + size / 2, z + size + 0.2],
        name,
        collection,
    )
    return {"created": name, "type": "demo_cube", "size": size}
```

------------------------------------------------------------------------

## 13.2 Einfaches Möbel — Hocker (`stool_basic`)

Regelbasiert, wenige Komponenten, keine Magic Numbers in der Logik.

```python
GENERATOR_NAME = "stool_basic"
GENERATOR_CATEGORY = "Seating"
GENERATOR_DESCRIPTION = "Simple stool: seat and four legs."
GENERATOR_VERSION = "0.1"
GENERATOR_ICON = "MESH_CYLINDER"

SEAT_HEIGHT_DEFAULT = 4.5
LEG_SIZE_DEFAULT = 0.4
MIN_SEAT_SIZE = 2.0

def generate(params, api):
    name = params.get("name", "STOOL_basic")
    x, y, z = params.get("location", [0, 0, 0])
    seat_w = max(params.get("width", 3), MIN_SEAT_SIZE)
    seat_d = max(params.get("depth", 3), MIN_SEAT_SIZE)
    seat_h = params.get("seat_height", SEAT_HEIGHT_DEFAULT)
    leg = min(params.get("leg_size", LEG_SIZE_DEFAULT), seat_w * 0.2)
    collection = params.get("collection", "layout_tests")
    wood = params.get("color", [0.6, 0.45, 0.3, 1])

    cb = api["create_box"]
    cb(f"{name}_seat", [x, y, z + seat_h], [seat_w, seat_d, 0.35], wood, collection, "stool_seat", None)

    for sx, sy, tag in [(0, 0, "leg_xmin_ymin"), (seat_w - leg, 0, "leg_xmax_ymin"),
                        (0, seat_d - leg, "leg_xmin_ymax"), (seat_w - leg, seat_d - leg, "leg_xmax_ymax")]:
        cb(f"{name}_{tag}", [x + sx, y + sy, z], [leg, leg, seat_h], wood, collection, "stool_leg", None)

    return {"created": name, "type": "stool_basic", "seat_size": [seat_w, seat_d]}
```

------------------------------------------------------------------------

## 13.3 Parametrisches Bett — Muster `bed_basic`

**Vollständige Implementierung:** `layoutlab/generators/bed_basic.py`  
**Parameter-Referenz:** [bed_basic.md](../layoutlab/generators/bed_basic.md)

Kernprinzipien (Auszug):

```python
# Schwellenwerte benennen — nicht inline
MIN_BED_DIMENSION = 3
PILLOW_COUNT_WIDTH_THRESHOLD = 13

def generate(params, api):
    name = params.get("name", "BED_basic")
    length = max(params.get("length", 20), MIN_BED_DIMENSION)
    width = max(params.get("width", 12), MIN_BED_DIMENSION)
    # … Pfosten, Rahmen, Matratze getrennt — Regeln pro Komponente …
    pillow_count = 2 if width >= PILLOW_COUNT_WIDTH_THRESHOLD else 1
    return {"created": name, "type": "bed_basic", "size": [length, width]}
```

Nach Erstellung: `regenerate` mit neuen Params möglich (gleiche `object_id`).

------------------------------------------------------------------------

## 13.4 Hochbett (`loft_bed_basic`) — Entwurf

Illustration für höhere Komplexität: Schlafen oben, Platz darunter, Leiter, Geländer.

```python
GENERATOR_NAME = "loft_bed_basic"
GENERATOR_CATEGORY = "Beds"
GENERATOR_DESCRIPTION = "Loft bed with elevated mattress, ladder, and guard rail."
GENERATOR_VERSION = "0.1"
GENERATOR_ICON = "BED"

MIN_CLEAR_HEIGHT = 8.0   # Mindesthöhe unter dem Bett (≈ 80 cm)
DEFAULT_DECK_HEIGHT = 14.0

def generate(params, api):
    name = params.get("name", "LOFT_BED")
    x, y, z = params.get("location", [0, 0, 0])
    length = max(params.get("length", 20), 3)
    width = max(params.get("width", 12), 3)
    deck_z = max(params.get("deck_height", DEFAULT_DECK_HEIGHT), MIN_CLEAR_HEIGHT + 2)
    collection = params.get("collection", "layout_tests")
    cb = api["create_box"]

    post = 0.5
    # Vier Pfosten bis deck_z + Matratze
    for sx, sy, tag in [(0, 0, "post_xmin_ymin"), (length - post, 0, "post_xmax_ymin"),
                        (0, width - post, "post_xmin_ymax"), (length - post, width - post, "post_xmax_ymax")]:
        cb(f"{name}_{tag}", [x + sx, y + sy, z], [post, post, deck_z + 2], [0.7, 0.5, 0.35, 1],
           collection, "bed_post", None)

    # Matratze auf Höhe deck_z
    cb(f"{name}_mattress", [x + 0.3, y + 0.3, z + deck_z], [length - 0.6, width - 0.6, 2],
       [0.86, 0.86, 0.82, 0.65], collection, "bed_mattress", None)

    # Leiter an y_min Seite
    ladder_x = x + length - post - 1.2
    for i in range(int(deck_z)):
        cb(f"{name}_ladder_rung_{i + 1}", [ladder_x, y, z + i * 1.2], [1.0, 0.15, 0.12],
           [0.7, 0.5, 0.35, 1], collection, "bed_ladder", None)

    # Geländer an offener Längsseite
    cb(f"{name}_guard_rail", [x, y + width - 0.15, z + deck_z + 1.5], [length, 0.15, 1.2],
       [0.7, 0.5, 0.35, 1], collection, "bed_guard_rail", None)

    api["create_label"](f"{name}_label", [x + length / 2, y + width / 2, z + deck_z + 3], name, collection)

    clear_height = deck_z - z
    return {
        "created": name,
        "type": "loft_bed_basic",
        "size": [length, width],
        "clear_height_under": clear_height,
    }
```

Später: Clearance-Zonen für Einstieg und Spielhöhe (Phase E).

------------------------------------------------------------------------

# 14. Best Practices

| Praxis | Begründung |
|---|---|
| Keine Magic Numbers | Konstanten mit sprechenden Namen oben im File |
| Nur API, kein `bpy` | Testbarkeit, klare Grenze Engine/Generator |
| Komponentenbasiert | Regenerate, Export, spätere Constraints |
| Keine UI im Generator | Trennung Plugin / Generator |
| Keine Szenenanalyse | Generatoren bleiben rein parametrisch |
| Keine Generator-Abhängigkeiten | Engine orchestriert; ein Generator = ein Objekttyp |
| Return-Dict aussagekräftig | Debugging und KI-Feedback |
| `{name}.md` pflegen | Params, Rollen, JSON-Beispiele für ChatGPT/Cursor |
| Regeln statt Skalieren | DD-002 — Geometrie neu berechnen |
| Einheiten konsistent | Immer Blender-Units; Doku verlinken |

------------------------------------------------------------------------

# 15. Anti-Patterns

## 15.1 Blind skalieren

```python
# SCHLECHT
obj = cb(f"{name}_bed", loc, [10, 20, 5], ...)
obj.scale = (length / 10, width / 20, 1)  # verboten — auch via bpy
```

**Warum:** Pfosten, Kissen, Leiter skaliert mit — physikalisch falsch. Stattdessen Komponenten mit Regeln neu platzieren.

## 15.2 Monolith-Mesh

```python
# SCHLECHT — ein Block für alles
cb(f"{name}_furniture", [x, y, z], [length, width, height], ...)
```

**Warum:** Keine Semantik, kein gezieltes Regenerate einzelner Teile, Export nutzlos für KI.

## 15.3 Szenen-Zustand lesen

```python
# SCHLECHT
for obj in api["bpy"].data.objects:
    if "WALL" in obj.name:
        ...
```

**Warum:** Generator hängt von fremder Szene ab; nicht reproduzierbar aus JSON allein.

## 15.4 UI im Generator

```python
# SCHLECHT
class MY_PT_panel(api["bpy"].types.Panel):
    ...
```

**Warum:** UI gehört ins Addon-Plugin, nicht in Generatoren.

## 15.5 Andere Generatoren laden

```python
# SCHLECHT
exec(open("other_generator.py").read())
```

**Warum:** Keine Kopplung; gemeinsame Logik später als Komponenten-Bibliothek.

## 15.6 Undokumentierte Parameter

Parameter nur im Code, nicht in `{name}.md` — **Warum:** KI und Menschen können den Generator nicht korrekt per JSON aufrufen.

------------------------------------------------------------------------

# 16. Debugging und Testen

## 16.1 Entwicklungs-Workflow

1. **Neu:** Generator Browser → *New* → Text Block bearbeiten  
2. **Speichern:** *Save* → landet in `layoutlab_generators/`  
3. **Quick Test:** Browser → Generator wählen → Location/Length/Width → *Create Test Object*  
4. **JSON-Test:** Command-Block mit `run_generator` → *Apply Commands*  
5. **Regenerate-Test:** Szene exportieren → `regenerate` mit geändertem Param  
6. **Bundled:** Für Repo-Release nach `layoutlab/generators/` + `{name}.md` + README-Eintrag

Symlink-Install (Option C in README) beschleunigt Iteration.

## 16.2 Quick Test (Browser)

Quick Test lebt im **Generator Browser** (nicht im Sidebar-Panel). Ruft `execute_generator` auf — gleicher Pfad wie JSON.

Felder und Defaults sind **generator-spezifisch** — siehe Abschnitt unten und `layoutlab/plugin/quick_test.py`.

## 16.3 Konsole

*Window → Toggle System Console* — Ergebnisse und Tracebacks erscheinen dort.

## 16.4 Quick Test Profile

Der Generator Browser passt Felder und Defaults **pro Generator** an (`layoutlab/plugin/quick_test.py`):

| Generator | Felder | Default-Name |
|---|---|---|
| `bed_basic` | Length, Width | `TEST_BED` |
| `wardrobe_basic` | Width, Depth, Height | `TEST_WARDROBE` |
| andere | Length, Width | `TEST_<GENERATOR>` |

Beim Wechsel in der Generator-Liste werden Test-Defaults automatisch gesetzt.

Neuen Generator eintragen: Eintrag in `QUICK_TEST_PROFILES` in `quick_test.py`.

## 16.5 Diagnostics

*LayoutLab → Run Console Checks* — strukturierter Report (9 Checks), inkl. Metadaten und `regenerate`.

## 16.6 Unit-Tests (ohne Blender)

Reine Logik (Metadata-Parsing, Param-Merge) in `tests/` — siehe `test_layoutlab_util.py`.  
Generator-Geometrie: manuell in Blender + Diagnostics.

## 16.7 Checkliste vor Merge

- [ ] Alle fünf Metadaten-Konstanten gesetzt
- [ ] Jede Komponente hat `layoutlab_role`
- [ ] Namen folgen `{name}_{suffix}`
- [ ] `{name}.md` mit Params, Rollen, JSON-Beispielen
- [ ] Eintrag in `layoutlab/generators/README.md`
- [ ] Quick Test + mindestens ein JSON-Command getestet
- [ ] Documentation Update Checklist ([00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md))

------------------------------------------------------------------------

# 17. Dokumentationspflicht (dieses Dokument)

Dieses Dokument ist die **Referenz für Generator-Entwicklung**.

Es muss aktualisiert werden, wenn sich ändert:

| Änderung | Auch prüfen |
|---|---|
| Neue/geänderte `api`-Funktion | [generator_api.md](generator_api.md) |
| Neue Pflicht-Metadaten / Struktur | [LayoutLab_Generator_Specification.md](../LayoutLab_Generator_Specification.md) |
| Best Practices / Anti-Patterns | Dieses Dokument |
| Beispiel-Patterns (neuer Canonical) | Dieses Dokument + ggf. neuer bundled Generator |
| Parameter-Konventionen global | [units_and_coordinates.md](units_and_coordinates.md) |

Eintrag in [documentation_map.md](documentation_map.md) — Zeile **how_to_write_generators.md**.

------------------------------------------------------------------------

# 18. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-10 | Initial developer guide |
