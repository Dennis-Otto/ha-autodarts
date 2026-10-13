# Autodarts für Home Assistant

[← Projektseite](https://github.com/Dennis-Otto/ha-autodarts) · [English documentation](README.md)

**Dein Autodarts-Board live in Home Assistant: lokal, in Echtzeit und bereit für Automationen.**

Die [Website der Dokumentation](https://dennis-otto.github.io/ha-autodarts/de/) hat dieselben Seiten, mit Suche und Umschalter auf Englisch.

<img src="images/de/hero.webp" alt="Animation: ein 301-Match auf der Live-Karte und der Anzeigetafel nebeneinander. Alex wirft drei Triple 20, die Felder leuchten auf und die Anzeigetafel zählt auf 121 herunter; Sam wirft 85; Alex checkt 121 mit T20, Single-Bull und D18 zum Game shot" width="100%">

**Schnell zu:** [Schnellstart](#schnellstart) · [Das kann die Integration](#das-kann-die-integration) · [Anleitungen](#anleitungen) · [Anwendungsfälle](#anwendungsfälle) · [Blueprints](#blueprints) · [Glossar](glossary.de.md) · [Änderungen](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md)

## Schnellstart

Du brauchst Home Assistant ab 2026.8 mit [HACS](https://hacs.xyz) und ein Autodarts-Board in deinem Netzwerk oder eine beliebige Dartscheibe, deren Darts du auf einem Tastenfeld eingibst ([Voraussetzungen](#voraussetzungen)).

1. **Mit HACS installieren, dann Home Assistant neu starten.**

   [![Home Assistant öffnen und dieses Repository in HACS anzeigen.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dennis-Otto&repository=ha-autodarts&category=integration)

   Alternativ fügst du `https://github.com/Dennis-Otto/ha-autodarts` in HACS als benutzerdefiniertes Repository vom Typ **Integration** hinzu und lädst **Autodarts** herunter.

2. **Board hinzufügen.** Mit Board Manager 2 erscheint dein Board meist schon unter **Einstellungen → Geräte & Dienste → Entdeckt**. Sonst:

   [![Home Assistant öffnen und Autodarts einrichten.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=autodarts)

   Wähle **Boards im Netzwerk suchen** oder **Board-Adresse eingeben** und bestätige. Ohne Autodarts wählst du **Dartscheibe ohne Autodarts: jeden Dart selbst eingeben**.

3. **Karten hinzufügen.** Erzeuge in einem Schritt ein komplettes Dashboard: **Einstellungen → Dashboards → Dashboard hinzufügen → Autodarts**. Oder bearbeite ein Dashboard, wähle **Karte hinzufügen** und suche nach *Autodarts*.

Neu bei Home Assistant? [Von null bis zur Anzeigetafel](getting-started.de.md) führt dich von null bis zur Anzeigetafel neben deinem Board. Die [Installationsanleitung](installation.de.md) beschreibt die manuelle Installation, die Neukonfiguration, Updates und das Entfernen.

## Warum

- **Sofort und lokal.** Darts erscheinen in Home Assistant Sekundenbruchteile, nachdem sie landen, direkt vom Board Manager in deinem Netzwerk. Kein Konto, keine Cloud, keine Client-ID.
- **Ein ganzer Dartabend.** X01 von 101 bis 1001, vier Cricket-Spiele, sechs Partyspiele und acht Trainingsspiele, allein, als Match mit bis zu vier Spielern, als Partyspiel mit bis zu acht oder als Turnier mit bis zu acht, mit einer Anzeigetafel für das Tablet am Board.
- **Deine Entwicklung in Zahlen.** Averages, Trefferbilder der echten Dart-Positionen, Bestleistungen, Abzeichen, Wochentrends, Spielerprofile, ein Wochenbericht und ein Jahr Verlauf, alles bei dir zu Hause.
- **Dein Zuhause spielt mit.** Licht für eine 180, ein Caller auf deinen Lautsprechern, das Boardlicht bei der Entnahme, ein Foto deines besten Checkouts.

## Das kann die Integration

[Spielen](#spielen) · [Wie am Dartautomaten](#wie-am-dartautomaten) · [Trainieren](#trainieren) · [Auswerten](#auswerten) · [Bildschirm am Board](#bildschirm-am-board) · [Automatisieren](#automatisieren) · [Lokal und privat](#lokal-und-privat)

### Spielen

- X01 von 101 bis 1001 mit Double-Out, Double-In und dem Checkout-Weg nach jedem Dart
- Cricket, Cut-Throat Cricket, Tactics und Wild Mouse auf einer Kreidetafel
- Partyspiele für bis zu acht: Shanghai, Halve-It, Killer, Golf, Baseball und Count-Up
- Turniere mit drei bis acht Spielern: jeder gegen jeden mit Tabelle oder K.-o.-System mit Turnierbaum

<details>
<summary>Matches, der Bot, Korrekturen und mehr</summary>

- Matches mit bis zu vier Spielern, Legs und Sätzen, zwei Teams zu zwei, Startpunkten als Handicap und Ausbullen, und eine Zusammenfassung jedes Matches
- Ein Bot mit Stärke 20 bis 120 als Gegner bei X01 und Cricket
- Ein Tipp korrigiert einen falsch erkannten Dart; ein Tastenfeld gibt Darts von Hand ein, und die letzte Aufnahme lässt sich zurücknehmen
- Kein Autodarts? Jede Dartscheibe spielt mit, jeder Dart auf dem Tastenfeld eingegeben
- Stellwürfe, wo kein Checkout möglich ist, etwa T20 T20 S17 für Rest 32

</details>

<img src="images/de/tournament-bracket.webp" alt="Animation: der Turnierbaum mit fünf Spielern auf der Anzeigetafel; die Sieger rücken in die nächste Runde, bis Alex das Finale gewinnt" width="100%">

[Spiele und Regeln →](games.de.md)

### Wie am Dartautomaten

- Wild Mouse, auch als Minnesota Cricket bekannt, mit Doubles, Triples und Three in a Bed
- Zielhilfen auf der Kreidetafel: grün, wo ein Dart punktet, gelb, was zu schließen ist, und ein Dart ohne Wirkung durchgestrichen
- Konfetti und ein goldenes Leuchten bei 180, Game Shot und Match, ein Leuchten bei einem Ton
- So wird gespielt: jedes Spiel kurz erklärt auf dem Bildschirm für ein neues Spiel, für Gäste, die es noch nie gespielt haben, und Partyspiele für bis zu acht Spieler

<img src="images/de/celebration.webp" alt="Animation: eine 180 auf der Anzeigetafel. Alex wirft drei Triple 20, ein goldenes Leuchten erhellt die Anzeigetafel und Konfetti fliegt aus ihrer Mitte, dann zeigt die Anzeigetafel 321 wie zuvor" width="100%">

[Wild Mouse →](games.de.md#wild-mouse)

### Trainieren

- Trainingssessions, die mit dem ersten Dart beginnen und die letzten 20 Sessions behalten
- Acht Trainingsspiele: Around the Clock, Doppeltraining, Checkout-Training, Bob's 27, der 121-Checkout, Catch 40, die JDC Challenge und das Singles-Training
- Ein Tagesziel, eine Trainingsserie und Bestleistungen mit einem Ereignis, sobald du eine übertriffst

<img src="images/de/training-game.webp" alt="Animation: Around the Clock auf der Live-Karte; jeder Treffer bringt das Ziel weiter und umrandet die Felder der nächsten Zahl" width="100%">

[Trainingsspiele →](games.de.md#trainingsspiele)

### Auswerten

- 3-Dart-Average, First-9-Average, Checkout- und Doppelquote
- Ein Trefferbild jedes Feldes oder der echten Dart-Positionen, mit der Streuung in Millimetern
- Spielerprofile mit Abzeichen in Bronze, Silber, Gold und Platin und eine Bestenliste

<details>
<summary>Trends, Berichte, Kalender und Exporte</summary>

- Wochentrends, direkte Vergleiche und der Match-Verlauf jedes Spielers
- Die Quote jedes Doubles, ein Wochenbericht, ein Trainingskalender und Exporte als CSV oder JSON
- Langzeitstatistik für Grafiken über Wochen und Monate

</details>

<p align="center"><img src="images/de/heatmap-modes.webp" alt="Animation: Das Trefferbild der Trainingskarte wechselt von Feldern zu Zahlen und den echten Dart-Positionen, dann zu den Darts eines Spielers" width="520"></p>

[Statistik und Spieler →](statistics.de.md)

### Bildschirm am Board

- Eine Anzeigetafel für Tablet oder Fernseher, lesbar vom Abwurf aus
- Eine Spielauswahl, um Spiel, Spieler und Format direkt am Board zu wählen oder ein Turnier zu starten
- Ein Caller, der das Spiel über den Browser des Bildschirms ansagt
- Ein Ruhemodus mit Bestenliste, Bestleistungen, den Darts von heute und einer Uhr

<p align="center"><img src="images/de/lobby.webp" alt="Animation: Auf dem Tablet öffnet Neues Spiel die Spielauswahl, Cricket und ein zweiter Spieler werden gewählt und das Spiel startet" width="600"></p>

[Anzeigetafel am Board →](scoreboard.de.md)

### Automatisieren

- Board-Ereignisse für jeden Dart, jede Aufnahme, Entnahme, jedes Überwerfen, gewonnene Leg und Match, jede Bestleistung und mehr
- Dreizehn Blueprints: Lichtshow, Dart- und Übungs-Caller, Highlight-Fotos, Berichte, Warnungen, Routinen sowie Spielstart und Darts per Sprache ([importieren](#blueprints))
- Jedes Spiel mit einer Aktion starten, auch per Sprache, und Assist deine Darts sagen, wie am Dartautomaten
- Online-Matches auf play.autodarts.io über eine optionale Brücke *(experimentell)*

<img src="images/de/media-gallery.png" alt="Die Highlight-Galerie in der Medienansicht von Home Assistant: Fotos eines 121er-Checkouts, einer 180 und einer 140" width="100%">

[Automationen →](automations.de.md)

### Lokal und privat

- Mit Board Manager 2 automatisch gefunden; Board Manager 1 funktioniert auch
- Nichts verlässt dein Netzwerk, außer du nutzt die Board-Suche, die Cloud-Verknüpfung oder die Online-Brücke; Geheimnisse des Boards werden nie gespeichert
- Sieben Dashboard-Karten und ein automatisches Dashboard, auf Deutsch, Englisch, Niederländisch, Französisch und Spanisch ([Sprachen](#sprachen))
- Leicht für einen Raspberry Pi: Eine Nachricht des Boards aktualisiert nur die Entitäten, die zeigen, was sich geändert hat ([Aktualisierung](how-it-works.de.md#aktualisierung))
- Alle Regeln der Qualitätsskala von Home Assistant bis Platin, 100 % Testabdeckung

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/de/architecture-dark.png">
    <img src="images/de/architecture-light.png" alt="Architektur: Der Board Manager auf dem Board-PC sendet Echtzeitereignisse an die Autodarts-Integration in Home Assistant, die Entitäten, Board-Ereignisse, Karten und Automationen bereitstellt; die Autodarts-Cloud ist optional" width="480">
  </picture>
</p>

[Funktionsweise →](how-it-works.de.md)

## Voraussetzungen

**Home Assistant ab 2026.8** mit [HACS](https://hacs.xyz) und ein Autodarts-Board in deinem Netzwerk oder eine beliebige Dartscheibe, deren Darts du auf einem Tastenfeld eingibst ([Spielen ohne Autodarts](without-autodarts.de.md)). Ein Autodarts-Konto brauchst du nicht.

- **Board Manager 2**, also Autodarts 2 ohne Bildschirm, ist empfohlen und bis 2.0.2 getestet; der klassische **Board Manager 1** funktioniert auch.
- Laut dem Bericht eines Spielers funktioniert auch **Autodarts Desktop** 2.0.2 unter Linux.
- Autodarts Desktop unter Windows und die Winmau-Autodarts-Geräte wie Autodarts X oder Lens sind noch nicht getestet; ein [Kompatibilitätsbericht](https://github.com/Dennis-Otto/ha-autodarts/issues/new?template=board_compatibility.yml) hilft, ob es klappt oder nicht.

## Anleitungen

### Erste Schritte

- [Von null bis zur Anzeigetafel](getting-started.de.md): für Autodarts-Spieler ohne Home Assistant: Home Assistant und HACS aufsetzen, die Integration installieren, das Board hinzufügen und das erste Spiel auf der Anzeigetafel
- [Installation und Einrichtung](installation.de.md): Voraussetzungen, HACS und manuelle Installation, die Wege, ein Board hinzuzufügen, die optionale Cloud-Verknüpfung, Neukonfiguration, Updates und Entfernen
- [Spielen ohne Autodarts](without-autodarts.de.md): jede Dartscheibe mit allen Spielen, dem Training und den Statistiken: einrichten, die Darts auf einem Tastenfeld eingeben, und was anders ist

### Anleitungen

- [Spiele und Regeln](games.de.md): alle Spiele im Überblick, vier Wege, eines zu starten, Matches, Teams, Handicaps, das Ausbullen, die Match-Zusammenfassung, Turniere und die Regeln von X01, den Cricket-Spielen, den Partyspielen und den Trainingsspielen
- [Anzeigetafel am Board](scoreboard.de.md): ein Tablet oder Fernseher neben dem Board: Einrichtung, Quer- und Hochformat, Spielauswahl, Turniere, Caller und Ruhemodus
- [Statistik und Spieler](statistics.de.md): Trainingssessions, Bestleistungen, Trefferbild und Dart-Positionen, Fortschritt über die Zeit, Doubles, Spielerprofile, Erfolge, Trends, Bestenliste, Wochenbericht, Trainingskalender und Exporte
- [Automationen](automations.de.md): dreizehn Blueprints, ihre Einstellungen, Board-Ereignisse und fertige Beispiele
- [Online-Matches](online-matches.de.md): Überwerfen, gewonnene Legs und Matches von Online-Matches als Board-Ereignisse, mit der Browser-Erweiterung Tools for Autodarts *(experimentell)*

### Nachschlagen

- [Dashboard-Karten](cards.de.md): Live-Karte, Trainingskarte, Board-Status, Anzeigetafel, Doubles-Karte, Spielerkarte, Bestenliste und automatisches Dashboard, mit allen Optionen und Barrierefreiheit
- [Entitäten und Ereignisse](entities.de.md): alle Entitäten, Board-Ereignisse, Zustände, Attribute und Aktionen, und welche Board-Manager-Generation sie liefert
- [Funktionsweise](how-it-works.de.md): Architektur, Aktualisierung, Verbindungsverhalten, Board-Manager-Generationen, Adresswechsel, Training und Bestleistungen, gespeicherte Daten und Datenschutz
- [Fehlerbehebung](troubleshooting.de.md): Meldungen bei der Einrichtung, Reparaturen, nicht verfügbare Entitäten, fehlgeschlagene Aktionen, Diagnose und Logs
- [Sicherheit](security.de.md): Schutzgüter, Vertrauensgrenzen, Bedrohungen und Gegenmaßnahmen
- [Glossar](glossary.de.md): die Begriffe des Dartsports und dieser Integration, mit ihren englischen Entsprechungen

### Projekt

- [Änderungen](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md): was jede Version gebracht hat (auf Englisch)
- [Roadmap](roadmap.de.md): erschienene Versionen und was als Nächstes kommt
- [Development](development.md), [Releases](releases.md): die Entwickler-Dokumentation, auf Englisch
- [Bilder und Prüfungen der Karten](development.de.md): wie die Bilder der Dokumentation entstehen, der Screenshot-Bot, der Bildvergleich und die Prüfung der Barrierefreiheit, auf Deutsch
- [Creator-Kit](creator-kit.de.md): Fakten, Beschreibungen, Videos, Animationen und Bilder für YouTuber, Streamer und Blogger, frei nutzbar

## Anwendungsfälle

### Gezielt trainieren

Verfolge nach jeder Session deinen Average, deine 180er und wohin deine Darts fliegen, und lass dich von Tagesziel und Trainingsserie antreiben.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="images/de/training-card-light.png">
    <img src="images/de/training-card.png" alt="Trainingskarte mit 3-Dart-Average, Trefferbild, Statistik und letzten Aufnahmen" width="480">
  </picture>
</p>

[Statistik →](statistics.de.md)

### Ein Dartabend mit Freunden

Wähle das Spiel am Tablet neben dem Board oder starte ein Turnier, lass die Anzeigetafel zählen und ansagen, und sieh zwischen den Spielen Tabelle oder Bestenliste.

<p align="center"><img src="images/de/lobby.webp" alt="Animation: In der Spielauswahl des Tablets am Board wird ein Spiel gewählt und startet auf der Anzeigetafel" width="600"></p>

[Anzeigetafel →](scoreboard.de.md)

### Atmosphäre

Lichtshows für eine 180 oder ein gewonnenes Match, ein Dart-Caller auf deinen Lautsprechern und das Boardlicht bei der Entnahme.

<img src="images/de/blueprint-light-show.png" alt="Eine neue Automation aus dem Blueprint Light show mit einem Abschnitt für jeden Moment des Spiels" width="100%">

[Automationen →](automations.de.md)

### Highlights festhalten

Ein Foto des Boards nach jeder 180 oder jedem Checkout, auf dem Handy und in einer Galerie nach Monaten.

<img src="images/de/media-gallery.png" alt="Die Highlight-Galerie in der Medienansicht mit Fotos eines Checkouts und zweier hoher Aufnahmen" width="100%">

[Highlight-Galerie →](automations.de.md#highlight-galerie)

### Fortschritt über Monate

Langzeitgrafiken, ein Wochenbericht aufs Handy und ein Trainingskalender mit einem Jahr Sessions und Matches.

<p align="center"><img src="images/de/dashboard-trends.png" alt="Grafiken der Darts pro Tag, des 3-Dart-Averages und der Übungslegs über vier Wochen" width="480"></p>

[Fortschritt über die Zeit →](statistics.de.md#fortschritt-über-die-zeit)

### Ein Board, das sich selbst kümmert

Starte die Erkennung, wenn du den Dartraum betrittst, stoppe sie, wenn du gehst, und erfahre, wenn das Board offline geht oder eine Kamera ausfällt.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="images/de/status-card-light.png">
  <img src="images/de/status-card.png" alt="Board-Status-Karte mit Erkennung, Verbindungen, Board-PC und Kameras" width="100%">
</picture>

[Blueprints →](automations.de.md#blueprints)

## Blueprints

Importiere einen Blueprint mit einem Klick, wähle dein Board und fertig.

- **Light show.** Deine WLED-Presets oder Raumlichter bei einer 180, einem High Finish, beim Überwerfen, einem gewonnenen Leg oder Match, einer Bestleistung, einem Erfolg, dem Sieger eines Turniers und mehr, und danach zurück zu deinem normalen Licht.

  [![Blueprint „Light show“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Flight_show.yaml)

- **Dart caller.** Jede Aufnahme auf deinen Lautsprechern, mit einer eigenen Ansage für die 180.

  [![Blueprint „Dart caller“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fdart_caller.yaml)

- **Highlight photo.** Ein Bild des Boards nach einer 180 oder einem Checkout, aufs Handy und in eine Galerie der Medienansicht.

  [![Blueprint „Highlight photo“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fhighlight_photo.yaml)

<details>
<summary>Zehn weitere: Aufnahme feiern, Übungs-Caller, Entnahme, Erkennung, Routinen, Berichte, Warnungen und Sprache</summary>

- **Celebrate a visit score.** Deine Aktionen für jede 180, jede Aufnahme ab 100 oder eine Punktzahl deiner Wahl, sobald der dritte Dart landet.

  [![Blueprint „Celebrate a visit score“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fvisit_score.yaml)

- **Practice caller.** Wer was braucht, Überwerfen und Game shots des Übungsspiels auf deinen Lautsprechern.

  [![Blueprint „Practice caller“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fpractice_caller.yaml)

- **Takeout actions.** Licht am Board, während du die Darts ziehst.

  [![Blueprint „Takeout actions“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftakeout.yaml)

- **Start and stop detection automatically**, je nachdem, ob jemand im Dartraum ist.

  [![Blueprint „Start and stop detection automatically“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fauto_detection.yaml)

- **Training session routine.** Licht, Erkennung und Kalibrierung folgen deinen Trainingssessions.

  [![Blueprint „Training session routine“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftraining_session.yaml)

- **Weekly report.** Deine Trainingswoche mit dem Trend deines 3-Dart-Averages, als Benachrichtigung.

  [![Blueprint „Weekly report“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fweekly_report.yaml)

- **Training report.** Deine Tageszusammenfassung mit dem 3-Dart-Average.

  [![Blueprint „Training report“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftraining_report.yaml)

- **Board problem alert**, wenn das Board offline geht oder eine Kamera ausfällt, mit optionaler Entwarnung.

  [![Blueprint „Board problem alert“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fboard_alert.yaml)

- **Start a game by voice.** Sag Assist „Starte 501 für Alex und Sam“, auf Deutsch oder Englisch.

  [![Blueprint „Start a game by voice“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fstart_game_by_voice.yaml)

- **Enter darts by voice.** Sag Assist „Alex hat 140“, „Triple 20“ oder „Nächster Spieler“, wie am Dartautomaten, auf Deutsch oder Englisch.

  [![Blueprint „Enter darts by voice“ importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fenter_darts_by_voice.yaml)

</details>

Die Blueprints sind auf Englisch beschriftet; ihre Texte, etwa die Ansagen, wählst du beim Anlegen selbst. Die [Anleitung zu Automationen](automations.de.md) enthält deutsche Beispiele.

<!-- --8<-- [start:devices-and-languages] -->

## Unterstützte Geräte

| | Unterstützt | Getestet mit |
| --- | --- | --- |
| Board Manager 2: Autodarts 2 ohne Bildschirm (Headless) | 2.x | 2.0.0 und 2.0.2 |
| Board Manager 1 (klassische App) | 1.x | 1.0.7 |
| Autodarts Desktop unter Linux | Funktioniert laut Spielerbericht | 2.0.2 unter Ubuntu 24.04 ([Bericht](https://github.com/Dennis-Otto/ha-autodarts/issues/105)) |
| Autodarts Desktop unter Windows und anderen Systemen | Noch nicht getestet | – |
| Winmau-Autodarts-Geräte wie Autodarts X oder Lens | Noch nicht getestet | – |
| Kameras | Jede Anzahl, die der Board Manager unterstützt | 3 |
| Home Assistant | ab 2026.8 | 2026.8.0 und 2026.9.4 |

Jede Board-Hardware, auf der der Autodarts Board Manager läuft, funktioniert, weil die Integration mit dem Board Manager spricht, nicht mit den Kameras. Einträge „laut Spielerbericht“ hat ein Spieler an seinem eigenen Board getestet, nicht das Projekt.

Seit September 2026 beschreibt die Doku von Autodarts den Board Manager als Browser-Oberfläche von Autodarts 0.x, die ab Version 2 nicht mehr unterstützt wird. Die lokale Schnittstelle auf Port 3180, die die Integration nutzt, antwortet mit Autodarts 2.0.2 weiterhin. Ändert ein Update sie, zeigt die Integration eine Reparaturmeldung, statt still auszufallen (siehe [Fehlerbehebung](troubleshooting.de.md#reparaturen)). Läuft dein Setup nicht in der Tabelle, hilft ein [Kompatibilitätsbericht](https://github.com/Dennis-Otto/ha-autodarts/issues/new?template=board_compatibility.yml), auch wenn alles klappt.

## Sprachen

Die Integration spricht Deutsch, Englisch, Niederländisch, Französisch und Spanisch: Einrichtung, Optionen, Entitäten und ihre Zustände, Aktionen, Meldungen und Reparaturen, die Karten mit ihren Editoren und der Caller der Anzeigetafel. Sie folgt der Sprache von Home Assistant, eine regionale Variante wie `de-CH` oder `es-419` zählt zu ihrer Sprache. Andere Sprachen sehen Englisch.

- Die Namen der Entitäten legt Home Assistant in der Sprache des Servers fest (**Einstellungen → System → Allgemein**), Zustände und Karten folgen der Sprache deines Benutzerprofils.
- Der Caller spricht die Sprache der Karte mit einer Stimme deines Browsers oder Tablets für diese Sprache.
- Die Dokumentation gibt es auf Englisch und Deutsch, die Blueprints auf Englisch, weil Home Assistant Blueprints nicht übersetzt.

Texte, die in einer Sprache fehlen oder älter sind als ihr englisches Original, stehen im [Übersetzungs-Issue](https://github.com/Dennis-Otto/ha-autodarts/issues?q=is%3Aissue%20is%3Aopen%20label%3Atranslations) dieser Sprache, das ein Bot aktuell hält. Es erklärt, wie du sie direkt auf GitHub korrigierst, ganz ohne Programmierkenntnisse. Eine Übersetzung verbessern oder eine Sprache hinzufügen: [Übersetzungen in CONTRIBUTING.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CONTRIBUTING.md#translations).

<!-- --8<-- [end:devices-and-languages] -->

## Bekannte Einschränkungen

- **Cloud-Spieldaten sind noch nicht verfügbar.** Sie brauchen eine OAuth-Client-ID, die Autodarts für diese Integration vergibt, und noch ist keine enthalten. Alles Lokale funktioniert ohne sie.
- **Online-Matches über eine Browser-Erweiterung.** Überwerfen und Game shots von Online-Matches kommen nur an, solange die Autodarts-Seite mit Tools for Autodarts offen ist, einer Erweiterung von Dritten. [Grenzen](online-matches.de.md#grenzen).
- **Trainingssessions zählen Darts, keine Spiele.** Eine Session zählt jeden Dart, den das Board erkennt; Spieler, Legs und Checkouts gehören zum Übungsspiel, das seine eigene Statistik führt.
- **Board-Manager-Updates installierst du auf dem Board-PC.** Die Update-Entität meldet neue Versionen von Board Manager 2.
- **Liveansicht der Kameras nur mit Board Manager 2.** Mit Board Manager 1 zeigen die Kamera-Entitäten Standbilder.

## Hilfe und Mitmachen

- **Fragen und Ideen:** [GitHub Discussions](https://github.com/Dennis-Otto/ha-autodarts/discussions), gern auf Deutsch. **Fehler:** [Issues](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose), mit den Diagnosedaten deines Boards. [SUPPORT.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/SUPPORT.md) erklärt, wo du was fragst.
- **Ausprobiert?** Ein [Erfahrungsbericht](https://github.com/Dennis-Otto/ha-autodarts/issues/new?template=tester_report.yml) sagt uns, was geklappt hat, was nicht und was dir fehlt; kurze Antworten genügen, gern auf Deutsch.
- **Du sprichst Deutsch, Niederländisch, Französisch oder Spanisch?** Die [Übersetzungs-Issues](https://github.com/Dennis-Otto/ha-autodarts/issues?q=is%3Aissue%20is%3Aopen%20label%3Atranslations) nennen die Texte, die in deiner Sprache fehlen oder veraltet sind, und wie du sie im Browser korrigierst, ganz ohne Programmierkenntnisse.
- **Sicherheit:** Melde Schwachstellen vertraulich, wie in [SECURITY.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/SECURITY.md) beschrieben.
- **Zeigen:** Für Videos und Artikel gibt es ein [Creator-Kit](creator-kit.de.md) mit Fakten, Videos und Bildern zur freien Verwendung.
- **Mitmachen:** Beiträge sind willkommen; [CONTRIBUTING.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CONTRIBUTING.md) erklärt die Prüfungen. Die Mitarbeit folgt dem [Verhaltenskodex](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CODE_OF_CONDUCT.md) und der [Governance](https://github.com/Dennis-Otto/ha-autodarts/blob/main/GOVERNANCE.md) des Projekts.

## Qualität und Sicherheit

[![CodeQL](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/codeql.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/codeql.yml)
[![Secret scan](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/secret-scan.yml)
[![SBOM](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/sbom.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/sbom.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Dennis-Otto/ha-autodarts/badge)](https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/ha-autodarts)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/14935/badge)](https://www.bestpractices.dev/projects/14935)

- Erfüllt jede Regel der [Qualitätsskala für Home-Assistant-Integrationen](https://developers.home-assistant.io/docs/core/integration-quality-scale/) bis Platin ([Selbstbewertung](https://github.com/Dennis-Otto/ha-autodarts/blob/main/custom_components/autodarts/quality_scale.yaml)), einschließlich strikter Typisierung.
- 100 % Zeilen- und Zweigabdeckung der Integration, Fuzz-Tests der Karten, ein Docker-End-to-End-Test gegen beide Board-Manager-Generationen und das älteste unterstützte Home Assistant, ein echter Browsertest jeder Karte und wöchentliche [Mutationstests](development.de.md#mutationstests) der Spielregeln. [Entwicklung](development.md) (englisch).
- Signierte Release-Pakete mit SLSA-Herkunftsnachweis. [Releases](releases.md#signed-release-packages) (englisch).

## Herkunft und Lizenz

Diese Integration begann als Fork von [Trkal/HACSAutodarts](https://github.com/Trkal/HACSAutodarts), einem cloudbasierten Prototyp vom April 2026. Seit September 2026 ist sie neu geschrieben und wird unabhängig von [@Dennis-Otto](https://github.com/Dennis-Otto) gepflegt: lokale Echtzeitsteuerung für beide Board-Manager-Generationen, Spiele, Trainingsauswertung, Dashboard-Karten, Blueprints, Tests und Dokumentation. Beide nutzen die Domain `autodarts`; die [Installationsanleitung](installation.de.md#von-der-ursprünglichen-integration-umsteigen) erklärt den Wechsel. Danke an Trkal für die ursprüngliche Arbeit und an das Autodarts-Team für seine offene lokale Schnittstelle.

Lizenziert unter der [MIT-Lizenz](https://github.com/Dennis-Otto/ha-autodarts/blob/main/LICENSE). Namen und Markengrafiken von Autodarts und Winmau gehören ihren Inhabern; die mitgelieferten Markenbilder kennzeichnen das unterstützte Produkt und fallen nicht unter die MIT-Lizenz. Dies ist eine inoffizielle Community-Integration ohne Verbindung zu Autodarts.
