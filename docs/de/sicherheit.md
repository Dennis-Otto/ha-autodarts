# Sicherheit

[← Übersicht](README.md) · [English](../security.md)

Diese Seite erklärt, wie die Integration deine Daten und dein Board schützt, wem sie vertraut und welche Risiken bleiben. Sicherheitslücken meldest du bitte vertraulich, wie in [SECURITY.md](../../SECURITY.md) beschrieben.

## Was geschützt wird

| Schutzgut | Wo es liegt | Schutz |
| --- | --- | --- |
| API-Schlüssel des Boards, TLS-Schlüssel, Kamerapfade | Konfiguration des Board Managers | Werden direkt beim Lesen verworfen; nie gespeichert, protokolliert, angezeigt oder in Diagnosedaten übernommen |
| Autodarts-OAuth-Token (optionale Cloud-Verknüpfung) | Integrationseintrag in Home Assistant | Nur dort gespeichert, automatisch erneuert, nie protokolliert; das Passwort sieht die Integration nie |
| Board-ID, Board-Adresse, Client-ID | Integrationseintrag in Home Assistant | In Diagnosedaten geschwärzt; der Verbindungsverlauf in den Diagnosedaten enthält Zähler, Fehlerarten und Dauern, nie Adressen oder Fehlermeldungen |
| Trainingssession, Übungsspiele und Spielernamen | `.storage` von Home Assistant | Nur lokal; wird mit der Integration gelöscht; Spielernamen sind in Diagnosedaten geschwärzt |
| Steuerung des Boards | Board-Manager-API | Aktionen nur auf Wunsch eines Nutzers oder einer Automation, genau einmal gesendet |

## Vertrauensgrenzen

```text
 Board-PC                      Home Assistant                    Internet
┌────────────────────┐        ┌──────────────────────────┐       ┌──────────────────────┐
│ Board Manager      │  LAN   │ Autodarts-Integration    │ HTTPS │ Autodarts-Cloud      │
│ Port 3180, ohne    ├───────►│ prüft jede Antwort       ├──────►│ (optional, OAuth)    │
│ Anmeldung          │        │ Dashboard-Karten         │       │ Suchdienst           │
└────────────────────┘        └──────────────────────────┘       │ (nur bei Suche)      │
                                                                 └──────────────────────┘
```

1. **Board Manager → Integration.** Die lokale API hat keine Anmeldung. Die Integration behandelt jede Antwort als nicht vertrauenswürdig: Typen, Wertebereiche und Strukturen werden geprüft, bevor ein Wert eine Entität erreicht. Unerwartete Daten erscheinen als *unbekannt*, statt Fehler auszulösen. Versionsnummern müssen wie Versionsnummern aussehen, Texte mit mehr als 255 Zeichen erscheinen als unbekannt, und Echtzeitnachrichten werden auf dieselben bekannten Werte reduziert wie gelesene Antworten. Eine Antwort in unbekanntem Format wird einmal protokolliert; antwortet eine nötige Abfrage weiter so, erscheint ein Reparaturhinweis. HTTP 401 oder 403 wird als verweigerter Zugriff gemeldet; die Integration sendet dem Board nie Zugangsdaten.
2. **Integration → Dashboard.** Die Karten zeigen Board-Daten im Browser. Jeder Text vom Board oder aus der Entitätsverwaltung wird maskiert, Zahlen werden geprüft, bevor sie zu SVG-Geometrie werden.
3. **Integration → Internet.** Im lokalen Betrieb verlässt nichts das Heimnetz. *Boards im Netzwerk suchen* fragt einmalig und nur auf Wunsch den öffentlichen Suchdienst von Autodarts; von sich aus fragt die Integration ihn nie. Die optionale Cloud-Verknüpfung nutzt die OAuth-Geräteanmeldung über HTTPS mit der gemeinsamen Verbindung von Home Assistant, und Board- und Match-IDs aus der Cloud werden als einzelner Pfadabschnitt kodiert.
4. **Netzwerk → Integration (mDNS).** Jedes Gerät im Netzwerk kann ein Autodarts-Board melden. Die Integration spricht nur die Adressen an, von denen die Meldung kommt, nie Loopback-, Link-local- oder Multicast-Adressen und nie eine Adresse, die nur in den Eigenschaften der Meldung steht. Ein eingerichtetes Board zieht nur dann auf eine neue Adresse um, wenn es unter seiner eingerichteten Adresse nicht mehr mit seiner Board-ID antwortet.

## Bedrohungen und Gegenmaßnahmen

