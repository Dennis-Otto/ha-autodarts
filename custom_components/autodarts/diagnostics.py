"""Diagnostics contain local status only; never cloud tokens or board API keys."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .local_coordinator import AutodartsLocalCoordinator
from .practice import OPTIONS
from .runtime import AutodartsConfigEntry

# Identifiers, addresses, credentials and player names that must never leave a
# bug report; segment names of darts are redacted with the player names.
TO_REDACT = {"board_id", "client_id", "host", "token", "ip", "name", "team_name"}


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
        # Set up with a cloud client, not merely asked for one.
        "cloud_configured": runtime.cloud is not None,
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
        "practice_game": _practice(local) if local else None,
        # Counts only: the bests, profiles and matches carry the names of players.
        "records": (
            {
                "stored_bests": len(local.records.bests),
                "streak": local.records.streak,
                "best_streak": local.records.best_streak,
                "daily_goal": local.records.goal,
                "player_profiles": len(local.practice.profiles.players),
                "stored_matches": len(local.practice.profiles.matches),
                "double_attempts": local.practice.doubles.snapshot()["attempts"],
            }
            if local
            else None
        ),
        # Counts only: the journal carries the names of players.
        "reports": (
            {
                "weekday": local.reports.report.weekday,
                "time": local.reports.report.time.isoformat(timespec="minutes"),
                "journal_sessions": len(local.reports.journal.sessions),
                "journal_matches": len(local.reports.journal.matches),
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
        # Never the secret webhook address.
        "online_bridge": (
            runtime.bridge.diagnostics() if runtime.bridge else {"enabled": False}
        ),
    }


def _practice(local: AutodartsLocalCoordinator) -> dict[str, Any]:
    """The game, its rules and its progress; the players only as a number."""
    practice = local.practice
    return {
        # A training game, or 501, cricket or a party game such as killer.
        "game": practice.drill or practice.kind,
        **{option: getattr(practice, option) for option in OPTIONS},
        "bull_off_running": practice.bulling is not None,
        "players": len(practice.players),
        "legs_to_win": practice.legs_to_win,
        "sets_to_win": practice.sets_to_win,
        "stored_legs": len(practice.legs),
        "legs_total": practice.legs_total,
    }
