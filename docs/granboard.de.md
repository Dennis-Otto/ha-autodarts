---
description: "Auf einem Granboard in Home Assistant spielen: Seine Darts kommen über Bluetooth, auch über ESPHome-Proxys, für jedes Spiel, das Training und die Statistiken."
---

# Granboard über Bluetooth

[← Dokumentation](README.de.md) · [English](granboard.md)

Ein Granboard ist eine Softdartscheibe mit Bluetooth. Home Assistant empfängt seine Darts über sein eigenes Bluetooth, über einen Adapter des Rechners von Home Assistant oder einen ESPHome-Bluetooth-Proxy irgendwo im Haus, und spielt damit jedes Spiel, das Training und die Statistiken wie auf einer [Dartscheibe ohne Autodarts](without-autodarts.de.md). Niemand muss einen Dart eingeben, und kein Handy, kein Browser und keine Windows-App muss mit dem Board verbunden bleiben.

**Experimentell.** Die Integration liest die Frames des Granboards so, wie Open-Source-Apps für das Granboard sie lesen, und ihre Tests spielen sie ab, aber ein echtes Board hat sie noch nicht getroffen. Zählt ein Feld falsch, [prüfe jedes Feld](#jedes-feld-prüfen) und melde es; die Kennzeichnung fällt, sobald ein echtes Board bestanden hat.

**Auf dieser Seite:** [Was du brauchst](#was-du-brauchst) · [Einrichten](#einrichten) · [Spielen](#spielen) · [Die Verbindung](#die-verbindung) · [Jedes Feld prüfen](#jedes-feld-prüfen) · [Fehlersuche](#fehlersuche) · [Woher die Frames stammen](#woher-die-frames-stammen)

## Was du brauchst

- **Ein Granboard mit Bluetooth.** Die Frames sind die des Granboard 3s; ein anderes Modell, das andere Frames sendet, zeigt sie in der [Diagnose](#jedes-feld-prüfen).
- **Bluetooth von Home Assistant:** ein Adapter des Rechners, auf dem Home Assistant läuft, oder ein [ESPHome-Bluetooth-Proxy](https://esphome.io/components/bluetooth_proxy.html) in Reichweite des Boards, mit aktiven Verbindungen, wie sie die fertigen Proxys haben. Home Assistant 2026.8 oder neuer, wie für die ganze Integration.
- **Das Board frei:** Ein Granboard nimmt eine Verbindung zur Zeit an, also schließe die Granboard-App oder einen Browser, der mit ihm verbunden ist.

## Einrichten

[![Öffne deine Home-Assistant-Instanz und richte HomeDarts for Autodarts ein.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=homedarts)

1. Schalte das Board ein. Home Assistant findet es von selbst und bietet es unter **Einstellungen → Geräte & Dienste → Entdeckt** an; wähle **Hinzufügen**. Hast du das Angebot verworfen, wähle die Schaltfläche oben oder öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen → HomeDarts for Autodarts**, wähle **Granboard über Bluetooth (experimentell)** und das Board.
2. Gib dem Board einen Namen, etwa *Granboard* oder *Kneipe*, und wähle **Absenden**. Die Integration legt ein Gerät mit diesem Namen und dem Modell *Granboard* an, mit den Entitäten der Spiele, des Trainings und der Statistiken und der Diagnose-Entität *Granboard-Verbindung*.
3. Lege das Dashboard an: **Einstellungen → Dashboards → Dashboard hinzufügen → HomeDarts**. Seine Ansichten *Live* und *Anzeigetafel* zeigen die Darts, sobald sie das Board treffen.

## Spielen

Starte ein Spiel auf der Anzeigetafel wie auf jedem Board und wirf:

- **Jeder Treffer ist ein Dart** des Spielers am Board, in seinem Feld: Single, Double, Triple, Single-Bull oder Bullseye. Das innere und das äußere Single einer Zahl zählen gleich.
- **Die Taste** neben dem Board beendet die Aufnahme, wie **Nächster Spieler**. Ohne Dart passt sie, wo das Spiel ein Passen erlaubt.
- **Ein Dart neben dem Board** ist einer, den das Board nicht sieht: Tippe **Fehlwurf** auf dem Tastenfeld, oder beende die Aufnahme mit der Taste.
- **Ein Dart im falschen Feld,** nach einem Abpraller oder einer klemmenden Spitze: Tippe ihn auf der Anzeigetafel an und lege ihn in ein anderes Feld, wie auf jeder [Dartscheibe ohne Autodarts](without-autodarts.de.md#darts-eingeben). Das Tastenfeld, die Aktionen und der Sprach-Blueprint funktionieren neben dem Board weiter.
- **Ein vierter Dart** einer Aufnahme zählt nicht, und die Darts, während der [Bot](games.de.md#gegen-den-bot-spielen) wirft, auch nicht; drücke zuerst die Taste.

Die Board-Ereignisse wie `visit_completed` oder `leg_won` kommen mit `manual: true` und der Quelle `manual`, wie für jeden in Home Assistant eingegebenen Dart, also funktionieren die [Blueprints](automations.de.md#blueprints) unverändert. Das Board meldet nicht, wo in einem Feld ein Dart steckt, also zählen seine Darts nicht für die Dartpositionen und ihre Streuung; das Trefferbild der Felder zählt sie.

## Die Verbindung

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/granboard-dark.png">
  <img src="images/de/granboard-light.png" alt="Wie ein Dart eines Granboards in die Spiele kommt: Für jeden Treffer sendet das Granboard einen kurzen Frame über Bluetooth LE, etwa 3.4@ für das Triple 20. Ein Bluetooth-Adapter von Home Assistant oder ein ESPHome-Bluetooth-Proxy in Reichweite gibt ihn weiter. Die Integration liest den Frame. Ein Feld kommt in die Aufnahme, wie es die Aktion throw_dart tut; die Taste beendet die Aufnahme, wie next_player; ein Frame in den ersten zwei Sekunden nach dem Verbinden wird verworfen, und ein unbekannter bleibt für die Diagnose. Die Spiele, das Training und die Statistiken folgen der Aufnahme. Geht das Board weg, verbindet sich die Integration wieder, sobald Home Assistant es sieht, sonst nach 2, 4, 8 bis 300 Sekunden." width="560">
</picture>

- **Granboard-Verbindung,** eine Diagnose-Entität des Boards, ist *Verbunden*, solange das Board es ist.
- **Ein Board, das weggeht,** weil es schläft, ausgeschaltet oder außer Reichweite ist, verbindet sich wieder, sobald Home Assistant es erneut sieht. Eine Verbindung, die scheitert, wird nach 2, 4, 8 und bis zu 300 Sekunden erneut versucht.
- **In den ersten zwei Sekunden,** nachdem sich das Board verbunden hat, werden seine Frames verworfen, weil ein Board seinen letzten Treffer beim Verbinden noch einmal melden kann.
- **Ohne Bluetooth von Home Assistant** sagt es das Protokoll, und die Darts werden auf dem Tastenfeld eingegeben, bis Bluetooth eingerichtet und die Integration neu geladen ist.

## Jedes Feld prüfen

Hilf mit deinem Board, die Kennzeichnung *experimentell* zu entfernen:

1. Öffne **Einstellungen → Geräte & Dienste → HomeDarts for Autodarts**, das Menü (⋮) → [**Debug-Protokollierung aktivieren**](troubleshooting.de.md#debug-protokollierung).
2. Drücke jedes Feld mit einem Dart oder einem Finger. Das Protokoll unter **Einstellungen → System → Protokolle** nennt jeden Frame und sein Feld, etwa `Granboard frame '3.4': T20`.
3. Ein Frame, den die Integration nicht kennt, heißt `unknown`. Die [Diagnose](troubleshooting.de.md#diagnosedaten-herunterladen) des Boards, **Diagnose herunterladen** im selben Menü, listet die letzten zehn unter `connection → granboard → unknown_frames`, mit den Zahlen der Verbindungen, Frames, Darts und Tastendrücke.
4. Melde ein Feld, das falsch zählt, oder einen unbekannten Frame in einem [Issue](https://github.com/Dennis-Otto/homedarts-for-autodarts/issues), mit dem Frame und dem Feld, das du getroffen hast. Die Diagnose lässt die Bluetooth-Adresse des Boards weg.

## Fehlersuche

| Symptom | Was zu tun ist |
| --- | --- |
| Kein Board gefunden | Schalte das Board ein, bringe es in Reichweite eines Adapters oder Proxys, und schließe jede App, die mit ihm verbunden ist. **Einstellungen → Bluetooth** listet, was Home Assistant sieht. |
| *Granboard-Verbindung* bleibt aus | Ein Proxy verbindet sich mit wenigen Geräten zugleich; gib einen frei oder stelle einen Proxy nahe ans Board. Das Debug-Protokoll nennt den Grund jedes gescheiterten Versuchs. |
| Ein Treffer zählt nicht | Ein vierter Dart, der Zug des Bots und die ersten zwei Sekunden nach dem Verbinden zählen nicht. Sonst [prüfe das Feld](#jedes-feld-prüfen). |
| Ein Feld zählt falsch | [Prüfe jedes Feld](#jedes-feld-prüfen) und melde es. Korrigiere den Dart bis dahin auf der Anzeigetafel. |

## Woher die Frames stammen

Das Board sendet pro Treffer ein paar ASCII-Zeichen, die Zeile und den Pin des Schalters unter dem Feld, etwa `3.4@`, und `BTN@` für die Taste. Die Integration kennt sie so, wie die MIT-lizenzierten Apps [gran-app](https://github.com/sobassy/gran-app) von sobassy und [granboard-app](https://github.com/bastiennoel93/granboard-app) von bastiennoel93 sie lesen; die Tests von `custom_components/homedarts/granboard.py` spielen aufgezeichnete Frames gegen einen Ersatz für Bleak und das Bluetooth von Home Assistant ab. Die Lichter des Rings bleiben vorerst aus: Keine App dokumentiert, wie man sie verlässlich setzt. [Entscheidung 0024](decisions/0024-granboard-over-home-assistant-bluetooth.md) (auf Englisch) erklärt die Wahl.
