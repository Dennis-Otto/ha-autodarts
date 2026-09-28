# Roadmap

[← Dokumentation](README.md) · [English](../roadmap.md)

Diese Roadmap zeigt, was jede Version gebracht hat, was das nächste Release bringt und was danach kommt. Sie ist eine Richtung, kein Versprechen: Die Prioritäten richten sich nach den Rückmeldungen der Spieler, die Termine nach der verfügbaren Freizeit. Ideen und Stimmen sind als [Funktionswunsch](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose) willkommen.

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

- Cricket für einen bis vier Spieler mit Marks, geschlossenen Zahlen, Punkten und Marks pro Runde sowie einer Kreidetafel in der Live-Karte.
- Eine Anzeigetafel als Karte und als Vollbild-Ansicht für einen Bildschirm am Board, lesbar vom Abwurf aus.
- Bestleistungen mit einem Ereignis, sobald eine fällt, eine Trainingsserie in Tagen und ein Tagesziel.
- `autodarts.start_game` startet X01, Cricket oder ein Trainingsspiel mit Spielern, Namen und Format in einer Aktion.
- Erkennungsqualität: der Anteil korrigierter Darts, mit einer Reparatur, die das Board nachkalibriert, wenn er steigt.

## Version 1.5: Partyspiele, Spielerprofile, Doubles und ein Caller

- Shanghai, Halve-It und Killer für einen bis vier Spieler; X01 von 101 bis 1001 mit Double-In und Ausbullen.
- Spielerprofile mit Statistik und Bestleistungen pro Name, Match-Verlauf und direkten Vergleichen sowie eine Spielerkarte.
- Eine Doppelanalyse mit der Quote jedes Doubles, eine Doubles-Karte und persönliche Checkout-Wege.
- Ein Caller in der Anzeigetafel, der das Spiel über den Browser ansagt, standardmäßig aus.
- `autodarts.delete_player` löscht ein Spielerprofil, etwa nach einem Tippfehler im Namen.

## Version 1.6: mehr Spiele, eine Spielauswahl, Berichte und Online-Matches

