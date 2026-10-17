---
description: "Umstieg von Autodarts Local, einer anderen Autodarts-Integration, einer MQTT-Brücke oder darts-caller: was ersetzt was, was bleibt und wie du es entfernst."
---

# Umstieg von anderen Werkzeugen

[← Dokumentation](README.de.md) · [English](coming-from.md)

Andere Projekte bringen ein Autodarts-Board nach Home Assistant oder daneben. Diese Seite vergleicht sie mit dieser Integration und zeigt für jedes, welche Entitäten, Ereignisse und Blueprints seinen Platz einnehmen, ob es installiert bleiben darf und wie du es entfernst. Die Angaben haben den Stand Oktober 2026 und stammen aus der Dokumentation und dem Code des jeweiligen Projekts, zu denen die Links führen. Hat sich ein Projekt seitdem geändert, [sag uns Bescheid](https://github.com/Dennis-Otto/ha-autodarts/discussions), damit diese Seite fair bleibt.

**Schnell zu:** [Auf einen Blick](#auf-einen-blick) · [Darf es bleiben?](#darf-es-bleiben) · [Autodarts Local](#autodarts-local) · [Integration von Quevinsta](#autodarts-for-home-assistant-von-quevinsta) · [Integration von belese](#autodarts-von-belese) · [Autodarts Connect Online](#autodarts-connect-online) · [Darts Hub](#darts-hub) · [MQTT-Brücken](#mqtt-brücken) · [darts-caller und darts-wled](#darts-caller-und-darts-wled) · [Tools for Autodarts](#tools-for-autodarts) · [Die ursprüngliche Integration](#die-ursprüngliche-integration)

## Auf einen Blick

<!-- --8<-- [start:compare] -->

| | Diese Integration | Autodarts-App mit [Tools for Autodarts](https://github.com/creazy231/tools-for-autodarts) | [darts-caller](https://github.com/Peschi90/darts-caller) und [darts-wled](https://github.com/Peschi90/darts-wled) | Andere Home-Assistant-Integrationen |
| --- | --- | --- | --- | --- |
| **Läuft ohne Cloud** | Ja, mit der [lokalen Schnittstelle](how-it-works.de.md#datenschutz) des Board Managers | Nein, mit einem [Autodarts-Konto](https://autodarts.com/) | Nein, darts-caller [meldet sich bei Autodarts an](https://github.com/Peschi90/darts-caller#autodarts-login) | Manche ([Einzelheiten](coming-from.de.md#darf-es-bleiben)) |
| **Entitäten und Ereignisse in Home Assistant** | Ja, ein [Ereignis](entities.de.md#board-ereignisse) für jeden Dart, jede Aufnahme, Entnahme, jedes Überwerfen, Leg und Match | Nein | Nein | Sensoren der aktuellen Aufnahme oder des Spiels |
| **Blueprints** | [Dreizehn](automations.de.md#blueprints) | Nein | Nein | Nein |
| **Lichtshow** | Blueprint [Light show](automations.de.md#light-show), für WLED oder jedes Licht | WLED, mit Tools | WLED, mit darts-wled | Eigene Automationen |
| **Caller** | Auf der [Anzeigetafel](scoreboard.de.md#der-caller) oder deinen [Lautsprechern](automations.de.md#welcher-caller) | Mit Tools | Sprachpakete, mit darts-caller | Nein |
| **Statistik bleibt zu Hause** | [Ja](statistics.de.md): Averages, Trefferbilder, Profile und ein Jahr Verlauf | Nein, im Autodarts-Konto | Nein | Nein |
| **Ohne Autodarts-Board** | Ja, auf einem [Tastenfeld](without-autodarts.de.md) | Ja, auf einem Tastenfeld oder mit [Lens](https://autodarts.com/) | Nein | Nein |
| **Online-Matches** | Deine Darts, und die Momente des Matches über die [Online-Brücke](online-matches.de.md) *(experimentell)* | Ja | Ja | Manche, über die Cloud |
| **Lizenz und Kosten** | [MIT](https://github.com/Dennis-Otto/ha-autodarts/blob/main/LICENSE), kostenlos | Autodarts: ein kostenloser Tarif und das bezahlte [Plus](https://autodarts.com/); Tools: [CC BY-NC 4.0](https://github.com/creazy231/tools-for-autodarts/blob/main/LICENSE) | Kostenlos, ohne angegebene Lizenz | MIT, Apache 2.0 oder ohne Lizenzdatei |

<!-- --8<-- [end:compare] -->

*Stand Oktober 2026, aus der Dokumentation und dem Code jedes Projekts. Die Abschnitte unten haben die Einzelheiten und die Quellen.*

## Darf es bleiben?

Home Assistant lädt eine Integration pro Domain, deshalb können zwei Integrationen mit der Domain `autodarts` nicht gleichzeitig installiert sein. Eine mit eigener Domain darf bleiben, während du deine Automationen umstellst, und gehen, wenn nichts sie mehr nutzt.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/coming-from-dark.png">
  <img src="images/de/coming-from-light.png" alt="Umstieg von einer anderen Autodarts-Integration: Das ursprüngliche HACSAutodarts nutzt die Domain autodarts; ersetze es in HACS und behalte seinen Eintrag, der umgestellt wird. Die Integrationen von Quevinsta und belese nutzen ebenfalls die Domain autodarts; lösche ihre Einträge, entferne sie in HACS, prüfe, dass custom_components/autodarts weg ist, und starte neu. Autodarts Local, Autodarts Connect Online, Darts Hub und MQTT-Brücken haben eine eigene Domain und dürfen vorerst bleiben. Dann installierst du diese Integration, fügst das Board hinzu, stellst die Automationen auf ihre Ereignisse und Blueprints um und entfernst, was nichts mehr nutzt" width="520">
</picture>

| Projekt | Domain | Neben dieser Integration |
| --- | --- | --- |
| [Ursprüngliche Integration](#die-ursprüngliche-integration) von Trkal | `autodarts` | Wird ersetzt: ihr Eintrag wird umgestellt |
| [Autodarts for Home Assistant](#autodarts-for-home-assistant-von-quevinsta) von Quevinsta | `autodarts` | [Vorher entfernen](#eine-integration-mit-derselben-domain-entfernen) |
| [autodarts](#autodarts-von-belese) von belese | `autodarts` | [Vorher entfernen](#eine-integration-mit-derselben-domain-entfernen) |
| [Autodarts Local](#autodarts-local) | `autodarts_local` | Darf bleiben |
| [Autodarts Connect Online](#autodarts-connect-online) | `autodarts_connect` | Darf bleiben |
| [Darts Hub](#darts-hub) | `darts_hub` | Darf bleiben |
| [MQTT-Brücken](#mqtt-brücken) | `mqtt` | Darf bleiben |
| [darts-caller und darts-wled](#darts-caller-und-darts-wled) | Außerhalb von Home Assistant | Darf bleiben; lass einen Caller sprechen |
| [Tools for Autodarts](#tools-for-autodarts) | Im Browser | Bleibt; die Online-Brücke nutzt es |

### Eine Integration mit derselben Domain entfernen

1. **Notiere, was sie nutzt.** Der Dialog einer Entität listet unter **Verwandt** die Automationen und Skripte, die sie nutzen.
2. **Lösche ihre Einträge** unter **Einstellungen → Geräte & Dienste**: Öffne die Integration und wähle bei jedem Eintrag im Menü (⋮) **Löschen**. Tu das zuerst: Nach dem Wechsel würde Home Assistant die Einträge dieser Integration übergeben, die ihre Einstellungen nicht kennt.
3. **Entferne den Code.** Öffne die Integration in HACS, dann ihr Menü (⋮) → **Entfernen**. Bei einer manuellen Installation löschst du den Ordner `config/custom_components/autodarts`. Prüfe, dass der Ordner weg ist.
4. **Starte Home Assistant neu.**
5. **Installiere diese Integration** und füge dein Board hinzu, wie die [Installationsanleitung](installation.de.md#board-hinzufügen) es beschreibt.

### Eine mit eigener Domain behalten

1. Installiere diese Integration daneben und füge dein Board hinzu. Beide lesen denselben Board Manager.
2. Stell deine Automationen nacheinander um, mit den Tabellen unten.
3. Nutzt nichts mehr die alte Integration, lösche ihren Eintrag unter **Einstellungen → Geräte & Dienste**, entferne sie in HACS und starte Home Assistant neu.

Die Entitäts-IDs unten gehören zu einem Board namens *Autodarts Board* in einem deutschsprachigen Home Assistant, wie in den [Beispielen der Automationen](automations.de.md#beispiele). Deine findest du auf der Geräteseite des Boards.

## Autodarts Local

[Autodarts Local](https://github.com/Mastershort/ha-autodarts-local) von Mastershort, Domain `autodarts_local`, liest jede Sekunde den Zustand des Board Managers: ob das Board online ist, seinen Status, die Darts der Aufnahme und ihre Summe, dazu drei Tasten für die Erkennung.

| Autodarts Local | Hier |
| --- | --- |
| *Verbindung*: `Online` oder `Offline` | Der Binärsensor *Lokale Verbindung*, unter [Zustand und Verbindungen](entities.de.md#zustand-und-verbindungen) |
| *Status*, etwa `Throw` oder `Takeout` | *Erkennungsstatus*: `throw`, `takeout`, `takeout_in_progress` und die anderen der [aktuellen Aufnahme](entities.de.md#aktuelle-aufnahme), mit dem Ereignis `status_changed`; für die Entnahme die Ereignisse `takeout_started` und `takeout_finished` |
| *Aktuelle Aufnahme* | *Erkannte Aufnahmepunkte*, und das Ereignis `visit_thrown` in dem Moment, in dem der dritte Dart landet |
| *Anzahl Würfe* | *Darts in der Aufnahme* |
| *Wurf 1*, *Wurf 2*, *Wurf 3* | Das Attribut `throws` von *Erkannte Aufnahmepunkte*, der Sensor *Letzter Dart* und das Ereignis `dart_detected` mit `dart_index` und `segment` |
| Die Tasten *Erkennung Starten*, *Erkennung Stoppen* und *Erkennung Zurücksetzen* | Die Tasten *Erkennung starten*, *Erkennung stoppen* und *Erkennung zurücksetzen* und der Schalter *Erkennung*, unter [Steuerung](entities.de.md#steuerung) |
| Die Beispiel-Automation *Takeout Light* | Der Blueprint [Takeout actions](automations.de.md#takeout-actions) oder das Beispiel [Boardlicht bei der Entnahme](automations.de.md#boardlicht-bei-der-entnahme) |

**Darf bleiben.** Beide nennen das Gerät *Autodarts Board*, so wie diese Integration ein Board, das du über seine Adresse hinzufügst. Solange beide installiert sind, bekommen die Tasten hier IDs mit `_2` am Ende, etwa `button.autodarts_board_erkennung_starten_2`. Entfernst du Autodarts Local, bevor du das Board hier hinzufügst, bekommen die Tasten die IDs, die deine Automationen schon nutzen, etwa `button.autodarts_board_erkennung_starten`.

## Autodarts for Home Assistant von Quevinsta

[Autodarts for Home Assistant](https://github.com/Quevinsta/autodarts-for-home-assistant) von Quevinsta, Domain `autodarts`, ist für X01 gemacht und liest alle zehn Sekunden den Zustand des Board Managers: die drei Darts und ihre Werte, die Aufnahme, die Restpunkte, ob ein Checkout möglich ist, und das Ergebnis des Legs.

| Integration von Quevinsta | Hier |
| --- | --- |
| *Dart 1*, *Dart 2*, *Dart 3* und ihre Werte | Das Attribut `throws` von *Erkannte Aufnahmepunkte* und das Ereignis `dart_detected` |
| *Throw Summary*, *Turn Total* | *Erkannte Aufnahmepunkte*, und `segments` und `score` des Ereignisses `visit_thrown` |
| *Remaining*, *Checkout Possible* | *Übungsspiel Restpunkte* und *Übungsspiel Checkout-Weg*, der *unbekannt* ist, wenn es keinen Weg gibt, in einem [Übungsspiel](entities.de.md#übungsspiel) |
| *Leg Won*, *Leg Lost*, *Leg Result* | Die Ereignisse `leg_won` und `match_won`, mit dem `name` des Gewinners |
| *Autodarts Status* | Der Binärsensor *Lokale Verbindung* |

Hier zählt Home Assistant das Übungsspiel selbst: X01 von 101 bis 1001, die Cricket-Spiele, die Partyspiele und die Trainingsspiele. Ein Spiel auf play.autodarts.io zählt der Browser, und seine Punkte kommen nur mit den [Cloud-Spieldaten](entities.de.md#cloud-spieldaten-optional) nach Home Assistant, die noch nicht verfügbar sind.

**Dieselbe Domain:** [vorher entfernen](#eine-integration-mit-derselben-domain-entfernen).

## autodarts von belese

[autodarts](https://github.com/belese/ha_integrations) von belese, Domain `autodarts`, folgt dem Board über die Autodarts-Cloud, mit der E-Mail-Adresse und dem Passwort deines Autodarts-Kontos. Es zeigt den Zustand des Boards, die Spieler, den Spieler am Board und den Gewinner. Seine letzte Änderung war im Februar 2025.

| Integration von belese | Hier |
| --- | --- |
| Zustand des Boards | *Erkennungsstatus*, lokal und ohne Konto |
| Spieler, aktueller Spieler | `players`, `player` und `name` von *Übungsspiel Restpunkte* in einem Übungsspiel, und das Ereignis `turn_changed` |
| Gewinner | Das Ereignis `match_won` und das Attribut `winner` von *Übungsspiel Restpunkte* |

Diese Integration speichert kein Passwort: Die optionale Cloud-Verknüpfung wird die Geräteanmeldung von Autodarts nutzen.

**Dieselbe Domain:** [vorher entfernen](#eine-integration-mit-derselben-domain-entfernen).

## Autodarts Connect Online

[Autodarts Connect Online](https://github.com/casef007/HA-autodarts-connect-online) von casef007, Domain `autodarts_connect`, ist eine Beta, die dem Board über die Autodarts-Cloud folgt, mit der E-Mail-Adresse, dem Passwort und der Board-ID deines Kontos. Laut seiner README meldet es sich vorerst mit den öffentlichen Zugangsdaten von darts-caller an. Es sieht Online-Matches und Bot-Spiele, mit Name, Punkten, Average und Cricket-Marks von bis zu vier Spielern, und feuert für jeden Dart das Ereignis `autodarts_throw`.

| Autodarts Connect Online | Hier |
| --- | --- |
| Das Ereignis `autodarts_throw` | Das Ereignis `dart_detected`, lokal, für jeden Dart auf deinem Board |
| Name, Punkte und Average von bis zu vier Spielern | `scores` von *Übungsspiel Restpunkte* für ein Match von bis zu vier Spielern, und bis zu acht Spieler in den [Partyspielen](entities.de.md#partyspiele) und [Turnieren](entities.de.md#turniere) |
| Cricket-Marks | `marks`, `points` und `mpr` jedes Spielers in den `scores` von *Übungsspiel Restpunkte*, in den [Cricket-Spielen](entities.de.md#cricket) |
| Online-Matches | Deine Darts wie gewohnt, und Überwerfen, gewonnene Legs und Matches über die [Online-Brücke](online-matches.de.md) *(experimentell)* |

**Darf bleiben.** Es sieht heute mehr von einem Online-Match als diese Integration, etwa die Darts und Punkte deiner Gegner. Spielst du vor allem online, behalte es neben dieser.

## Darts Hub

[Darts Hub](https://github.com/etienne72230/ha-darts-hub) von etienne72230, Domain `darts_hub`, braucht darts-hub oder darts-caller in deinem Netzwerk, auf Port 8079, und den Board Manager auf Port 3180. Es zeigt das Match, bis zu sechs Spieler mit ihren Punkten, die Einzelheiten jedes Darts mit seiner Position und Tasten zum Zurücksetzen und Kalibrieren des Boards.

| Darts Hub | Hier |
| --- | --- |
| Board-Status, aktuelles Ereignis | *Erkennungsstatus* und die [Board-Ereignisse](entities.de.md#board-ereignisse) |
| Spieler und Punkte des Matches | *Übungsspiel Restpunkte* mit seinen `scores`, für das Übungsspiel, das Home Assistant zählt |
| Dart 1 bis 3 und der letzte Dart, mit Wert, Multiplikator, Feld und Position | Das Attribut `throws` von *Erkannte Aufnahmepunkte*, mit `segment`, `multiplier`, `score`, `bed` und der Position `x`/`y` |
| Die Tasten *Reset Board* und *Calibrate Board* | *Erkennung zurücksetzen* und *Automatische Kalibrierung starten* |

**Darf bleiben.** Diese Integration braucht weder darts-hub noch darts-caller.

## MQTT-Brücken

MQTT-Brücken wie [Autodarts MQTT](https://github.com/Quevinsta/autodarts-mqtt) von Quevinsta sind Programme, die du selbst startest. Sie veröffentlichen den Board-Status, die Zahl der Darts und Averages an einen MQTT-Broker, und Home Assistant legt ihre Entitäten über MQTT Discovery an.

| Autodarts MQTT | Hier |
| --- | --- |
| Board Status | *Erkennungsstatus* |
| Number of Throws | *Darts in der Aufnahme* |
| 3-Dart Average | *Training 3-Dart-Average* der [Trainingssession](entities.de.md#trainingssession) |
| Leg Average | Das `average` des Ereignisses `leg_won` |

**Darf bleiben.** Diese Integration braucht weder einen Broker noch ein eigenes Programm. Um eine Brücke zu entfernen, stoppst du sie und löschst ihr Gerät unter **Einstellungen → Geräte & Dienste → MQTT**.

## darts-caller und darts-wled

[darts-caller](https://github.com/Peschi90/darts-caller) spielt die Tondateien eines Sprachpakets zum Stand eines Autodarts-Spiels und gibt das Spiel an andere Programme weiter, etwa an [darts-wled](https://github.com/Peschi90/darts-wled), das damit WLED-Lichter steuert. [darts-hub](https://github.com/lbormann/darts-hub) lädt sie herunter, richtet sie ein und startet sie. Sie laufen auf einem PC, und darts-caller meldet sich bei deinem Autodarts-Konto an und folgt dessen Spielen.

Was Home Assistant jetzt übernimmt:

| darts-caller und darts-wled | Hier |
| --- | --- |
| Ansagen von Punkten und Checkouts | Der [Caller der Anzeigetafel](scoreboard.de.md#der-caller), über den Bildschirm am Board, oder die Blueprints [Dart caller](automations.de.md#dart-caller) und [Practice caller](automations.de.md#practice-caller) auf deinen Lautsprechern |
| WLED-Effekte für eine 180, ein Überwerfen oder einen Game shot | Der Blueprint [Light show](automations.de.md#light-show) mit deinen [WLED-Presets oder anderem Licht](automations.de.md#lichtshow-mit-wled-und-anderem-licht) |
| Spielereignisse für andere Programme | [Board-Ereignisse](entities.de.md#board-ereignisse) für jeden Dart, jede Aufnahme, Entnahme, jedes Überwerfen, gewonnene Leg und Match, für jede Automation von Home Assistant |

**Darf bleiben.** darts-caller folgt der Cloud und diese Integration dem Board, deshalb funktionieren beide zugleich. Zwei Caller reden aber durcheinander, und zwei Programme, die dieselben WLED-Lichter steuern, kommen sich in die Quere: Lass von beidem nur eines sprechen und leuchten. In Online-Matches sagt darts-caller auch die Punkte deiner Gegner an, die diese Integration nicht sieht.

## Tools for Autodarts

[Tools for Autodarts](https://github.com/creazy231/tools-for-autodarts) ist eine Browser-Erweiterung für die Web-App von Autodarts, mit Caller, Soundeffekten, WLED-Effekten, Animationen und vielen Einstellungen für Lobby und Match.

**Bleibt.** Die [Online-Brücke](online-matches.de.md) nutzt seine WLED-Funktion: Sie ruft Home Assistant mit den Momenten eines Online-Matches auf, die zu `online_*`-[Board-Ereignissen](entities.de.md#board-ereignisse) werden. Wie bei darts-caller gilt: Lass im Raum einen Caller sprechen, den von Tools oder den von Home Assistant.

## Die ursprüngliche Integration

Diese Integration begann als Fork von [Trkal/HACSAutodarts](https://github.com/Trkal/HACSAutodarts) und nutzt dieselbe Domain `autodarts`. Ersetze sie in HACS und behalte ihren Eintrag: [Von der ursprünglichen Integration umsteigen](installation.de.md#von-der-ursprünglichen-integration-umsteigen) erklärt die Schritte.
