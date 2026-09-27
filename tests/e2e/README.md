# Docker end-to-end test

The suite mounts `custom_components/autodarts` read-only into a real Home Assistant
container and connects it to a deterministic Board Manager double. The double runs
from the same pinned Home Assistant image, so it needs no additional image. CI runs
the scenario on every push and pull request.

Run locally with Docker and Compose:

```bash
bash tests/e2e/run.sh
```

The scenario uses only Home Assistant's public REST and WebSocket APIs and verifies:

- onboarding and local config flow, including invalid-host, unreachable-board and
  duplicate-board handling
- entity and device registry contents, discovered per-camera entities and
  disabled-by-default entities
- buttons, switches and the standby select, compared with the exact Board Manager
  requests they send
- realtime darts, corrections and takeouts over the Board Manager WebSocket with
  polling disabled, including training counters and their persistence
- faults injected into the Board Manager double: a socket that drops in the middle
  of a visit, an outage while darts are pulled and thrown again, failing and slow
  reads, malformed frames and a restart; visits, practice scores and entities
  must come through them
- the online bridge: switched on in the options, calls of Tools for Autodarts
  become board events and the diagnostic sensor, and switched off it is gone
- the weekly report and its settings, the training calendar through
  `calendar.get_events`, and exports as JSON and CSV with their download, with and
  without a login, and a refused folder outside the configuration
- a practice match of two players that ends with its summary in the practice sensor
  and the `match_won` event, and double out switched during a leg, which applies
  from the next leg
- diagnostics without the board ID, API key or webhook address, and logs without
  errors, tracebacks or secrets
- removal of the entry, its entities, the realtime connection and the stored
  training session, weekly report and journal

Optional environment variables:

- `E2E_PORT`: host port for Home Assistant on `127.0.0.1`, default `18123`
- `DOCKER_BIN`: Docker CLI path, default `docker`
- `E2E_PROJECT_NAME`: Compose project name, default `autodarts_e2e`
- `HOME_ASSISTANT_IMAGE`: pinned Home Assistant image override
- `KEEP_E2E=1`: keep containers and the disposable volume after the suite

All users, passwords, board IDs and API keys are synthetic. Dependabot keeps the
pinned Home Assistant image up to date.