Erschienen als 1.6.0 am 27. September 2026; die Details stehen im [Changelog](../../CHANGELOG.md#160) (auf Englisch).

| Thema | Was es bringt | Stand |
| --- | --- | --- |
| **Mehr Spiele** | Cut-Throat Cricket, Tactics, Golf, Baseball und Count-Up; die Trainingsspiele 121-Checkout, Catch 40, JDC Challenge und Singles-Training | Fertig |
| **Handicap und Teams** | Unterschiedliche X01-Startpunkte pro Spieler im selben Match, etwa 501 gegen 301, und zwei Teams zu zwei bei X01 und den Cricket-Spielen | Fertig |
| **Offizielle Regeln** | Satzfolge der PDC, Match-Ergebnisse wie 3:2, Checkout-Wege wie in den Tabellen der Profis, Ausbullen nach den Regeln von WDF und PDC | Fertig |
| **Eine Anzeigetafel, die Spiele startet** | Eine Spielauswahl am Board, ein Ruhemodus mit Bestenliste und die Bilder von Spielern, die mit Personen von Home Assistant verknüpft sind | Fertig |
| **Berichte** | Ein Wochenbericht mit Blueprint, ein Trainingskalender über ein Jahr und Exporte als CSV oder JSON | Fertig |
| **Highlights und Licht** | Eine Highlight-Galerie in der Medienansicht und ein Blueprint für Lichtshows | Fertig |
| **Online-Matches** *(experimentell)* | Überwerfen, gewonnene Legs und Matches von Online-Matches über die Browser-Erweiterung Tools for Autodarts | Fertig |
| **Turniermodus** | Jeder gegen jeden oder K.-o. für drei bis acht benannte Spieler an einem Board: Tabelle oder Turnierbaum auf der Anzeigetafel, das nächste Match startet von selbst, und die Ergebnisse fließen in die Spielerprofile | Fertig |
| **Match-Zusammenfassung** | Averages, Checkout-Quote, höchster Checkout, 180er und bestes Leg jedes Spielers nach einem Match, auf der Anzeigetafel, der Live-Karte und in `match_won` | Fertig |
| **Erfolge** | Meilensteine pro Spieler in Stufen, etwa die erste 180, ein Checkout ab 100, ein Neun-Darter oder eine Serie von zehn Tagen, jeweils mit einem Ereignis und als Abzeichen | Fertig |
| **Trends und Trefferbilder pro Spieler** | Average, Checkout-Quote und Doppelquote pro Woche als Verlauf, das eigene Trefferbild jedes Spielers und eine Bestenliste mit den Rekorden aller Spieler | Fertig |
| **Trefferbild der Dart-Positionen** | Ein Trefferbild, das zeigt, wo jeder Dart gelandet ist, aus den Positionen, die das Board meldet, mit der Streuung in Millimetern; die Karte wechselt zwischen Feldern, Zahlen und Positionen | Fertig |
| **Ein Bot und Korrekturen** | Ein Bot mit Stärke 20 bis 120 bei X01 und den Cricket-Spielen, Korrekturen mit einem Tipp, von Hand eingegebene Darts per Tastenfeld, das Zurücknehmen der letzten Aufnahme und Stellwürfe, wo kein Checkout möglich ist | Fertig |
| **Niederländisch, Französisch und Spanisch** | Die Integration, die Karten und der Caller in drei weiteren Sprachen, mit Tests, die jede Sprache vollständig halten | Fertig |
| **Dokumentation** | Bebilderte Anleitungen zu Spielen, zur Anzeigetafel und zur Statistik, ein Glossar und ein Abschnitt zur Barrierefreiheit | Fertig |

## Version 1.7: Dart-Positionen, auf die du dich verlassen kannst

Erschienen als 1.7.0 am 28. September 2026; die Details stehen im [Changelog](../../CHANGELOG.md#170) (auf Englisch).

- Das Positionen-Trefferbild der Trainingskarte folgt jedem Dart live.
- Korrigierte Darts verlieren die falsch erkannte Position des Boards, oder sie bekommen die Stelle, die du auf der Scheibe der Anzeigetafel antippst, und damit gleich das Feld.

## Als Nächstes

Ideen für die Versionen nach 1.7. Stimmen und Reaktionen auf die [Feature-Wünsche](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose) bestimmen die Reihenfolge.

| Thema | Was es bringt | Voraussetzung |
| --- | --- | --- |
| **Sprachsteuerung mit Assist** | „Starte 501 für Alex und Sam“, „Wie ist mein Average heute?“ als eigene Sätze, ohne Automation | Sätze in jeder Sprache der Integration, die sich am Board natürlich anfühlen |
| **Autodarts Desktop** | Boards mit Autodarts Desktop prüfen und dokumentieren, was funktioniert | Testberichte von Spielern, die es nutzen |
| **Cloud-Verknüpfung** | Cloud-Spieldaten und Cloud-Spielereignisse: Leg und Match gewonnen, Überwerfen, Spielerwechsel, Restpunkte | Eine OAuth-Client-ID von Autodarts; sie ist beantragt |
| **HACS-Standardkatalog** | Installation, ohne ein benutzerdefiniertes Repository hinzuzufügen | Im September 2026 beantragt ([hacs/default#11306](https://github.com/hacs/default/pull/11306)); die Prüfung bei HACS dauert mehrere Monate |
| **Weitere Sprachen** | Integration und Karten in weiteren Sprachen | Beiträge von Muttersprachlern ([so kommt eine Sprache dazu](../../CONTRIBUTING.md#translations)) |

## Später

| Thema | Voraussetzung |
| --- | --- |
| **Protokoll-Bibliothek auf PyPI** (`aioautodarts`) | Eine eigene Bibliothek für das Board-Manager-Protokoll, Voraussetzung für einen möglichen Weg in den Home-Assistant-Kern; zurückgestellt, bis das Protokoll sich gesetzt hat |

## So werden Prioritäten gesetzt

1. Alles, was bei Nutzern kaputtgeht, auch durch neue Board-Manager-Versionen, kommt zuerst.
2. Lokale Funktionen kommen vor Cloud-Funktionen.
3. Danach Wünsche mit den meisten Reaktionen auf GitHub.
