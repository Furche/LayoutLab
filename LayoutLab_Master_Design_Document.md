# LayoutLab -- Master Design Document

Version: 0.9 (Living Document)

> Dieses Dokument beschreibt die Vision, Architektur und
> Entwicklungsregeln von LayoutLab. Es ist wichtiger als der aktuelle
> Code. Wenn Code und Dokumentation widersprechen, soll die Architektur
> zuerst diskutiert und erst danach der Code angepasst werden.

------------------------------------------------------------------------

# 1. Mission

LayoutLab ist **kein Blender-Addon zum Platzieren von Möbeln**.

LayoutLab ist eine **parametrische Raumplanungsplattform**, die langfristig
**menschliche Anforderungen an einen Raum in räumliche Lösungen übersetzt** —
und als eigenständige, KI-begleitete Anwendung erlebbar werden kann.

Objekte besitzen eigene Logik; eine KI kann auf semantischer Ebene planen;
das Plugin führt deterministisch aus (DD-009 Accepted).

**Heute:** Execution Layer (Generatoren, JSON, Clearances, Analyse) plus Planning-Grundlage
(Recipes, Candidates, Shortlist, optional AI-Ästhetik) — geordnete Übersicht in Roadmap §17.
**Blender** bleibt die Referenz-Runtime; Standalone Core HTTP + Viewer sind bereits da.

**Langfristig (Problem-first):** Nutzer beschreibt Ziele, nicht zwingend Möbeltypen.

Nicht: > „Skaliere diesen Würfel.“

Auch nicht (nur langfristig als Endziel): > „Erzeuge ein Hochbett.“

Sondern als Richtung:

> „Schaffe Schlafplätze, halte Spielfläche frei, blockiere Fenster und Heizung nicht.“

Ein Hochbett ist dann nur eine mögliche Lösung.

Visionsdetails: [docs/Future_Ideas.md](docs/Future_Ideas.md) — **keine Kursänderung** der aktuellen Roadmap.

------------------------------------------------------------------------

# 2. Langfristige Vision

Das System soll irgendwann in der Lage sein,

-   Nutzeranforderungen in natürlicher Sprache zu verstehen (Problem-first)
-   Räume, Wohnungen oder Immobilien in LayoutLab zu erfassen oder rekonstruieren zu lassen
-   Projekte vom einzelnen Raum bis zum mehrgeschossigen Gebäude zu unterstützen
-   eine integrierte KI für Erfassung, Anforderungen, Varianten und Planung einzubetten
-   komplette Räume zu analysieren
-   Lösungsvarianten zu entwickeln und zu bewerten
-   Möblierung vorzuschlagen — oder vorhandene Möbel umzustellen
-   bei Bedarf individuelle oder integrierte Konstruktionen zu entwerfen
-   Barrierefreiheit und besondere Bedürfnisse zu berücksichtigen
-   Kollisionsfreiheit und Laufwege zu prüfen
-   Spielflächen, Stauraum, Licht zu bewerten
-   mehrere Varianten gegeneinander zu vergleichen und zu erklären

**Leitsatz:** LayoutLab optimiert räumliche Lösungen für menschliche Bedürfnisse —
nicht Möbel um ihrer selbst willen.

**Standalone (Future Vision):** LayoutLab soll langfristig als eigenständige Anwendung
nutzbar sein können — ohne Blender-Kenntnisse und ohne JSON-Copy-Paste. Blender bleibt
**aktuell** die erste, vollständig unterstützte Runtime.

Die aktuelle Entwicklung (Phase E: Clearances, Constraints, `analyze_layout` und
Execution-Layer-Arbeit) bleibt die richtige Basisebene — siehe §17 Roadmap (**unverändert**).

Ausführlich: [docs/Future_Ideas.md](docs/Future_Ideas.md) (§1, §11–§19). Keine Schemas und
keine Implementierung in diesem Dokument.

------------------------------------------------------------------------

