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
(Recipes, Candidates, Shortlist, optional AI-Ästhetik) und Viewer-Manipulation auf Core —
verbindliche Arbeitsreihenfolge: [`docs/ROADMAP.md`](docs/ROADMAP.md).
**Blender** bleibt Runtime-Adapter; Standalone Core HTTP + Viewer sind die Produktfläche.

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
Execution-Layer-Arbeit) bleibt die richtige Basisebene — siehe [`docs/ROADMAP.md`](docs/ROADMAP.md).

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
siehe `docs/Future_Ideas.md` §19. Spatial Project / Multi-Room: [DD-020](docs/design_decisions/DD-020-spatial-project-independent-rooms.md) **Accepted** (independent rooms MVP).

------------------------------------------------------------------------

# 13. Dokumentation

docs/

ROADMAP.md          # verbindliche Produktprioritäten

HANDOFF.md          # Session-/Ist-Zustand

ARCHITECTURE.md

json_protocol.md

Future_Ideas.md

concepts/

design_decisions/

CHANGELOG.md · DEVLOG.md

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

# 17. Long-term product phases (summary)

> **Arbeitsreihenfolge und Prioritäten** gehören nicht mehr hierher.
> Verbindliche Quelle: [`docs/ROADMAP.md`](docs/ROADMAP.md).
> Session-/Ist-Zustand: [`docs/HANDOFF.md`](docs/HANDOFF.md).

Historische Modulphasen A–E (Docs → Generatoren → Split → Object Model → Clearances)
sind abgeschlossen — siehe `docs/ARCHITECTURE.md` §9.

**Langfristige Produktphasen (Orientierung, nicht Queue):**

| Phase | Meaning |
|---|---|
| Execution Layer | Generators, JSON, clearances, analysis — **shipped** |
| Planning foundation | Recipes, candidates, shortlist, optional AI aesthetics — **shipped** |
| Semantic editing / Spatial Project | FC-001 WP-01…WP-06 + Viewer direct manipulation — **shipped** (WP-07 later) |
| Problem-first planning | Intent → requirements → solutions — **vision**; see `docs/Future_Ideas.md` |
| Connected apartments / capture / cloud | **Deferred** — see ROADMAP §6 |

Do not expand this section into a second working roadmap. Update [`docs/ROADMAP.md`](docs/ROADMAP.md) instead.

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

Dieses Prinzip soll zukünftige Entscheidungen leiten. Die verbindliche Arbeits-Roadmap:
[`docs/ROADMAP.md`](docs/ROADMAP.md).
