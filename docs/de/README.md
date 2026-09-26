# Autodarts für Home Assistant

[← Projektseite](../../README.md) · [English documentation](../README.md)

**Dein Autodarts-Board live in Home Assistant: lokal, in Echtzeit und bereit für Automationen.**

<img src="../images/de/card-visit.webp" alt="Die Autodarts-Karte: drei Darts landen, ihre Felder blinken auf der Scheibe und die Aufnahme zählt mit" width="720">

## Das kann die Integration

- **Lokal und in Echtzeit.**
  - Direkte Verbindung zum Autodarts Board Manager in deinem Netzwerk.
  - Darts erscheinen in Sekundenbruchteilen.
  - Kein Cloud-Konto und keine Client-ID nötig.
- **Findet dein Board automatisch.**
  - Board Manager 2 meldet sich selbst im Netzwerk; Home Assistant bietet das Board mit einem Klick an.
  - Alternativ suchst du nach deinen Boards oder gibst die Adresse ein.
- **Beide Board-Manager-Generationen.** Unterstützt den klassischen Board Manager 1 und den Headless Board Manager 2. Nach einem Update stellt sich die Integration selbst um.
- **Sechs Dashboard-Karten**, die automatisch geladen werden:
  - Live-Dartscheibe mit blinkenden Treffern und Dart-Positionen;
  - Trainingskarte mit Trefferbild und Aufnahmeverlauf;
  - Board-Status mit Erkennung, Verbindungen und Kameras;
  - Anzeigetafel für ein Tablet oder einen Fernseher am Board, lesbar vom Abwurf aus, mit einem Caller, der das Spiel auf Wunsch ansagt;
  - Spielerkarte mit Profilen, direkten Vergleichen und letzten Matches;
  - Doppelkarte mit der Quote jedes Doubles auf der Scheibe;
  - dazu ein automatisches Dashboard, das alles pro Board mit einem Klick anordnet.
- **Trainingsanalyse:**
  - Trainingssessions, die mit dem ersten Dart oder bewusst beginnen, nach einer Pause enden und die letzten 20 Sessions behalten;
  - 3-Dart-Average, Aufnahmen, höchste Aufnahme, 100+/140+/180, Triple-Quote;
  - Treffer pro Feld, lokal gespeichert und über Neustarts hinweg erhalten.
  - Bestleistungen mit einem Ereignis, sobald du eine übertriffst, eine Trainingsserie in Tagen und ein Tagesziel in Darts;
  - Spielerprofile mit Statistik und Bestleistungen pro Name, Match-Verlauf und direkten Vergleichen;
  - Doppelanalyse mit der Quote jedes Doubles und Checkout-Wegen über deine stärksten Doubles.
- **Übungsspiele und Matches.** Spiele X01 (101 bis 1001, auf Wunsch mit Double-In und Ausbullen), Cricket oder die Partyspiele Shanghai, Halve-It und Killer am lokalen Board, allein oder als Match mit bis zu vier Spielern, Legs und Sätzen. Die Restpunkte zählen herunter, Überwerfen wird erkannt, und die Live-Karte zeigt Checkout-Weg, nächstes Zielfeld und eine Anzeigetafel, bei Cricket eine Kreidetafel mit Treffern, Punkten und Treffern pro Runde. Vier Trainingsspiele üben die Grundlagen: Around the Clock, Doppeltraining, Checkout-Training und Bob's 27. First-9-Average, Checkout-Quote, Doppelquote und Legs pro Tag zeigen deine Entwicklung.
- **Automationen mit Bühnenatmosphäre.**
  - Board-Ereignisse für jeden Dart, jede Korrektur, jede Entnahme, jede geworfene und abgeschlossene Aufnahme und jede Trainingssession.
  - Zehn fertige Blueprints: 180-Feier, Dart-Caller, Licht bei der Entnahme, automatische Erkennung, Warnungen, tägliche Berichte, eine Routine für Trainingssessions, ein Übungs-Caller, ein Highlight-Foto und eine Lichtshow.
- **Volle Kontrolle.**
  - Erkennung starten, stoppen und zurücksetzen.
  - Kalibrierung für das Board oder einzelne Kameras; Board Manager neu starten.
  - Board-Einstellungen, Kamera-Standby und Updates.
  - Zustandssensoren für jede Kamera.