# 3. Entwicklungsphilosophie

Grundsatz:

**Nicht Meshes manipulieren. Regeln modellieren.**

Ein Generator beschreibt Wissen.

Ein Mesh ist nur das Ergebnis.

------------------------------------------------------------------------

# 4. Systemarchitektur

LayoutLab besteht aus fünf Ebenen (heutige Blender-Runtime):

1.  Blender UI
2.  Hauptplugin
3.  Generator Engine
4.  Generatoren
5.  Szene

Langfristig (Future Vision, keine Implementierung): **LayoutLab Core** + **Runtime-Adapter**
(Blender; später optional Standalone-Editor, Capture-Client, Viewer). Blender bleibt
**aktuell** erste Runtime. Siehe [docs/Future_Ideas.md](docs/Future_Ideas.md) §11–§13,
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §2.2.

Das Hauptplugin kennt keine Möbellogik.

Generatoren kennen keine UI.

Die Kommunikation erfolgt ausschließlich über definierte APIs.

------------------------------------------------------------------------

# 5. Objektmodell

Room └── Layout ├── Furniture Object │ └── Generator │ └── Components
├── Door ├── Window ├── Heater └── Clearance Areas

Ein Objekt ist niemals nur ein Mesh.

Es besitzt:

-   Parameter
-   Regeln
-   Beziehungen
-   Metadaten

------------------------------------------------------------------------

# 6. Generatorprinzip

Ein Generator erzeugt ein Objekt aus Parametern.

Er darf niemals davon ausgehen, dass feste Größen existieren.

Generatoren müssen möglichst robust auf ungewöhnliche Werte reagieren.

Beispiele:

50 × 200 Bett

→ kleinere Kissen erzeugen

300 × 200 Bett

→ zusätzliche Kissen

Kinderbett

→ niedrigere Beine

Hochbett

→ Leiter, Geländer, Freiraum

------------------------------------------------------------------------

# 7. Komponenten

Generatoren bauen aus Komponenten.

Beispiel Bett

-   Beine
-   Rahmen
-   Lattenrost
-   Matratze
-   Kopfteil
-   Fußteil
-   Kissen
-   Geländer
-   Leiter

Komponenten besitzen eigene Regeln.

------------------------------------------------------------------------

# 8. Generator API

Jeder Generator besitzt Metadaten.

-   Name
-   Version
-   Kategorie
-   Beschreibung
-   Icon

und implementiert

generate(params, api)

Generatoren dürfen ausschließlich die API verwenden.

Keine Blender-spezifischen Hacks.

------------------------------------------------------------------------

# 9. Hauptplugin

Verantwortlich für:

-   Browser
-   JSON
-   Clipboard
-   Textblöcke
-   Generatorverwaltung
-   Import
-   Export
-   Ausführung
-   Logging

Nicht verantwortlich für Möbellogik.

------------------------------------------------------------------------

# 10. Generator Browser

Soll sich wie der Blender Asset Browser anfühlen.

Später geplant:

-   Vorschaubilder
-   Kategorien
-   Suche
-   Favoriten
-   Tags
-   Zuletzt verwendet
-   Parametervorlagen
-   Live-Vorschau

------------------------------------------------------------------------

# 11. JSON-Protokoll

ChatGPT kommuniziert ausschließlich über JSON.

Keine Python-Snippets.

Keine Blender-Operatoren.

Dadurch bleiben Plugin und KI entkoppelt.

Details: DD-003. Strategische Begründung (warum Plugin trotz direkter KI-Möglichkeit):
DD-009 — KI plant, LayoutLab führt deterministisch aus.

## 11.1 KI vs. Plugin (DD-009)

| Ebene | Aufgabe |
|---|---|
| KI | Nutzerwunsch, Varianten, Auswahl der Operationen |
| LayoutLab | Stabile Ausführung: Generatoren, Parts, Metadaten, Regeneration, Clearances, Analyse |
| Blender | Editor-Host (aktuell) |

