"""The start_game action and the detection quality with its calibration repair."""

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.autodarts.const import DOMAIN
from custom_components.autodarts.quality import (
    QUALITY_DARTS,
    QUALITY_MINIMUM,
    DetectionQuality,
)
from custom_components.autodarts.repairs import CalibrationFlow

from .local_helpers import (
    BASE,
    S20,
    T20,
    board,
    entity_id,
    setup_local,
    state,
)


def darts(quality: DetectionQuality, count: int, corrected_every: int = 0) -> None:
    """Visits of three darts; every n-th dart is corrected once."""
    for number in range(count):
        index = number % 3 + 1
        quality.record("dart_detected", {"dart_index": index})
        if corrected_every and (number + 1) % corrected_every == 0:
            quality.record("dart_corrected", {"dart_index": index})
        if index == 3:
            quality.record("visit_completed", {"score": 60})


def test_the_correction_rate_covers_the_last_hundred_darts():
    quality = DetectionQuality()
    assert quality.rate is None and not quality.enough
    darts(quality, 20, corrected_every=4)
    assert quality.snapshot() == {"rate": 25.0, "darts": 20, "corrected": 5}
    # A second correction of the same dart counts once; unknown darts not at all.
    quality.record("dart_detected", {"dart_index": 1})
    quality.record("dart_corrected", {"dart_index": 1})
    quality.record("dart_corrected", {"dart_index": 1})
    quality.record("dart_corrected", {"dart_index": 3})
    quality.record("dart_corrected", {"dart_index": "x"})
    assert quality.snapshot()["corrected"] == 6
    darts(quality, QUALITY_DARTS)
    assert quality.snapshot() == {"rate": 0.0, "darts": QUALITY_DARTS, "corrected": 0}
    assert quality.enough
    quality.reset()
    assert quality.rate is None


def test_a_correction_marks_the_dart_of_its_visit():
    quality = DetectionQuality()
    quality.record("dart_detected", {"dart_index": 1})
    quality.record("dart_detected", {"dart_index": 2})
    quality.record("dart_corrected", {"dart_index": 1})
    quality.record("visit_completed", {})
    # After the visit, index 1 belongs to the next visit only.
    quality.record("dart_corrected", {"dart_index": 1})
    assert quality.snapshot()["corrected"] == 1


def test_a_correction_of_a_dart_beyond_the_last_hundred_is_ignored():
    quality = DetectionQuality()
    quality.record("dart_detected", {"dart_index": 1})
    # Without pulled darts, the first dart leaves the window of the last hundred.
    for _ in range(QUALITY_DARTS):
        quality.record("dart_detected", {"dart_index": 2})
    quality.record("dart_corrected", {"dart_index": 1})
    assert quality.snapshot() == {"rate": 0.0, "darts": QUALITY_DARTS, "corrected": 0}
    quality.record("dart_corrected", {"dart_index": 2})
    assert quality.snapshot()["corrected"] == 1


async def test_start_game_sets_up_a_match_in_one_call(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {
            "game": "501",
            "players": ["Dennis", "Lea"],
            "legs": 3,
            "sets": 2,
            "double_out": False,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    practice = entry.runtime_data.local.practice
    assert practice.game == 501 and len(practice.players) == 2
    assert practice.names[:3] == ["Dennis", "Lea", ""]
    assert (practice.legs_to_win, practice.sets_to_win) == (3, 2)
    assert practice.double_out is False
    assert state(hass, "select", "practice_game") == "501"
    assert state(hass, "number", "practice_players") == "2"

    # Without players, the players stay; a training game replaces X01.
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {"game": "around_the_clock", "config_entry_id": entry.entry_id},
        blocking=True,
    )
    assert practice.drill == "around_the_clock" and len(practice.players) == 2
    assert state(hass, "sensor", "practice_target") == "1"

    await hass.services.async_call(
        DOMAIN, "start_game", {"game": "cricket", "legs": 2}, blocking=True
    )
    await hass.async_block_till_done()
    assert practice.cricket and practice.drill is None and practice.legs_to_win == 2
    assert state(hass, "select", "practice_game") == "cricket"
    assert state(hass, "sensor", "practice_target") == "T20"

    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {
            "game": "killer",
            "players": ["A", "B", "C"],
            "bull_off": True,
            "double_in": True,
        },
        blocking=True,
    )
    assert practice.party.kind == "killer" and len(practice.players) == 3
    assert practice.bull_off and practice.double_in and practice.bulling is not None
    assert state(hass, "select", "practice_game") == "killer"


