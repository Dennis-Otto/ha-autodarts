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
| Abgleich, solange Echtzeitereignisse ankommen | HTTP-Lesen | Alle 30 Sekunden |
| Ersatz ohne Echtzeitereignisse | HTTP-Lesen | Alle 2 Sekunden |
| Board Manager 2 | Ein gemeinsamer Aufruf von `/api/system` pro Intervall | Wie oben |
| Board-PC-Details bei Board Manager 2 | HTTP-Lesen von `/api/host`; übernommen werden nur System, Prozessor und Softwareversionen | Beim Start, stündlich und nach einem Board-Manager-Update |
| Einstellungen und Version bei Board Manager 1 | HTTP-Lesen | Alle 30 Sekunden und nach jeder Aktion |
| Cloud-Spieldaten | Autodarts-API | Während eines Matches alle 5 Sekunden, sonst jede Minute |

Weitere Details:

- **Wiederverbinden.** Bricht die Echtzeitverbindung ab, wechselt die Integration sofort auf schnelles Lesen. Danach verbindet sie sich mit wachsendem Abstand von 1 bis 60 Sekunden neu.
- **Keine veralteten Werte.** Ein langsames HTTP-Lesen überschreibt nie eine neuere Echtzeitnachricht.
- **Kurze Aussetzer.** Ein einzelner verpasster Lesevorgang zählt nicht als Ausfall, solange Echtzeitereignisse ankommen.
- **Nach einer Aktion.** Die Integration liest das Board direkt nach jeder Aktion; ein Schalter zeigt den neuen Zustand also nach etwa einer Sekunde.

## Board-Manager-Generationen

| | Board Manager 1 (klassische App) | Board Manager 2 (Headless) |
| --- | --- | --- |
| Erkennung | Version beginnt mit `1.` | Version beginnt mit `2.` und `/api/system` existiert |
| Lesen | Einzelne Aufrufe für Zustand, Statistik, Kameras, Bewegung, Einstellungen und Version | Ein gemeinsamer Aufruf von `/api/system` |
| Extras | Schalter für die Board-Cloud-Verbindung | Cloud-Verbindung, CPU, Speicher, Update-Hinweis, mDNS-Erkennung |

Die Generation wird bei jedem Lesen geprüft. Nach einem Update des Boards lädt sich die Integration neu und ergänzt oder entfernt die generationsspezifischen Entitäten; sonst ändert sich nichts. Solange ein Board noch Board Manager 1 nutzt, empfiehlt ein Reparaturhinweis das Update.

## Trainingssession

Trainingssessions berechnet Home Assistant aus dem, was das Board erkennt. Sie folgen diesen Regeln:

- **Sessions bestimmen, was zählt.** Nur Darts, die während einer laufenden Session geworfen werden, zählen. Darts, die beim Start einer Session schon im Board stecken, gehören zu keiner Session; Darts, die beim Ende noch stecken, bleiben bei der beendeten Session.
- **Ereignisse hängen nicht von Sessions ab.** Dart-, Korrektur-, Entnahme- und Aufnahme-Ereignisse kommen mit und ohne laufende Session.
- **Pausen beenden Sessions.** Mit eingestellter Pause endet eine Session so viele Minuten nach ihrem letzten Dart; als Ende gilt die Zeit dieses Darts. Wurde das Ende fällig, während Home Assistant aus war, wird es beim nächsten Start nachgeholt.
- **Jeder Dart zählt einmal.** Wiederholte Nachrichten, Kamerazittern und Neuverbindungen zählen keinen Dart doppelt.
- **Korrekturen überarbeiten.** Korrigiert das Board einen Dart der aktuellen Aufnahme, folgen die Summen der Korrektur, etwa wenn aus einer 180 eine 140 wird.
- **Die Entnahme beendet die Aufnahme.** Die entfernten Darts behalten ihre Punkte. Dasselbe gilt, wenn neue Darts ohne leeres Board dazwischen erscheinen (verpasste Entnahme) und wenn die Erkennung stoppt.
- **Der dritte Dart meldet die Aufnahme früh.** Landet der dritte gemeldete Dart einer Aufnahme, meldet `visit_thrown` die Aufnahme sofort, solange die Darts noch im Board stecken. Das geschieht einmal pro Aufnahme, auch nach Korrekturen; `visit_completed` folgt, wenn die Aufnahme endet, mit den endgültigen Punkten und `thrown: true`.
- **Darts beim Start zählen nicht.** Darts, die beim Start von Home Assistant oder der Verbindung schon im Board stecken, werden nicht mitgezählt.
- **Zurückgezogene Erkennungen.** Nimmt das Board außerhalb einer Entnahme eine Erkennung zurück, verschwindet der Dart wieder aus den Summen.
- **Punktstufen.** 100+ zählt Aufnahmen mit 100–139 Punkten, 140+ mit 140–179, 180 genau drei Triple 20. Zusammengelegte Aufnahmen mit mehr als drei Darts (nach verpasster Entnahme) zählen in keine Stufe.
- **Speicherung.** Session, Einstellungen, die letzten 20 Sessions und die letzten 10 Aufnahmen liegen im Ordner `.storage` von Home Assistant. Sie werden höchstens alle fünf Sekunden gespeichert, sofort beim Start oder Ende einer Session und beim Beenden von Home Assistant, und zusammen mit der Integration gelöscht.

Spieler und Spiele kennen die Sessions nicht. Eine laufende Session zählt jeden erkannten Dart, egal ob du X01, Cricket oder freies Training spielst.

## Übungsspiel

Das Übungsspiel folgt wie die Trainingssession den Darts der aktuellen Aufnahme, einschließlich Korrekturen. Wenn du die Darts ziehst, wird die Aufnahme verbucht.