Heute: Core-Agent/Chat und Viewer-Apply-Gate existieren bereits (DD-009 + DD-014).
Langfristig: lokale **Bridge** (kein Clipboard) und **Expertenmodus** (direktes bpy) —
nur definierte LayoutLab-Operationen, kein beliebiges Remote-Python. Bridge/Expert Mode
bleiben zurückgestellt — siehe `docs/Future_Ideas.md`.

------------------------------------------------------------------------

# 12. Design Decisions (DD)

Jede größere Entscheidung erhält eine fortlaufende Nummer.

Beispiele

DD-001 Generatoren sind parametrische Assets.

DD-002 Generatoren erzeugen Meshes neu.

DD-003 Kommunikation ausschließlich über JSON.

DD-004 UI orientiert sich am Asset Browser.

DD-005 Generatoren besitzen Metadaten.

**Accepted (Auswahl):** DD-009 (AI-Ausführungsgrenze) · DD-010 (Room Model) · DD-011 (ephemere
Candidates) · DD-014 (Standalone Core + Viewer) · DD-015 / DD-016 / DD-017 (Soft Metrics,
Recipes, collaborative Evaluation). Index: `docs/design_decisions/README.md`.

**Noch nicht angelegt (Reserve):** DD-012 Integrated AI Product Experience · DD-013 Capture —
siehe `docs/Future_Ideas.md` §19. Spatial Project / Multi-Room: aus [FC-001](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) ableiten (WP-01), nicht stillschweigend.

------------------------------------------------------------------------

# 13. Dokumentation

docs/

vision.md

architecture.md

generator_spec.md

json_protocol.md

roadmap.md

devlog.md

CHANGELOG.md

design_decisions/

------------------------------------------------------------------------

# 14. Rollen

Alexander

-   Product Owner
-   Priorisierung
-   Tests
-   Vision

ChatGPT

-   Systemarchitektur
-   Produktdesign
-   APIs
-   Generatorregeln
-   Reviews
-   Konzepte
-   Roadmap

Cursor

-   Implementierung
-   Refactoring
-   Blender API
-   Unit Tests
-   Dateistruktur

Cursor soll Architekturänderungen nicht eigenständig vornehmen.

------------------------------------------------------------------------

# 15. Entwicklungsregeln für Cursor

Vor größeren Änderungen:

1.  bestehende Architektur verstehen
2.  Dokumentation prüfen
3.  minimal-invasive Lösung bevorzugen
4.  keine stillen Architekturänderungen

Bei Unsicherheit:

Architekturfrage offen lassen statt Annahmen treffen.

------------------------------------------------------------------------

# 16. Codequalität

Bevorzugt werden:

-   kleine Funktionen
-   sprechende Namen
-   Wiederverwendung
-   lose Kopplung
-   klare APIs

Vermeiden:

-   Copy & Paste
-   Magic Numbers
-   Spezialfälle ohne Dokumentation

------------------------------------------------------------------------

# 17. Roadmap

> Verbindliche Produktübersicht. Aktueller Arbeitsfokus und Session-Details:
> [`docs/HANDOFF.md`](docs/HANDOFF.md). Vollständiges FC-001-Verhalten:
> [`docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md`](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md)
> — hier nur stabile WP-IDs, kein Verhaltens-Copy.
>
> Historische Modulphasen A–E (Docs → Generatoren → Split → Object Model → Clearances):
> abgeschlossen; siehe `docs/ARCHITECTURE.md` §9 und `README.md`.

### Implemented Foundations

