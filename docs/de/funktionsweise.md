# Funktionsweise

[← Übersicht](README.md) · [English](../how-it-works.md)

## Architektur

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../images/de/architecture-dark.png">
  <img src="../images/de/architecture-light.png" alt="Architektur: Der Board Manager auf dem Board-PC sendet Echtzeitereignisse an die Autodarts-Integration in Home Assistant. Sie liest und steuert das Board per HTTP, speichert die Trainingssession lokal und stellt Entitäten, Board-Ereignisse, Karten und Automationen bereit; die Autodarts-Cloud liefert optional Spieldaten." width="560">
</picture>

Ein Board ist ein Integrationseintrag mit bis zu zwei unabhängigen Verbindungen:

- **Lokal** (empfohlen): direkt zum Board Manager in deinem Netzwerk. Ohne Anmeldung; liefert Steuerung, Echtzeitereignisse und Training.
- **Cloud** (optional): Spieldaten von Autodarts. Fällt sie aus, läuft die lokale Steuerung weiter, und umgekehrt.

## Aktualisierung

| Quelle | Wie | Intervall |
| --- | --- | --- |
| Board-Zustand, Dart-Positionen, Bewegung, Kameras, Bildraten | WebSocket `/api/events` des Board Managers | Sofort |
| Abgleich, solange Echtzeitereignisse ankommen | HTTP-Lesen | Alle 30 Sekunden; alle 10 Sekunden bei Board Manager 2, der Kameraänderungen nicht meldet |
| Ersatz ohne Echtzeitereignisse | HTTP-Lesen | Alle 2 Sekunden; alle 15 Sekunden, wenn das Board seit etwa einer halben Minute fehlt |
| Board Manager 2 | Ein gemeinsamer Aufruf von `/api/system` pro Intervall | Wie oben |
| Board-PC-Details bei Board Manager 2 | HTTP-Lesen von `/api/host`; übernommen werden nur System, Prozessor und Softwareversionen | Beim Start, stündlich und nach einem Board-Manager-Update |
| Einstellungen und Version bei Board Manager 1 | HTTP-Lesen | Alle 30 Sekunden und nach jeder Aktion |
| Cloud-Spieldaten | Autodarts-API | Während eines Matches alle 5 Sekunden, sonst jede Minute |

## Verbindungsverhalten

- **Echtzeit zuerst.** Das Lesen wird erst langsamer, wenn die erste gültige Nachricht ankommt, nicht schon, wenn die Verbindung steht. Eine Verbindung, über die nichts kommt, behält also das schnelle Lesen.
- **Wiederverbinden.** Bricht die Echtzeitverbindung ab, wechselt die Integration sofort auf schnelles Lesen. Sie verbindet sich nach 1, 2, 4 … bis 60 Sekunden neu; jede Wartezeit wird zufällig um bis zu ein Fünftel verkürzt. Eine Verbindung, die 30 Sekunden gehalten hat, beginnt wieder bei 1 Sekunde, und findet ein Lesevorgang das Board nach einem Ausfall wieder, verbindet sich die Integration sofort.
- **Kurze Aussetzer.** Zwei verpasste Lesevorgänge in Folge, also wenige Sekunden, behalten die letzten Werte; erst der dritte macht die Board-Entitäten nicht verfügbar. Solange Echtzeitereignisse ankommen, ist ein verpasster Lesevorgang gar kein Ausfall.
- **Ein Board, das länger fehlt**, etwa weil sein PC aus ist, wird nach etwa zehn verpassten Lesevorgängen alle 15 Sekunden gefragt. Mit der ersten Antwort geht es wieder schnell weiter.
- **Board beim Start aus.** Die Integration lädt trotzdem. Training, Übungsspiele, persönliche Bestleistungen, ihre Entitäten und die Board-Ereignisse funktionieren ohne das Board; die Board-Entitäten folgen, sobald es antwortet.
- **Aufnahmen über Unterbrechungen.** Solange das Board nicht erreichbar ist, bleibt die laufende Aufnahme erhalten. Zeigt das Board danach zuerst noch ihre Darts, geht die Aufnahme weiter, und neue Darts werden erkannt. Sonst wurden die Darts inzwischen gezogen: Die Aufnahme wird mit `visit_completed` abgeschlossen, und das Übungsspiel verbucht sie. Darts, die danach noch während der Unterbrechung geworfen wurden, zählen nicht, weil sie sich nicht von korrigierten Darts unterscheiden lassen. Eine Statusänderung während der Unterbrechung wird mit dem ersten Zustand danach gemeldet.
- **Ein Lesevorgang nach dem anderen.** Lesevorgänge überschneiden sich nie, eine ältere Antwort ersetzt also nie eine neuere, und ein langsames HTTP-Lesen überschreibt nie eine neuere Echtzeitnachricht.
- **Schnell wechselnde Werte.** Bildraten und Erkennungsstatistik aktualisieren nur ihre Daten und den Kameraalarm; Training und Übungsspiel werden dafür nie neu berechnet.
- **Fehler bleiben begrenzt.** Ein Fehler im Training oder in einer Spielregel wird einmal protokolliert und trennt nie die Verbindung zum Board.
- **Unerwartete Antworten.** Eine Antwort in unbekanntem Format wird pro Abfrage einmal protokolliert. Antwortet eine nötige Abfrage (Zustand, Einstellungen oder `/api/system`) dreimal hintereinander so, bittet ein Reparaturhinweis um ein Update der Integration. Ein Board, das mit HTTP 401 oder 403 antwortet, bekommt einen eigenen Hinweis; der Board Manager braucht keine Anmeldung.
- **Nach einer Aktion.** Die Integration liest das Board direkt nach jeder Aktion; ein Schalter zeigt den neuen Zustand also nach etwa einer Sekunde.