async def test_start_game_needs_two_players_for_killer_and_names_of_their_own(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.practice
    for data, key in (
        # One player is at the board, and no names change that.
        ({"game": "killer"}, "killer_players"),
        ({"game": "killer", "players": ["Alex"]}, "killer_players"),
        ({"game": "501", "players": ["Alex", "Sam", " alex "]}, "duplicate_player"),
    ):
        with pytest.raises(ServiceValidationError) as error:
            await hass.services.async_call(DOMAIN, "start_game", data, blocking=True)
        assert error.value.translation_key == key
    assert error.value.translation_placeholders == {"name": "alex"}
    assert practice.game == 0 and practice.party is None
    # Players without a name may share it; the bull-off rule is a field, too.
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {"game": "killer", "players": ["", "", "Kim"], "bull_off_distance": True},
        blocking=True,
    )
    assert practice.party.kind == "killer" and practice.bull_off_distance
    assert practice.names[:3] == ["", "", "Kim"]
    # With the players at the board, Killer starts without names.
    await hass.services.async_call(DOMAIN, "start_game", {"game": "501"}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "start_game", {"game": "killer"}, blocking=True
    )
    assert practice.party.kind == "killer"


async def fix(hass, hass_client, issue_id: str, confirm: bool = True) -> dict:
    """Open a repair as the user interface does, and confirm it."""
    assert await async_setup_component(hass, "repairs", {})
    client = await hass_client()
    response = await client.post(
        "/api/repairs/issues/fix", json={"handler": DOMAIN, "issue_id": issue_id}
    )
    flow = await response.json()
    if not confirm or flow["type"] != "form":
        return flow
    assert flow["step_id"] == "confirm"
    response = await client.post(f"/api/repairs/issues/fix/{flow['flow_id']}", json={})
    return await response.json()


async def test_many_corrections_suggest_a_calibration_that_the_repair_runs(
    hass, aioclient_mock, hass_client
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    issue_id = f"calibration_{entry.entry_id}"
    registry = ir.async_get(hass)

    # Every visit, the board reads the first dart anew: a third is corrected.
    for visit in range(QUALITY_MINIMUM // 3 + 1):
        for darts_on_board in ((T20,), (S20,), (S20, T20), (S20, T20, T20), ()):
            coordinator.async_receive("state", board(*darts_on_board))
        if visit == QUALITY_MINIMUM // 3 - 1:
            # Too few darts yet to tell.
            assert registry.async_get_issue(DOMAIN, issue_id) is None
    await hass.async_block_till_done()
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None and issue.is_fixable
    assert issue.translation_placeholders == {"rate": "33"}
    rate = hass.states.get(entity_id(hass, "sensor", "correction_rate"))
    assert float(rate.state) == 33.3
    assert (rate.attributes["darts"], rate.attributes["corrected"]) == (51, 17)

    aioclient_mock.post(f"{BASE}/api/config/calibration/auto", json={})
    placeholders = (await fix(hass, hass_client, issue_id, confirm=False))[
        "description_placeholders"
    ]
    assert placeholders == {"rate": "33"}
    result = await fix(hass, hass_client, issue_id)
    assert result["type"] == "create_entry"
    assert any(
        call[0] == "POST" and call[1].path == "/api/config/calibration/auto"
        for call in aioclient_mock.mock_calls
    )
    assert registry.async_get_issue(DOMAIN, issue_id) is None
    assert coordinator.quality.rate is None
    assert state(hass, "sensor", "correction_rate") == "unknown"


async def test_a_rejected_calibration_keeps_the_repair_open(
    hass, aioclient_mock, hass_client
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    issue_id = f"calibration_{entry.entry_id}"
    darts(coordinator.quality, QUALITY_MINIMUM, corrected_every=2)
    coordinator.async_receive("state", board())
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

    aioclient_mock.post(f"{BASE}/api/config/calibration/auto", status=409)
    result = await fix(hass, hass_client, issue_id)
    assert result["type"] == "abort" and result["reason"] == "calibration_failed"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    assert coordinator.quality.snapshot()["darts"] == QUALITY_MINIMUM


async def test_the_repair_gives_up_on_an_unloaded_board(
    hass, aioclient_mock, hass_client
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    issue_id = f"calibration_{entry.entry_id}"
    darts(entry.runtime_data.local.quality, QUALITY_MINIMUM, corrected_every=2)
    entry.runtime_data.local.async_receive("state", board())
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    result = await fix(hass, hass_client, issue_id)
    assert result["type"] == "abort" and result["reason"] == "board_unavailable"


async def test_another_fixable_issue_only_asks_for_confirmation(
    hass, aioclient_mock, hass_client
):
    await setup_local(hass, aioclient_mock)
    ir.async_create_issue(
        hass,
        DOMAIN,
        "something_else",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="board_manager_1",
    )
    result = await fix(hass, hass_client, "something_else")
    assert result["type"] == "create_entry"


async def test_a_calibration_without_its_notice_asks_without_a_rate(hass):
    """The notice may be gone meanwhile, for example after a recalibration."""
    flow = CalibrationFlow("gone")
    flow.hass, flow.handler, flow.issue_id = hass, DOMAIN, "calibration_gone"
    result = await flow.async_step_init()
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"] is None
