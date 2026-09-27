# Glossar

[← Dokumentation](README.md) · [English](../glossary.md)

Die Begriffe des Dartsports und dieser Integration, wie sie die Dokumentation, die Entitäten und die Karten verwenden. Die letzte Spalte nennt den englischen Begriff der [englischen Dokumentation](../glossary.md) und der englischen Oberfläche.

## Darts

| Begriff | Bedeutung | Englisch |
| --- | --- | --- |
| **Feld** | Ein Bereich der Scheibe, der Punkte bringt: Single, Double oder Triple einer Zahl, das Single-Bull oder das Bullseye | Bed |
| **Single, Double, Triple** | Die Felder einer Zahl, die einfach, doppelt oder dreifach zählen. Englische Caller sagen *Treble* für Triple. | Single, double, triple |
| **Single-Bull, Bullseye** | Der äußere Ring des Bulls (25 Punkte) und seine Mitte (50 Punkte, ein Double) | Outer bull, bullseye |
| **Fehlwurf** | Ein Dart außerhalb der Punktefelder | Miss |
| **Aufnahme** | Bis zu drei Darts nacheinander, bis sie gezogen werden | Visit |
| **Entnahme** | Das Ziehen der Darts aus dem Board; sie beendet die Aufnahme | Takeout |
| **Abwurf** | Die Abwurflinie | Oche |
| **Leg, Satz, Match** | Ein Leg ist ein Spiel bis null; Legs gewinnen einen Satz, Sätze das Match | Leg, set, match |
| **X01** | 101, 301, 501, 701, 901 oder 1001, genau auf null heruntergezählt | X01 |
| **Double-Out, Double-In** | Ein Leg muss auf einem Double oder dem Bullseye enden oder zu zählen beginnen | Double out, double in |
| **Checkout** | Die Darts, die ein Leg beenden; der **Checkout-Weg** ist der Weg dorthin, etwa `T20 T19 D12` für 141 | Checkout, checkout route |
| **Überwerfen** | Ein Dart, der unter null geht, mit Double-Out 1 übrig lässt oder 0 ohne Double erreicht; die Aufnahme zählt nichts | Bust |
| **Game shot** | Der Dart, der ein Leg gewinnt | Game shot |
| **Ausbullen** | Ein Dart pro Spieler aufs Bull, der entscheidet, wer beginnt | Bull-off |
| **Marks** | Bei Cricket die Treffer auf eine Zahl: ein Single ist ein Mark, ein Double zwei, ein Triple drei | Marks |
| **Marks pro Runde (MPR)** | Die zählenden Cricket-Marks pro drei Darts | Marks per round (MPR) |
| **3-Dart-Average** | Punkte pro drei Darts, das übliche Maß für einen Spieler | 3-dart average |
| **First-9-Average** | Der 3-Dart-Average der ersten neun Darts eines Legs | First 9 average |
| **Checkout-Quote** | Gewonnene Legs pro Dart aufs Double | Checkout rate |
| **Doppelquote** | Treffer pro Dart aufs Double, auch im Doppeltraining und bei Bob's 27 | Doubles rate |
| **Handicap, Startpunkte** | Eigene Punkte eines Spielers, mit denen er X01 beginnt, etwa 301 gegen 501 | Handicap, start score |
| **100+, 140+, 180** | Eine Aufnahme mit 100 oder mehr, mit 140 oder mehr und das Maximum aus drei Triple 20 | Ton, ton-plus, 180 |

## Die Integration

