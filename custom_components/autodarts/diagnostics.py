"""Diagnostics contain local status only; never cloud tokens or board API keys."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_LOCAL_ONLY
from .runtime import AutodartsConfigEntry

# Identifiers, addresses, credentials and player names that must never leave a
# bug report; segment names of darts are redacted with the player names.
TO_REDACT = {"board_id", "client_id", "host", "token", "ip", "name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AutodartsConfigEntry
) -> dict[str, Any]:
    runtime = entry.runtime_data
    local = runtime.local
    return {
        "entry": {
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "local": async_redact_data(local.data if local else None, TO_REDACT),
        "local_available": bool(local and local.last_update_success),
        "cloud_configured": not entry.data.get(CONF_LOCAL_ONLY, False),
        "cloud_available": bool(runtime.cloud and runtime.cloud.last_update_success),
        "realtime_connected": bool(local and local.stream_connected),
        "board_manager_generation": local.generation if local else None,
        "training_sessions": (
            {
                "active": local.training.active,
                "auto_start": local.training.auto_start,
                "idle_minutes": local.training.idle_minutes,
                "stored_sessions": len(local.training.history),
            }
            if local
            else None
        ),
        "practice_game": (
            {
                "game": (
                    "cricket"
                    if local.practice.cricket
                    else local.practice.drill or local.practice.game or None
                ),
                "double_out": local.practice.double_out,
                "players": len(local.practice.players),
                "legs_to_win": local.practice.legs_to_win,
                "sets_to_win": local.practice.sets_to_win,
                "stored_legs": len(local.practice.legs),
                "legs_total": local.practice.legs_total,
            }
            if local
            else None
        ),
        # Counts only: the bests carry the names of players.
        "records": (
            {
                "stored_bests": len(local.records.bests),
                "streak": local.records.streak,
                "best_streak": local.records.best_streak,
                "daily_goal": local.records.goal,
            }
            if local
            else None
        ),
        "poll_interval_seconds": (
            local.update_interval.total_seconds()
            if local and local.update_interval
            else None
        ),
        # Counts, kinds of errors and durations only; no addresses or messages.
        "connection": local.diagnostics() if local else None,
    }
