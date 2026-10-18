"""Constants for the Autodarts integration."""

from typing import Final

DOMAIN: Final = "autodarts"

# The languages of the integration: its translations and the texts of the cards,
# the words of the calendar, of the highlight gallery and of the voice packs, and
# the names of the games that a voice assistant understands.
LANGUAGES: Final = ("en", "de", "es", "fr", "nl")

DEFAULT_PORT: Final = 3180
DEFAULT_SCAN_INTERVAL: Final = 5  # seconds, cloud polling during a match
IDLE_SCAN_INTERVAL: Final = 60  # seconds, cloud polling without a match

# Autodarts has not issued the public OAuth client ID for this integration yet.
# Until it does, setup offers no cloud link and entries without a client ID run
# locally instead of asking for a login that cannot be completed. Once it has,
# CLOUD_CLIENT_ID holds it and CLOUD_LINK_AVAILABLE turns True, as decision 0020
# in docs/decisions/ describes.
CLOUD_LINK_AVAILABLE = False
# The public client "Autodarts for Home Assistant" with the device grant, which
# the cloud step of the setup offers.
CLOUD_CLIENT_ID = ""


def event_signal(entry_id: str) -> str:
    """The signal that carries the events of a board to its event entity."""
    return f"{DOMAIN}_{entry_id}_event"


# Config entry keys
CONF_TOKEN: Final = "token"
CONF_CLIENT_ID: Final = "client_id"
CONF_LOCAL_ONLY: Final = "local_only"
CONF_BOARD_ID: Final = "board_id"
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
# Major Board Manager version the entities were built for (1 classic, 2 headless).
CONF_API_GENERATION: Final = "api_generation"
# Board Manager version found without /api/system; it runs as Board Manager 1.
CONF_NO_SYSTEM_API: Final = "no_system_api"
# A dartboard without Autodarts: every dart is entered in Home Assistant.
CONF_MANUAL_BOARD: Final = "manual_board"

# Detection states around a start or stop; the cameras open or close meanwhile.
LIFECYCLE_STATUSES: Final = ("starting", "stopping", "stopped", "calibrating", "error")

# Autodarts' guide to the headless Board Manager 2, which replaces the app.
BOARD_MANAGER_2_URL: Final = (
    "https://docs.autodarts.com/getting-started/detection/headless-installation/"
)

# Lists boards on the same public network, as the Board Manager app does.
DISCOVERY_URL: Final = "https://discover.autodarts.com"

PLATFORMS: Final = [
    "sensor",
    "binary_sensor",
    "button",
    "switch",
    "select",
    "number",
    "text",
    "camera",
    "event",
    "update",
    "calendar",
    "time",
]

# Sensor keys — board
SENSOR_BOARD_STATUS: Final = "board_status"
SENSOR_BOARD_EVENT: Final = "board_event"

# Sensor keys — match
SENSOR_GAME_MODE: Final = "game_mode"
SENSOR_MATCH_STATE: Final = "match_state"
SENSOR_ROUND: Final = "round"

# Sensor keys — detection
SENSOR_LAST_THROW: Final = "last_throw"
SENSOR_NUM_THROWS: Final = "num_throws"
SENSOR_VISIT_SCORE: Final = "visit_score"
SENSOR_DARTS_THROWN: Final = "darts_thrown"
