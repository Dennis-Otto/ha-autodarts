# Troubleshooting

[← Documentation](README.md) · [Deutsch](de/fehlerbehebung.md)

## Quick checks

1. **Is the Board Manager running?** Open `http://<board-ip>:3180` in a browser on a device in the same network. Board Manager 1 shows its app; Board Manager 2 answers on `http://<board-ip>:3180/api/state`.
2. **Is the entity *Local connection* on?** If not, Home Assistant cannot reach the board. Check the address, the port and the network between them (VLANs, firewall, Docker networking).
3. **Is the entity *Realtime connection* on?** If not, updates still arrive every 2 seconds, but not instantly. See [realtime connection](#no-realtime-updates).

## Setup

| Message | Cause and solution |
| --- | --- |
| *Cannot reach the local Board Manager or its response is invalid* | Wrong address or port, the Board Manager is not running, or something else answers on that port. Enter the IP address only, without `http://` and without a port. |
| *The board refused access (HTTP 401 or 403)* | The Board Manager itself needs no login, so something in front of port 3180 blocks Home Assistant, for example a reverse proxy, a firewall or a login page. Let Home Assistant reach the board directly, or enter the board's own address. |
| *No board ID is configured in Board Manager* | The board has not been set up with Autodarts yet. Finish the setup in the Board Manager, then try again. |
| *No new boards were found automatically* | The search only finds boards that registered from your internet connection and that are not set up yet. Enter the address instead. |
| *The board search is unavailable right now* | The Autodarts discovery service is unreachable. Enter the address instead. |
| *This Autodarts board is already configured* | The board is already set up. Use **Reconfigure** to change its address. |
| The board is not discovered automatically | Automatic discovery needs Board Manager 2 and mDNS in your network. Home Assistant in Docker needs `network_mode: host`, and mDNS does not cross VLANs without a repeater. Use the search or the address instead. |
| *This client ID is invalid or is not enabled for device login* | The cloud link needs a client ID issued by Autodarts for this integration. None is available yet; see [cloud link](installation.md#link-the-autodarts-cloud-optional). Local setup works without it. |

## Repairs

Home Assistant shows these notices under **Settings → Repairs**:

| Notice | Meaning and solution |
| --- | --- |
| **Autodarts board address points to a different board** | The configured address answers with a different board ID, for example because IP addresses were swapped. The entities stay unavailable so that they never show another board's data. Open the integration, choose **Reconfigure** and select the correct board. The notice disappears by itself. |
| **Calibrate the Autodarts board** | At least 20 % of the last darts needed a correction by the board, see *Detection correction rate*. Remove all darts, open the notice and confirm: the integration calibrates all cameras and counts again from zero. The notice also disappears once the rate falls below 10 %. |
| **Update the board to the new Autodarts Board Manager** | The board still runs the classic Board Manager 1, which Autodarts will switch off. Install Board Manager 2 on the board PC. The integration switches over by itself and the notice disappears. |
| **Autodarts board found at a new address** | The board has not answered at its address for five minutes, but the Autodarts cloud reports another address where it answers with its board ID, for example after a DHCP change. Open the notice and confirm: the integration checks the address once more, switches to it and reloads. Entities, training and settings are kept. Only entries linked to the Autodarts cloud get this notice; Board Manager 2 announces a new address itself, see [address changes](how-it-works.md#address-changes). |
| **Autodarts board refuses access** | The board answers with HTTP 401 or 403. The Board Manager needs no login, so a reverse proxy, a firewall or a login in front of port 3180 blocks Home Assistant. Let Home Assistant reach the board; the notice disappears with the next successful read. |
| **Autodarts board answers in an unknown format** | A required read (state, settings or `/api/system`) answered three times in a row in a format this version does not understand, typically after a Board Manager update. Update the integration. If the notice stays, [report it](#report-a-bug) with the diagnostics; the log names the affected reads. |

## Operation

### Entities are unavailable

- **All board entities unavailable:** the Board Manager has not answered three reads in a row; one or two missed reads, a few seconds, keep the last values. The entities recover by themselves within seconds after the board is back. Training, practice game, personal bests and the board events stay available, also when the board is switched off while Home Assistant starts.
- **Settings and camera entities unavailable, the rest works:** the board has not reported its configuration yet. This resolves with the next read, at the latest after 30 seconds.
- **Unavailable after a Board Manager update:** the integration reloads itself when the generation changes. Wait a few seconds.

### An action fails

| Message | Cause and solution |
| --- | --- |
| *The board did not accept the action* | The board rejected the command or did not answer. Check the connection and try again. |
| *This board does not support the action* | The Board Manager has no such command, for example the camera streams on Board Manager 1. |
| *Board Manager refused access* | See **Autodarts board refuses access** under [repairs](#repairs). |
| *No Autodarts board with a local connection is loaded* | `autodarts.start_game` and `autodarts.delete_player` need a board that is connected locally and loaded. Check the entry under **Settings → Devices & services**; an entry linked to the cloud only cannot play. |
| *Several Autodarts boards are set up. Choose the board.* | With more than one board, choose the board in the action, the `config_entry_id` field in YAML. |
| *Config entry … was not found*, *… does not belong to integration autodarts* or *… is not loaded* | The board chosen in the action was deleted, is another integration's entry or is not loaded. Choose the board again; a board that does not load shows why on its entry. |
| *… is on the list of players more than once* | Every player needs a name of their own. Players without a name may appear more than once. |
| *Killer needs at least two players* | Name two to four players in the action, or set *Practice players* to 2 or more. |
| *There is no player profile named …* | Check the spelling; upper and lower case do not matter. The *Player profiles* sensor lists every profile. |

### No realtime updates

*Realtime connection* is off, and changes appear with a delay of about 2 seconds:

- A proxy or firewall between Home Assistant and the board may block WebSocket connections to port 3180. If the board answers reads but its realtime events stay away for about half a minute, the log shows one warning.
- After a restart of the Board Manager, the integration reconnects as soon as a read finds the board back, otherwise within 60 seconds at most.

### Darts are counted wrongly in the training session

- Darts on the board while Home Assistant starts are deliberately ignored.
- If a takeout is not detected and new darts follow, the previous visit is closed and the new darts are counted.
- If the connection is interrupted during a visit, the visit continues when the board still shows its darts afterwards. If the darts were pulled meanwhile, the visit is completed with the darts known before the interruption; darts thrown after that during the interruption are not counted.
- The training session counts what the board detects. If the board detects a wrong segment and you correct it in Autodarts, the session follows the correction only if the board reports it.

To start over, press **New training session** or *New session* on the training card. To stop counting, turn off the **Training session** switch and *Start sessions automatically*.

### A camera is reported as a problem

*Camera problem* turns on when a camera delivers no frames for 15 seconds during active detection. Check the camera's cable and USB port, and whether the camera appears in the Board Manager. Calibrating once more often helps as well.

### The card is missing or outdated

- **Custom element doesn't exist: autodarts-card:** restart Home Assistant after installing, then reload the browser page.
- **An old version of a card after an update:** reload the page. In the companion app, use *Settings → Companion app → Debugging → Reset frontend cache*.
- **The training history is empty:** the history is read from the recorder. It needs the `recorder` integration (enabled by default) and fills with completed visits.

## Diagnostics and logs

### Download diagnostics

**Settings → Devices & services → Autodarts →** the board's menu (⋮) → **Download diagnostics**. The file contains the board state, the settings summary, the Board Manager generation, connection states and the poll interval, whether a cloud connection is set up, the practice game with its rules and whether a bull-off runs, and the numbers of stored sessions, personal bests, player profiles, matches and darts at a double. Under `connection`, it also shows the connection history: failed reads in a row, the kind of the last error, the last successful read, how long the board has been away, the duration of the last read, reads answered in an unknown format and, for the realtime connection, connects, failed attempts, the current back-off, why it last ended and how many frames were skipped. The board ID, the board name, addresses, tokens and player names are redacted; error messages are not included.

### Enable debug logging

On the integration page, select **Enable debug logging**, reproduce the problem and then select **Disable debug logging**. Home Assistant downloads the log. Alternatively, in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.autodarts: debug
```

### Report a bug

Open an [issue](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose) with the Home Assistant version, the Board Manager version, the diagnostics file and the relevant log lines. Report security problems privately as described in [SECURITY.md](../SECURITY.md).