| Begriff | Bedeutung | Englisch |
| --- | --- | --- |
| **Board Manager** | Die Software von Autodarts auf dem Board-PC, die die Darts erkennt; Generation 1 ist die klassische App, Generation 2 läuft headless | Board Manager |
| **Erkennung** | Die Dart-Erkennung des Board Managers mit den Kameras; sie lässt sich starten, stoppen, zurücksetzen und kalibrieren | Detection |
| **Erkennungsstatus** | Was das Board gerade tut: bereit zum Werfen, Entnahme, gestoppt, Kalibrierung und so weiter | Detection status |
| **Board-Ereignisse** | Die Momente des Spiels für Automationen, vom erkannten Dart bis zum gewonnenen Match, über die Entität *Ereignisse* | Board events, *Events* entity |
| **Trainingssession** | Die Darts eines Trainings, gezählt von seinem Beginn bis zu seinem Ende, egal was du spielst | Training session |
| **Übungsspiel** | Ein Spiel, das Home Assistant am lokalen Board zählt: X01, ein Cricket-Spiel, ein Partyspiel oder ein Trainingsspiel | Practice game |
| **Cricket-Spiele** | Cricket, Cut-Throat Cricket und Tactics | Cricket games |
| **Partyspiele** | Shanghai, Halve-It, Killer, Golf, Baseball und Count-Up | Party games |
| **Trainingsspiele** | Around the Clock, Doppeltraining, Checkout-Training, Bob's 27, 121-Checkout, Catch 40, JDC Challenge und Singles-Training | Training games |
| **Team-Match** | Vier Spieler bei X01 oder einem Cricket-Spiel als zwei Teams: 1 und 3 gegen 2 und 4 | Team match |
| **Bestleistung** | Der beste Wert einer Kategorie, etwa der höchste Checkout, pro Board und pro Spieler | Personal best |
| **Trainingsserie** | Tage in Folge mit mindestens einem Dart | Training streak |
| **Tagesziel** | Die Darts, die du jeden Tag werfen willst | Daily goal |
| **Spielerprofil** | Statistik und Bestleistungen eines Spielers mit Namen über seine ganze Zeit | Player profile |
| **Direkter Vergleich** | Die Siege zweier Spieler gegeneinander | Head-to-head |
| **Lieblingsdouble** | Das Double mit deiner besten Quote, unter denen mit mindestens 10 Darts | Favorite double |
| **Trefferbild** | Die Scheibe, eingefärbt danach, wie oft jedes Feld getroffen wurde; auch Heatmap | Heatmap, hit map |
| **Wochenbericht** | Die Summe einer Trainingswoche, gemeldet, wenn die Woche endet | Weekly report |
| **Trainingskalender** | Sessions und Matches des letzten Jahres im Kalender von Home Assistant | Training calendar |
| **Live-Karte** | Die Karte mit der aktuellen Aufnahme auf einer Live-Dartscheibe | Live card |
| **Anzeigetafel** | Die Karte für ein Tablet oder einen Fernseher am Board | Scoreboard |
| **Spielauswahl** | Der Bildschirm der Anzeigetafel, auf dem du Spiel, Spieler und Format wählst | New game screen |
| **Ruhemodus** | Die Tafeln, die die Anzeigetafel zwischen den Spielen zeigt | Idle mode |
| **Caller** | Die Stimme, die das Spiel ansagt: der Caller der Anzeigetafel im Browser oder die Caller-Blueprints auf deinen Lautsprechern | Caller |
| **Automatisches Dashboard** | Das Dashboard, das die Integration für jedes Board baut | Automatic dashboard |
| **Highlight-Galerie** | Die Fotos des Blueprints Highlight photo in der Medienansicht | Highlight gallery |
| **Online-Brücke** | Die optionale Verbindung, die Momente von Online-Matches aus der Browser-Erweiterung Tools for Autodarts nach Home Assistant bringt | Online bridge |
| **Blueprint** | Eine fertige Automation zum Importieren und Ausfüllen | Blueprint |

## Schreibweisen

- Die deutsche Dokumentation spricht dich mit *du* an; die englische nutzt amerikanische Schreibweise.
- Entitätsnamen stehen *kursiv*, so wie die Oberfläche sie zeigt; Entitäts-IDs, Attribute, Ereignistypen und Optionen stehen als `Code`.
- Tasten und Menüpunkte stehen **fett**, mit Pfeilen für einen Weg: **Einstellungen → Geräte & Dienste**.
- Die Blueprints sind auf Englisch beschriftet; die deutsche Dokumentation nennt ihre englischen Namen und Einstellungen.