| Foundation | Notes |
|---|---|
| JSON commands + scene export | DD-003 · `json_protocol.md` |
| Parametric generators + regeneration | DD-001 / DD-002 · Browser DD-004 (Basis) · Metadata DD-005 (Basis) |
| Clearances + layout analysis | DD-007 / DD-008 · soft metrics DD-015 |
| Room Model (single space, rectangle MVP) | DD-010 · `room_model.md` |
| Standalone Core HTTP + read-only Viewer | DD-014 Phase A/B/B2 |
| AI chat / agent path (Core tools, Apply-Gate) | DD-009 · `agent_tool_contract.md` |
| Deterministic layout recipes | DD-016 · e.g. `bedroom_basic` |
| Candidate expansion + soft ranking | DD-011 · `plan_layout` `mode=candidates` (`0.10.24`) |
| Evaluation schema, signed scores, veto, shortlist, revision | DD-017 · `0.10.25` / `0.10.26` |
| Shortlist selection + blueprint cards | `0.10.29`–`0.10.33` |
| Experimental AI aesthetics + visual evidence | `0.10.34` / `0.10.35` (opt-in flag) |
| Feature Concept FC-001 (behaviour captured) | `docs/concepts/` — not yet implemented |

**Begriffsklärung (bereits vs. später):**

| Term | Heute | Später |
|---|---|---|
| **Varianten** | Ephemere Planning-Candidates + Shortlist (DD-011/017) | Persistente, benannte Projekt-/Raumvarianten |
| **Automatische Raumplanung** | Recipe-driven Candidates + Force-Path | Vollständiger Problem-first-Planner / „Optimierer“ |
| **KI bewertet Layouts** | Deterministische Scores + optionale AI-Ästhetik auf Shortlist | Breitere Produkt-UX, kalibrierte Rubriken |
| **Möbelbibliothek** | Bundled generators + Browser-Liste | Katalog / Import / Asset-Polish |
| **Komplette Wohnungsplanung** | Ein Raum (DD-010) | Multi-Room (FC-001/WP-06+) → später verbundene Topologie |
| **Laufwege** | — | Navigations-/Erreichbarkeitsanalyse (nur Future Idea) |
| **Undo** | Blender-/Session-Undo ad hoc | Semantische Transaktionen (FC-001/WP-02) |

### Active

