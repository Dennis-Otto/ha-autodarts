"""The stored training: private, versioned and restored after a restart."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts.const import DOMAIN
from custom_components.autodarts.storage import (
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
    TrainingStore,
    storage_key,
)

from .local_helpers import T20, board, local_entry_data, mock_board, state


async def setup(hass, aioclient_mock, entry_id="stored-entry"):
    mock_board(aioclient_mock, state=board())
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data=local_entry_data(), entry_id=entry_id
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_the_store_is_private_and_named_after_the_entry(hass):
    store = TrainingStore(hass, "some-entry")
    assert store.key == storage_key("some-entry") == "autodarts.some-entry.training"
    assert (store.version, store.minor_version) == (1, 1)
    # Player names are stored, so the file is readable by Home Assistant only.
    assert store._private is True


async def test_the_current_layout_survives_a_restart(
    hass, aioclient_mock, hass_storage
):
    entry = await setup(hass, aioclient_mock)
    coordinator = entry.runtime_data.local
    await coordinator.async_start_game(501, names=["Alex", "Sam"], legs=2)
    for count in range(1, 4):
        coordinator.async_receive("state", board(*[T20] * count))
    coordinator.async_receive("state", board())
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    saved = hass_storage[storage_key(entry.entry_id)]
    assert (saved["version"], saved["minor_version"]) == (
        STORAGE_VERSION,
        STORAGE_MINOR_VERSION,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    practice = entry.runtime_data.local.practice
    assert practice.names[:2] == ["Alex", "Sam"] and practice.legs_to_win == 2
    assert [player.remaining for player in practice.players] == [321, 501]
    assert practice.current == 1
    assert state(hass, "sensor", "training_darts") == "3"
    assert "alex" in practice.profiles.players


async def test_data_of_a_newer_minor_version_loads_after_a_downgrade(
    hass, aioclient_mock, hass_storage
):
    key = storage_key("stored-entry")
    hass_storage[key] = {
        "version": STORAGE_VERSION,
        "minor_version": STORAGE_MINOR_VERSION + 1,
        "key": key,
        "data": {
            "darts": 12,
            "points": 300,
            "practice": {"game": 301, "names": ["Kim"], "future_rule": True},
            "records": {"goal": 150},
            "a_future_part": {"kept": "or ignored"},
        },
    }
    entry = await setup(hass, aioclient_mock)
    coordinator = entry.runtime_data.local
    assert coordinator.training.snapshot()["darts"] == 12
    assert coordinator.practice.game == 301 and coordinator.practice.names[0] == "Kim"
    assert coordinator.records.goal == 150
    # The migration writes the data back in this version's layout.
    assert hass_storage[key]["minor_version"] == STORAGE_MINOR_VERSION
