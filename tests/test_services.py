"""The actions: which board they act on, and what they accept."""

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts.const import DOMAIN
from custom_components.autodarts.practice import MAX_LEGS, MAX_PLAYERS, MAX_SETS
from custom_components.autodarts.profiles import NAME_LENGTH

from .local_helpers import board, entry_data, mock_cloud, setup_local

LONGEST = "x" * NAME_LENGTH


@pytest.mark.parametrize(
    "data",
    [
        {"game": "401"},
        {"game": "Cricket"},
        {"game": "501", "players": []},
        {"game": "501", "players": ["A"] * (MAX_PLAYERS + 1)},
        {"game": "501", "players": [LONGEST + "x"]},
        {"game": "501", "legs": 0},
        {"game": "501", "legs": MAX_LEGS + 1},
        {"game": "501", "sets": 0},
        {"game": "501", "sets": MAX_SETS + 1},
        {"game": "501", "legs": "many"},
        {"game": "501", "double_out": "sometimes"},
        {"game": "501", "unknown": True},
        {},
    ],
)
async def test_start_game_rejects_values_beyond_its_limits(hass, aioclient_mock, data):
    entry = await setup_local(hass, aioclient_mock, state=board())
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, "start_game", data, blocking=True)
    assert entry.runtime_data.local.practice.game == 0


@pytest.mark.parametrize(
    "data,check",
    [
        (
            {"game": "501", "players": ["A", "B", "C", LONGEST]},
            lambda practice: practice.names == ["A", "B", "C", LONGEST],
        ),
        # One name is a list of one.
        (
            {"game": "301", "players": "Alex"},
            lambda practice: practice.names[0] == "Alex",
        ),
        (
            {"game": "501", "legs": MAX_LEGS, "sets": MAX_SETS},
            lambda practice: (
                (practice.legs_to_win, practice.sets_to_win) == (MAX_LEGS, MAX_SETS)
            ),
        ),
        (
            {"game": "501", "legs": "2", "double_in": "on"},
            lambda practice: practice.legs_to_win == 2 and practice.double_in,
        ),
    ],
)
async def test_start_game_accepts_values_at_its_limits(
    hass, aioclient_mock, data, check
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    await hass.services.async_call(DOMAIN, "start_game", data, blocking=True)
    assert check(entry.runtime_data.local.practice)


@pytest.mark.parametrize(
    "data", [{}, {"name": ""}, {"name": LONGEST + "x"}, {"name": ["A", "B"]}]
)
async def test_delete_player_needs_one_name(hass, aioclient_mock, data):
    await setup_local(hass, aioclient_mock, state=board())
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, "delete_player", data, blocking=True)


@pytest.mark.parametrize("service", ["start_game", "delete_player"])
async def test_an_action_names_the_board_problem(hass, aioclient_mock, service):
    """Home Assistant explains entries that are unknown, foreign or not loaded."""
    data = {"game": "501"} if service == "start_game" else {"name": "Alex"}
    entry = await setup_local(hass, aioclient_mock, state=board())
    other = MockConfigEntry(domain="demo", title="Demo")
    other.add_to_hass(hass)

    async def problem(entry_id: str) -> tuple[str | None, str | None]:
        with pytest.raises(ServiceValidationError) as error:
            await hass.services.async_call(
                DOMAIN,
                service,
                {**data, "config_entry_id": entry_id},
                blocking=True,
            )
        return error.value.translation_domain, error.value.translation_key

    assert await problem("nope") == (
        "homeassistant",
        "service_config_entry_not_found",
    )
    assert await problem(other.entry_id) == (
        "homeassistant",
        "service_config_entry_wrong_domain",
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await problem(entry.entry_id) == (
        "homeassistant",
        "service_config_entry_not_loaded",
    )
    # Without an entry, only a loaded board with a local connection counts.
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(DOMAIN, service, data, blocking=True)
    assert error.value.translation_key == "no_board"


async def test_a_cloud_only_board_cannot_play(hass, aioclient_mock):
    mock_cloud(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, version=2, data=entry_data())
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for data in ({"game": "501"}, {"game": "501", "config_entry_id": entry.entry_id}):
        with pytest.raises(ServiceValidationError) as error:
            await hass.services.async_call(DOMAIN, "start_game", data, blocking=True)
        assert error.value.translation_key == "no_board"