## Board-Manager-Generationen

| | Board Manager 1 (klassische App) | Board Manager 2 (Headless) |
| --- | --- | --- |
| Erkennung | Version beginnt mit `1.` | Version beginnt mit `2.` und `/api/system` existiert |
| Lesen | Einzelne Aufrufe für Zustand, Statistik, Kameras, Bewegung, Einstellungen und Version | Ein gemeinsamer Aufruf von `/api/system` |
| Extras | Schalter für die Cloud-Verbindung | Cloud-Verbindung, CPU, Speicher, Update-Hinweis, mDNS-Erkennung |

Die Generation wird bei jedem Lesen geprüft. Nach einem Update des Boards lädt sich die Integration neu und ergänzt oder entfernt die generationsspezifischen Entitäten; sonst ändert sich nichts. Solange ein Board noch Board Manager 1 nutzt, empfiehlt ein Reparaturhinweis das Update. Solange die Generation noch unbekannt ist, etwa weil das Board beim ersten Start aus ist, werden keine Entitäten entfernt.

Ein Board, das Version 2 meldet, aber kein `/api/system` hat, gilt nach drei Antworten ohne diese Abfrage als Board Manager 1. Die Integration merkt sich das für diese Board-Manager-Version, damit ein Neustart nicht hin und her wechselt; eine andere Version wird erneut geprüft.

## Adresswechsel

- **Board Manager 2** meldet sich im Netzwerk (mDNS). Meldet er eine neue Adresse, übernimmt Home Assistant sie und lädt die Integration neu. Genutzt werden nur die Adressen, von denen die Meldung kommt, und ein Board, das unter seiner eingerichteten Adresse noch antwortet, wird nie umgezogen.
- **Einträge mit Autodarts-Cloud-Verknüpfung** nutzen beim Start die Adresse, die die Cloud meldet, wenn die eingerichtete nicht antwortet. Fehlt das Board im Betrieb fünf Minuten und antwortet es unter einer Adresse, die die Cloud meldet, mit seiner Board-ID, bietet ein Reparaturhinweis den Wechsel an. Die Cloud-Adressen werden höchstens alle 30 Minuten geprüft.
- **Sonst** öffnest du die Integration, wählst **Neu konfigurieren** und suchst das Board oder gibst seine Adresse ein. Den Suchdienst von Autodarts fragt die Integration nie von sich aus.

## Trainingssession

Trainingssessions berechnet Home Assistant aus dem, was das Board erkennt. Sie folgen diesen Regeln:

