# Automationen

[← Übersicht](README.md) · [English](../automations.md)

Dein Board ist schnell genug für Automationen, die *während* des Spiels passieren. Das Licht flackert in dem Moment, in dem der dritte Dart einer 180 landet, und der Lautsprecher ruft die Punkte, bevor du am Board bist.

## Blueprints

Blueprints sind fertige Automationen. Importieren, Board und Geräte auswählen, fertig. Sie brauchen Home Assistant ab 2026.8 und folgen der aktuellen Version der Integration: Aktualisiere beide zusammen.

| Blueprint | Was er macht | Import |
| --- | --- | --- |
| **Celebrate a visit score** | Führt deine Aktionen für Aufnahmen ab einer Mindestpunktzahl aus (Standard 180), sobald der dritte Dart landet. Die Aktionen können `score`, `darts`, `segments` und `game` nutzen. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fvisit_score.yaml) |
| **Dart caller** | Sagt jede Aufnahme mit einer beliebigen Sprachausgabe auf deinen Lautsprechern an, mit eigener Ansage für 180, auf Wunsch auch jeden einzelnen Dart. Während eines Übungsspiels schweigt er, das sagt der Übungs-Caller an. Die Texte sind Vorlagen. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fdart_caller.yaml) |
| **Takeout actions** | Aktionen, wenn du die Darts ziehst und wenn das Board wieder frei ist, zum Beispiel für helleres Boardlicht. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftakeout.yaml) |
| **Start and stop detection automatically** | Startet die Erkennung, sobald jemand am Board ist, und stoppt sie nach einer frei wählbaren Pause. Kameras und Board-PC können so ruhen. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fauto_detection.yaml) |
| **Board problem alert** | Warnt nach einer Karenzzeit, wenn das Board offline geht oder eine Kamera ausfällt. Eine Entwarnung kommt nur nach einer echten Warnung. Die Aktionen können `problem` und `recovered` nutzen. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fboard_alert.yaml) |
| **Training report** | Tägliche Zusammenfassung mit Darts, 3-Dart-Average, höchster Aufnahme und 180ern; Tage ohne Darts werden übersprungen. Die Variable `summary` enthält den fertigen Satz. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftraining_report.yaml) |
| **Training session routine** | Beginnt eine [Trainingssession](entitaeten.md#trainingssession), führt sie deine Aktionen aus, schaltet die Erkennung ein und kalibriert nach kurzer Wartezeit die Kameras. Endet sie, schaltet sie die Erkennung aus und führt deine Aktionen mit `reason`, `darts`, `average` und `duration_minutes` aus. Erkennungsschalter und Kalibrierungstaste sind optional. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftraining_session.yaml) |
| **Practice caller** | Sagt das [Übungsspiel](entitaeten.md#übungsspiel) auf deinen Lautsprechern an: "Sam, you require 81", wenn ein Checkout möglich ist, "No score" nach dem Überwerfen, den Game shot eines Legs oder Matches und auf Wunsch das Ausbullen. Die Texte sind Vorlagen. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fpractice_caller.yaml) |
| **Weekly report** | Schickt deine [Trainingswoche](entitaeten.md#wochenbericht), wenn das Board sie beendet, standardmäßig montags um Mitternacht: Darts, Trainingszeit, Sessions, den 3-Dart-Average und seine Veränderung zur Vorwoche, beste Aufnahme, 180er, Checkout-Quote, Serie und neue Bestleistungen. Die Nachricht ist eine Vorlage; ohne eigene Aktionen erscheint der Bericht in den Benachrichtigungen von Home Assistant. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fweekly_report.yaml) |
| **Highlight photo** | Macht ein Bild mit einer Board-Kamera nach einer Aufnahme ab 180 Punkten (einstellbar) oder einem Checkout im Übungsspiel, solange die Darts noch im Board stecken. Es speichert das Bild in der [Highlight-Galerie](#highlight-galerie) und führt deine Aktionen aus, die `image`, `message`, `score`, `checkout`, `who` und `photo` nutzen können. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fhighlight_photo.yaml) |
| **Light show** | Spielt deine Lichteffekte, etwa WLED-Presets oder die Raumbeleuchtung, bei einer 180, einem High Finish, beim Überwerfen, bei einem gewonnenen Leg oder Match, einer Bestleistung, dem Tagesziel und einem gewonnenen Ausbullen, auf Wunsch auch bei der Entnahme und in [Online-Matches](#online-matches-experimentell). Danach kann er dein Licht wiederherstellen und die Erkennung während eines Effekts pausieren. | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Flight_show.yaml) |

Ohne My Home Assistant öffnest du **Einstellungen → Automationen & Szenen → Blueprints → Blueprint importieren**. Dort fügst du den Link zur Datei aus [`blueprints/automation/autodarts`](../../blueprints/automation/autodarts) ein. Um einen früher importierten Blueprint zu aktualisieren, importierst du ihn über sein Menü auf der Blueprint-Seite erneut; deine Automationen behalten ihre Einstellungen.

Die Blueprints sind auf Englisch beschriftet; ihre Texte kannst du beim Anlegen frei wählen.

### Welcher Caller?

- **Dart caller:** sagt jede Aufnahme an, in jedem Spiel am Board, etwa auch bei einem Online-Match. Während ein [Übungsspiel](entitaeten.md#übungsspiel) der Integration läuft, schweigt er, damit er dem Übungs-Caller nie ins Wort fällt. Schalte *Stay silent in practice games* aus, wenn du den Übungs-Caller nicht nutzt.
- **Practice caller:** sagt an, worauf es im Übungsspiel ankommt: Rest, Überwerfen, Game shot und auf Wunsch das Ausbullen.
- **Caller der Anzeigetafel:** Die [Anzeigetafel](karten.md#anzeigetafel) sagt Aufnahmen und Übungsspiel mit einer Stimme an, über den Browser des Bildschirms am Board. Dafür brauchst du keine Lautsprecher in Home Assistant.

## Einstellungen der Blueprints

Jeder Blueprint zeigt diese Einstellungen, wenn du eine Automation daraus anlegst. Einstellungen mit Standardwert sind optional.

### Celebrate a visit score

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| Minimum score | 180 | Die niedrigste Punktzahl einer Aufnahme, die die Aktionen auslöst. Eine Aufnahme aus drei Darts zählt, sobald ihr dritter Dart landet, eine kürzere beim Ziehen der Darts. |
| Actions | | Was nach einer solchen Aufnahme passiert. Nutzbar sind `score`, `darts`, `segments` und `game` (das Übungsspiel oder leer). |

### Dart caller

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| Text-to-speech engine | | Die Sprachausgabe, etwa Home Assistant Cloud oder Piper. |
| Speakers | | Die Mediaplayer, die die Ansagen abspielen. |
| Language | leer | Die Sprache der Stimme, etwa `de-DE`; leer nutzt die Sprache der Sprachausgabe. |
| Voice options | leer | Optionen der Sprachausgabe, etwa `voice: ...` für eine andere Stimme. |
| Call every dart | aus | Sagt zusätzlich jeden Dart an, sobald er landet. Der dritte Dart wird nicht einzeln angesagt, weil gleich die Aufnahme folgt. |
| Stay silent in practice games | an | Überlässt die Ansagen dem Übungs-Caller, solange ein X01-, Cricket- oder Partyspiel der Integration läuft. |
| Visit message | `{{ score }}` | Wird nach einer Aufnahme gesagt. Nutzbar sind `score`, `darts` und `segments`. |
| Message for 180 | `One hundred and eighty!` | Wird nach einer 180 statt der normalen Ansage gesagt. |
| Dart message | `{{ dart_name }}` | Wird für jeden Dart gesagt. Nutzbar sind `dart_name` (etwa `Treble 20`, `5`, `Bull` oder `Miss`), `segment` (etwa `T20`), `dart_score` und `dart_index`. |

Ein leerer Text bleibt stumm.

### Takeout actions

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| When the takeout starts | keine | Läuft, wenn eine Hand zum Board greift, um die Darts zu ziehen. |
| When the board is clear | keine | Läuft, wenn alle Darts aus dem Board sind. |

Fülle mindestens eines der beiden Felder aus.

### Start and stop detection automatically

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Presence | | Eine beliebige Ein/Aus-Entität, die an ist, solange jemand am Board ist: ein Präsenzmelder, das Raumlicht oder ein Input Boolean. |
| Detection switch | | Der Schalter *Erkennung* deines Boards. |
| Stop after | 10 Minuten | Wie lange die Präsenz aus sein muss, bevor die Erkennung stoppt. |

Kombiniere diesen Blueprint nicht mit einem Erkennungsschalter in der *Training session routine*: Beide würden die Erkennung schalten.

### Board problem alert

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board connection | | Der Sensor *Lokale Verbindung* deines Boards. |
| Camera problem | | Der Sensor *Kamerastörung* deines Boards. |
| Grace period | 2 Minuten | Wie lange ein Problem dauern muss, bevor gewarnt wird, damit ein Neustart des Board Managers oder eine kurze Kalibrierung ruhig bleibt. |
| Alert actions | | Zum Beispiel eine Benachrichtigung aufs Handy. `problem` ist `offline` oder `cameras`. |
| Recovery actions | keine | Laufen, wenn ein Problem vorbei ist, vor dem gewarnt wurde; `recovered` ist dann `true`. |

Ein Problem zählt auch, wenn es beginnt, während der Sensor nicht verfügbar ist, etwa eine Kamera, die beim Neustart des Boards ausfällt. Endet ein Problem, während das Board offline ist, gibt es dafür keine eigene Entwarnung; die Entwarnung der Verbindung deckt es ab.

### Training report

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Time | 21:00 | Wann der Bericht kommt. Wähle eine späte Uhrzeit: Darts zählen für den Tag, an dem sie geworfen werden. |
| Minimum darts | 1 | Kein Bericht, wenn heute weniger Darts geworfen wurden. |
| Training darts | | Der Sensor *Training Darts* deines Boards. |
| Training 3-dart average | | Der Sensor *Training 3-Dart-Average* deines Boards. |
| Training highest visit | | Der Sensor *Training höchste Aufnahme* deines Boards. |
| Training 180s | | Der Sensor *Training 180er* deines Boards. |
| Actions | | Zum Beispiel eine Benachrichtigung mit `summary`. Nutzbar sind auch `darts`, `average`, `highest`, `scores_180` und `darts_today`. |

Eine beendete Session behält ihre Summen bis zur nächsten. Deshalb prüft der Bericht den Sensor *Darts heute* desselben Boards und überspringt Tage ohne Darts. Ist dieser Sensor deaktiviert, entscheiden die Darts der Session. Für jeden Tag eine neue Session füge *Neue Trainingssession* deines Boards als letzte Aktion hinzu.

### Training session routine

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| Detection switch | keiner | Wird beim Start einer Session ein- und am Ende ausgeschaltet. |
| Calibration button | keine | Die Taste *Automatische Kalibrierung starten*, gedrückt nach dem Start der Erkennung. Hat der erste Dart die Session gestartet, entfällt sie, weil dieser Dart noch im Board steckt. |
| Wait before calibrating | 5 Sekunden | Gibt den Kameras Zeit zum Öffnen. |
| When a session starts | keine | Läuft zuerst, zum Beispiel um das Boardlicht einzuschalten. Das Board wird auch vorbereitet, wenn eine dieser Aktionen fehlschlägt. |
| When a session ends | keine | Läuft, nachdem die Erkennung gestoppt ist, mit `reason`, `darts`, `average` und `duration_minutes`. |
| Run for a new training session | aus | *Neue Trainingssession* beendet eine Session und startet sofort die nächste, etwa jeden Morgen per Automation. Standardmäßig läuft das Board dann einfach weiter; schalte das ein, damit auch dann der ganze Ablauf läuft. |

Lass die Kalibrierungstaste leer, wenn die Board-Einstellung *Beim Start kalibrieren* an ist: Das Board kalibriert dann beim Start der Erkennung von selbst. Kombiniere einen Erkennungsschalter hier nicht mit dem Blueprint, der die Erkennung automatisch startet und stoppt.

### Practice caller

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| Text-to-speech engine, Speakers, Language, Voice options | | Wie beim Dart caller. |
| Checkout possible | `{{ who ~ ', you' if who else 'You' }} require {{ remaining }}` | Wird gesagt, wenn die nächste Aufnahme das Leg beenden kann. |
| Next player | leer | Wird gesagt, wenn die nächste Aufnahme das Leg nicht beenden kann. Leer bleibt stumm. |
| Bust | `No score` | Wird gesagt, wenn ein Dart die Aufnahme überwirft. |
| Leg won | `Game shot, and the leg{{ ', ' ~ (team or who) if team or who }}!` | Wird gesagt, wenn ein Dart ein Leg gewinnt, das nicht das Match entscheidet; im Team-Match mit dem Namen des Teams. |
| Match won | `Game shot, and the match, {{ team or who }}!` | Wird gesagt, wenn ein Dart das Match entscheidet; im Team-Match mit dem Namen des Teams. |
| Bull-off throw | leer | Wird gesagt, wenn der nächste Spieler zum Ausbullen wirft, etwa `{{ who }}, throw for the bull`. Der erste Spieler des Ausbullens wird nicht aufgerufen. Leer nutzt den Text von *Next player*. |
| Bull-off won | leer | Wird gesagt, wenn das Ausbullen entscheidet, wer beginnt, zusammen mit der ersten Ansage des Matches, etwa `{{ who }} to throw first. Game on!`. Leer bleibt stumm. |
| Word for a player without a name | `Player` | Ergibt „Player 2“ in einem Match ohne Namen. |

### Highlight photo

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| Camera | | Die Board-Kamera, die das Foto macht. Aktiviere vorher die Kamera-Entität; Kamera-Entitäten sind standardmäßig deaktiviert. |
| Visits from | 180 | Eine Aufnahme mit mindestens diesen Punkten bekommt ein Foto, sobald ihr dritter Dart landet. |
| Checkouts | an | Auch ein Foto, wenn ein Übungsleg mit einem Checkout gewonnen wird. Beendet derselbe Dart eine Aufnahme und ein Leg, bekommst du ein Foto, mit dem Checkout-Text. |
| Save to the gallery | an | Speichert jedes Foto im Ordner darunter, für die [Highlight-Galerie](#highlight-galerie) der Medienansicht. |
| Folder | `/media/autodarts/highlights` | Wohin die Fotos kommen. Home Assistant OS und Container nutzen `/media`; andere Installationen den Ordner `media` im Konfigurationsordner, etwa `/config/media/autodarts/highlights`. |
| Actions | keine | Zum Beispiel eine Benachrichtigung, siehe [unten](#highlight-foto-aufs-handy). Optional, solange die Fotos in die Galerie gehen. |
| Message for a visit | `{{ score }}!` | Die `message` eines Aufnahme-Fotos. |
| Message for a checkout | `Checkout {{ checkout }}{{ ' by ' ~ who if who }}!` | Die `message` eines Checkout-Fotos. |

Deine Aktionen können `image` (das Kamerabild), `message`, `score`, `checkout`, `who` (der Spieler am Board, wenn das Übungsspiel ihn nennt) und `photo` (die Datei, in der das Bild gespeichert wird) nutzen.

### Light show

| Einstellung | Standard | Was sie bewirkt |
| --- | --- | --- |
| Board events | | Die Entität *Ereignisse* deines Boards. |
| Actions for a 180 | keine | Laufen, sobald der dritte Dart einer 180 landet. |
| High finish from | 100 | Ein Übungsleg, das mit einem Checkout ab diesen Punkten gewonnen wird, ist ein High Finish. |
| Actions for a high finish | keine | Laufen bei einem High Finish, statt der Aktionen für ein gewonnenes Leg. |
| Actions for a bust | keine | Laufen, wenn ein Dart im Übungsspiel die Aufnahme überwirft. |
| Actions for a won leg | keine | Laufen, wenn ein Dart ein Übungsleg gewinnt. Das Leg, das ein Match entscheidet, spielt stattdessen die Aktionen für das Match. |
| Actions for a won match | keine | Laufen, wenn ein Dart ein Übungsmatch entscheidet. |
| Actions for a personal best | keine | Laufen, wenn ein Wert deine [Bestleistung](entitaeten.md#bestleistungen-serie-und-tagesziel) übertrifft. |
| Actions for the daily goal | keine | Laufen, wenn die Darts von heute das Tagesziel erreichen. |
| Actions for a won bull-off | keine | Laufen, wenn das Ausbullen entscheidet, wer beginnt. |
| When the takeout starts | keine | Läuft, wenn eine Hand zum Board greift. Wird nicht wiederhergestellt. |
| When the board is clear | keine | Läuft, wenn alle Darts aus dem Board sind. Wird nicht wiederhergestellt. |
| Moments with an effect | keine | Die Momente, deren Aktionen einen Effekt starten. Nur für sie wird das Licht wiederhergestellt und die Erkennung pausiert. |
| Restore these lights | keine | Ihr Zustand wird vor einem Effekt gespeichert und danach wiederhergestellt. |
| Effect duration | 10 Sekunden | Wie lange ein Effekt spielt, bevor das Licht wiederhergestellt wird und die Erkennung wieder startet. |
| Pause the detection during effects | aus | Schaltet die Erkennung während eines Effekts aus und danach wieder ein, wenn sie an war. |
| Detection switch | keiner | Der Schalter *Erkennung* deines Boards, zum Pausieren. |
| Also react to online matches | aus | Spielt auch die Aktionen für Überwerfen, ein gewonnenes Leg und ein gewonnenes Match eines [Online-Matches](#online-matches-experimentell). Eine 180 und die Entnahme deiner eigenen Darts kommen sowieso von deinem Board. |

Die Aktionen können `moment` (`maximum`, `high_finish`, `bust`, `leg`, `match`, `personal_best`, `daily_goal`, `bull_off`, `takeout` oder `board_clear`), `who`, `player`, `score` (einer 180), `checkout` (eines gewonnenen Legs) und `trigger.to_state.attributes` für alle Details des [Board-Ereignisses](entitaeten.md#board-ereignisse) nutzen. Siehe [Lichtshow mit WLED und anderem Licht](#lichtshow-mit-wled-und-anderem-licht).

### Deutscher Dart-Caller

Wähle eine deutsche Stimme für die Sprachausgabe und trage zum Beispiel ein:

| Feld | Beispiel |
| --- | --- |
| Visit message | `{{ score }} Punkte` |
| Message for 180 | `Einhundertachtzig!` |
| Dart message | `{% if dart_score == 0 %}Daneben{% elif segment[:1] == 'T' %}Triple {{ segment[1:] }}{% elif segment[:1] == 'D' %}Doppel {{ segment[1:] }}{% elif segment[:1] == 'S' %}{{ segment[1:] }}{% else %}{{ segment }}{% endif %}` |

### Deutscher Übungs-Caller

Die Texte des Übungs-Callers sind Vorlagen mit diesen Variablen:

| Variable | Inhalt |
| --- | --- |
| `who` | Der Name des Spielers, „Spieler 2“ in einem Match ohne Namen, leer, wenn du allein spielst |
| `team` | Das Team des Spielers im [Team-Match](entitaeten.md#teams-und-startpunkte), etwa `Alex & Kim`, wenn beide Partner einen Namen haben; sonst leer |
| `remaining` | Der Rest |
| `checkout` | Der Weg, wenn ein Checkout möglich ist, etwa `T20 T20 BULL`; bei *Leg won* die ausgecheckten Punkte, etwa `121` |
| `darts`, `average` | Darts und 3-Dart-Average des Legs, bei *Leg won* |
| `points` | Punkte bei den Cricket- und Partyspielen; Schläge beim Golf, Runs beim Baseball |
| `target` | Das nächste Ziel eines Partyspiels, etwa `20`, `D` oder `D16`; das Loch beim Golf und das Inning beim Baseball |
| `hit` | Das Feld des siegreichen Darts beim Ausbullen, bei *Bull-off won*: `BULL`, `25` oder etwa `S20` |
| `distance` | Wie weit der siegreiche Dart beim Ausbullen von der Mitte entfernt landete, in Millimetern, bei *Bull-off won*; leer, wenn das Board für ihn keine Position gemeldet hat, nie `None` |

Zum Beispiel:

| Feld | Beispiel |
| --- | --- |
| Checkout possible | `{{ who ~ ', du' if who else 'Du' }} brauchst {{ remaining }}` |
| Next player | `{{ who }} ist dran`, bei Partyspielen `{{ who }} ist dran, {{ target }}` |
| Bust | `Überworfen` |
| Leg won | `Game shot und das Leg{{ ' für ' ~ who if who }}!` |
| Match won | `Game shot und das Match für {{ team or who }}!` |
| Bull-off throw | `{{ who }}, dein Wurf aufs Bull` |
| Bull-off won | `{{ who }} beginnt. Game on!`, oder `{{ who }} gewinnt das Ausbullen{{ ' mit ' ~ distance ~ ' Millimetern' if distance is number }}` |
| Word for a player without a name | `Spieler` |

### Deutscher Wochenbericht

Die fertige Variable `summary` ist englisch. Für einen deutschen Bericht trägst du bei *Title* und *Message* eigene Texte ein, im YAML-Modus der Automation zum Beispiel:

```yaml
use_blueprint:
  path: autodarts/weekly_report.yaml
  input:
    board_events: event.autodarts_board_events
    report_title: Deine Dartwoche
    report_message: >-
      {{ darts }} Darts{{ ' in ' ~ training_minutes ~ ' Minuten' if training_minutes else '' }}{{ ', 3-Dart-Average ' ~ (average | replace('.', ',')) ~ (' (' ~ ('+' if average_change > 0 else '') ~ (average_change | replace('.', ',')) ~ ')' if average_change is not none else '') if average is not none else '' }}{{ ', ' ~ scores_180 ~ ' × 180' if scores_180 else '' }}{{ ', ' ~ streak ~ (' Tag' if streak == 1 else ' Tage') ~ ' in Folge' if streak else '' }}.
```

Daraus wird etwa: *312 Darts in 95 Minuten, 3-Dart-Average 54,2 (+2,1), 1 × 180, 4 Tage in Folge.* Teile ohne Wert, etwa ohne 180er, lässt die Vorlage weg.

<img src="../images/de/weekly-report-notification.png" alt="Benachrichtigung „Deine Dartwoche“ in Home Assistant mit Darts, 3-Dart-Average und Trainingsserie der Woche" width="468">

Aufs Handy kommt der Bericht, wenn du unter *Notification actions* eine Benachrichtigung der Home-Assistant-App einträgst:

```yaml
action: notify.mobile_app_dein_handy
data:
  title: "{{ title }}"
  message: "{{ message }}"
```

### Highlight-Foto aufs Handy

Füge unter *Actions* des Highlight-Fotos eine Benachrichtigung der Home-Assistant-App hinzu und gib ihr das Bild mit:

```yaml
action: notify.mobile_app_dein_handy
data:
  message: "{{ message }}"
  data:
    image: "{{ image }}"
```

Die App lädt das Bild sofort von der Kamera, solange die Darts noch im Board stecken. Aktiviere vorher die Kamera-Entität auf der Geräteseite; Kamera-Entitäten sind standardmäßig deaktiviert.

### Highlight-Galerie

Das Highlight-Foto speichert jedes Bild als Datei, benannt nach Zeitpunkt, Spieler und Punkten, etwa `2026-09-26_21-05-33_Alex_180.jpg` oder `2026-09-26_21-07-10_Alex_checkout-121.jpg`. Öffne **Medien → Autodarts** in der Seitenleiste: Die Galerie listet die Monate, die neuesten zuerst, und jedes Foto mit einem Titel wie *180 · Alex · 26.09.*

<img src="../images/de/media-gallery.png" alt="Die Highlight-Galerie in der Medienansicht von Home Assistant: September 2026 mit einem Checkout von 121 durch Sam, einer 180 von Alex und einer 140 von Kim" width="760">

- Die Galerie zeigt den Ordner `autodarts/highlights` im Medienordner von Home Assistant, also `/media/autodarts/highlights` unter Home Assistant OS und im Container. [So funktioniert die Galerie](funktionsweise.md#highlight-galerie).
- Fotos, die du selbst dorthin kopierst, erscheinen auch; ohne einen solchen Namen mit ihrem Dateinamen und der Zeit, zu der sie gespeichert wurden.
- Um ein Foto zu löschen, öffne **Medien → Meine Medien → autodarts → highlights**.
- Die Galerie braucht die Medienansicht, die zur Standardkonfiguration von Home Assistant gehört.

### Lichtshow mit WLED und anderem Licht

Gib jedem Moment, den du magst, eigene Aktionen; Momente ohne Aktionen bleiben dunkel. Ein WLED-Preset, das du in WLED als „180“ gespeichert hast, für eine 180:

```yaml
action: select.select_option
target:
  entity_id: select.wled_preset
data:
  option: "180"
```

Ein WLED-Effekt in voller Helligkeit, etwa für ein gewonnenes Match:

```yaml
action: light.turn_on
target:
  entity_id: light.wled
data:
  effect: Fireworks
  brightness_pct: 100
```

Normale Raumbeleuchtung in der Farbe des Spielers, der das Leg gewonnen hat, von Spieler 1 bis 4; beim Überwerfen färbt `rgb_color: [255, 0, 0]` sie rot:

```yaml
action: light.turn_on
target:
  entity_id: light.dartraum
data:
  rgb_color: "{{ [[255, 0, 0], [0, 90, 255], [0, 200, 80], [255, 200, 0]][player - 1] }}"
  brightness_pct: 100
```

- **Zurück zum normalen Licht:** Wähle unter *Moments with an effect* die Momente mit Aktionen und trage deine Lampen unter *Restore these lights* ein, bei WLED die WLED-Lampe, nicht die Preset-Auswahl. Vor einem Effekt speichert der Blueprint ihren Zustand in einer Szene und stellt nach *Effect duration* Farbe, Helligkeit und Effekt wieder her. Lass die Lampen leer, wenn deine Aktionen den Effekt selbst beenden. Nicht gewählte Momente führen nur ihre Aktionen aus, ein Moment ohne Aktionen hält das Board also nie an.
- **Erkennung pausieren:** Blinkendes Licht neben dem Board kann die Kameras Darts sehen lassen, die nicht da sind. Schalte *Pause the detection during effects* ein und wähle den Schalter *Erkennung*: Die Erkennung stoppt für die Effekte der gewählten Momente und startet danach wieder, aber nur, wenn sie lief. Stoppt die Erkennung, gilt die Aufnahme im Board als beendet, wie nach einer Entnahme: Das Übungsspiel verbucht sie, und der nächste Spieler ist dran.
- **Einer nach dem anderen:** Ein Moment, der während eines Effekts passiert, wartet auf ihn, und jeder Effekt stellt das Licht wieder her, das er vorgefunden hat. Höchstens zwei Momente warten; die Automation läuft im Modus „queued“, weil ein neu gestarteter Effekt das Licht nie wiederherstellen würde und parallele Effekte sich auf denselben Lampen mischen würden.
- **Entnahme und freies Board** setzen ein eigenes Licht, etwa helles Boardlicht beim Ziehen der Darts und danach dein normales Licht. Sie werden nicht wiederhergestellt und pausieren die Erkennung nicht.

## Board-Ereignisse

Alle Echtzeitmomente kommen über die Entität **Ereignisse** des Boards. Jedes Ereignis hat einen `event_type` und seine Details, siehe [Ereignisse](entitaeten.md#board-ereignisse). Die Beispiele nutzen `event.autodarts_board_events`, die Entitäts-ID eines Boards namens *Autodarts Board*; ein mit einer früheren Version eingerichtetes Board behält `event.autodarts_board_board_events`.

Im Automationseditor wählst du den Auslöser **Ereignis empfangen** (*Entität → Ereignis*), die Entität *Ereignisse* deines Boards und die gewünschten Ereignistypen. In YAML:

```yaml
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - visit_thrown
```

Eine Aufnahme aus drei Darts kommt als `visit_thrown`, sobald ihr dritter Dart landet, und als `visit_completed`, wenn die Darts gezogen werden. Für Feiern und Ansagen nutzt du `visit_thrown` und für Aufnahmen mit weniger Darts zusätzlich `visit_completed`, dessen Attribut `thrown` gleich `false` ist.

Lies die Details aus `trigger.to_state.attributes`, nicht aus dem aktuellen Zustand der Entität. Zwei Ereignisse können innerhalb von Millisekunden aufeinander folgen, etwa `visit_completed` und `takeout_finished`. Der aktuelle Zustand zeigt dann womöglich schon das zweite.

## Beispiele

Die Entitäts-IDs in den Beispielen hängen vom Namen deines Boards und der Sprache bei der Einrichtung ab. Du findest sie auf der Geräteseite des Boards.

### Lichtshow bei einer 180

```yaml
alias: Darts – 180-Lichtshow
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - visit_thrown
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.get('score') == 180 }}"
actions:
  - action: light.turn_on
    target:
      entity_id: light.dartraum
    data:
      effect: colorloop
  - delay: 10
  - action: light.turn_on
    target:
      entity_id: light.dartraum
    data:
      effect: none
      brightness_pct: 100
mode: single
```

### Boardlicht bei der Entnahme

```yaml
alias: Darts – Licht bei der Entnahme
triggers:
  - trigger: event.received
    id: started
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - takeout_started
  - trigger: event.received
    id: finished
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - takeout_finished
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: started
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.boardlicht
            data:
              brightness_pct: 100
    default:
      - action: light.turn_on
        target:
          entity_id: light.boardlicht
        data:
          brightness_pct: 60
mode: queued
```

### Kamerastörung melden

```yaml
alias: Darts – Kamerastörung
triggers:
  - trigger: state
    entity_id: binary_sensor.autodarts_board_camera_problem
    to: "on"
    for:
      minutes: 2
actions:
  - action: notify.mobile_app_handy
    data:
      title: Autodarts
      message: Eine Board-Kamera liefert keine Bilder. Prüfe Kamera und Kabel.
mode: single
```

### Erkennung nachts stoppen

```yaml
alias: Darts – Erkennung nachts stoppen
triggers:
  - trigger: time
    at: "01:00:00"
conditions:
  - condition: state
    entity_id: switch.autodarts_board_detection
    state: "on"
actions:
  - action: switch.turn_off
    target:
      entity_id: switch.autodarts_board_detection
mode: single
```

### Das Board zum Start einer Trainingssession vorbereiten

Schalte beim Start einer Session das Boardlicht ein, starte die Erkennung und kalibriere die Kameras; beim Ende schaltest du alles wieder aus. Schalte *Sessions automatisch starten* aus und starte Sessions mit dem Schalter *Trainingssession*, zum Beispiel über die Trainingskarte. Lass die Kalibrierung weg, wenn die Board-Einstellung *Beim Start kalibrieren* an ist, und kombiniere das nicht mit Automationen, die die Erkennung nach Anwesenheit schalten.

```yaml
alias: Darts – Ablauf der Trainingssession
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - session_started
    id: started
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - session_ended
    id: ended
conditions:
  # „Neue Trainingssession“ beendet eine Session und startet sofort die nächste.
  - condition: template
    value_template: "{{ trigger.to_state.attributes.get('reason') != 'new_session' }}"
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: started
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.dart_board
          - action: switch.turn_on
            target:
              entity_id: switch.autodarts_board_detection
          # Der Dart, der eine Session gestartet hat, steckt noch im Board.
          - if:
              - condition: template
                value_template: "{{ trigger.to_state.attributes.get('reason') != 'first_dart' }}"
            then:
              # Gib den Kameras Zeit zum Öffnen.
              - delay: 5
              - action: button.press
                target:
                  entity_id: button.autodarts_board_start_automatic_calibration
      - conditions:
          - condition: trigger
            id: ended
        sequence:
          - action: switch.turn_off
            target:
              entity_id: switch.autodarts_board_detection
          - action: light.turn_off
            target:
              entity_id: light.dart_board
mode: queued
```

### Jeden Montag eine neue Trainingssession

```yaml
alias: Darts – wöchentliche Trainingssession
triggers:
  - trigger: time
    at: "04:00:00"
conditions:
  - condition: time
    weekday: mon
actions:
  - action: button.press
    target:
      entity_id: button.autodarts_board_new_training_session
mode: single
```

### Game shot im Übungsspiel ansagen

Sagt ein gewonnenes Leg und ein Überwerfen im [Übungsspiel](entitaeten.md#übungsspiel) mit dem Namen des Spielers auf deinen Lautsprechern an.

```yaml
alias: Darts – Ansage im Übungsspiel
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - leg_won
        - bust
actions:
  - action: tts.speak
    target:
      entity_id: tts.home_assistant_cloud
    data:
      media_player_entity_id: media_player.dartraum
      message: >-
        {% set event = trigger.to_state.attributes %}
        {# Im Team-Match gewinnt das Team das Leg. #}
        {% set spieler = event.team_name or event.name or 'Spieler ' ~ event.player %}
        {% if event.event_type == 'leg_won' %}
          Game shot, das Leg für {{ spieler }} mit {{ event.darts }} Darts.
        {% else %}
          Überworfen. {{ spieler }}, du brauchst weiter {{ event.remaining }}.
        {% endif %}
mode: queued
```

### Die Zusammenfassung eines Matches senden

Schickt nach einem Übungsmatch mehrerer Spieler die Zahlen jedes Spielers aufs Handy. `match_won` bringt die [Match-Zusammenfassung](entitaeten.md#übungsspiel) in `summary` mit; X01 hat Averages und Checkouts, Cricket `mpr` und `marks`.

```yaml
alias: Darts – Match-Zusammenfassung
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - match_won
actions:
  - action: notify.mobile_app_handy
    data:
      title: "{{ trigger.to_state.attributes.name or 'Spieler ' ~ trigger.to_state.attributes.player }} gewinnt"
      message: >-
        {%- for player in trigger.to_state.attributes.summary %}
        {{ player.name or 'Spieler ' ~ player.player }}: Legs {{ player.legs }}
        {%- if player.get('average') is not none %}, Average {{ player.average }}{% endif %}
        {%- if 'scores_180' in player %}, 180er {{ player.scores_180 }}{% endif %}
        {%- if player.get('checkout_rate') is not none %}, Checkout {{ player.checkout_rate }} %{% endif %}
        {%- if player.get('mpr') is not none %}, MPR {{ player.mpr }}{% endif %}.
        {%- endfor %}
mode: queued
```

### Bestleistung und Tagesziel feiern

```yaml
alias: Darts – Bestleistung
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - personal_best
        - daily_goal_reached
actions:
  - action: notify.mobile_app_handy
    data:
      message: >-
        {% set event = trigger.to_state.attributes %}
        {% if event.event_type == 'personal_best' %}
          Neue Bestleistung: {{ event.record | replace('_', ' ') }} {{ event.value }}
          (vorher {{ event.previous }}){{ ' von ' ~ event.name if event.name }}!
        {% else %}
          Tagesziel erreicht: {{ event.darts }} Darts, {{ event.streak }} Tage in Folge.
        {% endif %}
mode: queued
```

### Trainingssessions des Monats zählen

Der [Trainingskalender](entitaeten.md#trainingskalender) beantwortet Fragen zur Vergangenheit, etwa in einem Skript:

```yaml
sequence:
  - action: calendar.get_events
    target:
      entity_id: calendar.autodarts_board_training_calendar
    data:
      start_date_time: "{{ now().replace(day=1, hour=0, minute=0, second=0) }}"
      end_date_time: "{{ now() }}"
    response_variable: kalender
  - variables:
      sessions: >-
        {{ kalender['calendar.autodarts_board_training_calendar'].events
           | selectattr('summary', 'match', 'Training') | list | count }}
```

### Spiel per Sprache starten

Mit dem Sprachassistenten Assist startet ein Satz das Spiel. `{names}` nimmt den Rest des Satzes auf, etwa „Dennis und Lea“ oder „Dennis, Lea und Sam“. Das Spiel kommt als gesprochene Wörter an, deshalb macht die Automation aus „Halve it“, „Around the Clock“ oder „Bob's 27“ die Namen der Aktion: `halve_it`, `around_the_clock` und `bobs_27`.

```yaml
alias: Darts – per Sprache starten
triggers:
  - trigger: conversation
    command:
      - "starte {game} für {names}"
actions:
  - action: autodarts.start_game
    data:
      game: >-
        {{ trigger.slots.game | lower | replace("'", "") | replace("-", " ")
           | replace(" ", "_") }}
      players: "{{ (trigger.slots.names | replace(', ', ' und ')).split(' und ') }}"
  - set_conversation_response: "Game on, {{ trigger.slots.names }}!"
mode: single
```

## Online-Matches (experimentell)

Die Integration sieht die Darts auf deinem Board auch in einem Online-Match auf play.autodarts.io: `dart_detected`, `visit_thrown` und die Entnahme kommen wie gewohnt. Das Spiel selbst sieht sie nicht: Überwerfen, ein gewonnenes Leg oder Match und die Darts deiner Gegner passieren im Browser. Autodarts teilt sie nur über seine Cloud, und dafür fehlt noch eine Client-ID.

Die optionale **Online-Brücke** bringt diese Momente mit der Browser-Erweiterung [Tools for Autodarts](https://github.com/creazy231/tools-for-autodarts) nach Home Assistant. Deren WLED-Funktion ruft für jeden Moment des Spiels eine Adresse deiner Wahl auf. Die Brücke bietet dafür eine geheime Adresse von Home Assistant an und macht aus jedem Aufruf ein [Board-Ereignis](entitaeten.md#board-ereignisse), dessen Typ mit `online_` beginnt und dessen `source` `online` ist. Standardmäßig ist sie aus.

### Brücke einrichten

1. Öffne **Einstellungen → Geräte & Dienste → Autodarts**, dort **Konfigurieren** (das Zahnrad) deines Boards, schalte **Online-Matches von Tools for Autodarts empfangen** ein und sende ab.
2. Der nächste Schritt zeigt die geheime Adresse und fertige Zeilen für Tools for Autodarts. Kopiere die Zeilen und sende ab. Ab jetzt nimmt Home Assistant Aufrufe unter der Adresse an. Öffne die Optionen wieder, wann immer du die Adresse brauchst.
3. Öffne im Browser am Board die Einstellungen von Tools for Autodarts, schalte **WLED** ein, wähle **Import CSV**, füge die Zeilen ein und speichere. Jede Zeile ist ein Effekt vom Typ **URL** für einen Trigger; lösche die, die du nicht brauchst.
4. Prüfe, ob die Momente ankommen: Öffne die Adresse mit angehängtem `?event=gameon` in einem Browser in deinem Heimnetz, oder spiele ein Match. Der Sensor **Letztes Ereignis der Online-Brücke** auf der Geräteseite unter *Diagnose* zeigt, wann der letzte Moment ankam, und seinen Trigger.

Für einen Effekt von Hand gibst du ihm einen Trigger, den Typ **URL** und die Adresse mit `?event=` und demselben Trigger, zum Beispiel `…/api/webhook/<geheim>?event=busted`. Der Name eines Spielers kann als `&player=Lea` folgen. Ein Effekt vom Typ **JSON API** geht auch, mit einem Body wie `{"event": "busted", "player": "Lea"}`.

### Trigger und Ereignisse

| Trigger in Tools for Autodarts | Board-Ereignis | Details |
| --- | --- | --- |
| `gameon`, `bot_throw` | `online_game_on` | Tools for Autodarts sendet `gameon` zu Beginn jeder Aufnahme und nach jedem Moment ohne eigenen Effekt: ein guter Moment für dein normales Licht. |
| `busted` | `online_busted` | Überworfen. |
| `gameshot`, `gameshot+d10`, `gameshot_<name>` | `online_game_shot` | Ein gewonnenes Leg, mit dem `segment` des Siegerdarts oder dem `name` des Spielers, wenn der Trigger sie nennt. |
| `matchshot`, `matchshot+bull`, `matchshot_<name>` | `online_match_shot` | Ein gewonnenes Match, mit denselben Details. |
| `0` bis `180` | `online_visit` | Die Punkte (`score`) einer Aufnahme. |
| `range_100_140` oder `100-140` | `online_visit` | Eine Aufnahme in dem Bereich, mit `score_min` und `score_max`. |
| Drei Darts wie `t20_t20_t20` | `online_visit` | `score`, `darts` und `segments` (zum Beispiel `["T20", "T20", "T20"]`). |
| `t20`, `d16`, `s5`, `s25`, `bull`, `m17`, `miss`, `outside` | `online_dart` | Ein Dart, mit `segment` (`T20`, `D16`, `S5`, `25`, `BULL` oder `MISS`) und `score`. |
| `bulloff` | `online_bull_off` | Das Ausbullen beginnt. |
| `tournament_ready` | `online_tournament_ready` | Ein Turniermatch von dir wartet darauf, dass du dich bereit meldest. |
| `idle` | `online_match_left` | Du hast das Match verlassen. |
| `other` | keins | Ein Moment auf einem anderen Board; die Brücke ignoriert ihn. |

Jedes Online-Ereignis hat `trigger` (wie gesendet, kleingeschrieben), `source` (`online`) und `name`, wenn die Adresse `&player=` enthält. Eine reine Zahl ist immer die Punktzahl einer Aufnahme: `25` ist eine Aufnahme mit 25 Punkten, `s25` ein Dart im Single-Bull. Die Board-Trigger von Tools for Autodarts wie `board_started`, `throw` oder `takeout` nimmt die Brücke nicht an: Die Board-Ereignisse melden sie direkt von deinem Board, schneller und ohne Browser.

- **Deine eigenen Darts** kommen sowieso vom Board: `dart_detected`, `visit_thrown` und die Entnahme sind schneller als die Erweiterung und funktionieren ohne sie. Nutze die Online-Ereignisse für das, was nur das Match weiß: Überwerfen, gewonnene Legs und Matches und die Darts deiner Gegner.
- **Nur dein Board:** Tools for Autodarts meldet die Momente aller Spieler im Match, auch die deiner Gegner. Um nur auf dein Board zu reagieren, trägst du in den WLED-Einstellungen unter **Board IDs** deine Board-ID ein und behältst die Zeile `other`: Momente auf anderen Boards senden dann stattdessen `other`.
- **Lichtshow:** Schalte in der [Lichtshow](#light-show) *Also react to online matches* ein, damit sie Überwerfen, gewonnene Legs und gewonnene Matches in Online-Matches spielt.

Eine Benachrichtigung, wenn ein Turniermatch bereit ist:

```yaml
alias: Darts - Turniermatch bereit
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - online_tournament_ready
actions:
  - action: notify.mobile_app_handy
    data:
      message: Dein Turniermatch ist bereit. Melde dich bei Autodarts bereit.
mode: single
```

### Sicherheit

- Die Adresse enthält ein Geheimnis aus 64 zufälligen Hexadezimalzeichen. Wer sie kennt, kann deinem Home Assistant Momente eines Spiels senden, sonst nichts: Die Brücke nimmt nur die Trigger oben an, Felder begrenzter Länge und höchstens 20 Aufrufe pro Sekunde. Die Integration schreibt die Adresse nie ins Log, und die Diagnosedaten enthalten sie nicht. Home Assistant selbst nennt sie in einigen eigenen Warnungen, etwa zu einem Aufruf von außerhalb deines Netzes; prüfe Logs also, bevor du sie teilst.
- Standardmäßig können nur Geräte in deinem Heimnetz die Adresse aufrufen; Aufrufe aus dem Internet ignoriert Home Assistant. Schalte **Aufrufe von außerhalb deines Heimnetzes annehmen** nur für eine https-Adresse über Home Assistant Cloud oder deine eigene Domain ein.
- Ist die Adresse nach außen gelangt, schalte in den Optionen **Neue geheime Adresse erzeugen** ein und importiere die neuen Zeilen in Tools for Autodarts. Die alte Adresse funktioniert dann nicht mehr.
- Ausgeschaltet gibt es die Brücke nicht: Home Assistant beantwortet ihre Adresse wie jede unbekannte. Die Integration behält die Adresse für das nächste Einschalten.

### Grenzen

- **Eine Browser-Erweiterung von Dritten.** Momente kommen nur an, solange die Autodarts-Seite in einem Browser mit Tools for Autodarts und eingeschalteter WLED-Funktion offen ist. Ändert die Erweiterung ihre Trigger, braucht die Brücke eventuell ein Update. Ereignisse werden nie nachgeliefert.
- **Ein Effekt pro Trigger.** Tools for Autodarts spielt pro Trigger einen Effekt und wählt zufällig einen aus, wenn sich mehrere Effekte einen Trigger teilen. Ein Trigger, der in der Erweiterung ein WLED-Gerät und gleichzeitig Home Assistant steuert, erreicht beide nur hin und wieder. Lass Home Assistant dein Licht steuern, etwa mit der Lichtshow, oder nutze getrennte Trigger.
- **Effekte nur einmal.** Mit *trigger Effects only once* überspringt die Erweiterung einen Effekt, der schon läuft; derselbe Moment zweimal hintereinander kommt dann einmal an.
- **Gemischte Inhalte.** play.autodarts.io ist eine https-Seite, und Browser blockieren womöglich ihre Aufrufe einer reinen http-Adresse; die Erweiterung warnt davor, wenn du eine einträgst. Das funktioniert:
  - Eine https-Adresse von Home Assistant mit vertrauenswürdigem Zertifikat, etwa deine Adresse von Home Assistant Cloud oder deine eigene Domain. Schalte *Aufrufe von außerhalb deines Heimnetzes annehmen* ein, außer der Browser erreicht diese Adresse innerhalb deines Heimnetzes.
  - Eine reine http-Adresse in deinem Heimnetz wie `http://homeassistant.local:8123`, wenn der Browser die Aufrufe durchlässt: Erlaube in den Website-Einstellungen von Chrome oder Edge *Unsichere Inhalte* für play.autodarts.io, und erlaube den Zugriff auf Geräte in deinem lokalen Netzwerk, wenn der Browser fragt.
  - Was du auch wählst: Der Sensor *Letztes Ereignis der Online-Brücke* zeigt, ob die Momente ankommen.
- **Nur Board-Ereignisse.** Online-Momente zählen nicht für die Trainingssession, das Übungsspiel oder die Bestleistungen.

## Automationen älterer Versionen anpassen

Automationen, die eine 180 feiern oder eine Aufnahme mit `visit_completed` ansagen, reagieren erst beim Ziehen der Darts. Stelle sie auf `visit_thrown` um, dann reagieren sie, sobald der dritte Dart landet, wie in den [Beispielen](#lichtshow-bei-einer-180).

Ab Version 1.0 meldet der Sensor **Erkennungsstatus** übersetzbare Zustände wie `stopped`, `throw` oder `takeout_in_progress`. Ältere Versionen meldeten den Rohtext des Board Managers, etwa `Stopped` oder `Takeout in progress`. Passe Automationen an, die mit dem alten Text vergleichen:

| Vorher | Jetzt |
| --- | --- |
| `Stopped` | `stopped` |
| `Starting`, `Stopping` | `starting`, `stopping` |
| `Throw` | `throw` |
| `Takeout`, `Takeout in progress` | `takeout`, `takeout_in_progress` |
| `Calibrating` | `calibrating` |
| `Error` | `error` |

Die Oberfläche zeigt diese Zustände übersetzt an. Der Sensor *Letztes Ereignis* liefert weiterhin den Rohtext.
