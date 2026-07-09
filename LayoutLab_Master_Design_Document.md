# LayoutLab -- Master Design Document

Version: 0.9 (Living Document)

> Dieses Dokument beschreibt die Vision, Architektur und
> Entwicklungsregeln von LayoutLab. Es ist wichtiger als der aktuelle
> Code. Wenn Code und Dokumentation widersprechen, soll die Architektur
> zuerst diskutiert und erst danach der Code angepasst werden.

------------------------------------------------------------------------

# 1. Mission

LayoutLab ist **kein Blender-Addon zum Platzieren von Möbeln**.

LayoutLab ist eine **parametrische Raumplanungsplattform**, bei der
Objekte ihre eigene Logik besitzen und von einer KI auf semantischer
Ebene erzeugt, verändert und bewertet werden können.

Nicht: \> "Skaliere diesen Würfel."

Sondern:

> "Erzeuge ein 120x200 Hochbett mit Leiter links."

------------------------------------------------------------------------

# 2. Langfristige Vision

Das System soll irgendwann in der Lage sein,

-   komplette Räume zu analysieren
-   Möblierung vorzuschlagen
-   Kollisionsfreiheit sicherzustellen
-   Laufwege zu prüfen
-   Spielflächen zu bewerten
-   Stauraum zu optimieren
-   Lichtverhältnisse zu berücksichtigen
-   mehrere Varianten gegeneinander zu vergleichen
-   KI-gestützte Empfehlungen zu erzeugen

Blender ist zunächst nur das Frontend.

------------------------------------------------------------------------

# 3. Entwicklungsphilosophie

Grundsatz:

**Nicht Meshes manipulieren. Regeln modellieren.**

Ein Generator beschreibt Wissen.

Ein Mesh ist nur das Ergebnis.

------------------------------------------------------------------------

# 4. Systemarchitektur

LayoutLab besteht aus fünf Ebenen:

1.  Blender UI
2.  Hauptplugin
3.  Generator Engine
4.  Generatoren
5.  Szene

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

------------------------------------------------------------------------

# 12. Design Decisions (DD)

Jede größere Entscheidung erhält eine fortlaufende Nummer.

Beispiele

DD-001 Generatoren sind parametrische Assets.

DD-002 Generatoren erzeugen Meshes neu.

DD-003 Kommunikation ausschließlich über JSON.

DD-004 UI orientiert sich am Asset Browser.

DD-005 Generatoren besitzen Metadaten.

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

Phase 1

✔ JSON

✔ Generatoren

✔ Browser

✔ Parametrische Möbel

Phase 2

□ Clearance

□ Kollisionsprüfung

□ Laufwege

□ Varianten

□ Undo für Generatoren

Phase 3

□ Constraints

□ Optimierer

□ automatische Raumplanung

□ Möbelbibliothek

□ IKEA-Import

□ Asset-Vorschaubilder

Phase 4

□ KI bewertet Layouts

□ automatische Vorschläge

□ komplette Wohnungsplanung

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
> LayoutLab beschreibt Objekte.
>
> Meshes sind lediglich deren aktuelle Darstellung.

Dieses Prinzip soll zukünftige Entscheidungen leiten.