- **Robust.**
  - Erfüllt alle Regeln der [Qualitätsskala für Home-Assistant-Integrationen](https://developers.home-assistant.io/docs/core/integration-quality-scale/) bis Platin ([Selbsteinschätzung](../../custom_components/autodarts/quality_scale.yaml)), einschließlich strikter Typisierung.
  - Stellt Verbindungen selbst wieder her und meldet eine falsche Board-Adresse unter Reparaturen.
  - Diagnosedaten ohne Geheimnisse.
  - Auf Deutsch und Englisch.
  - Mehr als 350 automatische Tests, darunter ein Docker-End-to-End-Test mit beiden Board-Manager-Generationen und ein Browsertest jeder Karte.

## Schnellstart

1. **Mit HACS installieren.**

   [![Home Assistant öffnen und dieses Repository in HACS anzeigen.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dennis-Otto&repository=ha-autodarts&category=integration)

   Alternativ fügst du `https://github.com/Dennis-Otto/ha-autodarts` in HACS als benutzerdefiniertes Repository vom Typ **Integration** hinzu. Dann installierst du **Autodarts** und startest Home Assistant neu.

2. **Board hinzufügen.** Mit Board Manager 2 erscheint dein Board meist schon unter **Einstellungen → Geräte & Dienste → Entdeckt**. Sonst:

   [![Home Assistant öffnen und Autodarts einrichten.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=autodarts)

   Wähle **Boards im Netzwerk suchen** oder **Board-Adresse eingeben** und bestätige. Konto, Passwort oder Client-ID brauchst du nicht.

3. **Karten hinzufügen.** Bearbeite ein Dashboard, wähle **Karte hinzufügen** und suche nach *Autodarts*. Oder erzeuge in einem Schritt ein komplettes Dashboard: **Einstellungen → Dashboards → Dashboard hinzufügen → Autodarts**.

## Bilder

<table>
  <tr>
    <td width="50%"><img src="../images/de/training-card.png" alt="Trainingskarte mit 3-Dart-Average, Trefferbild, Statistik und letzten Aufnahmen"><p align="center"><b>Trainingskarte</b></p></td>
    <td width="50%"><img src="../images/de/status-card.png" alt="Board-Status-Karte mit Erkennung, Version, Verbindungen, Board-PC und Kameras"><p align="center"><b>Board-Status</b></p></td>
  </tr>
  <tr>
    <td width="50%"><img src="../images/de/card.png" alt="Live-Karte mit der aktuellen Aufnahme auf der Dartscheibe"><p align="center"><b>Live-Karte</b></p></td>
    <td width="50%"><img src="../images/de/device.png" alt="Geräteseite des Autodarts-Boards in Home Assistant"><p align="center"><b>Geräteseite</b></p></td>
  </tr>
  <tr>
    <td width="50%"><img src="../images/de/scoreboard.webp" alt="Animation: die Anzeigetafel in einem 501-Match; nach jeder Aufnahme wechselt der Wurf, und Alex checkt 141 zum Sieg"><p align="center"><b>Anzeigetafel</b>: ein 501-Match am Bildschirm neben dem Board</p></td>
    <td width="50%"><img src="../images/de/cricket.webp" alt="Animation: Cricket zwischen Alex und Sam auf der Kreidetafel der Live-Karte"><p align="center"><b>Cricket</b>: Treffer, Punkte und die nächste Zahl</p></td>
  </tr>
  <tr>
    <td width="50%"><img src="../images/de/practice-checkout.webp" alt="Animation: ein 141er-Checkout mit Weg und umrandetem Feld nach jedem Dart"><p align="center"><b>Übungsspiel</b>: der Checkout-Weg folgt jedem Dart</p></td>
    <td width="50%"><img src="../images/de/training-game.webp" alt="Animation: Around the Clock, jeder Treffer bringt das Ziel und seine umrandeten Felder weiter"><p align="center"><b>Trainingsspiel</b>: Around the Clock</p></td>
  </tr>
</table>

## Anleitungen

| Anleitung | Inhalt |
| --- | --- |
| [Installation und Einrichtung](installation.md) | Voraussetzungen, HACS, manuelle Installation, Einrichtung, Cloud-Verknüpfung, Updates, Entfernen |
| [Entitäten und Ereignisse](entitaeten.md) | Alle Entitäten, Board-Ereignisse, Zustände und Attribute |
| [Dashboard-Karten](karten.md) | Live-Karte, Trainingskarte, Board-Status, Anzeigetafel, Spieler- und Doppelkarte mit allen Optionen |
| [Automationen](automationen.md) | Blueprints, Board-Ereignisse und fertige Beispiele |
| [Funktionsweise](funktionsweise.md) | Architektur, Aktualisierung, Trainingsregeln, Datenschutz |
| [Fehlerbehebung](fehlerbehebung.md) | Meldungen, Reparaturen, Diagnose und Logs |
| [Sicherheit](sicherheit.md) | Schutzgüter, Vertrauensgrenzen, Bedrohungen und Gegenmaßnahmen |
| [Roadmap](roadmap.md) | Erschienene Versionen und was als Nächstes kommt |

Die Entwickler-Dokumentation gibt es auf Englisch: [Development](../development.md), [Releases](../releases.md).

## Unterstützte Geräte

| | Unterstützt | Getestet mit |
| --- | --- | --- |
| Board Manager 2 (Headless) | 2.x | 2.0.0 |
| Board Manager 1 (klassische App) | 1.x | 1.0.7 |
| Kameras | Jede Anzahl, die der Board Manager unterstützt | 3 |
| Home Assistant | ab 2026.8 | 2026.9.3 |

## Bekannte Einschränkungen

- **Cloud-Spieldaten sind noch nicht verfügbar.** Sie brauchen eine OAuth-Client-ID, die Autodarts für diese Integration vergibt; sie ist beantragt, aber noch nicht enthalten. Alles Lokale funktioniert ohne sie.
- **Keine Spiellogik im Training.** Das Training zählt die Darts, die das Board erkennt. Spieler, Legs, Überwerfen oder Checkouts kennt es nicht.
- **Board-Manager-Updates installierst du auf dem Board-PC.** Die Update-Entität zeigt neue Versionen von Board Manager 2 nur an.
- **Liveansicht der Kameras nur mit Board Manager 2.** Mit Board Manager 1 zeigen die Kamera-Entitäten Standbilder.