- **Herunterzählen:** Der Rest beginnt bei 301, 501 oder 701, und jeder Dart zieht seine Punkte ab.
- **Überwerfen:** Ein Dart, der unter null geht, mit Double-Out 1 übrig lässt oder 0 ohne Double erreicht, überwirft die Aufnahme. Der Rest springt auf den Beginn der Aufnahme zurück. Der überwerfende Dart zählt als geworfen, spätere Darts der Aufnahme nicht.
- **Checkout:** Ein Dart, der genau 0 erreicht, mit Double-Out auf einem Double oder dem Bullseye, gewinnt das Leg. `leg_won` wird sofort gemeldet. Verbucht wird das Leg beim Ziehen der Darts, eine Korrektur davor zählt also noch. Die nächste Aufnahme beginnt ein neues Leg.
- **Average:** erzielte Punkte pro drei Darts des Legs. Darts einer überworfenen Aufnahme zählen, ihre Punkte nicht.
- **Persönliche Wege:** Mit *Übungsspiel persönliche Checkout-Wege* rücken die Doubles mit der besten Quote des Spielers am Board (je mindestens 10 Darts) an den Anfang dieser Reihenfolge; die übrigen Regeln bleiben.
- **Checkout-Weg:** Die Integration probiert jede Kombination für die restlichen Darts der Aufnahme. Sie bevorzugt weniger Darts, Stellwürfe ohne Double, ein Double statt des Bullseyes zum Checkout, weniger Triples, dann das Checkout-Double in der Reihenfolge D20, D16, D8, D18, D12, D10, D4, D14, D6, D2 und die ungeraden Doubles, zuletzt den größeren Dart zuerst. Für 159, 162, 163, 165, 166, 168, 169 und alles über 170 gibt es mit Double-Out keinen Weg.
- **Statistik:** Jedes beendete Leg ergibt einen Eintrag für alle am Board: Punkte und Darts der ersten neun Darts, Darts aufs Double und den Checkout. Überworfene Aufnahmen zählen keine Punkte, auch nicht in den ersten neun. Die Statistik-Sensoren nutzen die letzten 10 Einträge, ihr Verlauf zeigt deine Entwicklung.
- **Matches:** Mit mehreren Spielern wechselt der Wurf beim Ziehen der Darts, auch nach dem Überwerfen. Wer das Leg beginnt, wechselt jedes Leg. Wer *Legs pro Satz* Legs gewinnt, holt den Satz, und die Legs aller beginnen wieder bei null; wer *Sätze zum Sieg* Sätze holt, gewinnt das Match. Der Average jedes Spielers gilt für das ganze Match.
- **Cricket:** Ein Dart setzt seine Treffer auf seine Zahl, bis drei sie schließen; weitere Treffer bringen den Wert der Zahl, solange ein anderer Spieler sie offen hat. Der Sieg wird nach jedem Dart geprüft: Ein schließender Dart gewinnt sofort, wenn die Punkte reichen, und spätere Darts der Aufnahme zählen nicht. Treffer pro Runde zählen die Treffer, die eine Zahl geschlossen oder gepunktet haben, pro drei Darts.
- **Partyspiele:** Shanghai und Killer entscheidet der Dart, der den Shanghai vollendet oder das letzte Leben nimmt; der Sieg wird sofort gemeldet. Das Ende der letzten Runde bei Shanghai und Halve-It wird beim Ziehen der Darts entschieden. Halve-It halbiert eine Aufnahme ohne Treffer auf das Ziel auch, wenn weniger als drei Darts geworfen wurden.
- **Ausbullen:** Nur der erste Dart jeder Aufnahme zählt. Sein Abstand ergibt sich aus der Position, die das Board meldet, bezogen auf den äußeren Rand des Doppelrings (170 mm).
- **Speicher:** Spiel, Spieler mit ihren Ständen und Treffern, Matchformat und die letzten 10 Legs werden zusammen mit der Trainingssession gespeichert.

## Kamerazustand

Eine Kamera gilt als gestört, wenn sie bei laufender Erkennung **15 Sekunden** lang keine Bilder liefert. Gestoppte Erkennung, Kalibrierung und Kamera-Standby sind keine Störung. Der gemeinsame Sensor *Kamerastörung* ist an, sobald eine Kamera gestört ist.

## Datenschutz

- **Lokaler Betrieb:** Die Integration spricht nur mit dem Board Manager in deinem Netzwerk; ins Internet geht nichts.
- **Boards im Netzwerk suchen:** Fragt einmalig bei Benutzung `discover.autodarts.com`, den öffentlichen Suchdienst von Autodarts. Er sieht deine öffentliche IP-Adresse und liefert die von dort registrierten Boards.
- **Die optionale Cloud-Verknüpfung** nutzt die Geräteanmeldung von Autodarts. Home Assistant speichert OAuth-Token, nie dein Passwort.
- **Board-Geheimnisse** wie der API-Schlüssel des Boards, TLS-Schlüssel, Kamerapfade und ähnliche Konfiguration werden direkt beim Lesen verworfen. Sie werden nie gespeichert, protokolliert oder angezeigt.
- **Diagnosedaten** schwärzen Board-ID, Adresse, Client-ID und Token.

## Sicherheit

- Die lokale API des Board Managers verlangt keine Anmeldung. Jeder, der Port 3180 in deinem Netzwerk erreicht, kann sie nutzen, mit oder ohne Home Assistant. Betreibe den Board-PC in einem vertrauenswürdigen Netzwerk.
- Aktionen werden nur gesendet, wenn du oder eine Automation sie auslöst, und nie automatisch wiederholt.
