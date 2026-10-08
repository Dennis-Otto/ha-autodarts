# Entwicklung: Bilder und Prüfungen der Karten

[← Dokumentation](README.de.md)

Die vollständige Entwickler-Dokumentation ist auf Englisch: [Development](development.md). Diese Seite beschreibt auf Deutsch, wie die Bilder der Dokumentation entstehen und wie sie aktuell bleiben, und wie die Karten bei jeder Änderung auf ihr Aussehen und ihre Barrierefreiheit geprüft werden.

**Auf dieser Seite:** [Bilder der Dokumentation](#bilder-der-dokumentation) · [In jedem Lauf dieselben Bilder](#in-jedem-lauf-dieselben-bilder) · [Screenshot-Bot](#screenshot-bot) · [Bildvergleich](#bildvergleich) · [Prüfung der Barrierefreiheit](#prüfung-der-barrierefreiheit)

## Bilder der Dokumentation

`tests/e2e/screenshots.sh` erzeugt jedes Bild in `docs/images/en` und `docs/images/de` neu aus der Demo, auch die animierten WebP-Bilder, und komprimiert die PNG-Bilder mit pngquant. `tests/e2e/screenshots.py` hat eine Funktion pro Bild oder Animation, sodass sich ein einzelnes Bild neu erzeugen lässt, indem man seine Funktion gegen eine laufende Demo aufruft. Jedes Bild zeigt das simulierte Board und erfundene Spieler, persönliche Daten können also nicht erscheinen; die geheime Adresse der Online-Brücke wird abgedeckt. Die Suche im Netzwerk öffnet das Werkzeug nie, sie würde echte Boards zeigen. Die Diagramme in `docs/images` entstehen dagegen mit `scripts/render_diagrams.sh`.

Schlägt eine Aufnahme fehl, speichert das Werkzeug jede offene Seite in `tests/e2e/artifacts/`. Git ignoriert diesen Ordner.

## In jedem Lauf dieselben Bilder

Zwei Läufe des Werkzeugs erzeugen dieselben Bilder, Byte für Byte. Ein Bild, das sich ändert, zeigt also immer eine Karte oder eine Seite, die sich geändert hat, und [Screenshot-Bot](#screenshot-bot) und [Bildvergleich](#bildvergleich) erkennen das:

- **Eine eingefrorene Uhr.** Die Demo der Screenshots steht auf Dienstag, dem 29. September 2026, 20:30 Uhr (`DEMO_TIME` in `screenshots.sh`), ganz gleich, wann sie läuft. `tests/e2e/frozen/sitecustomize.py` stellt diese Uhr für Home Assistant und jedes Skript in seinem Container, über `compose.frozen.yaml`, das `demo.sh` hinzunimmt, wenn `DEMO_TIME` gesetzt ist. Die Uhr geht nur weiter, wenn die Demo sie weiterstellt: Jede Bewegung am simulierten Board, ein Dart, das Herausziehen oder ein neuer Status, dauert zwei Sekunden, in `demo.py` wie in `screenshots.py`, geschrieben in die Datei `.demo_clock` in der Konfiguration der Demo. So kommt jede Zeit, die Home Assistant festhält, in jedem Lauf gleich heraus, auf die Millisekunde, während der Verlauf des Boards, die Länge einer Session und die Trainingszeit des Wochenberichts aussehen wie an einem echten Abend; der Wochenbericht bekommt die Minute, auf die er wartet, auf dieselbe Weise. Auch der Browser zeigt die Zeit der Demo: Die Uhr von Playwright steht auf ihr still, außer in den Seiten der Spiel-Animationen, in denen das Ergebnis eines Turnierspiels seine Zeit lang stehen bleiben muss; ihre Bilder zeigen keine Uhrzeit. Die Seite der Statistik-Grafiken wünscht reduzierte Bewegung, damit Home Assistant ihre Linien sofort zeichnet statt als Animation, die die stehende Uhr anhalten würde.
- **Eine Quelle für Änderungen.** Die eingefrorene Demo fragt das Board nicht regelmäßig ab: Jede Änderung kommt über die Verbindung zum Board, in der Reihenfolge, in der das Board sie sendet, nie zuerst aus einer Abfrage, deren Zeitpunkt vom Lauf abhängt.
- **Feste Zufallszahlen.** Die Darts des Bots und jede andere Zufallszahl ohne eigenen Startwert beginnen mit demselben Startwert.
- **Ruhige Bilder.** Vor jedem Screenshot und jedem Bild einer Animation wartet das Werkzeug auf Bilder, die noch laden, lässt Übergänge und Einblendungen an ihr Ende springen und hält endlose Animationen wie die blinkenden Felder im selben Moment an. Das wiederholt es, bis sich keine Karte mehr ändert und zwei Blicke im Abstand einer Zehntelsekunde nichts finden, das sich bewegt. Chromium zeichnet jedes Bild ganz und animiert auf seinem Hauptthread (`STEADY_CHROMIUM` in `screenshots.py`). Die Werkzeugleiste eines Dashboards wirft keinen Schatten auf das, was unter ihr scrollt, eine Karte, die höher als der Bildschirm ist, wird vom Anfang der Seite aufgenommen, und der Dialog der Board-Ereignisse öffnet sich erst, wenn der Rekorder den Verlauf geschrieben hat, den er zeigt.
- **Feste Adressen.** Die Online-Brücke zeigt `homeassistant.local` als Adresse von Home Assistant (`internal_url` in `demo.configuration.yaml`), nicht die Adresse, die Docker dem Container zufällig gibt.
- **Festgelegte Kompression.** pngquant 2.18.0 aus Ubuntu 24.04 komprimiert jedes PNG-Bild direkt nach der Aufnahme. `tests/e2e/pngquant.sh` installiert es im festgelegten Playwright-Image von Launchpad, wo jedes veröffentlichte Paket seine Adresse behält, und prüft beide Pakete gegen ihre SHA-256-Prüfsumme. Die Animationen entstehen mit dem festgelegten Pillow.

Um herauszufinden, was sich zwischen zwei Läufen unterscheidet, behält `KEEP_RAW=1` jedes Bild und jedes Bild einer Animation so, wie es aufgenommen wurde, vor der Kompression, in `tests/e2e/artifacts/raw/`, einem Ordner pro Sprache; `tests/e2e/compare.py` vergleicht zwei Ordner mit Bildern.

Ohne `DEMO_TIME`, wie bei `demo.sh` für eine Vorschau oder bei `browser.sh`, läuft die Demo mit der echten Uhr.

## Screenshot-Bot

Der Workflow **Screenshot bot** (`.github/workflows/screenshots.yml`) hält die Bilder aktuell. Wenn eine Änderung der Karten (`custom_components/autodarts/frontend/`) oder des Screenshot-Werkzeugs (`tests/e2e/`, außer Browsertest und End-to-End-Test) auf `main` landet, jeden Donnerstag und auf Abruf erzeugt er jedes Bild beider Sprachen neu, mit `tests/e2e/visual.sh` und einem Job pro Sprache, und vergleicht es Pixel für Pixel mit dem eingecheckten. Ein Bild, dessen Pixel gleich geblieben sind, behält seine Datei.

Hat sich ein Bild geändert, öffnet der Bot einen Pull Request, *docs: update the screenshots of the cards*, oder aktualisiert den noch offenen, und schaltet Auto-Merge ein: Die Bilder folgen, sobald jede Prüfung bestanden ist. Die Beschreibung nennt jedes geänderte Bild mit dem Anteil seiner Pixel, der sich geändert hat; der Workflow-Lauf behält die Bilder vorher und nachher mit ihren Unterschieden drei Tage lang. Der Pull Request kommt von der Release-App, damit seine Prüfungen laufen, und seine Commits gehen über die API von GitHub: GitHub signiert sie, wie `main` es verlangt, und sie tragen das `Signed-off-by:` der App. Hat `main` die Bilder eines noch offenen Pull Requests schon, schließt der Bot ihn. Das Erzeugen der Bilder läuft ohne jedes Geheimnis; nur der letzte Job, der den Pull Request schreibt, nutzt den Schlüssel der Release-App aus der Umgebung `release`.

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

## Prüfung der Barrierefreiheit

Der Schritt *accessibility* des Browsertests (`tests/e2e/browser.py`) lässt [axe-core](https://github.com/dequelabs/axe-core) über jede Karte jeder Ansicht beider Dashboards laufen, über den Ruhebildschirm, ein Übungsspiel auf der Live-Karte und die eigenen Seiten der Anzeigetafel: die Spielauswahl, das Tastenfeld mit seiner Scheibe zum Antippen, die Scheibe einer Korrektur und Cricket. Das geschieht auf einem Laptop (1280 × 800) und einem iPhone (393 × 852) mit Touch, jeweils im dunklen und im hellen Design, nach den Regeln von WCAG 2.1 in den Stufen A und AA, etwa zum Kontrast von Text, zu Namen von Bedienelementen und Rollen und zum Erreichen dessen, was scrollt, mit der Tastatur.

- Ein schwerer oder kritischer Verstoß lässt den Schritt fehlschlagen, mit Bildschirm, Ansicht, Karte, Regel, Element und dem, was nicht stimmt. Mittlere und leichte nennt das Protokoll.
- `tests/e2e/accessibility-baseline.toml` führt die Verstöße, die vorerst hingenommen werden, jeden mit seinem Grund: Ein Eintrag nennt die Regel, die Karte und ein `target`, das Teil des Selektors ist, den axe-core dem Element gibt. Der Schritt nennt einen Eintrag, der nicht mehr vorkommt, damit er geht. Die Liste ist leer: Jede Karte besteht.
- Der Schritt behält jeden Verstoß und jede geprüfte Ansicht in `accessibility.json`, bei den übrigen Artefakten des Browsertests.

axe-core kommt aus `package.json`, festgelegt in `package-lock.json`; führe also vor `browser.sh` `npm ci` aus, wie es die CI tut. `BROWSER_STEPS=accessibility` führt die Prüfung allein aus. Behebe einen Verstoß lieber in der Karte, als ihn hinzunehmen: Gedämpfte Wörter nehmen `--ad-muted-text` aus den Bausteinen, das den Kontrast in beiden Designs und auf einer getönten Kachel hält, jedes Bedienelement hat Wörter oder ein `aria-label`, und was scrollt, erreicht auch die Tastatur.
