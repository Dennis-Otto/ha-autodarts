# Entwicklung: Bilder und Prüfungen der Karten

[← Dokumentation](README.de.md)

Die vollständige Entwickler-Dokumentation ist auf Englisch: [Development](development.md). Diese Seite beschreibt auf Deutsch, wie die Bilder der Dokumentation entstehen und wie sie aktuell bleiben, wie die Karten bei jeder Änderung auf ihr Aussehen und ihre Barrierefreiheit geprüft werden, wie der Browsertest dabei wartet und in vier Teilen nebeneinander läuft, wie ihre Tests die Timer der Karten prüfen und wann die End-to-End-Tests laufen.

**Auf dieser Seite:** [Bilder der Dokumentation](#bilder-der-dokumentation) · [In jedem Lauf dieselben Bilder](#in-jedem-lauf-dieselben-bilder) · [Screenshot-Bot](#screenshot-bot) · [Bildvergleich](#bildvergleich) · [Wie der Browsertest wartet](#wie-der-browsertest-wartet) · [Der Browsertest in Teilen](#der-browsertest-in-teilen) · [Prüfung der Barrierefreiheit](#prüfung-der-barrierefreiheit) · [Timer der Karten](#timer-der-karten) · [Wann die End-to-End-Tests laufen](#wann-die-end-to-end-tests-laufen)

## Bilder der Dokumentation

`tests/e2e/screenshots.sh` erzeugt jedes Bild in `docs/images/en` und `docs/images/de` neu aus der Demo, auch die animierten WebP-Bilder, und komprimiert die PNG-Bilder mit pngquant. `tests/e2e/screenshots.py` hat eine Funktion pro Bild oder Animation, sodass sich ein einzelnes Bild neu erzeugen lässt, indem man seine Funktion gegen eine laufende Demo aufruft. Jedes Bild zeigt das simulierte Board und erfundene Spieler, persönliche Daten können also nicht erscheinen; die geheime Adresse der Online-Brücke wird abgedeckt. Die Suche im Netzwerk öffnet das Werkzeug nie, sie würde echte Boards zeigen. Die Diagramme in `docs/images` entstehen dagegen mit `scripts/render_diagrams.sh`.

Schlägt eine Aufnahme fehl, speichert das Werkzeug jede offene Seite in `tests/e2e/artifacts/`. Git ignoriert diesen Ordner.

## In jedem Lauf dieselben Bilder

Zwei Läufe des Werkzeugs erzeugen dieselben Bilder, Byte für Byte. Ein Bild, das sich ändert, zeigt also immer eine Karte oder eine Seite, die sich geändert hat, und [Screenshot-Bot](#screenshot-bot) und [Bildvergleich](#bildvergleich) erkennen das:

- **Eine eingefrorene Uhr.** Die Demo der Screenshots steht auf Dienstag, dem 29. September 2026, 20:30 Uhr (`DEMO_TIME` in `screenshots.sh`), ganz gleich, wann sie läuft. `tests/e2e/frozen/sitecustomize.py` stellt diese Uhr für Home Assistant und jedes Skript in seinem Container, über `compose.frozen.yaml`, das `demo.sh` hinzunimmt, wenn `DEMO_TIME` gesetzt ist. Die Uhr geht nur weiter, wenn die Demo sie weiterstellt: Jede Bewegung am simulierten Board, ein Dart, das Herausziehen oder ein neuer Status, dauert zwei Sekunden, in `demo.py` wie in `screenshots.py`, geschrieben in die Datei `.demo_clock` in der Konfiguration der Demo. So kommt jede Zeit, die Home Assistant festhält, in jedem Lauf gleich heraus, auf die Millisekunde, während der Verlauf des Boards, die Länge einer Session und die Trainingszeit des Wochenberichts aussehen wie an einem echten Abend; der Wochenbericht bekommt die Minute, auf die er wartet, auf dieselbe Weise. Auch der Browser zeigt die Zeit der Demo: Die Uhr von Playwright steht auf ihr still, außer in den Seiten der Spiel-Animationen, in denen das Ergebnis eines Turnierspiels seine Zeit lang stehen bleiben muss; ihre Bilder zeigen keine Uhrzeit. Die Seite der Statistik-Grafiken wünscht reduzierte Bewegung, damit Home Assistant ihre Linien sofort zeichnet statt als Animation, die die stehende Uhr anhalten würde.
- **Eine Quelle für Änderungen.** Die eingefrorene Demo fragt das Board nicht regelmäßig ab: Jede Änderung kommt über die Verbindung zum Board, in der Reihenfolge, in der das Board sie sendet, nie zuerst aus einer Abfrage, deren Zeitpunkt vom Lauf abhängt.
- **Feste Zufallszahlen.** Die Darts des Bots und jede andere Zufallszahl ohne eigenen Startwert beginnen mit demselben Startwert.
- **Ruhige Bilder.** Vor jedem Screenshot und jedem Bild einer Animation wartet das Werkzeug auf Bilder, die noch laden, lässt Übergänge und Einblendungen an ihr Ende springen und hält endlose Animationen wie die blinkenden Felder im selben Moment an. Das wiederholt es, bis sich keine Karte mehr ändert und zwei Blicke im Abstand einer Zehntelsekunde nichts finden, das sich bewegt. Chromium zeichnet jedes Bild ganz und animiert auf seinem Hauptthread (`STEADY_CHROMIUM` in `screenshots.py`). Die Werkzeugleiste eines Dashboards wirft keinen Schatten auf das, was unter ihr scrollt, eine Karte, die höher als der Bildschirm ist, wird vom Anfang der Seite aufgenommen, und der Dialog der Board-Ereignisse öffnet sich erst, wenn der Rekorder das letzte Ereignis geschrieben hat, das er zeigt (`RECORDED`), nicht nach einer festen Zeit.
- **Farben in fester Reihenfolge.** Home Assistant gibt jedem Zustand, den es in einem Verlauf oder einer Aktivitätsliste zeichnet, eine eigene Farbe, die nächste seiner Palette, in der Reihenfolge, in der es die Zustände zuerst zeichnet, solange die Seite besteht; die Ereignis-Entität des Boards bekommt mit jedem Ereignis einen neuen Zustand. Die Zeitleiste eines Verlaufs zeichnet in jedem Pixel nur den Zustand, der dort am längsten dauert. Welche Zustände sie zuerst färbt, hängt also von ihrer Breite in dem Moment ab, in dem ihre Daten ankommen, und Verlauf und Aktivität des Dialogs kommen in beliebiger Reihenfolge an. Deshalb zeichnet das Werkzeug, bevor sich der Dialog öffnet, jedes Ereignis der letzten 24 Stunden einmal, das neueste zuerst, in einer eigenen, unsichtbaren Aktivitätsliste (`COLOUR_EVENTS` in `screenshots.py`): Der Dialog findet jedes Ereignis gefärbt vor, und die neuesten bekommen immer die ersten Farben der Palette, ganz gleich, wie viele Ereignisse davor kamen.
- **Alle Texte der Einstellungen.** Home Assistant lädt die Texte seiner Einstellungen, etwa die Namen ihrer Tabs, getrennt von seinen übrigen Texten. Es führt jede Ladung mit den Texten zusammen, die es schon hat, zeigt aber nur, was seine neueste Ladung zusammengestellt hat, und verlässt sich darauf, dass seine Timer ohne Verzögerung in der Reihenfolge laufen, in der sie angefordert wurden. Das müssen sie nicht: Chrome hält einen Timer zurück, der tief in anderen Timern angefordert wird, und die stehende Uhr von Playwright einen, der während eines Ticks angefordert wird. Überholt eine spätere Ladung die der Einstellungen, fehlen einer Seite der Einstellungen die Namen ihrer Tabs und die Köpfe ihrer Spalten, solange die Seite besteht; so sind zwei Läufe des Screenshot-Bots gescheitert. Deshalb warten die Seiten der Einstellungen, bis ihre Texte zusammengeführt sind, und lassen Home Assistant seine Texte dann noch einmal aktualisieren (`SETTINGS_TEXTS` in `screenshots.py`).
- **Feste Adressen.** Die Online-Brücke zeigt `homeassistant.local` als Adresse von Home Assistant (`internal_url` in `demo.configuration.yaml`), nicht die Adresse, die Docker dem Container zufällig gibt.
- **Eine feste Version.** Hinter den Optionen der Online-Brücke zeigt die Seite der Integration ihre Version, und jedes Release ändert sie. In der eingefrorenen Demo lässt `sitecustomize.py` Home Assistant nur die Hauptversion aus dem Manifest lesen: Die Seite zeigt *Version 1* für jedes Release 1.x. So ändert ein Release kein Bild, und der Bildvergleich meldet das Bild danach nicht bei jedem Pull Request. Alles andere auf der Seite zeigt Home Assistant so, wie es ist; außerhalb der eingefrorenen Demo zeigt es die volle Version.
- **Festgelegte Kompression.** pngquant 2.18.0 aus Ubuntu 24.04 komprimiert jedes PNG-Bild direkt nach der Aufnahme. `tests/e2e/pngquant.sh` installiert es im festgelegten Playwright-Image von Launchpad, wo jedes veröffentlichte Paket seine Adresse behält, und prüft beide Pakete gegen ihre SHA-256-Prüfsumme. Die Animationen entstehen mit dem festgelegten Pillow.

Um herauszufinden, was sich zwischen zwei Läufen unterscheidet, behält `KEEP_RAW=1` jedes Bild und jedes Bild einer Animation so, wie es aufgenommen wurde, vor der Kompression, in `tests/e2e/artifacts/raw/`, einem Ordner pro Sprache; `tests/e2e/compare.py` vergleicht zwei Ordner mit Bildern.

Ohne `DEMO_TIME`, wie bei `demo.sh` für eine Vorschau oder bei `browser.sh`, läuft die Demo mit der echten Uhr.

## Screenshot-Bot

Der Workflow **Screenshot bot** (`.github/workflows/screenshots.yml`) hält die Bilder aktuell. Wenn eine Änderung der Karten (`custom_components/autodarts/frontend/`) oder des Screenshot-Werkzeugs (`tests/e2e/`, außer Browsertest und End-to-End-Test) auf `main` landet, jeden Donnerstag und auf Abruf erzeugt er jedes Bild beider Sprachen neu, mit `tests/e2e/visual.sh` und einem Job pro Sprache, und vergleicht es Pixel für Pixel mit dem eingecheckten. Ein Bild, dessen Pixel gleich geblieben sind, behält seine Datei.

Auch ein Release startet den Bot. Es schreibt seine Version in `custom_components/autodarts/manifest.json`, und die Integrationsseite in `online-bridge.png` zeigt davon die Hauptversion ([eine feste Version](#in-jedem-lauf-dieselben-bilder)): Ein Release derselben Hauptversion erzeugt jedes Bild wie zuvor, eine neue Hauptversion wie 2.0.0 ändert dieses Bild. Den Release-Pull-Request merget der Maintainer oder die Release-App, also startet sein Push auf `main` Workflows wie jeder andere; nur ein Merge mit dem `GITHUB_TOKEN` eines Workflows startete keine. So folgt das Bild einer neuen Hauptversion binnen einer Stunde statt erst am Donnerstag, und der Bildvergleich späterer Pull Requests meldet es nicht tagelang als geändert.

Hat sich ein Bild geändert, öffnet der Bot einen Pull Request, *docs: update the screenshots of the cards*, oder aktualisiert den noch offenen, und schaltet Auto-Merge ein: Die Bilder folgen, sobald jede Prüfung bestanden ist. Die Beschreibung nennt jedes geänderte Bild mit dem Anteil seiner Pixel, der sich geändert hat; der Workflow-Lauf behält die Bilder vorher und nachher mit ihren Unterschieden drei Tage lang. Der Pull Request kommt von der Release-App, damit seine Prüfungen laufen, und seine Commits gehen über die API von GitHub: GitHub signiert sie, wie `main` es verlangt, und sie tragen das `Signed-off-by:` der App. Der Branch des Pull Requests beginnt bei `main`, wie es nach dem Erzeugen der Bilder steht, nicht beim Commit, aus dem sie erzeugt wurden: Ein Branch, dessen Workflows von denen auf `main` abweichen, gilt GitHub als Änderung der Workflows, und dafür hat die App keine Berechtigung. Die Bilder kommen zuerst auf einen eigenen Branch, und der Branch des Pull Requests springt in einem Schritt dorthin: Zeigte er auch nur kurz auf einen Commit, den `main` schon hat, schlösse das seinen Pull Request. Lässt sich der Branch eines offenen Pull Requests wegen der Workflows, die sich seitdem auf `main` geändert haben, nicht verschieben, beginnt er neu, und ein neuer Pull Request löst den alten ab. Hat `main` die Bilder eines noch offenen Pull Requests schon, schließt der Bot ihn. Das Erzeugen der Bilder läuft ohne jedes Geheimnis; nur der letzte Job, der den Pull Request schreibt, nutzt den Schlüssel der Release-App aus der Umgebung `release`.

## Bildvergleich

Der Workflow **Visual check** (`.github/workflows/visual.yml`) erzeugt die Bilder auf dieselbe Weise für jeden Pull Request, der die Karten oder das Screenshot-Werkzeug ändert, und vergleicht sie mit den eingecheckten. Er meldet nur, denn eine gewollte Änderung kommt nach dem Merge über den Screenshot-Bot nach `docs/images`:

- Die Zusammenfassung jedes Jobs nennt jedes Bild, das anders aussieht, mit dem Anteil seiner Pixel, der sich geändert hat.
- Die Artefakte `visual-en` und `visual-de` behalten jedes geänderte Bild vorher und nachher und ein Bild des Unterschieds: das neue Bild in Grau, jedes geänderte Pixel in Rot.
- Der Workflow **Visual check comment** (`visual-comment.yml`) schreibt die Liste in einen Kommentar am Pull Request, mit Links zu den Artefakten, und aktualisiert ihn nach jedem Lauf.

Ein Bild, das sich nicht erzeugen lässt, lässt die Prüfung fehlschlagen. Der Kommentar-Workflow startet, wenn eine Prüfung endet (`workflow_run`), damit er auch Pull Requests aus Forks kommentieren darf, checkt ihren Code aber nie aus und führt ihn nie aus: Er liest nur die Berichte der Prüfung, übernimmt daraus nichts als Bildnamen und Zahlen, die er prüft, und schreibt den Kommentar selbst. Die Prüfung läuft nur, wenn sich ihre Dateien ändern, und ist deshalb keine Pflichtprüfung.

Derselbe Vergleich läuft auch lokal; er lässt die neuen Bilder in `docs/images` und den Bericht in `tests/e2e/artifacts/visual/`:

```sh
LANGUAGES=de bash tests/e2e/visual.sh
git checkout -- docs/images   # zurück zu den eingecheckten Bildern
```

## Wie der Browsertest wartet

Der Browsertest (`tests/e2e/browser.py`) wartet auf das, was er prüft, nie eine feste Zeit, die auf einem langsamen Runner zu kurz und überall sonst zu lang wäre. `tests/e2e/pages.py` enthält seine Wartefunktionen:

- `show()` öffnet eine Ansicht auf mehreren Seiten zugleich: beim ersten Mal mit einem Laden der Seite, danach in der App, wie es ihre Links tun. So bleiben das Frontend und sein Websocket erhalten, und eine Ansicht braucht eine Zehntelsekunde statt eines Ladens der ganzen App. Es wartet, bis die Karten der Ansicht die der Ansicht davor ersetzt und sich gezeichnet haben.
- `expect_state()` wartet, bis jede Seite die Zustände zeigt, die ein Zug am Board setzt, etwa `num_throws` 2 nach dem zweiten Dart einer Aufnahme oder `local_status` `takeout_in_progress`, während die Darts herausgezogen werden.
- `settle()` wartet, bis eine Seite zur Ruhe gekommen ist: Ihre Karten haben sich gezeichnet, keine Anfrage des Frontends am Websocket von Home Assistant wartet auf ihre Antwort, 100 ms kam kein Frame, keine Animation einer Karte läuft, und der Browser hat seitdem zwei Frames gezeichnet. Ein Skript, das jede Seite vor dem von Home Assistant ausführt, verfolgt dafür den Websocket.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/browser-waits-dark.png">
  <img src="images/de/browser-waits-light.png" alt="Wie der Browsertest wartet: Alle Bildschirme eines Schritts sind zugleich offen. Nach einem Zug am Board, etwa einem Dart, oder einer Ansicht, die in der App geöffnet wird, wartet der Test, bis jede Seite den Zustand zeigt, den der Zug setzt, etwa zwei Darts in der Aufnahme, und bis jede Seite zur Ruhe gekommen ist: ihre Karten gezeichnet, keine Anfrage am Websocket wartet auf ihre Antwort, 100 ms kein Frame, keine Animation einer Karte läuft und zwei Frames gezeichnet. Dann prüft er jede Seite, das Layout, die Höhen oder die Barrierefreiheit, und macht mit dem nächsten Zug weiter. Eine Seite, die nicht rechtzeitig dahin kommt, lässt den Schritt mit dem fehlschlagen, worauf sie wartete und was sie zeigt." width="560">
</picture>

Die Schritte, die viele Bildschirme ansehen, öffnen sie nebeneinander und spielen jedes Spiel einmal für alle: *every screen size* seine neun Bildschirme und danach die Telefone in vier weiteren Sprachen, *steady heights* seine vier Bildschirme mit je drei Ansichten, *accessibility* seine vier Bildschirme und Designs, auf denen axe-core zugleich prüft, und *a dartboard without Autodarts* seine neun Bildschirme. Eine Wartezeit, die abläuft, nennt die Seite mit der Größe ihres Bildschirms und ihrer Sprache, worauf sie wartete und was die Seite stattdessen zeigte, etwa die Anfrage ohne Antwort oder den Zustand jeder Entität.

`tests/test_e2e_waits.py` schlägt fehl, wenn der Browsertest mit `page.wait_for_timeout` eine feste Zeit wartet, außer bei den zwei Wartezeiten, die er mit ihren Gründen nennt, jede einmal aufgerufen: ein Finger, der 120 ms auf der Lupe ruht, bevor er loslässt, und die sechs Sekunden, die der Safari-Schritt `autodarts-card.js` zurückhält. Kein Skript, das einen Browser steuert, darf `time.sleep` aufrufen: Die synchrone API von Playwright verarbeitet die Ereignisse des Browsers, etwa eine Anfrage, die eine Route zurückhält, nur in ihren eigenen Aufrufen, also hielte ein Schlaf sie alle an.

Nach jedem Schritt zeigt das Protokoll seine Sekunden, etwa `Browser step: steady heights (74.2 s)`, und `browser-steps-table.md` bei den Artefakten führt jeden Schritt mit seinen Sekunden auf; in der CI zeigt die Zusammenfassung des Jobs diese Tabelle.

## Der Browsertest in Teilen

Nacheinander brauchen die Schritte fünf Minuten, zu lang für einen Job. Jeder Schritt gehört zu einer von vier Gruppen mit etwa gleich vielen Sekunden (`steps()` in `tests/e2e/browser.py`), und `BROWSER_SHARD=k/n` führt die Gruppen `g` mit `(g - 1) % n = k - 1` aus: `1/1`, die Vorgabe, jede Gruppe, `1/2` die Gruppen 1 und 3, `2/4` die Gruppe 2. `BROWSER_WORKERS=W` verteilt den Teil des Rechners auf W Demo-Instanzen nebeneinander, jede mit ihrem Browser, einem eigenen Compose-Projekt (`autodarts_browser_1`, …), dem nächsten Port ab 18125 und einem eigenen Ordner bei den Artefakten (`shard-3-of-4`). Jede Zeile eines Workers im Protokoll beginnt mit seinem Teil, etwa `[3/4]`.

```sh
BROWSER_WORKERS=4 bash tests/e2e/browser.sh                   # alle Schritte, vier Teile zugleich
BROWSER_SHARD=2/4 bash tests/e2e/browser.sh                   # ein Teil: die gleichbleibenden Höhen
BROWSER_SHARD=2/2 BROWSER_WORKERS=2 bash tests/e2e/browser.sh # der zweite Runner der CI: 3/4 und 4/4
```

`BROWSER_STEPS` führt nur die genannten Schritte aus, durch Kommas getrennt: Der ganze Name eines Schritts führt diesen allein aus, etwa `BROWSER_STEPS="training card"` ohne den *training card editor*, der Anfang von Namen jeden Schritt, mit dem sie beginnen, etwa `BROWSER_STEPS="touch"`.

Jeder Schritt beginnt mit dem Board zwischen zwei Spielen, was auch immer der Schritt davor hinterließ: `Board.between_games()` in `browser.py` beendet ein Turnier, schaltet das Tastenfeld, das Spiel und die Teams aus, stellt einen Spieler, ein Leg und einen Satz ohne den Bot ein, startet die Erkennung, räumt das Board ab und wartet, bis Home Assistant das alles zeigt, über eine eigene Seite ohne Karte. Eine Karte, die ein Spiel zeigte, öffnet acht Sekunden nach seinem Ende von selbst die Spielauswahl; ein weiterlaufendes Spiel würde sie also mitten im nächsten Schritt öffnen. Nur die Trainingskarte und die Live-Karte lesen die Demo so, wie `demo.py` sie hinterließ, ihre Sitzung und die Aufnahme auf dem Board; sie kommen in Gruppe 1 zuerst, und vor ihnen wird nichts zurückgesetzt. So besteht jeder Teil und jeder Schritt für sich, wie der ganze Lauf.

`tests/test_e2e_shards.py` prüft die Gruppen ohne Browser: Jeder Schritt hat eine, jede Zahl von Teilen von eins bis vier führt jeden Schritt genau einmal und in seiner Reihenfolge aus, die Schritte, die die Demo wie zu Beginn lesen, kommen zuerst, und die Dartscheibe ohne Autodarts zuletzt. Außerdem führt er `browser.sh` mit einem Ersatz für `docker` aus, der zeigt, welchen Teil, welches Projekt und welche Artefakte jeder Worker bekommt, und dass ein fehlgeschlagener Worker den Lauf fehlschlagen lässt und als einziger seine Protokolle behält. Wächst ein Schritt, zeigt `browser-steps-table.md` seines Teils das, und ein Schritt, der in `steps()` in eine andere Gruppe wandert, gleicht die Teile wieder aus.

## Prüfung der Barrierefreiheit

Der Schritt *accessibility* des Browsertests (`tests/e2e/browser.py`) lässt [axe-core](https://github.com/dequelabs/axe-core) über jede Karte jeder Ansicht beider Dashboards laufen, über den Ruhebildschirm, ein Übungsspiel auf der Live-Karte und die eigenen Seiten der Anzeigetafel: die Spielauswahl, das Tastenfeld mit seiner Scheibe zum Antippen, die Scheibe einer Korrektur und Cricket. Das geschieht auf einem Laptop (1280 × 800) und einem iPhone (393 × 852) mit Touch, jeweils im dunklen und im hellen Design, nach den Regeln von WCAG 2.1 in den Stufen A und AA, etwa zum Kontrast von Text, zu Namen von Bedienelementen und Rollen und zum Erreichen dessen, was scrollt, mit der Tastatur.

- Ein schwerer oder kritischer Verstoß lässt den Schritt fehlschlagen, mit Bildschirm, Ansicht, Karte, Regel, Element und dem, was nicht stimmt. Mittlere und leichte nennt das Protokoll.
- `tests/e2e/accessibility-baseline.toml` führt die Verstöße, die vorerst hingenommen werden, jeden mit seinem Grund: Ein Eintrag nennt die Regel, die Karte und ein `target`, das Teil des Selektors ist, den axe-core dem Element gibt. Der Schritt nennt einen Eintrag, der nicht mehr vorkommt, damit er geht. Die Liste ist leer: Jede Karte besteht.
- Der Schritt behält jeden Verstoß und jede geprüfte Ansicht in `accessibility.json`, bei den übrigen Artefakten des Browsertests.

axe-core kommt aus `package.json`, festgelegt in `package-lock.json`; führe also vor `browser.sh` `npm ci` aus, wie es die CI tut. `BROWSER_STEPS=accessibility` führt die Prüfung allein aus. Behebe einen Verstoß lieber in der Karte, als ihn hinzunehmen: Gedämpfte Wörter nehmen `--ad-muted-text` aus den Bausteinen, das den Kontrast in beiden Designs und auf einer getönten Kachel hält, jedes Bedienelement hat Wörter oder ein `aria-label`, und was scrollt, erreicht auch die Tastatur.

## Timer der Karten

Eine Karte auf einem Dashboard hat Timer: den Countdown bis zum nächsten Match eines Turniers, die Zeit, die das Ergebnis oder die Zusammenfassung eines Matches zeigt, und den Ruhemodus; die Trainingskarte folgt den Ereignissen des Boards über den History-Stream von Home Assistant. Nur das Verlassen der Seite hält sie an, in `disconnectedCallback`. Home Assistant kann einer Karte auch danach noch neue Zustände geben, deshalb startet eine Karte einen Timer oder einen Stream nur, solange sie auf der Seite ist (`isConnected`). Kommt sie zurück, aktualisiert `connectedCallback` sie, und das startet beides neu.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/card-timers-dark.png">
  <img src="images/de/card-timers-light.png" alt="Die Timer einer Karte und die Seite: Home Assistant gibt einer Karte neue Zustände. Eine Karte auf der Seite startet, was sie braucht, etwa den Countdown eines Turniers, die Zeit der Zusammenfassung, den Ruhemodus und den History-Stream; eine Karte, die die Seite verlassen hat, startet nichts. Das Verlassen der Seite hält jeden Timer und den Stream an, und eine Karte, die zurückkommt, wird aktualisiert und startet sie neu. Läuft nach den Tests einer Datei noch ein Timer, schlägt die Datei mit ihrem Namen und dem fehl, was der Timer aufruft, und der Timer hält an." width="560">
</picture>

`npm test` hält jede Karte daran:

- `tests/frontend/dom.mjs` verfolgt die echten Timer, die die Karten und die Tests stellen. Ein Timer, der noch läuft, wenn die Tests einer Datei fertig sind und ihre Karten die Seite verlassen haben, würde die Datei für immer laufen lassen. Stattdessen hält er an, und die Datei schlägt fehl, mit ihrem Namen und dem, was der Timer aufruft:

  ```text
  ✖ tests/frontend/dom.mjs
    Error: tournament.test.mjs left 1 timer running after its cards left the page:
    setInterval(() => this._update(), 1000)
  ```

- Ein Test, der nie endet, schlägt nach 60 Sekunden mit seinem Namen fehl (`--test-timeout=60000` in `package.json`), und die übrigen Dateien laufen weiter.

Simulierte Timer (`context.mock.timers`) enden mit ihrem Test und zählen nicht. Um zu prüfen, dass eine Karte keinen Timer startet, vergleicht ein Test `timers()` aus `dom.mjs` davor und danach, wie es *a scoreboard that left the page starts no countdown and no timer of the tournament* in `tests/frontend/tournament.test.mjs` tut.

## Wann die End-to-End-Tests laufen

Der Browsertest mit der Prüfung der Barrierefreiheit gehört zu den End-to-End-Tests in Docker, dem Workflow **Docker E2E** (`e2e.yml`). Mit ihren Jobs nebeneinander dauern sie etwa fünf Minuten, länger als die meisten anderen Prüfungen, und die meisten Pull Requests ändern nichts, was sie testen. Deshalb fragt der Job *changes* zuerst die API, welche Dateien ein Pull Request ändert, ohne Checkout und ohne Action eines Dritten. Die Test-Jobs laufen nur, wenn eine davon zu dem gehört, was die Tests ausführen oder einbinden: die Integration in `custom_components/`, die Blueprints in `blueprints/`, die Tests selbst in `tests/e2e/`, `package.json` und `package-lock.json` mit axe-core und der Workflow `.github/workflows/e2e.yml`. Eine umbenannte Datei zählt auch mit ihrem alten Namen. Scheitert die API oder ändert ein Pull Request mehr Dateien, als die API auflistet (3000), laufen die Tests. Jeder Push auf `main`, jede Nacht und jeder Lauf auf Abruf testen alles, nachts auch gegen die Beta von Home Assistant.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/e2e-gate-dark.png">
  <img src="images/de/e2e-gate-light.png" alt="Wann die End-to-End-Tests laufen: Ein Push auf main, der nächtliche Lauf und ein Lauf auf Abruf führen die Test-Jobs immer aus. Für einen Pull Request fragt der Job changes die API nach seinen Dateien; nutzen die Tests eine davon oder sind die Dateien unbekannt, laufen die Test-Jobs nebeneinander etwa 5 Minuten, sonst werden sie in Sekunden übersprungen. Die Pflichtprüfung e2e besteht, wenn jeder Test-Job bestanden hat oder keiner laufen musste, und schlägt fehl, wenn ein Job fehlschlug oder abgebrochen wurde." width="560">
</picture>

`main` verlangt eine einzige Prüfung der End-to-End-Tests, `e2e`, vom Job *gate*. Eine Matrix, die eine Bedingung überspringt, meldet keinen ihrer Job-Namen, und ein übersprungener Job zählt als bestanden. Deshalb läuft das Gate immer und entscheidet selbst: Es besteht, wenn jeder Test-Job bestanden hat oder *changes* nichts zu testen fand, und schlägt fehl, wenn ein Test-Job fehlschlug, abgebrochen oder übersprungen wurde, obwohl er laufen musste. Ein Pull Request, der nur die Dokumentation oder andere Workflows ändert, bekommt `e2e` etwa eine Minute nach dem Push. `tests/test_consistency.py` schlägt fehl, wenn eine Compose-Datei eine Datei des Repositorys einbindet oder der Browsertest eine liest, die in dieser Liste fehlt.

Die Test-Jobs laufen nebeneinander. Drei Jobs *scenario* führen `tests/e2e/run.sh` aus, auf Board Manager 1, Board Manager 2 und Home Assistant 2026.8.0. Vier Jobs *browser* führen den Browsertest aus, zwei für das aktuelle und zwei für das älteste unterstützte Home Assistant. Jeder Browser-Job lädt die Images von Home Assistant und Playwright zugleich und startet zwei Worker, mit `BROWSER_SHARD=1/2` oder `2/2` und `BROWSER_WORKERS=2`, sodass die vier [Teile](#der-browsertest-in-teilen) einer Version zugleich laufen. Ein Schritt, der fehlschlägt, lässt nur seinen Job fehlschlagen, und der Bot für unzuverlässige Tests führt nur diesen Job und das Gate erneut aus. Der nächtliche Job gegen die Beta führt das Szenario und danach jeden Teil aus, zwei zugleich.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/de/e2e-shards-dark.png">
  <img src="images/de/e2e-shards-light.png" alt="Die End-to-End-Tests nebeneinander: Findet der Job changes etwas zu testen, starten sieben Test-Jobs zugleich. Drei führen das Szenario aus, für Board Manager 1, Board Manager 2 und Home Assistant 2026.8.0. Vier führen den Browsertest aus, zwei für das aktuelle und zwei für das älteste unterstützte Home Assistant. Jeder Browser-Job startet zwei Demo-Instanzen, jede mit einem Browser und einem der vier Teile der Schritte: der erste Runner die Karten, Spiele und Formulare sowie die gleichbleibenden Höhen, der zweite das Tablet, jede Bildschirmgröße und die Dartscheibe ohne Autodarts sowie die Touchscreens, Safari und die Barrierefreiheit. Die Pflichtprüfung e2e wartet auf alle." width="640">
</picture>
