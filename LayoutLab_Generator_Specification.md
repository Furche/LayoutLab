# LayoutLab Generator Specification

Version: 1.0 (Draft)

> Dieses Dokument definiert den Standard für alle LayoutLab-Generatoren.
> Jeder Generator im Projekt soll diesen Regeln folgen.

Related: `docs/generator_api.md` (API signatures) · `docs/documentation_map.md` (when to update) · `layoutlab/generators/bed_basic.md` (reference instance)

------------------------------------------------------------------------

# 1. Ziel

Ein Generator beschreibt **Wissen über einen Objekttyp**.

Er erzeugt daraus eine konkrete Geometrie.

Er ist **kein Mesh**.

Er ist **kein Asset**.

Er ist die Beschreibung, wie ein Asset entsteht.

------------------------------------------------------------------------

# 2. Verantwortlichkeiten

Ein Generator darf:

-   Geometrie erzeugen
-   Komponenten positionieren
-   Parameter interpretieren
-   sinnvolle Defaults setzen
-   Fallbacks anwenden
-   Labels erzeugen
-   Metadaten bereitstellen

Ein Generator darf NICHT:

-   UI erzeugen
-   andere Generatoren verändern
-   Szenen analysieren
-   globale Entscheidungen treffen
-   Blender-Panels manipulieren

------------------------------------------------------------------------

# 3. Standardstruktur

Jeder Generator besitzt mindestens:

``` python
GENERATOR_NAME
GENERATOR_CATEGORY
GENERATOR_DESCRIPTION
GENERATOR_VERSION
GENERATOR_ICON

def generate(params, api):
    ...
```

Diese Metadaten werden im Generator Browser angezeigt.

------------------------------------------------------------------------

# 4. Parameter

Parameter sollen sprechend benannt sein.

Beispiele:

-   length
-   width
-   height
-   style
-   material
-   color
-   location
-   rotation
-   collection

Nicht:

-   a
-   size2
-   foo

------------------------------------------------------------------------

# 5. Komponenten

Generatoren bauen Objekte aus Komponenten.

Beispiel Bett:

-   legs
-   side rails
-   headboard
-   footboard
-   slats
-   mattress
-   pillows
-   ladder
-   guard rail

Komponenten sollen logisch getrennt erzeugt werden.

------------------------------------------------------------------------

# 6. Parametrik

Die Geometrie wird niemals einfach skaliert.

Stattdessen werden Regeln angewendet.

Beispiel:

120 cm Bett

→ zwei Pfosten bleiben gleich dick

→ Abstand wächst

→ Matratze wächst

→ Rahmen wächst

Nicht:

scale X = 1.5

------------------------------------------------------------------------

# 7. Fallbacks

Generatoren müssen mit ungewöhnlichen Eingaben umgehen.

Beispiele:

50 cm Bett

→ kleinere Kissen

400 cm Bett

→ zusätzliche Mittelstützen

Hochbett mit geringer Höhe

→ Warnung oder sinnvolle Mindesthöhe

Keine Exception, wenn sich das Problem sinnvoll lösen lässt.

------------------------------------------------------------------------

# 8. API-Regeln

Generatoren kommunizieren ausschließlich über die LayoutLab-API.

Beispiele:

create_box()

create_label()

ensure_material()

get_or_create_collection()

Später:

create_component()

create_profile()

create_mesh()

create_clearance()

Keine direkten bpy-Hacks, sofern die API eine passende Funktion bietet.

------------------------------------------------------------------------

# 9. Komponentenbibliothek (Ziel)

Langfristig sollen Generatoren auf wiederverwendbaren Bausteinen
aufbauen.

Beispiele:

SquareLeg

RoundLeg

Panel

Shelf

Drawer

Mattress

Door

Window

Ladder

GuardRail

So entstehen komplexe Möbel aus standardisierten Komponenten.

------------------------------------------------------------------------

# 10. Vererbung (Vision)

Später können Generatoren voneinander ableiten.

Furniture

└── Bed

    ├── Single Bed

    ├── Double Bed

    ├── Loft Bed

    └── Bunk Bed

Gemeinsame Logik wird nur einmal implementiert.

------------------------------------------------------------------------

# 11. Generator Browser

Jeder Generator sollte liefern:

-   Name
-   Kategorie
-   Beschreibung
-   Version
-   Icon

Später zusätzlich:

-   Thumbnail
-   Tags
-   Autor
-   Lizenz
-   Änderungsdatum
-   Beispiele

------------------------------------------------------------------------

# 12. Dokumentation

Jeder Generator sollte dokumentieren:

-   Zweck
-   Parameter
-   Beispiele
-   bekannte Einschränkungen

Damit kann sowohl Cursor als auch ChatGPT ihn korrekt verwenden.

------------------------------------------------------------------------

# 13. Qualitätsrichtlinien

Ein guter Generator ist:

-   robust
-   nachvollziehbar
-   modular
-   wiederverwendbar
-   parametrisierbar

Ein schlechter Generator:

-   enthält Magic Numbers
-   skaliert alles blind
-   mischt UI und Logik
-   ist voller Spezialfälle

------------------------------------------------------------------------

# 14. Zukunft

Generatoren sollen irgendwann nicht nur Geometrie erzeugen.

Sie sollen auch Wissen bereitstellen.

Zum Beispiel:

"Ein Erwachsener kann hier sitzen."

"Dieses Bett benötigt 70 cm Einstiegsfläche."

"Unter dem Hochbett entstehen 3,8 m² nutzbare Spielfläche."

Generatoren entwickeln sich damit von Geometrie-Erzeugern zu
Wissensmodulen.

------------------------------------------------------------------------

# Leitsatz

> Ein Generator beschreibt nicht, **wie ein Objekt aussieht**.

> Er beschreibt, **wie ein Objekt funktioniert**.
