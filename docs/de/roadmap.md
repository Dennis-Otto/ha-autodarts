# Roadmap

[← Übersicht](README.md) · [English](../roadmap.md)

Diese Roadmap zeigt, was jede Version gebracht hat und was als Nächstes kommt. Sie ist eine Richtung, kein Versprechen: Die Prioritäten richten sich nach den Rückmeldungen der Spieler, die Termine nach der verfügbaren Freizeit. Ideen und Stimmen sind als [Funktionswunsch](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose) willkommen.

## Version 1.0: das lokale Fundament

Enthalten, alles ohne Autodarts-Cloud:

- Lokale Echtzeitverbindung zu Board Manager 1 und 2 mit automatischer Erkennung.
- Steuerung, Board-Einstellungen, Kamerazustand und Board-Manager-Updates.
- Trainingsanalyse mit Treffern pro Feld, Aufnahmeverlauf und dem Ereignis `visit_completed`.
- Drei Dashboard-Karten, ein automatisches Dashboard und sechs Blueprints.
- Dokumentation auf Englisch und Deutsch.

## Version 1.1: Trainingssessions

- Trainingssessions, die mit dem ersten Dart oder bewusst beginnen, nach einer Pause enden und eine Übersicht der letzten 20 Sessions behalten.
- Die Ereignisse `session_started` und `session_ended` und ein siebter Blueprint, der Licht, Erkennung und Kalibrierung an die Session koppelt.
- Die letzten Aufnahmen in der Live-Karte, Sessionstatus und vergangene Sessions in der Trainingskarte.
- Details zum Board-PC aus Board Manager 2: Betriebssystem, Prozessor und Erkennungssoftware.

## Version 1.2: Übungsspiele und Live-Kameras

- X01-Übungsspiele (301, 501, 701) am lokalen Board: Restpunkte, Überwerfen, Double-Out, Checkout-Wege und die letzten 10 Legs, mit den Ereignissen `bust` und `leg_won`.
- Ein Übungsspiel-Bereich in der Live-Karte mit Checkout-Weg und nächstem Zielfeld sowie die Steuerung des Übungsspiels im automatischen Dashboard.
- Live-Kamerastreams von Board Manager 2 statt Standbildern.
- Kamerazustand direkt nach dem Start oder Stopp der Erkennung statt erst nach der nächsten Abfrage.

## Version 1.3: Matches, Trainingsspiele und Statistik

- X01-Matches für zwei bis vier Spieler an einem Board: Nach dem Ziehen der Darts ist der Nächste dran, mit Legs, Sätzen, Spielernamen und Anzeigetafel in der Live-Karte.
- Trainingsspiele: Around the Clock, Doppeltraining, Checkout-Training und Bob's 27, mit umrandetem Ziel auf der Scheibe.
- Übungsstatistik: First-9-Average, Checkout-Quote, Doppelquote und Legs pro Tag.
- Zwei Blueprints: ein Übungs-Caller und ein Highlight-Foto nach einer 180 oder einem Checkout.

## Version 1.4: Cricket, Anzeigetafel und Bestleistungen

- Cricket für einen bis vier Spieler mit Treffern, geschlossenen Zahlen, Punkten und Treffern pro Runde sowie einer Kreidetafel in der Live-Karte.
- Eine Anzeigetafel als Karte und als Vollbild-Ansicht für einen Bildschirm am Board, lesbar vom Abwurf aus.
- Bestleistungen mit einem Ereignis, sobald eine fällt, eine Trainingsserie in Tagen und ein Tagesziel.
- `autodarts.start_game` startet X01, Cricket oder ein Trainingsspiel mit Spielern, Namen und Format in einer Aktion.
- Erkennungsqualität: der Anteil korrigierter Darts, mit einer Reparatur, die das Board nachkalibriert, wenn er steigt.

## Version 1.5: Partyspiele, Spielerprofile, Doppel und ein Caller

- Shanghai, Halve-It und Killer für einen bis vier Spieler; X01 von 101 bis 1001 mit Double-In und Ausbullen.
- Spielerprofile mit Statistik und Bestleistungen pro Name, Match-Verlauf und direkten Vergleichen sowie eine Spielerkarte.
- Eine Doppelanalyse mit der Quote jedes Doubles, eine Doppelkarte und persönliche Checkout-Wege.
- Ein Caller in der Anzeigetafel, der das Spiel über den Browser ansagt, standardmäßig aus.

## Als Nächstes: 1.6

| Thema | Was es bringt |
| --- | --- |
| **Turniermodus** | Jeder gegen jeden oder K.-o. für drei bis acht benannte Spieler an einem Board: Tabelle oder Turnierbaum auf der Anzeigetafel, das nächste Match startet von selbst, und die Ergebnisse fließen in die Spielerprofile |
| **Erfolge** | Meilensteine pro Spieler, etwa die erste 180, ein Checkout über 100, ein Neun-Darter oder eine Serie von zehn Tagen, jeweils mit einem Ereignis und auf einer Abzeichen-Karte |
| **Trends und Trefferbilder pro Spieler** | Average, Checkout-Quote und Doppelquote pro Woche als Verlauf und das eigene Trefferbild jedes Spielers in der Spielerkarte |
| **Trefferbild der Dart-Positionen** | Ein Trefferbild, das zeigt, wo jeder Dart gelandet ist, aus den Positionen, die das Board meldet; die Karte wechselt zwischen Feldern, Zahlen und Positionen |
| **Handicap-Start** | Unterschiedliche X01-Startwerte pro Spieler im selben Match, etwa 501 gegen 301 |
| **Niederländisch, Französisch und Spanisch** | Die Integration, die Karten und der Caller in drei weiteren Sprachen, mit Tests, die jede Sprache vollständig halten |

## Später

| Thema | Voraussetzung |
| --- | --- |
| **Cloud-Spielereignisse:** Leg und Match gewonnen, Überwerfen, Spielerwechsel, Restpunkte | Eine OAuth-Client-ID von Autodarts; sie ist beantragt |
| **HACS-Standardkatalog** | Im September 2026 beantragt ([hacs/default#11306](https://github.com/hacs/default/pull/11306)); die Prüfung bei HACS dauert mehrere Monate |
| **Weitere Sprachen** | Beiträge von Muttersprachlern ([so kommt eine Sprache dazu](../../CONTRIBUTING.md#translations)) |
| **Protokoll-Bibliothek auf PyPI** | Eine eigene Bibliothek für das Board-Manager-Protokoll; Voraussetzung für einen möglichen Weg in den Home-Assistant-Kern |

## So werden Prioritäten gesetzt

1. Alles, was bei Nutzern kaputtgeht, auch durch neue Board-Manager-Versionen, kommt zuerst.
2. Lokale Funktionen kommen vor Cloud-Funktionen.
3. Danach Wünsche mit den meisten Reaktionen auf GitHub.
