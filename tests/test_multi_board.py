"""Two boards in one home: their entities, events and actions stay apart."""

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.autodarts.const import DOMAIN

from .local_helpers import (
    SECOND_BASE,
    T20,
    board,
    entity_id,
    record,
    state,
    unique_ids,
)


def own(ids: set[str], board_id: str) -> set[str]:
    """The keys of the unique IDs, without the board ID."""
    prefix = f"{board_id}_"
    assert all(unique_id.startswith(prefix) for unique_id in ids)
    return {unique_id.removeprefix(prefix) for unique_id in ids}


async def test_each_board_has_its_own_entities_and_device(hass, two_boards):
    first, second = two_boards
    keys = own(unique_ids(hass, first), "board-1")
    # The second board has two cameras instead of three.
    assert own(unique_ids(hass, second), "board-2") == keys - {
        "camera_2",
        "camera_2_fps",
        "camera_2_problem",
        "calibrate_camera_2",
    }
    for entry in two_boards:
        assert entry.runtime_data.local.board_id == entry.data["board_id"]
    assert second.runtime_data.local.client.base_url == SECOND_BASE
    # Both devices have the default name; their entity IDs still differ.
    first_id = entity_id(hass, "event", "board_events")
    second_id = entity_id(hass, "event", "board_events", "board-2")
    assert first_id != second_id


async def test_darts_of_one_board_announce_on_that_board_only(hass, two_boards):
    first, second = two_boards
    first_events = record(hass, first.runtime_data.local)
    second_events = record(hass, second.runtime_data.local)
    second.runtime_data.local.async_receive("state", board(T20))
    await hass.async_block_till_done()
    assert [kind for kind, _ in second_events] == ["dart_detected"]
    assert first_events == []
    assert state(hass, "sensor", "last_throw", "board-2") == "T20"
    assert state(hass, "sensor", "last_throw", "board-1") == "unknown"
    event = hass.states.get(entity_id(hass, "event", "board_events", "board-2"))
    assert event.attributes["event_type"] == "dart_detected"
    assert state(hass, "event", "board_events", "board-1") == "unknown"


async def test_actions_need_the_board_and_act_on_it_only(hass, two_boards):
    first, second = two_boards
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(
            DOMAIN, "start_game", {"game": "501"}, blocking=True
        )
    assert error.value.translation_key == "several_boards"
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {"game": "301", "players": ["Alex"], "config_entry_id": second.entry_id},
        blocking=True,
    )
    assert second.runtime_data.local.practice.game == 301
    assert first.runtime_data.local.practice.game == 0
    assert state(hass, "select", "practice_game", "board-2") == "301"
    assert state(hass, "select", "practice_game", "board-1") == "off"

    # Alex plays on the second board only, so only there is a profile to delete.
    coordinator = second.runtime_data.local
    for count in range(1, 4):
        coordinator.async_receive("state", board(*[T20] * count))
    coordinator.async_receive("state", board())
    await hass.async_block_till_done()
    assert "alex" in coordinator.practice.profiles.players
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(
            DOMAIN,
            "delete_player",
            {"name": "Alex", "config_entry_id": first.entry_id},
            blocking=True,
        )
    assert error.value.translation_key == "unknown_player"
    await hass.services.async_call(
        DOMAIN,
        "delete_player",
        {"name": "ALEX", "config_entry_id": second.entry_id},
        blocking=True,
    )
    assert not coordinator.practice.profiles.players


async def test_one_board_away_leaves_the_other_one_alone(hass, two_boards):
    first, second = two_boards
    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    # With one board loaded, the actions find it without an entry.
    await hass.services.async_call(
        DOMAIN, "start_game", {"game": "cricket"}, blocking=True
    )
    assert second.runtime_data.local.practice.cricket
    assert state(hass, "switch", "detection", "board-2") == "on"