| Bedrohung | Gegenmaßnahme | Nachweis |
| --- | --- | --- |
| Geheimnisse des Boards gelangen nach Home Assistant | Die Konfiguration wird direkt nach dem Lesen auf eine Liste erlaubter Felder reduziert; Antworten auf Schreibzugriffe werden verworfen | Tests prüfen, dass der API-Schlüssel nie in Entitäten, Diagnosedaten oder Logs erscheint, auch im Docker-End-to-End-Test |
| Fehlerhafte oder bösartige Board-Daten bringen Integration oder Karten zum Absturz | Prüfung jeder Nachricht; Property-based Tests mit Hypothesis (Trainings-Engine) und fast-check (Karten) mit Tausenden Zufallseingaben | `tests/test_training_properties.py`, `tests/frontend/properties.test.js` |
| Skripteinschleusung über Board- oder Gerätenamen in den Karten | Jeder eingefügte Text wird maskiert; kein `innerHTML` mit unmaskierten Daten | fast-check-Eigenschaft „maskierter Text enthält nie Markup“; DOM-Test, dass ein Spieler namens `<img onerror>` als Text erscheint |
| Ein falsches Board unter der eingerichteten Adresse zeigt oder steuert fremde Daten | Die Board-ID wird bei Board Manager 2 bei jedem Lesen geprüft, bei Board Manager 1 beim Start und mindestens alle 30 Sekunden; bei Abweichung sind die Entitäten nicht verfügbar, seine Echtzeitnachrichten werden ignoriert, und ein Reparaturhinweis erscheint | `tests/test_quality.py`, `tests/test_realtime.py` |
| Ein Gerät im Netzwerk meldet sich als Board | Nur die meldenden Adressen werden angesprochen; ein Board, das unter seiner eingerichteten Adresse noch antwortet, zieht nie um; die Board-ID muss passen | `tests/test_discovery.py` |
| Präparierte IDs aus der Cloud erreichen andere API-Pfade | Board- und Match-IDs werden als einzelner Pfadabschnitt kodiert; eine leere ID oder eine ID, die kein Text ist, sendet nichts | `tests/test_api.py` |
| Viele Zuschauer überlasten den Board-PC mit Kamerastreams | Pro Kamera werden höchstens zwei Livestreams weitergegeben; weitere Zuschauer bekommen Standbilder | `tests/test_camera_stream.py` |
| Fehlerhafte Board-Daten oder ein Fehler in einer Spielregel trennen die Verbindung | Fehler in Training und Spielen bleiben begrenzt und werden einmal protokolliert; schnell wechselnde Werte lösen keine Spiellogik aus; Lesevorgänge überschneiden sich nie | `tests/test_connection.py` |
| Eine Aktion läuft doppelt, etwa Neustart oder Zurücksetzen | Aktionen werden genau einmal gesendet und nie automatisch wiederholt | `tests/test_local_api.py` |
| Eine kompromittierte Abhängigkeit oder ein manipulierter Build | Abhängigkeiten per Hash, gepinnte Actions und Images, Dependabot, Dependency Review, CodeQL, Gitleaks, OpenSSF Scorecard | [Development](../development.md#continuous-integration) |
| Ein manipuliertes Release | Release-Pakete tragen eine mit Sigstore signierte SLSA-Provenance | [Releases](../releases.md#signed-release-packages) |

## Grundsätze

- **Minimale Rechte:** GitHub-Workflows laufen mit Lese-Token, außer ein Job braucht mehr. Die Integration liest den Board Manager und schreibt nur, wenn du oder eine Automation es verlangt.
- **Sicher im Fehlerfall:** Unbekannte Daten werden zu *unbekannt*, ein unerreichbares Board macht Entitäten nicht verfügbar, und ein falsches Board zeigt nie seine Daten.
- **Lokal zuerst:** Die Cloud ist optional; die lokale Steuerung hängt nie von ihr ab.
- **Kleine Angriffsfläche:** Keine Python-Abhängigkeiten zur Laufzeit, keine offenen Ports, keine Dienste außer den Entitäten.

## Verbleibende Risiken

- Die lokale API des Board Managers hat keine Anmeldung. Jeder, der Port 3180 in deinem Netzwerk erreicht, kann das Board steuern, mit oder ohne diese Integration. Betreibe den Board-PC in einem vertrauenswürdigen Netzwerk.
- Autodarts unterstützt die lokale API ab Board Manager 2 offiziell nicht mehr. Eine künftige Version kann sie ändern; die Integration erkennt die Generation und wird gegen beide getestet.
- Die Integration spricht unverschlüsseltes HTTP mit dem Board. Meldet Board Manager 2 einen HTTPS-Port, nutzt sie den gemeldeten HTTP-Port; TLS zum Board wird nicht unterstützt.
- Jeder im Netzwerk kann per mDNS ein Board melden. Home Assistant zeigt dann ein gefundenes Board an, das erst nach deiner Bestätigung hinzugefügt wird.
