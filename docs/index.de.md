---
description: "Autodarts in Home Assistant: jeder Dart live vom Board Manager, Spiele, eine Anzeigetafel, Statistik und Automationen. Lokal und kostenlos, ohne Cloud-Konto."
hide:
  - navigation
  - toc
# The headline of the preview card of a shared link, under the name of the website
# (in one line, which markdownlint doesn't take for the title of the page).
social: { cards_layout_options: { title: "Dein Autodarts-Board live in Home Assistant" } }
---

# Autodarts für Home Assistant

![Autodarts-Logo](branding/icon.svg){ width="96" align="right" }

**Dein Autodarts-Board live in Home Assistant: lokal, in Echtzeit und bereit für Automationen.**

Darts erscheinen in Home Assistant Sekundenbruchteile, nachdem sie landen, direkt vom Board Manager in deinem Netzwerk. Spiele und trainiere damit, stell eine Anzeigetafel neben das Board, verfolge deine Statistik und lass dein Zuhause mitspielen. Kein Konto, keine Cloud, keine Client-ID.

[:material-download: Zu HACS hinzufügen](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dennis-Otto&repository=ha-autodarts&category=integration){ .md-button .md-button--primary } [:material-rocket-launch: Erste Schritte](getting-started.de.md){ .md-button } <a href="demo/index.html?lang=de" class="md-button">:material-play-circle: Live ausprobieren</a>

![Animation: ein 301-Match auf der Live-Karte und der Anzeigetafel nebeneinander. Alex wirft drei Triple 20, die Felder leuchten auf und die Anzeigetafel zählt auf 121 herunter; Sam wirft 85; Alex checkt 121 mit T20, Single-Bull und D18 zum Game shot](images/de/hero.webp)

## Das kann die Integration

<div class="grid cards" markdown>

- :material-lan-connect:{ .lg .middle } **Lokal und in Echtzeit**

    ---

    Mit Board Manager 2 automatisch gefunden; Board Manager 1 funktioniert auch. Nichts verlässt dein Netzwerk, außer du nutzt die Board-Suche, die Cloud-Verknüpfung oder die Online-Brücke, und Geheimnisse des Boards werden nie gespeichert.

    [:octicons-arrow-right-24: Funktionsweise](how-it-works.de.md)

- :material-bullseye-arrow:{ .lg .middle } **Spiele**

    ---

    X01 von 101 bis 1001 mit dem Checkout-Weg nach jedem Dart, Cricket, Cut-Throat Cricket, Tactics, Wild Mouse, Random und Hidden Cricket und neun Partyspiele für bis zu acht, allein oder als Match mit bis zu vier Spielern, mit Legs, Sätzen, Teams und Handicap.

    [:octicons-arrow-right-24: Spiele und Regeln](games.de.md)

