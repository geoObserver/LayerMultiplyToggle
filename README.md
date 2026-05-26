# Layer Multiply Toggle

![QGIS](https://img.shields.io/badge/QGIS-3.x%20%7C%204.x-589632?logo=qgis&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-5%20%7C%206-41cd52?logo=qt&logoColor=white)
![Version](https://img.shields.io/badge/version-0.3-blue)
![License](https://img.shields.io/badge/license-GPL--2.0-brightgreen)

**DE** — Schaltet mit einem Klick einen Mischmodus (Multiplizieren, Negativ multiplizieren, Ineinanderkopieren, Abdunkeln, Aufhellen) für **alle** oder nur die **ausgewählten** Ebenen und Gruppen ein und wieder aus.

**EN** — Toggles a blend mode (Multiply, Screen, Overlay, Darken, Lighten) for **all** or only the **selected** layers and groups with a single click.

![Layer Multiply Toggle in Aktion / in action](./QGIS_Plugin_LayerMultiplyToggle_Animation_1.gif)

---

## Inhalt / Contents

- [Deutsch](#deutsch)
  - [Wozu dient das Plugin?](#wozu-dient-das-plugin)
  - [Funktionen](#funktionen)
  - [Installation](#installation)
  - [Verwendung](#verwendung)
  - [Die Mischmodi im Detail](#die-mischmodi-im-detail)
  - [Verhalten und Persistenz](#verhalten-und-persistenz)
  - [Kompatibilität](#kompatibilität)
- [English](#english)
  - [What is it for?](#what-is-it-for)
  - [Features](#features)
  - [Installation](#installation-1)
  - [Usage](#usage)
  - [Blend modes in detail](#blend-modes-in-detail)
  - [Behaviour and persistence](#behaviour-and-persistence)
  - [Compatibility](#compatibility)
- [Letzte Änderungen / Changelog](#letzte-änderungen--changelog)
- [Lizenz und Haftung / License and disclaimer](#lizenz-und-haftung--license-and-disclaimer)
- [Autor / Author](#autor--author)

---

# Deutsch

## Wozu dient das Plugin?

In der Kartografie sollen sich Ebenen oft gegenseitig durchscheinen lassen, statt sich zu verdecken: ein Schummerungs- oder Reliefraster über der Landnutzung, Schraffuren über einem Luftbild, ALKIS-Linien über einer Hintergrundkarte. Der dafür passende Mischmodus liegt in QGIS tief in den *Layereigenschaften → Symbolisierung → Layer-Rendering → Mischmodus* – und muss für jede Ebene einzeln gesetzt werden.

**Layer Multiply Toggle** macht daraus einen einzigen Klick in der Werkzeugleiste: Der gewählte Mischmodus wird auf einen Schlag für alle oder die ausgewählten Ebenen/Gruppen gesetzt und beim erneuten Klick wieder zurückgenommen – ohne die ursprünglichen Einstellungen zu verlieren.

## Funktionen

- Ein-Klick-Umschalter in der Werkzeugleiste `geoObserverTools` (geteilter Knopf mit Aufklapp-Menü).
- Wirkt auf **alle** Ebenen oder nur auf die im Layerbaum **ausgewählten** Ebenen und Gruppen (rekursiv inkl. Untergruppen).
- Auswählbarer Mischmodus: **Multiplizieren, Negativ multiplizieren, Ineinanderkopieren, Abdunkeln, Aufhellen**.
- **Ursprüngliche Mischmodi werden gesichert** und beim Ausschalten exakt wiederhergestellt – kein Überschreiben bewusst gesetzter Modi.
- **Projektbezogene Persistenz**: Der Ein/Aus-Zustand und der gewählte Modus überstehen Speichern, Schließen und erneutes Öffnen des Projekts.
- Rückmeldungen über die QGIS-Meldungsleiste, Protokollierung im QGIS-Logfenster (Reiter `LayerMultiplyToggle`).

## Installation

1. QGIS öffnen: *Erweiterungen → Erweiterungen verwalten und installieren*.
2. Nach „Layer Multiply Toggle" suchen und installieren.

Alternativ manuell: den Plugin-Ordner nach `…/QGIS3/profiles/default/python/plugins/LayerMultiplyToggle` kopieren und das Plugin in der Erweiterungsverwaltung aktivieren.

## Verwendung

1. Optional im Layerbaum die gewünschten Ebenen/Gruppen markieren. Ohne Auswahl wirkt das Plugin auf alle Ebenen.
2. In der Werkzeugleiste auf den **Layer-Multiply-Knopf** klicken: Der aktive Mischmodus wird gesetzt (Knopf „an").
3. Über den **Pfeil am Knopf** das Aufklapp-Menü öffnen, um den Mischmodus zu wählen. Bei aktivem Zustand wird der neue Modus sofort übernommen.
4. Mit *Auf aktuelle Auswahl anwenden* lässt sich die Wirkung bei eingeschaltetem Zustand auf weitere markierte Ebenen ausdehnen.
5. Erneuter Klick auf den Knopf stellt die ursprünglichen Mischmodi wieder her (Knopf „aus").

## Die Mischmodi im Detail

Mischmodi bestimmen, wie die Farben einer Ebene mit den darunterliegenden verrechnet werden.

| Modus | Wirkung | Typischer Einsatz |
|-------|---------|-------------------|
| **Multiplizieren** | Multipliziert die Farben; das Ergebnis ist stets **dunkler**. Weiß bleibt wirkungslos, Schwarz bleibt schwarz. | Der Klassiker: Schummerung/Relief über Landnutzung legen, Schraffuren oder ALKIS-Linien über ein Luftbild – der Untergrund bleibt sichtbar. |
| **Negativ multiplizieren** (Screen) | Gegenstück zu Multiplizieren; das Ergebnis ist stets **heller**. | Aufhellen dunkler Hintergründe, Licht-/Dunst-Effekte, Leuchten. |
| **Ineinanderkopieren** (Overlay) | Kombiniert Multiplizieren und Negativ multiplizieren: dunkelt Dunkles ab, hellt Helles auf – **mehr Kontrast** und Sättigung. | Textur und Relief betonen, ohne die Mitteltöne zu verlieren. |
| **Abdunkeln** (Darken) | Behält je Pixel den **dunkleren** der beiden Farbwerte. | Nur dunklere Strukturen (z. B. dunkle Linien) sollen durchscheinen. |
| **Aufhellen** (Lighten) | Behält je Pixel den **helleren** der beiden Farbwerte. | Nur hellere Strukturen sollen durchscheinen. |

## Verhalten und Persistenz

- Beim Einschalten merkt sich das Plugin pro Ebene den **vorherigen** Mischmodus (nur beim ersten Mal je Ebene). Beim Ausschalten wird genau dieser Zustand wiederhergestellt – unabhängig von der aktuellen Auswahl.
- Zustand (an/aus), gewählter Modus und die gesicherten Originalwerte werden **im QGIS-Projekt** gespeichert. Nach erneutem Öffnen spiegelt der Knopf den gespeicherten Zustand wider, ohne den Mischmodus erneut anzuwenden (die Ebenen tragen ihn bereits aus der Projektdatei).

## Kompatibilität

- QGIS 3.x (Qt5) und QGIS 4.x (Qt6).

---

# English

## What is it for?

In cartography, layers should often show through one another instead of hiding each other: a hillshade or relief raster over land use, hatching over an aerial image, cadastral lines over a basemap. The blend mode for this lives deep inside *Layer Properties → Symbology → Layer Rendering → Blending mode* in QGIS, and has to be set for each layer individually.

**Layer Multiply Toggle** turns this into a single toolbar click: the chosen blend mode is applied at once to all or the selected layers/groups, and removed again on the next click, without losing the original settings.

## Features

- One-click toggle in the `geoObserverTools` toolbar (split button with dropdown menu).
- Acts on **all** layers, or only the layers and groups **selected** in the layer tree (recursively, including subgroups).
- Selectable blend mode: **Multiply, Screen, Overlay, Darken, Lighten**.
- **Original blend modes are captured** and restored exactly when toggling off, so deliberately set modes are not overwritten.
- **Per-project persistence**: the on/off state and the chosen mode survive saving, closing and reopening the project.
- Feedback via the QGIS message bar, logging in the QGIS log panel (tab `LayerMultiplyToggle`).

## Installation

1. In QGIS: *Plugins → Manage and Install Plugins*.
2. Search for "Layer Multiply Toggle" and install it.

Or manually: copy the plugin folder into `…/QGIS3/profiles/default/python/plugins/LayerMultiplyToggle` and enable the plugin in the Plugin Manager.

## Usage

1. Optionally select the desired layers/groups in the layer tree. With no selection, the plugin acts on all layers.
2. Click the **Layer Multiply button** in the toolbar: the active blend mode is applied (button "on").
3. Use the **arrow next to the button** to open the dropdown and choose the blend mode. While active, the new mode is applied immediately.
4. *Apply to current selection* extends the effect to additional selected layers while the toggle is on.
5. Clicking the button again restores the original blend modes (button "off").

## Blend modes in detail

Blend modes determine how a layer's colours are combined with the layers beneath it.

| Mode | Effect | Typical use |
|------|--------|-------------|
| **Multiply** | Multiplies the colours; the result is always **darker**. White has no effect, black stays black. | The classic: place hillshade/relief over land use, hatching or cadastral lines over an aerial image while keeping the background visible. |
| **Screen** | The opposite of Multiply; the result is always **lighter**. | Lightening dark backgrounds, haze/glow effects. |
| **Overlay** | Combines Multiply and Screen: darkens darks, lightens lights — **more contrast** and saturation. | Emphasise texture and relief without losing the midtones. |
| **Darken** | Keeps the **darker** of the two colour values per pixel. | Let only darker features (e.g. dark linework) show through. |
| **Lighten** | Keeps the **lighter** of the two colour values per pixel. | Let only lighter features show through. |

## Behaviour and persistence

- On enable, the plugin remembers each layer's **previous** blend mode (only the first time per layer). On disable it restores exactly that state, regardless of the current selection.
- State (on/off), the chosen mode and the captured originals are stored **in the QGIS project**. After reopening, the button mirrors the stored state without re-applying the blend mode (the layers already carry it from the project file).

## Compatibility

- QGIS 3.x (Qt5) and QGIS 4.x (Qt6).

---

## Letzte Änderungen / Changelog

### v0.3 (26.05.2026)
- **DE:** Wählbare Mischmodi (Multiplizieren, Negativ multiplizieren, Ineinanderkopieren, Abdunkeln, Aufhellen) über ein Aufklapp-Menü. Ursprüngliche Mischmodi werden gesichert und wiederhergestellt. Zustand und Modus werden projektbezogen gespeichert. Werkzeugknopf als QAction-Splitbutton neu umgesetzt, Rückmeldung über die Meldungsleiste. Fehlerbehebungen (Werkzeugleisten-Leak beim Entladen, wirkungslose Gruppen-Eigenschaft entfernt).
- **EN:** Selectable blend modes (Multiply, Screen, Overlay, Darken, Lighten) via a dropdown. Original blend modes are preserved and restored. State and mode are persisted per project. Toolbar button reworked as a QAction split button, feedback via the message bar. Bug fixes (toolbar leak on unload, removed ineffective group property).

### v0.2 (24.02.2026)
- **DE:** Kleinere Korrekturen. — **EN:** Minor corrections.

### v0.1 (23.02.2026)
- **DE:** Erstveröffentlichung. — **EN:** Initial release.

---

## Lizenz und Haftung / License and disclaimer

**DE** — Lizenziert unter der [GNU General Public License v2](./LICENSE). Eine Haftung für die Richtigkeit aller Funktionen des Plugins kann trotz sorgfältiger Prüfung nicht übernommen werden. Das gilt auch für eventuelle Schäden oder Konsequenzen, die durch die direkte oder indirekte Nutzung der angebotenen Inhalte entstehen.

**EN** — Licensed under the [GNU General Public License v2](./LICENSE). Despite careful testing, no liability can be accepted for the accuracy of all functions of the plugin. This also applies to any damage or consequences resulting from the direct or indirect use of the content provided.

---

## Autor / Author

**Mike Elstermann** (#geoObserver)

- Beschreibung und FAQ / Description and FAQ: <https://geoobserver.de/qgis-plugin-layermultiplytoggle/>
- Repository: <https://github.com/geoObserver/LayerMultiplyToggle/>
- Issues: <https://github.com/geoObserver/LayerMultiplyToggle/issues/>