- **Sessions bestimmen, was zählt.** Nur Darts, die während einer laufenden Session geworfen werden, zählen. Darts, die beim Start einer Session schon im Board stecken, gehören zu keiner Session; Darts, die beim Ende noch stecken, bleiben bei der beendeten Session.
- **Ereignisse hängen nicht von Sessions ab.** Dart-, Korrektur-, Entnahme- und Aufnahme-Ereignisse kommen mit und ohne laufende Session.
- **Pausen beenden Sessions.** Mit eingestellter Pause endet eine Session so viele Minuten nach ihrem letzten Dart; als Ende gilt die Zeit dieses Darts. Wurde das Ende fällig, während Home Assistant aus war, wird es beim nächsten Start nachgeholt.
- **Jeder Dart zählt einmal.** Wiederholte Nachrichten, Kamerazittern und Neuverbindungen zählen keinen Dart doppelt.
- **Korrekturen überarbeiten.** Korrigiert das Board einen Dart der aktuellen Aufnahme, folgen die Summen der Korrektur, etwa wenn aus einer 180 eine 140 wird.
- **Die Entnahme beendet die Aufnahme.** Die entfernten Darts behalten ihre Punkte. Dasselbe gilt, wenn neue Darts ohne leeres Board dazwischen erscheinen (verpasste Entnahme) und wenn die Erkennung stoppt.
- **Der dritte Dart meldet die Aufnahme früh.** Landet der dritte gemeldete Dart einer Aufnahme, meldet `visit_thrown` die Aufnahme sofort, solange die Darts noch im Board stecken. Das geschieht einmal pro Aufnahme, auch nach Korrekturen; `visit_completed` folgt, wenn die Aufnahme endet, mit den endgültigen Punkten und `thrown: true`.
- **Darts beim Start zählen nicht.** Darts, die beim Start von Home Assistant schon im Board stecken, werden nicht mitgezählt.
- **Unterbrechungen behalten die Aufnahme.** Nach einer Unterbrechung der Verbindung geht die Aufnahme weiter, wenn das Board noch ihre Darts zeigt; sonst wird sie abgeschlossen, siehe [Verbindungsverhalten](#verbindungsverhalten).
- **Zurückgezogene Erkennungen.** Nimmt das Board außerhalb einer Entnahme eine Erkennung zurück, verschwindet der Dart wieder aus den Summen.
- **Punktstufen.** 100+ zählt Aufnahmen mit 100–139 Punkten, 140+ mit 140–179, 180 genau drei Triple 20. Zusammengelegte Aufnahmen mit mehr als drei Darts (nach verpasster Entnahme) zählen in keine Stufe.
- **Speicherung.** Session, Einstellungen, die letzten 20 Sessions und die letzten 10 Aufnahmen liegen im Ordner `.storage` von Home Assistant. Sie werden höchstens alle fünf Sekunden gespeichert, sofort beim Start oder Ende einer Session und beim Beenden von Home Assistant, und zusammen mit der Integration gelöscht.

Spieler und Spiele kennen die Sessions nicht. Eine laufende Session zählt jeden erkannten Dart, egal ob du X01, Cricket oder freies Training spielst.

## Übungsspiel

Das Übungsspiel folgt wie die Trainingssession den Darts der aktuellen Aufnahme, einschließlich Korrekturen. Wenn du die Darts ziehst, wird die Aufnahme verbucht. Wie jedes Spiel zählt, steht unten bei den [Regeln](#regeln).

- **Aufnahmen:** Eine Aufnahme hat drei Darts. Ein vierter Dart vor dem Ziehen zählt nicht. Darts, die das Board nicht erkennt, etwa Abpraller oder Darts auf dem Boden, zählen nicht; eine Aufnahme mit weniger Darts zählt nur die erkannten.
- **Checkout-Weg:** Die Integration probiert jede Kombination für die restlichen Darts der Aufnahme und wählt den Weg, den die Checkout-Tabellen der Profis wählen, nach diesen Grundsätzen in dieser Reihenfolge:
  1. Die wenigsten Darts, also das Bullseye bei 50 auch mit drei Darts in der Hand.
  2. Kein Double als Stellwurf, und ein Double statt des Bullseyes zum Checkout.
  3. Mit drei Darts in der Hand ein erstes Triple, dessen Single noch einen Checkout mit zwei Darts lässt: 129 beginnt mit T19, weil eine Single 20 den Rest 109 ließe.
  4. Das größte erste Triple, meist T20.
  5. Stellwürfe auf Triple 20 oder 19 oder auf ein Single zu D20, D16, D8, D18, D12, D10 oder D4. Mit zwei Darts übrig passt Triple 20 oder 19 zu jedem Double, wenn ihr Single noch einen Checkout mit einem Dart lässt: 70 mit zwei Darts ist T20 D5, mit dem Bull hinter einer Single 20.
  6. Dann jeder Stellwurf zu den guten Doubles D20, D16, D8, D18 oder D12, dann alles andere; weniger Triples, größere Triples und das Checkout-Double in der Reihenfolge D20, D16, D8, D18, D12, D10, D4, D14, D6, D2 und die ungeraden Doubles.

  So wird 144 zu T20 T20 D12, 136 zu T20 T20 D8, 130 zu T20 T20 D5, 127 zu T20 T17 D8, 73 zu T19 D8 und 64 zu T16 D8. Für 159, 162, 163, 165, 166, 168, 169 und alles über 170 gibt es mit Double-Out keinen Weg. Ohne Double-Out checkt das größte Feld: ein Single vor einem Double oder Triple.
- **Persönliche Wege:** Mit *Übungsspiel persönliche Checkout-Wege* gewinnen die Doubles des Spielers am Board mit je mindestens 10 Darts, die beste Quote zuerst, gegen den üblichen Weg, sobald ein Weg mit gleich vielen Darts sie ohne Double als Stellwurf erreicht; zwischen Wegen zum selben Double entscheiden die Grundsätze oben.
- **Statistik:** Jedes beendete X01-Leg ergibt einen Eintrag für alle am Board: Punkte und Darts der ersten neun Darts, Darts aufs Double und den Checkout. Überworfene Aufnahmen zählen keine Punkte, auch nicht in den ersten neun. Die Statistik-Sensoren nutzen die letzten 10 Einträge, ihr Verlauf zeigt deine Entwicklung. *Übungsspiel gespielte Legs* zählt jedes beendete Leg von X01, den Cricket-Spielen und den Partyspielen.
- **Speicher:** Spiel, Regeln, Teams und Startpunkte, Spieler mit ihren Ständen und Treffern, Matchformat und die letzten 10 Legs werden zusammen mit der Trainingssession gespeichert.

## Regeln

### X01

- **Herunterzählen:** Der Rest beginnt bei 101, 301, 501, 701, 901 oder 1001, und jeder Dart zieht seine Punkte ab.
- **Double-Out** (standardmäßig an): Der letzte Dart eines Legs muss ein Double oder das Bullseye treffen. Ohne Double-Out checkt jedes Feld.
- **Double-In** (standardmäßig aus): Die Zählung eines Spielers beginnt mit dem ersten Double oder Bullseye des Legs; Darts davor zählen nichts. Ein Überwerfen nimmt das öffnende Double zurück.
- **Überwerfen:** Ein Dart, der unter null geht, mit Double-Out 1 übrig lässt oder 0 ohne Double erreicht, überwirft die Aufnahme. Der Rest springt auf den Beginn der Aufnahme zurück. Der überwerfende Dart zählt als geworfen, spätere Darts der Aufnahme nicht.
- **Checkout:** Ein Dart, der genau 0 erreicht, gewinnt das Leg. `leg_won` wird sofort gemeldet, mit den Regeln des Legs (`double_out`, `double_in`). Verbucht wird das Leg beim Ziehen der Darts, eine Korrektur davor zählt also noch. Darts nach dem Siegdart zählen nicht. Die nächste Aufnahme beginnt ein neues Leg.
- **Average:** erzielte Punkte pro drei Darts des Legs. Darts einer überworfenen Aufnahme zählen, ihre Punkte nicht.
- **Startpunkte (Handicap):** Ein Spieler, dessen *Übungsspiel Startpunkte* nicht 0 sind, beginnt jedes Leg mit diesen Punkten, von 2 bis 1001, zum Beispiel 301 gegen 501. Alle anderen Regeln bleiben gleich; der Average zählt ab den eigenen Startpunkten, und `leg_won` nennt sie in `start`.

### Matches, Legs und Sätze

- **Wechsel:** Mit zwei bis vier Spielern wechselt der Wurf beim Ziehen der Darts, auch nach dem Überwerfen.
- **Legs und Sätze:** Wer zuerst *Legs pro Satz* Legs gewinnt, holt den Satz; es gibt keinen Tie-Break und keine zwei Legs Vorsprung. Wer zuerst *Sätze zum Sieg* Sätze holt, gewinnt das Match. Mit einem Satz zum Sieg gewinnt einfach, wer zuerst so viele Legs holt. Mit einem Spieler zählen die Legs nur hoch.
- **Anwurf:** Wie bei den Sätzen der PDC wechselt der Anwurf innerhalb eines Satzes jedes Leg zum nächsten Spieler, und jeder neue Satz beginnt mit dem Spieler nach dem, der den vorigen Satz begonnen hat. Bei zwei Spielern beginnt Spieler 1 die Sätze 1, 3 und 5 und Spieler 2 die Sätze 2 und 4. Das erste Leg eines Matches beginnt Spieler 1 oder wer das Ausbullen gewinnt.
- **Ergebnis:** Das Ergebnis bleibt stehen, bis der nächste Dart ein neues Match beginnt. Der Sieger behält die Legs des entscheidenden Satzes, ein Match auf drei Legs endet also 3:2 auf der Anzeigetafel. `match_won`, der Verlauf von *Letztes Match* und die Spielerprofile behalten Legs und Sätze aller Spieler; `match_legs` zählt die Legs des ganzen Matches.
- **Averages:** Average und Treffer pro Runde jedes Spielers gelten für das ganze Match.

### Teams

- **Zwei Teams zu zwei:** Mit *Übungsspiel Teams* und vier Spielern in X01 oder einem Cricket-Spiel spielen Spieler 1 und 3 gegen Spieler 2 und 4. Geworfen wird in der Reihenfolge der Plätze, die Teams wechseln sich also ab: A1, B1, A2, B2. Mit weniger oder mehr als vier Spielern und in Party- und Trainingsspielen spielt jeder für sich.
- **Ein Stand pro Team:** Partner teilen sich den Rest, mit Double-In das öffnende Double und in den Cricket-Spielen Treffer und Punkte. Ein Team spielt mit den Startpunkten seines ersten Spielers, Spieler 1 oder Spieler 2.
- **Anwurf:** Wie in jedem Match zu viert wechselt der Anwurf jedes Leg zum nächsten Platz, die Teams wechseln sich also ab.
- **Sieg:** Beide Partner gewinnen das Leg und das Match. `leg_won` und `match_won` nennen zusätzlich `team` und `team_name` (*Alex & Kim*, wenn beide Partner einen Namen haben); Darts, Average und Treffer pro Runde des Legs sind die des Teams.
- **Statistik pro Person:** First 9, Checkout-Quote, Averages und Treffer pro Runde bleiben bei dem Spieler, der die Darts geworfen hat. Die Spielerprofile zählen Leg und Match für beide Partner, und jeder von ihnen schlägt im direkten Vergleich beide Gegner; Partner haben keinen direkten Vergleich. Ein Team-Leg setzt keine Bestleistung für die wenigsten Darts und für Treffer pro Runde, weder am Board noch im Profil; ein Checkout zählt weiter für den Spieler, der ihn geworfen hat.

### Ausbullen

- Mit *Übungsspiel Ausbullen* und zwei oder mehr Spielern beginnt ein Match mit einem Dart pro Spieler aufs Bull, in der Reihenfolge der Plätze. Nur der erste Dart jeder Aufnahme zählt.
- Wie es die Regeln von WDF und PDC wollen, schlägt das Bullseye das Single-Bull und dieses jedes andere Feld. Zwei oder mehr Darts im selben Bull-Feld sind gleichauf: Diese Spieler werfen noch einmal, der letzte von ihnen zuerst.
- Außerhalb des Bulls gewinnt der Dart, der der Mitte näher ist. Der Abstand ergibt sich aus der Position, die das Board meldet, bezogen auf den äußeren Rand des Doppelrings (170 mm).
- Mit *Übungsspiel Ausbullen nach Abstand* entscheidet der gemessene Abstand auch zwischen zwei Darts im selben Bull-Feld; Darts mit gleichem Abstand auf 0,1 mm werfen noch einmal.
- Ein Dart ohne Position lässt sich nicht messen und schlägt deshalb nie einen gemessenen Dart: Braucht die Entscheidung einen Abstand, den das Board nicht gemeldet hat, werfen diese Spieler noch einmal.
- Das Ausbullen entscheidet nur, wer beginnt. Bei drei oder vier Spielern folgen die anderen in der Reihenfolge der Plätze.

### Cricket

- **Treffer:** Nur 20 bis 15 und das Bull zählen. Ein Single ist ein Treffer, ein Double zwei, ein Triple drei; das Single-Bull ist ein Treffer, das Bullseye zwei. Drei Treffer schließen eine Zahl.
- **Punkte:** Weitere Treffer bringen den Wert der Zahl (25 fürs Bull), solange ein anderer Spieler sie offen hat.
- **Sieg:** Schließe alle Zahlen mit mindestens so vielen Punkten wie alle anderen. Der Sieg wird nach jedem Dart geprüft: Ein schließender Dart gewinnt sofort, wenn die Punkte reichen, und spätere Darts der Aufnahme zählen nicht. Allein gewinnt, wer alle Zahlen schließt.
- **Treffer pro Runde:** die Treffer, die eine Zahl geschlossen oder gepunktet haben, pro drei tatsächlich geworfene Darts.

### Cut-Throat Cricket

- **Treffer:** wie bei Cricket, auf 20 bis 15 und das Bull.
- **Punkte für die anderen:** Weitere Treffer auf eine geschlossene Zahl geben ihren Wert jedem anderen Spieler, der sie noch offen hat; wer sie wirft, bekommt nichts.
- **Sieg:** Schließe alle Zahlen mit nicht mehr Punkten als alle anderen: Die wenigsten Punkte gewinnen. Allein gewinnt, wer alle Zahlen schließt.

### Tactics

- Cricket auf die Zahlen 20 bis 10 und das Bull, zwölf Zahlen insgesamt. Treffer, Punkte und Sieg folgen den Regeln von Cricket.

### Shanghai

- Sieben Runden auf die Zahlen 1 bis 7; das klassische Kneipenspiel geht über 1 bis 20 oder neun Runden.
- Jeder Dart in einem Feld der Rundenzahl bringt seinen Wert. Ein Fehlwurf neben der Zahl zählt nichts.
- Single, Double und Triple der Zahl in einer Aufnahme, ein *Shanghai*, gewinnen das Leg sofort; spätere Darts der Aufnahme zählen nicht.
- Nach sieben Runden gewinnen die meisten Punkte. Bei gleichen Punkten gewinnt, wer öfter getroffen hat; bei gleich vielen Treffern wird das Leg neu gespielt, und der nächste Spieler beginnt es.

### Halve-It

- Alle beginnen mit 40 Punkten. Die neun Runden zielen auf 15, 16, ein beliebiges Double, 17, 18, ein beliebiges Triple, 19, 20 und das Bull, angezeigt als 25.
- Treffer bringen ihre Punkte. *Beliebiges Double* schließt das Bullseye ein. In der Bull-Runde bringt das Single-Bull 25 und das Bullseye 50.
- Eine Aufnahme ohne Treffer aufs Ziel halbiert die Punkte, abgerundet, auch wenn weniger als drei Darts geworfen wurden.
- Die meisten Punkte nach neun Runden gewinnen; Gleichstände werden wie bei Shanghai entschieden.

### Killer

- Zwei bis vier Spieler mit je 3 Leben.
- Zuerst wirft jeder einen Dart für seine eigene Zahl: ein beliebiges Feld von 1 bis 20, das noch niemand hat. Ein Fehlwurf, das Bull oder eine vergebene Zahl heißen: noch einmal werfen.
- Danach zählen nur Doubles. Wer das Double der eigenen Zahl trifft, ist für den Rest des Legs Killer. Vorher bewirken die Doubles der anderen nichts.
- Ein Killer nimmt mit jedem Treffer auf das Double eines anderen ein Leben und verliert mit jedem Treffer auf das eigene eines, auch mit einem zweiten eigenen Double in der Aufnahme, die ihn zum Killer gemacht hat.
- Wer keine Leben mehr hat, ist raus: Der Rest der Aufnahme bewirkt nichts, und der Wurf überspringt ihn von da an.
- Wer als Letzter noch ein Leben hat, gewinnt sofort; spätere Darts der Aufnahme zählen nicht.

### Golf

- Neun oder 18 Löcher, eingestellt in *Übungsspiel Golf-Löcher*; Loch *n* wird auf die Zahl *n* gespielt.
- Ein Spieler wirft bis zu drei Darts pro Loch und darf nach jedem Dart aufhören, indem er die Darts zieht: **Der letzte geworfene Dart zählt.**
- Schläge: ein Triple 1, ein Double 2, ein inneres Single 3, ein äußeres Single 4, alles andere 5. Ob ein Single innen oder außen liegt, ergibt sich aus der Position, die das Board meldet; ein Single ohne Position zählt als äußeres Single.
- Die wenigsten Schläge nach dem letzten Loch gewinnen. Bei Gleichstand an der Spitze spielen die Gleichauf-Liegenden in ihrer Wurfreihenfolge Zusatzlöcher auf die nächsten Zahlen (nach 20 wieder ab 1), bis einer von ihnen nach einem Loch weniger Schläge hat.

### Baseball

- Neun Innings; Inning *n* wird auf die Zahl *n* gespielt, mit einer Aufnahme aus drei Darts.
- Jeder Dart in einem Feld der Zahl des Innings bringt Runs: ein Single 1, ein Double 2, ein Triple 3. Das Bull bringt nichts.
- Die meisten Runs nach neun Innings gewinnen. Bei Gleichstand an der Spitze spielen die Gleichauf-Liegenden Zusatz-Innings auf 10, 11 und so weiter, bis einer von ihnen nach einem Inning vorn liegt.

### Count-Up

- 1 bis 20 Runden, eingestellt in *Übungsspiel Count-Up-Runden*, standardmäßig 8. Jeder Dart bringt seinen Wert.
- Die meisten Punkte gewinnen. Bei Gleichstand an der Spitze spielen die Gleichauf-Liegenden Zusatzrunden, bis einer von ihnen nach einer Runde vorn liegt.

### Trainingsspiele

- **Around the Clock:** 1 bis 20, dann das Bull, der Reihe nach, mit jedem Feld der Zahl. Das Bull-Ziel heißt `25`: Single-Bull und Bullseye zählen beide.
- **Doppeltraining:** D1 bis D20, dann das Bullseye (`BULL`); nur Doppelring und Bullseye zählen.
- **Checkout-Training:** ein zufälliger Rest von 2 bis 170, der mit drei Darts checkbar ist, auf einem Double in höchstens drei Aufnahmen ausgecheckt. Überwerfen oder eine dritte Aufnahme ohne Checkout beenden den Versuch; der Weg steht nur, solange der Versuch läuft.
- **Bob's 27:** Start mit 27 Punkten, je eine Aufnahme auf jedes Double von D1 bis D20 und dann aufs Bullseye. Jeder Treffer bringt den Wert des Doubles; eine Aufnahme ohne Treffer zieht ihn ab. Das Spiel ist verloren, sobald die Punkte null oder weniger erreichen, und geschafft nach dem Bullseye.
- **121-Checkout:** Checke 121 auf einem Double in höchstens drei Aufnahmen, also neun Darts. Ein Checkout hebt das Ziel auf den nächsten Rest; Überwerfen oder drei Aufnahmen ohne Checkout senken es um eins, nie unter 121. Reste ohne Checkout (159, 162, 163, 165, 166, 168, 169) werden übersprungen, 170 ist das höchste Ziel. Jeder Versuch meldet `checkout_attempt` mit dem nächsten Ziel in `next`.
- **Catch 40:** Checke 61, 62 und so weiter bis 100, jeden Rest auf einem Double in höchstens zwei Aufnahmen, also sechs Darts. Ein Checkout mit zwei Darts bringt 3 Punkte, mit drei Darts 2 und mit vier bis sechs Darts 1. Überwerfen oder zwei Aufnahmen ohne Checkout bringen nichts, und der nächste Rest folgt. Höchstens 120 Punkte.
- **JDC Challenge:** das Trainingsprogramm der [Junior Darts Corporation](https://www.juniordarts.com/) mit 57 Darts, wie es ihre Akademien spielen ([Regeln](https://www.godartspro.com/jdc/)). Zuerst eine Aufnahme auf jede Zahl von 10 bis 15: Jeder Dart in einem Feld der Zahl bringt seinen Wert, und Single, Double und Triple der Zahl in der Aufnahme bringen 100 dazu (ein Shanghai). Dann ein Dart auf jedes Double von D1 bis D20, 50 Punkte pro Treffer, und einer aufs Bullseye für 100. Dann eine Aufnahme auf jede Zahl von 15 bis 20 wie im ersten Teil. Höchstens 3.380 Punkte.
- **Singles-Training:** eine Aufnahme auf jede Zahl von 1 bis 20 und dann aufs Bull (`25`). Jeder Dart in einem Feld der Zahl bringt einen Punkt pro Treffer: ein Single 1, ein Double 2, ein Triple 3; das Single-Bull 1 und das Bullseye 2. Höchstens 186 Punkte.
- Darts, die das Board nicht erkennt, zählen nicht: Im Double-Teil der JDC Challenge geht der nächste erkannte Dart aufs nächste Double.

### Bestleistungen und Statistik

- **Höchste Aufnahme:** Der Sensor *Training höchste Aufnahme* und die Bestleistung `highest_visit` nehmen die Punkte der Darts im Board in einer Aufnahme mit bis zu drei Darts, egal in welchem Spiel: Eine überworfene Aufnahme oder eine Cricket-Aufnahme zählt mit ihren Board-Punkten, wie bei den Stufen 100+, 140+ und 180. Die `highest_visit` eines [Spielerprofils](entitaeten.md#spielerprofile) ist dagegen die höchste X01-Aufnahme dieses Spielers: Überwerfen zählt nichts, und mit Double-In auch keine Darts vor dem öffnenden Double.
- **Höchster Checkout und wenigste Darts:** Die Bestleistungen `highest_checkout` und `fewest_darts_*` und dieselben Werte der Spielerprofile kommen nur aus gewonnenen X01-Legs mit Double-Out, mit oder ohne Double-In. Ein Leg ohne Double-Out ist leichter zu beenden und setzt keine Bestleistung; Double-In macht ein Leg nur schwerer.
- **Startpunkte und Teams:** Die wenigsten Darts zählen für die Punkte, mit denen ein Leg wirklich begonnen hat: Ein Leg ab 301 Startpunkten zählt für `fewest_darts_301`, ein Leg ab 401 für keine Bestleistung, weil 401 kein X01-Spiel ist. Ein Team-Leg setzt keine Bestleistung für die wenigsten Darts und für Treffer pro Runde.
- **Cricket-Spiele:** Die Treffer pro Runde der Profile und `best_cricket_mpr` kommen aus Cricket; Cut-Throat und Tactics zählen ihre Legs und Matches.
- **Trainingsspiele:** `checkout_121` hält den höchsten Rest, der im 121-Checkout gecheckt wurde; `catch_40`, `jdc_challenge` und `singles` halten die höchste Punktzahl eines beendeten Spiels.
- **Darts aufs Double:** Mit Double-Out zählt ein Dart als Wurf aufs Double, wenn ein Double den Rest checken könnte: 2 bis 40 bei geraden Zahlen oder 50. Bei 50 zählt also jeder Dart als Versuch aufs Bullseye, auch wenn ein Spieler stattdessen mit einer Single 10 stellt.

## Wochenbericht

Der Wochenbericht zählt, was das Board erkennt, wie bei den Darts des Tages, und folgt diesen Regeln:

- **Jeder Dart zählt.** Darts zählen mit oder ohne Session, im Spiel oder ohne. Der 3-Dart-Average umfasst jede abgeschlossene Aufnahme der Woche, auch zusammengelegte Aufnahmen nach einer verpassten Entnahme; höchste Aufnahme und 180er zählen Aufnahmen mit bis zu drei Darts.
- **Trainingszeit** ist die Zeit von einem Dart zum nächsten. Eine Pause von mehr als fünf Minuten zwischen zwei Darts zählt nicht, eine Pause zwischen zwei Sessions ist also kein Training.
- **Sessions** zählen, wenn sie enden: Eine Session über das Wochenende hinaus zählt für die nächste Woche.
- **Checkout-Quote** folgt den X01-Übungslegs, die in der Woche verbucht wurden: ausgecheckte Legs pro Dart aufs Double, wie bei *Übungsspiel Checkout-Quote*.
- **Die Woche** reicht vom Berichtstag und der Uhrzeit bis zum selben Tag und derselben Uhrzeit eine Woche später, in der Zeitzone von Home Assistant. Eine Woche mit Zeitumstellung ist eine Stunde länger oder kürzer; eine Uhrzeit, die die Uhr überspringt, zählt in der Zeit vor der Umstellung.
- **Ein neuer Berichtstag oder eine neue Uhrzeit** beendet die laufende Woche bei ihrem nächsten Eintreten; diese Woche kann also kürzer oder länger sein.
- **Verpasste Berichte.** Ein Bericht, der fällig wurde, während Home Assistant aus war, folgt beim nächsten Start; Wochen dazwischen hatten keine Darts und entfallen.
- **Speicherung.** Die laufende Woche und der letzte Bericht liegen in einem eigenen Speicher im Ordner `.storage` von Home Assistant. Sie werden höchstens alle zehn Sekunden gespeichert, sofort am Ende einer Woche und beim Beenden von Home Assistant, und zusammen mit der Integration gelöscht.

## Trainingskalender und Exporte

- **Journal.** Der Trainingskalender behält jede beendete Session und jedes Match mehrerer Spieler 365 Tage lang, höchstens je 3.000, in einem eigenen Speicher in `.storage`. Er wird gespeichert, wenn eine Session oder ein Match endet, und mit der Integration gelöscht. Beim ersten Start übernimmt er die Sessions und Matches, die die Integration schon gespeichert hat.
- **Erster Dart.** Ein Match beginnt mit dem ersten Dart, der erkannt wird, während ein Match mehrerer Spieler gewählt ist. Wird das Spiel ausgeschaltet oder auf ein Trainingsspiel oder ein anderes Spiel umgestellt, vergisst der Kalender diesen Dart.
- **Exporte** schreibt nur die Aktion `autodarts.export`, in einen Ordner im Konfigurationsordner. Der Ordner wird vor dem Schreiben aufgelöst, sodass weder `..`, ein absoluter Pfad noch ein symbolischer Link nach draußen führt; versteckte Ordner wie `.storage` werden abgelehnt. Jeder Export bekommt einen neuen Namen mit einem zufälligen Teil und ersetzt nie eine Datei. In CSV bekommt ein Text, der wie eine Tabellenformel beginnt (`=`, `+`, `-`, `@`), einen Apostroph vorangestellt, damit ein Spielername nicht als Formel läuft.
- **Downloads.** Neben `/local/` können angemeldete Benutzer die seit dem Start von Home Assistant geschriebenen Exporte unter `/api/autodarts/export/<Name>` herunterladen; die Spielerkarte nutzt diese Adresse mit einem signierten Link, der nach einer Minute abläuft.

## Highlight-Galerie

Die Medienquelle *Autodarts* zeigt die Fotos, die der [Highlight-Foto-Blueprint](automationen.md#highlight-galerie) speichert:

- **Ordner:** `autodarts/highlights` im Medienordner von Home Assistant. Das ist der Medienordner `local`: `/media` unter Home Assistant OS und im Container, sonst der Ordner `media` im Konfigurationsordner. Hast du `media_dirs` ohne `local` gesetzt, der erste davon.
- **Namen:** `JJJJ-MM-TT_HH-MM-SS_<Spieler>_<Punkte>.jpg`; Uhrzeit und Spieler sind optional, ein Checkout heißt `checkout-121`. Andere Bilder (`.jpg`, `.jpeg`, `.png`, `.webp`) erscheinen mit ihrem Dateinamen und der Zeit, zu der sie gespeichert wurden.
- **Reihenfolge:** die Monate, die neuesten zuerst, jeder mit seinem neuesten Foto als Titelbild; die Fotos eines Monats, die neuesten zuerst.
- **Sicherheit:** Nur einfache Dateinamen dieses Ordners öffnen sich, und nur Bilder; versteckte Dateien, Unterordner und Verknüpfungen aus dem Ordner hinaus werden ignoriert. Die Fotos liefert die Medienansicht von Home Assistant selbst aus, an angemeldete Benutzer oder mit einer signierten Adresse.

## Kamerazustand

Eine Kamera gilt als gestört, wenn sie bei laufender Erkennung **15 Sekunden** lang keine Bilder liefert. Gestoppte Erkennung, Kalibrierung und Kamera-Standby sind keine Störung. Der gemeinsame Sensor *Kamerastörung* ist an, sobald eine Kamera gestört ist. Mit Echtzeitereignissen erscheint der Alarm, sobald die Bildraten ihn zeigen.

Die Kamera-Entitäten geben den Livestream von Board Manager 2 an höchstens zwei Zuschauer pro Kamera weiter; weitere Zuschauer bekommen Standbilder. Das schont den Board-PC, auf dem auch die Erkennung läuft.

## Datenschutz

- **Lokaler Betrieb:** Die Integration spricht nur mit dem Board Manager in deinem Netzwerk; ins Internet geht nichts.
- **Boards im Netzwerk suchen:** Fragt einmalig bei Benutzung `discover.autodarts.com`, den öffentlichen Suchdienst von Autodarts. Er sieht deine öffentliche IP-Adresse und liefert die von dort registrierten Boards.
- **Die optionale Cloud-Verknüpfung** nutzt die Geräteanmeldung von Autodarts. Home Assistant speichert OAuth-Token, nie dein Passwort.
- **Die optionale Online-Brücke** empfängt nur: Die Browser-Erweiterung Tools for Autodarts ruft Home Assistant mit den Momenten eines Online-Matches auf, standardmäßig nur aus deinem Heimnetz. Sie sendet nirgendwohin. [Online-Matches](automationen.md#online-matches-experimentell).
- **Board-Geheimnisse** wie der API-Schlüssel des Boards, TLS-Schlüssel, Kamerapfade und ähnliche Konfiguration werden direkt beim Lesen verworfen. Sie werden nie gespeichert, protokolliert oder angezeigt.
- **Diagnosedaten** schwärzen Board-ID, Adresse, Client-ID, Token und Spielernamen. Der Verbindungsverlauf darin enthält Zähler, Fehlerarten und Dauern, aber keine Adressen oder Fehlermeldungen.
- **Exporte** enthalten Spielernamen. Die Aktion schreibt sie nur auf Anforderung; Dateien in `www` liefert Home Assistant unter `/local/` ohne Anmeldung aus, siehe [Exporte](#trainingskalender-und-exporte).
- **Highlight-Fotos** bleiben in deinem Medienordner; die Galerie liest nichts anderes.
- **Personen:** Ein mit einer Person verknüpfter Spieler behält nur die Entitäts-ID der Person; Bild und Anwesenheit liest die Karte aus Home Assistant.

## Sicherheit

- Die lokale API des Board Managers verlangt keine Anmeldung. Jeder, der Port 3180 in deinem Netzwerk erreicht, kann sie nutzen, mit oder ohne Home Assistant. Betreibe den Board-PC in einem vertrauenswürdigen Netzwerk.
- Aktionen werden nur gesendet, wenn du oder eine Automation sie auslöst, und nie automatisch wiederholt.
