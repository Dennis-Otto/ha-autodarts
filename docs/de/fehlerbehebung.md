# Fehlerbehebung

[← Übersicht](README.md) · [English](../troubleshooting.md)

## Schnelle Prüfung

1. **Läuft der Board Manager?** Öffne `http://<Board-IP>:3180` im Browser eines Geräts im selben Netzwerk. Board Manager 1 zeigt seine App; Board Manager 2 antwortet unter `http://<Board-IP>:3180/api/state`.
2. **Ist die Entität *Board-Manager-Verbindung* an?** Wenn nicht, erreicht Home Assistant das Board nicht. Prüfe Adresse, Port und das Netzwerk dazwischen: VLANs, Firewall, Docker-Netzwerk.
3. **Ist die Entität *Echtzeitverbindung* an?** Wenn nicht, kommen Änderungen trotzdem alle 2 Sekunden an, nur nicht sofort. Siehe [Echtzeitverbindung](#keine-echtzeitaktualisierung).

## Einrichtung

| Meldung | Ursache und Lösung |
| --- | --- |
| *Der lokale Board Manager ist nicht erreichbar oder liefert keine gültigen Daten.* | Falsche Adresse oder falscher Port, der Board Manager läuft nicht, oder auf dem Port antwortet etwas anderes. Trage nur die IP-Adresse ein, ohne `http://` und ohne Port. |
| *Das Board verweigert den Zugriff (HTTP 401 oder 403).* | Der Board Manager selbst braucht keine Anmeldung. Etwas vor Port 3180 blockiert Home Assistant, zum Beispiel ein Reverse Proxy, eine Firewall oder eine Anmeldeseite. Lass Home Assistant direkt auf das Board zugreifen oder trage die Adresse des Boards selbst ein. |
| *Im Board Manager ist noch keine Board-ID hinterlegt.* | Das Board ist noch nicht bei Autodarts eingerichtet. Schließe die Einrichtung im Board Manager ab und versuche es erneut. |
| *Es wurden keine neuen Boards automatisch gefunden.* | Die Suche findet nur Boards, die von deinem Internetanschluss aus registriert und noch nicht eingerichtet sind. Gib stattdessen die Adresse ein. |
| *Die Board-Suche ist gerade nicht erreichbar.* | Der Suchdienst von Autodarts ist nicht erreichbar. Gib stattdessen die Adresse ein. |
| *Dieses Autodarts-Board ist bereits eingerichtet.* | Das Board ist schon vorhanden. Über **Neu konfigurieren** änderst du seine Adresse. |
| Das Board wird nicht automatisch gefunden | Die automatische Erkennung braucht Board Manager 2 und mDNS im Netzwerk. Home Assistant in Docker braucht dafür `network_mode: host`; über VLAN-Grenzen hinweg funktioniert mDNS nur mit einem Repeater. Nutze sonst die Suche oder die Adresse. |
| *Diese Client-ID ist ungültig oder nicht für die Geräteanmeldung freigeschaltet.* | Die Cloud-Verknüpfung braucht eine Client-ID, die Autodarts für diese Integration vergibt. Sie gibt es noch nicht; siehe [Cloud-Verknüpfung](installation.md#autodarts-cloud-verknüpfen-optional). Die lokale Einrichtung funktioniert ohne sie. |


## Reparaturen

Unter **Einstellungen → Reparaturen** kann Home Assistant diese Hinweise anzeigen:

| Hinweis | Bedeutung und Lösung |
| --- | --- |
| **Autodarts-Board-Adresse zeigt auf ein anderes Board** | Unter der eingerichteten Adresse antwortet ein Board mit anderer Board-ID, etwa nach vertauschten IP-Adressen. Die Entitäten bleiben nicht verfügbar, damit sie nie Daten eines fremden Boards zeigen. Öffne die Integration, wähle **Neu konfigurieren** und das richtige Board. Der Hinweis verschwindet dann von selbst. |
| **Autodarts-Board kalibrieren** | Mindestens 20 % der letzten Darts musste das Board korrigieren, siehe *Korrekturquote der Erkennung*. Zieh alle Darts, öffne den Hinweis und bestätige: Die Integration kalibriert alle Kameras und zählt wieder bei null. Der Hinweis verschwindet auch, sobald die Quote unter 10 % fällt. |
| **Board auf den neuen Autodarts Board Manager umstellen** | Das Board nutzt noch den klassischen Board Manager 1, den Autodarts abschalten wird. Installiere Board Manager 2 auf dem Board-PC; die Integration stellt sich selbst um, und der Hinweis verschwindet. |
| **Autodarts-Board unter neuer Adresse gefunden** | Das Board antwortet seit fünf Minuten nicht unter seiner Adresse, aber die Autodarts-Cloud meldet eine andere Adresse, unter der es mit seiner Board-ID antwortet, etwa nach einer DHCP-Änderung. Öffne den Hinweis und bestätige: Die Integration prüft die Adresse noch einmal, wechselt zu ihr und lädt neu. Entitäten, Training und Einstellungen bleiben erhalten. Diesen Hinweis bekommen nur Einträge mit Autodarts-Cloud-Verknüpfung; Board Manager 2 meldet eine neue Adresse selbst, siehe [Adresswechsel](funktionsweise.md#adresswechsel). |
| **Autodarts-Board verweigert den Zugriff** | Das Board antwortet mit HTTP 401 oder 403. Der Board Manager braucht keine Anmeldung, also blockiert ein Reverse Proxy, eine Firewall oder eine Anmeldung vor Port 3180 Home Assistant. Lass Home Assistant auf das Board zugreifen; der Hinweis verschwindet beim nächsten erfolgreichen Lesen. |
| **Autodarts-Board antwortet in einem unbekannten Format** | Eine nötige Abfrage (Zustand, Einstellungen oder `/api/system`) hat dreimal hintereinander in einem Format geantwortet, das diese Version nicht versteht, meist nach einem Board-Manager-Update. Aktualisiere die Integration. Bleibt der Hinweis, [melde ihn](#fehler-melden) mit den Diagnosedaten; das Protokoll nennt die betroffenen Abfragen. |

## Betrieb

### Entitäten sind nicht verfügbar

- **Alle Board-Entitäten:** Der Board Manager hat dreimal hintereinander nicht geantwortet; ein oder zwei verpasste Lesevorgänge, also wenige Sekunden, behalten die letzten Werte. Sobald das Board wieder da ist, erholen sich die Entitäten innerhalb von Sekunden. Training, Übungsspiel, persönliche Bestleistungen und die Board-Ereignisse bleiben verfügbar, auch wenn das Board beim Start von Home Assistant ausgeschaltet ist.
- **Nur Einstellungen und Kameras, der Rest funktioniert:** Das Board hat seine Konfiguration noch nicht gemeldet. Das erledigt sich beim nächsten Lesen, spätestens nach 30 Sekunden.
- **Nach einem Board-Manager-Update:** Beim Wechsel der Generation lädt sich die Integration neu. Warte ein paar Sekunden.

### Eine Aktion schlägt fehl

| Meldung | Ursache und Lösung |
| --- | --- |
| *Das Board hat die Aktion nicht angenommen.* | Das Board hat den Befehl abgelehnt oder nicht geantwortet. Prüfe die Verbindung und versuche es erneut. |
| *Dieses Board unterstützt die Aktion nicht.* | Der Board Manager kennt diesen Befehl nicht, zum Beispiel die Kamerastreams bei Board Manager 1. |
| *Der Board Manager verweigert den Zugriff.* | Siehe **Autodarts-Board verweigert den Zugriff** unter [Reparaturen](#reparaturen). |

### Keine Echtzeitaktualisierung

*Echtzeitverbindung* ist aus, und Änderungen erscheinen mit etwa 2 Sekunden Verzögerung:

- Ein Proxy oder eine Firewall zwischen Home Assistant und dem Board blockiert möglicherweise WebSocket-Verbindungen auf Port 3180. Antwortet das Board auf Lesevorgänge, bleiben seine Echtzeitereignisse aber etwa eine halbe Minute aus, steht einmal eine Warnung im Protokoll.
- Nach einem Neustart des Board Managers verbindet sich die Integration neu, sobald ein Lesevorgang das Board wieder erreicht, sonst spätestens nach 60 Sekunden.

### Darts werden im Training falsch gezählt

- Darts, die beim Start von Home Assistant im Board stecken, werden absichtlich nicht gezählt.
- Wird eine Entnahme nicht erkannt und folgen neue Darts, schließt die Integration die vorige Aufnahme und zählt die neuen Darts.
- Reißt die Verbindung während einer Aufnahme ab, geht die Aufnahme weiter, wenn das Board danach noch ihre Darts zeigt. Wurden die Darts inzwischen gezogen, wird die Aufnahme mit den Darts abgeschlossen, die vor der Unterbrechung bekannt waren; Darts, die danach noch während der Unterbrechung geworfen wurden, zählen nicht.
- Das Training zählt, was das Board erkennt. Korrigierst du ein falsch erkanntes Feld in Autodarts, übernimmt das Training die Korrektur nur, wenn das Board sie meldet.

Neu beginnen: **Neue Trainingssession** oder *Neue Session* auf der Trainingskarte. Soll nichts mehr gezählt werden, schalte **Trainingssession** und *Sessions automatisch starten* aus.

### Eine Kamera wird als gestört gemeldet

*Kamerastörung* geht an, wenn eine Kamera bei laufender Erkennung 15 Sekunden lang keine Bilder liefert. Prüfe Kabel und USB-Anschluss der Kamera und ob sie im Board Manager erscheint. Oft hilft auch eine neue Kalibrierung.

### Karte fehlt oder ist veraltet

- **Custom element doesn't exist: autodarts-card:** Starte Home Assistant nach der Installation neu und lade die Seite neu.
- **Alte Kartenversion nach einem Update:** Lade die Seite neu. In der Companion-App hilft *Einstellungen → Companion-App → Fehlerbehebung → Frontend-Cache zurücksetzen*.
- **Der Aufnahmeverlauf ist leer:** Er kommt aus dem Recorder und braucht daher die Integration `recorder` (standardmäßig aktiv). Er füllt sich mit abgeschlossenen Aufnahmen.

## Diagnose und Logs

### Diagnosedaten herunterladen

**Einstellungen → Geräte & Dienste → Autodarts →** Menü des Boards (⋮) → **Diagnosedaten herunterladen**. Die Datei enthält:

- den Board-Zustand und die Zusammenfassung der Einstellungen;
- die Board-Manager-Generation, die Verbindungen und das Leseintervall;
- unter `connection` den Verlauf der Verbindung: verpasste Lesevorgänge in Folge, die Art des letzten Fehlers, das letzte erfolgreiche Lesen, wie lange das Board schon fehlt, die Dauer des letzten Lesens, Abfragen mit unbekanntem Format und für die Echtzeitverbindung Verbindungsaufbauten, fehlgeschlagene Versuche, den aktuellen Abstand bis zum nächsten Versuch, den Grund des letzten Abbruchs und die Zahl übersprungener Nachrichten.

Board-ID, Adressen, Token und Spielernamen sind geschwärzt; Fehlermeldungen sind nicht enthalten.

### Debug-Protokollierung

Wähle auf der Integrationsseite **Debug-Protokollierung aktivieren**, stelle das Problem nach und wähle **Debug-Protokollierung deaktivieren**. Home Assistant lädt dann das Protokoll herunter. Alternativ in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.autodarts: debug
```

### Fehler melden

Öffne ein [Issue](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose) mit:

- Home-Assistant-Version und Board-Manager-Version;
- den Diagnosedaten;
- den passenden Protokollzeilen.

Sicherheitsprobleme meldest du bitte vertraulich, wie in [SECURITY.md](../../SECURITY.md) beschrieben.
