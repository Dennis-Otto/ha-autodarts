# Glossary

[← Documentation](README.md) · [Deutsch](de/glossar.md)

The words of darts and of this integration, as the documentation, the entities and the cards use them. The last column names the German term of the [German documentation](de/glossar.md) and the German user interface.

## Darts

| Term | Meaning | German |
| --- | --- | --- |
| **Bed** | One scoring area of the board: a single, double or triple of a number, the outer bull or the bullseye | Feld |
| **Single, double, triple** | The beds of a number worth one, two or three times its value. Callers say *treble* for a triple. | Single, Double, Triple |
| **Outer bull, bullseye** | The outer ring of the bull (25 points) and its center (50 points, a double) | Single-Bull, Bullseye |
| **Miss** | A dart outside the scoring area | Fehlwurf |
| **Visit** | Up to three darts thrown in a row, until the darts are pulled | Aufnahme |
| **Takeout** | Pulling the darts from the board; it ends the visit | Entnahme |
| **Oche** | The throwing line | Abwurf |
| **Leg, set, match** | A leg is one game to zero; legs win a set, sets win the match | Leg, Satz, Match |
| **X01** | 101, 301, 501, 701, 901 or 1001 counted down to exactly zero | X01 |
| **Double out, double in** | A leg must end, or start scoring, on a double or the bullseye | Double-Out, Double-In |
| **Checkout** | The darts that finish a leg; the **checkout route** is the way to do it, for example `T20 T19 D12` for 141 | Checkout, Checkout-Weg |
| **Bust** | A dart that goes below zero, leaves 1 with double out, or reaches zero without a double; the visit counts nothing | Überwerfen |
| **Game shot** | The dart that wins a leg | Game shot |
| **Bull-off** | One dart per player at the bull to decide who throws first | Ausbullen |
| **Marks** | In Cricket, the hits on a number: a single is one mark, a double two, a triple three | Marks |
| **MPR** | Marks per round: the Cricket marks that counted, per three darts | Marks pro Runde (MPR) |
| **3-dart average** | Points per three darts, the usual measure of a player | 3-Dart-Average |
| **First 9 average** | The 3-dart average of the first nine darts of a leg | First-9-Average |
| **Checkout rate** | Legs won per dart thrown at a double | Checkout-Quote |
| **Doubles rate** | Hits per dart thrown at a double, also in the doubles training and Bob's 27 | Doppelquote |
| **Handicap, start score** | A score of a player's own to start X01 from, such as 301 against 501 | Handicap, Startpunkte |
| **Setup, leave** | Darts that cannot finish but leave a good score for the next visit, such as T20 T20 S17 to leave 32 on D16 | Stellwurf, Rest |
| **Ton, ton-plus, ton-forty, 180** | A visit of 100, of more than 100, of 140 or more, and the maximum of three triple 20s. The statistics count visits of 100 to 139 as 100+ and of 140 to 179 as 140+ | 100+, 140+, 180 |

## The integration

| Term | Meaning | German |
| --- | --- | --- |
| **Board Manager** | The software of Autodarts on the board PC that detects the darts; generation 1 is the classic app, generation 2 is Autodarts 2 without a screen (headless). Autodarts Desktop and the Winmau Autodarts devices have not been tested yet | Board Manager |
| **Detection** | The Board Manager's dart detection with the cameras; it can be started, stopped, reset and calibrated | Erkennung |
| **Detection status** | What the board does: ready to throw, takeout, stopped, calibrating and so on | Erkennungsstatus |
| **Board events** | The moments of the game for automations, from a detected dart to a won match, through the *Events* entity | Board-Ereignisse, Entität *Ereignisse* |
| **Training session** | The darts of one training, counted from its start to its end, whatever you play | Trainingssession |
| **Practice game** | A game Home Assistant counts on the local board: X01, a Cricket game, a party game or a training game | Übungsspiel |
| **Cricket games** | Cricket, Cut-Throat Cricket and Tactics | Cricket-Spiele |
| **Party games** | Shanghai, Halve-It, Killer, Golf, Baseball and Count-Up | Partyspiele |
| **Training games** | Around the Clock, doubles training, checkout training, Bob's 27, 121 checkout, Catch 40, JDC Challenge and singles training | Trainingsspiele |
| **Team match** | Four players of X01 or a Cricket game as two teams: 1 and 3 against 2 and 4 | Team-Match |
| **Match summary** | The numbers of every player after a match: averages, checkout rate, highest checkout, 180s and the best leg | Match-Zusammenfassung |
| **Bot** | A computer player for X01 and the Cricket games; its level is the 3-dart average it plays | Bot |
| **Darts entered by hand** | Darts added in Home Assistant, with the scoreboard's keypad or an action, as if the board had detected them | Von Hand eingegebene Darts |
| **Tournament** | Three to eight players in a round robin or a knockout, one match at a time | Turnier |
| **Round robin** | Everyone plays everyone once; a table ranks the players | Jeder gegen jeden |
| **Knockout** | The winners go on through a bracket until the final | K.-o.-System |
| **Bracket, bye, seed** | The tree of a knockout; a free pass into the next round; a player's place in the draw | Turnierbaum, Freilos, Setzliste |
| **Personal best** | The best value of a record, such as the highest checkout, kept per board and per player | Bestleistung |
| **Training streak** | Days in a row with at least one dart | Trainingsserie |
| **Daily goal** | The darts you want to throw every day | Tagesziel |
| **Player profile** | The lifetime statistics and personal bests of a named player | Spielerprofil |
| **Head-to-head** | The wins of two players against each other | Direkter Vergleich |
| **Achievement, badge** | A milestone of a player in tiers of bronze, silver, gold and platinum, shown as a badge | Erfolg, Abzeichen |
| **Dart positions** | Where the darts really landed, as the board reports it | Dart-Positionen |
| **Grouping** | How closely a player's darts land around the bed they aimed at, in millimeters | Streuung |
| **Leaderboard** | The records of all players on the leaderboard card, or the best players by average in idle mode | Bestenliste |
| **Favorite double** | The double with your best hit rate, among those with at least 10 darts | Lieblingsdouble |
| **Heatmap** | The board colored by how often each bed was hit; the card calls it *hit map* | Trefferbild |
| **Weekly report** | The sum of a training week, announced when the week ends | Wochenbericht |
| **Training calendar** | Sessions and matches of the last year in Home Assistant's calendar | Trainingskalender |
| **Live card** | The card with the current visit on a live dartboard | Live-Karte |
| **Scoreboard** | The card for a tablet or TV at the board | Anzeigetafel |
| **New game screen** | The scoreboard's screen to choose the game, the players and the format | Spielauswahl |
| **Idle mode** | The panels the scoreboard shows between games | Ruhemodus |
| **Caller** | The voice that calls the game: the scoreboard's caller in the browser, or the caller blueprints on your speakers | Caller |
| **Automatic dashboard** | The dashboard the integration builds for every board | Automatisches Dashboard |
| **Highlight gallery** | The photos of the highlight photo blueprint in the media browser | Highlight-Galerie |
| **Online bridge** | The optional link that brings moments of online matches from the browser extension Tools for Autodarts into Home Assistant | Online-Brücke |
| **Blueprint** | A ready-made automation to import and fill in | Blueprint |

## Writing conventions

- The English documentation uses US spelling; the German documentation addresses the reader as *du*.
- Entity names appear in *italics*, as the user interface shows them; entity IDs, attributes, event types and options appear as `code`.
- Buttons and menu items appear in **bold**, with arrows for a path: **Settings → Devices & services**.