- :material-target:{ .lg .middle } **Training**

    ---

    Trainingssessions, die mit dem ersten Dart beginnen, acht Trainingsspiele von Around the Clock bis zur JDC Challenge, ein Tagesziel, eine Trainingsserie und Bestleistungen.

    [:octicons-arrow-right-24: Trainingsspiele](games.de.md#trainingsspiele)

- :material-monitor-dashboard:{ .lg .middle } **Anzeigetafel und Karten**

    ---

    Eine Anzeigetafel für Tablet oder Fernseher, auch über Chromecast, lesbar vom Abwurf aus, mit Spielauswahl, Caller und Ruhemodus. Sieben Dashboard-Karten und ein automatisches Dashboard, auf Deutsch, Englisch, Niederländisch, Französisch und Spanisch.

    [:octicons-arrow-right-24: Anzeigetafel am Board](scoreboard.de.md) · [Dashboard-Karten](cards.de.md)

- :material-chart-line:{ .lg .middle } **Statistik mit Trefferbildern**

    ---

    3-Dart-Average, First-9-Average, Checkout- und Doppelquote, ein Trefferbild jedes Feldes oder der echten Dart-Positionen und wohin jeder Spieler für die meisten Punkte pro Dart zielt. Spielerprofile mit Abzeichen, Wochentrends, eine Bestenliste, ein Wochenbericht und ein Trainingskalender.

    [:octicons-arrow-right-24: Statistik und Spieler](statistics.de.md)

- :material-home-automation:{ .lg .middle } **Automationen und Blueprints**

    ---

    Board-Ereignisse für jeden Dart, jede Aufnahme, Entnahme, jedes Überwerfen, gewonnene Leg und Match. Fünfzehn Blueprints: Lichtshow, Spielstand-Anzeige, Dart- und Übungs-Caller, Highlight-Fotos, Berichte, Warnungen, Routinen, Spielstart und Darts per Sprache sowie Antworten von Assist zu deinen Darts.

    [:octicons-arrow-right-24: Automationen](automations.de.md)

- :material-tournament:{ .lg .middle } **Turniere und ein Bot**

    ---

    Turniere mit drei bis 32 Spielern, jeder gegen jeden mit Tabelle, im K.-o.-System, im Doppel-K.-o.-System oder in Gruppen mit K.-o.-System, und ein Bot mit Stärke 20 bis 120 als Gegner bei X01 und Cricket.

    [:octicons-arrow-right-24: Turniere](games.de.md#turniere) · [Der Bot](games.de.md#gegen-den-bot-spielen)

- :material-microphone:{ .lg .middle } **Sprache**

    ---

    Sag Assist „Starte 501 für Alex und Sam“, auf Deutsch, Englisch, Spanisch, Französisch oder Niederländisch, und das Spiel beginnt; dann gibt „Alex hat 140“ oder „Triple 20“ die Darts ein, wie am Dartautomaten, und „Wie ist mein Schnitt heute?“ beantworten die Statistiken des Boards. Jedes Spiel startet auch mit einer Aktion einer Automation.

    [:octicons-arrow-right-24: Spiel per Sprache starten](automations.de.md#spiel-per-sprache-starten)

    [:octicons-arrow-right-24: Darts per Sprache eingeben](automations.de.md#enter-darts-by-voice)

    [:octicons-arrow-right-24: Assist nach deinen Darts fragen](automations.de.md#ask-assist-about-your-darts)

</div>

## Vom Dart in dein Zuhause

Alles geschieht in deinem Netzwerk, in weniger als einer Sekunde: Der Board Manager bestimmt das Feld, und Home Assistant zeigt es auf den Karten und gibt es an deine Automationen weiter.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/dart-journey-dark.png">
  <img src="images/de/dart-journey-light.png" alt="Der Weg eines Darts: Ein Dart landet in der Triple 20. Die Kameras des Boards sehen ihn, und der Board Manager auf dem Board-PC bestimmt das Feld. Eine Echtzeitnachricht bringt es durch dein Netzwerk zur Autodarts-Integration in Home Assistant; sie aktualisiert die Entitäten, sendet die Board-Ereignisse und lässt das Feld auf den Karten und der Anzeigetafel aufleuchten. Deine Automation reagiert auf die Ereignisse, etwa mit blinkendem Licht bei einer 180 oder einem Caller. Das alles dauert weniger als eine Sekunde und braucht keine Cloud" width="560">
</picture>

[:octicons-arrow-right-24: Funktionsweise](how-it-works.de.md)

## Im Vergleich

Wie sich diese Integration mit der Autodarts-App und ihrer Browser-Erweiterung, mit darts-caller und darts-wled und mit den anderen Home-Assistant-Integrationen für Autodarts vergleicht. [Umstieg von anderen Werkzeugen](coming-from.de.md) zeigt, wie du umsteigst.

--8<-- "docs/coming-from.de.md:compare"

*Stand Oktober 2026, aus der Dokumentation und dem Code jedes Projekts. [Umstieg von anderen Werkzeugen](coming-from.de.md) hat die Einzelheiten und die Quellen.*

## Anleitungen

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } [**Von null bis zur Anzeigetafel**](getting-started.de.md)

    ---

    Für Autodarts-Spieler ohne Home Assistant: Home Assistant und HACS aufsetzen, die Integration installieren, das Board hinzufügen und das erste Spiel auf der Anzeigetafel.

- :material-download:{ .lg .middle } [**Installation und Einrichtung**](installation.de.md)

    ---

    Voraussetzungen, HACS und manuelle Installation, die Wege, ein Board hinzuzufügen, die optionale Cloud-Verknüpfung, Neukonfiguration, Updates und Entfernen.

- :material-pencil:{ .lg .middle } [**Spielen ohne Autodarts**](without-autodarts.de.md)

    ---

    Jede Dartscheibe, mit allen Spielen, dem Training und den Statistiken: Du gibst die Darts auf einem Tastenfeld ein.

- :material-bluetooth:{ .lg .middle } [**Granboard über Bluetooth**](granboard.de.md)

    ---

    Die Darts eines Granboards kommen von selbst, über das Bluetooth von Home Assistant und ESPHome-Proxys. Experimentell.

- :material-frequently-asked-questions:{ .lg .middle } [**Häufige Fragen**](faq.de.md)

    ---

    Kurze Antworten zu Konto, Geräten, Online-Spiel, Datenschutz, mehreren Boards, Bildschirmen, Sprachen, Updates und Umstieg.

- :material-swap-horizontal:{ .lg .middle } [**Umstieg von anderen Werkzeugen**](coming-from.de.md)

    ---

    Autodarts Local, die anderen Integrationen, MQTT-Brücken, darts-caller, darts-wled und Tools for Autodarts im Vergleich, und wie du von ihnen umsteigst.

- :material-bullseye-arrow:{ .lg .middle } [**Spiele und Regeln**](games.de.md)

    ---

    Alle Spiele im Überblick, vier Wege, eines zu starten, Matches, Teams, Handicaps, das Ausbullen, Turniere und die Regeln jedes Spiels.

- :material-television:{ .lg .middle } [**Anzeigetafel am Board**](scoreboard.de.md)

    ---

    Ein Tablet oder Fernseher neben dem Board: Einrichtung, Quer- und Hochformat, Spielauswahl, Turniere, Caller und Ruhemodus.

- :material-chart-line:{ .lg .middle } [**Statistik und Spieler**](statistics.de.md)

    ---

    Trainingssessions, Bestleistungen, Trefferbild und Dart-Positionen, wohin zielen, Fortschritt über die Zeit, Doubles, Spielerprofile, Erfolge, Bestenliste und Exporte.

- :material-home-automation:{ .lg .middle } [**Automationen**](automations.de.md)

    ---

    Fünfzehn Blueprints, ihre Einstellungen, Board-Ereignisse und fertige Beispiele.

- :material-play-network:{ .lg .middle } [**Online-Matches**](online-matches.de.md)

    ---

    Überwerfen, gewonnene Legs und Matches von Online-Matches als Board-Ereignisse, mit der Browser-Erweiterung Tools for Autodarts *(experimentell)*.

</div>

## Nachschlagen

<div class="grid cards" markdown>

- :material-view-dashboard:{ .lg .middle } [**Dashboard-Karten**](cards.de.md)

    ---

    Alle sieben Karten und das automatische Dashboard, mit allen Optionen und Barrierefreiheit.

- :material-format-list-bulleted:{ .lg .middle } [**Entitäten und Ereignisse**](entities.de.md)

    ---

    Alle Entitäten, Board-Ereignisse, Zustände, Attribute und Aktionen, und welche Board-Manager-Generation sie liefert.

- :material-cog-transfer:{ .lg .middle } [**Funktionsweise**](how-it-works.de.md)

    ---

    Architektur, Aktualisierung, Verbindungsverhalten, Training und Bestleistungen, gespeicherte Daten und Datenschutz.

- :material-lifebuoy:{ .lg .middle } [**Fehlerbehebung**](troubleshooting.de.md)

    ---

    Meldungen bei der Einrichtung, Reparaturen, nicht verfügbare Entitäten, fehlgeschlagene Aktionen, Diagnose und Logs.

- :material-shield-lock:{ .lg .middle } [**Sicherheit**](security.de.md)

    ---

    Schutzgüter, Vertrauensgrenzen, Bedrohungen und Gegenmaßnahmen.

- :material-book-alphabet:{ .lg .middle } [**Glossar**](glossary.de.md)

    ---

    Die Begriffe des Dartsports und dieser Integration, mit ihren englischen Entsprechungen.

</div>

Was jede Version gebracht hat, steht in den [Änderungen](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md) (auf Englisch), was als Nächstes kommt, in der [Roadmap](roadmap.de.md). Für Videos, Artikel und Beiträge hat das [Creator-Kit](creator-kit.de.md) Fakten, fertige Texte, Videos und Bilder, frei nutzbar.

--8<-- "docs/README.de.md:devices-and-languages"