| ID | Scope | Status |
|---|---|---|
| [FC-001/WP-01](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Architecture package: Transactions/Authority, Semantic Direct Manipulation, Spatial Project — Schema-Ownership klären | **Current** |

Noch **keine** direkte Feature-Implementierung. Zuerst die notwendigen Architekturentscheidungen
ableiten und reviewen lassen.

### Queued

Reihenfolge beibehalten: WP-01 → WP-02 → WP-03 / WP-04 / WP-05 → WP-06.

| ID | Scope | Entry |
|---|---|---|
| [FC-001/WP-02](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Semantische Transaktionen, Revisionen, Preview/Commit, Undo/Redo, stale-proposal protection, gemeinsame Authority-Grenze | Nach akzeptierten DDs aus WP-01 |
| [FC-001/WP-03](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Direkte Möbelbearbeitung (Select, XY-Move, Z-Rotation, Floor-Support, duplicate/delete/hide/lock) | Nach WP-02 |
| [FC-001/WP-04](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Parametrische Möbel-Größenänderung (Generator-Parameter + Regeneration, kein Mesh-Scaling) | Nach WP-03 |
| [FC-001/WP-05](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Wand-/Ecken-Resize, Opening-Host-Verhalten, inactive openings, invalid furniture visualization | Nach WP-02 + Direct-Manipulation-DD |
| [FC-001/WP-06](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Unabhängiges Multi-Room Spatial Project, lokale Transforms, Whole-Room-Ops | Nach Spatial-Project-DD |

### Refinement / On demand

Nicht blockierend für **FC-001/WP-01**. Keine festen Sprint-Zusagen außer dem
Minimal-Hinweis für experimentelle AI-Ästhetik (Stufe 1 unten).

**Viewer Score- / Trade-off-Erklärung (Refinement)**

- **MVP heute ausreichend:** Soft-Warnungen, `selection_reason` / Auswahlbegründung,
  optionaler Ästhetik-Hinweis — kein Zahlen-Dashboard.
- **Zielbild (gestuft):** zuerst eine kurze, verständliche Zusammenfassung der wichtigsten
  Vorteile, Nachteile und Trade-offs; später optional aufklappbare Detailansicht mit
  funktionalen Scores, Penalties, Vetos und Ästhetikbewertung.
- Kein komplexes Metrics-Dashboard einplanen.

**Weitere Recipes (streng on-demand)**

- Kein zweites Recipe verbindlich einplanen.
- Erst wenn ein konkretes reales Planungsszenario das vorhandene Recipe nicht trägt,
  entscheiden wir das nächste Recipe.
- `kids_room` ist ein naheliegender Kandidat, **keine** feste Zusage.

**AI-Ästhetik: Privacy- / Provider-Transparenz (zweistufig)**

| Stufe | Wann | Inhalt |
|---|---|---|
| **1 — Minimum** | Sobald experimentelle AI-Ästhetik aktiviert ist und Bilder/Raumdaten an einen externen Provider gehen | Offenlegen: dass Daten/Bilder übertragen werden; Provider und Modell; mögliche API-Kosten; dass die Funktion experimentell und optional ist |
| **2 — Ausgearbeitet** | Bevor Default-on oder produktives Angebot | Einwilligungsdialoge, detaillierte Einstellungen, Default-on-Verhalten |

Stufe 1 ist eine bekannte Lücke zur aktuellen Opt-in-Flag-Nutzung und gehört zum
Ästhetik-Refinement — **nicht** zum FC-001-Track. Stufe 2 bleibt zurückgestellt.

**Weitere Refinements**

- DD-017-Rubriken und Gewichtungen an realen Räumen kalibrieren; Nutzerfeedback auswerten

### Later Feature Concepts

Brauchen vor Implementierung ein Feature Concept und/oder DD — **nicht** aktive Zusagen:

| Topic | Notes |
|---|---|
| [FC-001/WP-07](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Erweiterte Support Surfaces und Stapeln |
| Persistente Projektvarianten | Speichern, benennen, vergleichen, favorisieren — **nicht** dasselbe wie ephemere Candidates |
| Laufweg- / Navigationsanalyse | Experimental Idea in `Future_Ideas.md` §5 |
| Polygonale Räume | DD-010 Next (`footprint.kind = polygon`) — nach FC-001 WP-01…WP-05, nicht davor |

### Explicitly Deferred

Nicht jetzt bauen (Details: `docs/Future_Ideas.md` §18):

- Capture / LiDAR / Rekonstruktion / Floor-Plan-OCR
- Verbundene Räume, Shared-Wall-Topologie, Passagen
- Multi-Floor / Building Model
- IKEA- / Produktkatalog-Import
- Asset-Browser-Polish (Thumbnails, Favoriten, Drag-and-drop, Live Preview) — DD-004 `[PLANNED]`, zurückgestellt
- Cloud, Auth, Sync
- Custom Render Engine
- Vollständige Standalone-Authoring-App (Viewport-Schreiben jenseits Viewer + Chat-Grundlage)
- AI-Ästhetik Privacy **Stufe 2** (Einwilligung / Default-on) — erst vor produktivem Angebot

------------------------------------------------------------------------

# 18. Non Goals (vorerst)

Nicht Bestandteil von Version 1:

-   fotorealistische Möbel
-   Materialsystem
-   Rendering
-   Animation
-   Physiksimulation

Der Fokus liegt auf Raumplanung.

------------------------------------------------------------------------

# 19. Leitsatz

> LayoutLab erzeugt keine Meshes.
>
> LayoutLab beschreibt Objekte — und langfristig: räumliche Lösungen für menschliche Bedürfnisse.
>
> Meshes und Möbel sind Mittel, nicht das Ziel.

Dieses Prinzip soll zukünftige Entscheidungen leiten. Die technische Roadmap (§17) bleibt bestehen.
