"""The X01 rules in Home Assistant: their entities, the start_game action with
its old fields, tournaments and the leg a round limit decides."""

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.autodarts.const import DOMAIN
from custom_components.autodarts.scoring import (
    BULL_25_50,
    BULL_50_50,
    DOUBLE,
    MASTER,
    STRAIGHT,
)

from .local_helpers import (
    S20,
    T20,
    board,
    entity_id,
    record,
    setup_local,
    state,
    switch,
)
from .test_practice_setup import select_game, set_number, throw

S1 = ("S1", 1, 1)
S5 = ("S5", 5, 1)
PLAYERS = ["Alex", "Sam", "Kim"]


async def select(hass, key: str, option: str) -> None:
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id(hass, "select", key), "option": option},
        blocking=True,
    )
    await hass.async_block_till_done()


async def action(hass, service: str, **data) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)
    await hass.async_block_till_done()


async def test_the_rules_are_configuration_entities(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    practice = coordinator.practice
    registry = er.async_get(hass)
    for platform, key, value in (
        ("select", "practice_in_mode", STRAIGHT),
        ("select", "practice_out_mode", DOUBLE),
        ("select", "practice_bull_mode", BULL_25_50),
        ("number", "practice_max_rounds", "0"),
    ):
        assert state(hass, platform, key) == value
        entity = registry.async_get(entity_id(hass, platform, key))
        assert entity.entity_category == er.EntityCategory.CONFIG
    options = hass.states.get(entity_id(hass, "select", "practice_out_mode"))
    assert options.attributes["options"] == [STRAIGHT, DOUBLE, MASTER]
    await select_game(hass, "501")
    await throw(hass, coordinator, T20)
    # Another In mode starts the match anew; the same one changes nothing.
    await select(hass, "practice_in_mode", MASTER)
    assert practice.in_mode == MASTER and practice.players[0].remaining == 501
    await throw(hass, coordinator, T20)
    await select(hass, "practice_in_mode", MASTER)
    assert practice.players[0].remaining == 441
    # The Out mode waits for the next leg once darts count.
    await select(hass, "practice_out_mode", MASTER)
    assert state(hass, "select", "practice_out_mode") == MASTER
    assert practice.out_mode == DOUBLE and practice.out_mode_next == MASTER
    assert state(hass, "switch", "practice_double_out") == "off"
    await select(hass, "practice_bull_mode", BULL_50_50)
    assert practice.bull_mode == BULL_50_50 and practice.out_mode == MASTER
    await set_number(hass, "practice_max_rounds", 10)
    assert practice.max_rounds == 10
    assert state(hass, "number", "practice_max_rounds") == "10"
    remaining = hass.states.get(entity_id(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["round"] == 1
    assert remaining.attributes["max_rounds"] == 10
    # The old switches set the modes double or straight.
    await switch(hass, "practice_double_out", True)
    assert practice.out_mode == DOUBLE
    assert state(hass, "select", "practice_out_mode") == DOUBLE
    await switch(hass, "practice_double_in", True)
    assert state(hass, "select", "practice_in_mode") == DOUBLE


async def test_a_mode_that_cannot_win_a_start_of_3_is_refused(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.practice
    await select_game(hass, "501")
    # Master in and master out win a start of 3 with the treble 1.
    await select(hass, "practice_out_mode", MASTER)
    await select(hass, "practice_in_mode", MASTER)
    await set_number(hass, "practice_start_1", 3)
    with pytest.raises(ServiceValidationError) as error:
        await select(hass, "practice_out_mode", DOUBLE)
    assert error.value.translation_key == "unwinnable_start"
    with pytest.raises(ServiceValidationError):
        await select(hass, "practice_in_mode", DOUBLE)
    assert (practice.in_mode, practice.out_mode) == (MASTER, MASTER)
    await select(hass, "practice_out_mode", STRAIGHT)
    assert practice.out_mode == STRAIGHT
    # The bull mode wins or loses nothing.
    await select(hass, "practice_bull_mode", BULL_50_50)
    assert practice.bull_mode == BULL_50_50


async def test_start_game_sets_the_rules_and_takes_the_old_fields(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.practice
    await action(
        hass,
        "start_game",
        game="501",
        in_mode=MASTER,
        out_mode=MASTER,
        bull_mode=BULL_50_50,
        max_rounds=15,
        start_scores=[3],
    )
    assert (practice.in_mode, practice.out_mode, practice.bull_mode) == (
        MASTER,
        MASTER,
        BULL_50_50,
    )
    assert practice.max_rounds == 15 and practice.game == 501
    # Double in and double out still work, as the modes double or straight.
    await action(hass, "start_game", game="301", double_out=False, double_in=True)
    assert (practice.in_mode, practice.out_mode) == (DOUBLE, STRAIGHT)
    assert practice.bull_mode == BULL_50_50 and practice.max_rounds == 15
    await action(hass, "start_game", game="301", max_rounds=0, bull_mode=BULL_25_50)
    assert practice.max_rounds == 0 and practice.bull_mode == BULL_25_50
    # One mode is set one way.
    with pytest.raises(vol.Invalid):
        await action(hass, "start_game", game="501", out_mode=MASTER, double_out=True)
    for data in ({"in_mode": "sometimes"}, {"bull_mode": "50"}, {"max_rounds": 51}):
        with pytest.raises(vol.Invalid):
            await action(hass, "start_game", game="501", **data)
    # A start of 3 is checked against the modes the game will have.
    with pytest.raises(ServiceValidationError) as error:
        await action(
            hass,
            "start_game",
            game="501",
            in_mode=MASTER,
            out_mode=DOUBLE,
            start_scores=[3],
        )
    assert error.value.translation_key == "unwinnable_start"
    with pytest.raises(ServiceValidationError):
        await action(hass, "start_game", game="501", double_out=True, start_scores=[3])
    await action(
        hass,
        "start_game",
        game="501",
        in_mode=STRAIGHT,
        double_out=True,
        start_scores=[3],
    )
    assert practice.starts[0] == 3 and practice.out_mode == DOUBLE


async def test_a_tournament_plays_its_own_rules_and_gives_the_others_back(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    practice = coordinator.practice
    await action(
        hass,
        "start_game",
        game="501",
        in_mode=MASTER,
        out_mode=MASTER,
        bull_mode=BULL_50_50,
        max_rounds=12,
    )
    # A tournament plays straight or double in and out: master comes closest
    # to double.
    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1, sets=1)
    assert (practice.in_mode, practice.out_mode) == (DOUBLE, DOUBLE)
    assert practice.bull_mode == BULL_25_50 and practice.max_rounds == 0
    assert coordinator.tournament.plays(practice)
    await select(hass, "practice_bull_mode", BULL_50_50)
    assert not coordinator.tournament.plays(practice)
    await action(hass, "stop_tournament")
    await select_game(hass, "501")
    assert (practice.in_mode, practice.out_mode, practice.max_rounds) == (
        MASTER,
        MASTER,
        12,
    )
    # Master in and out win a start of 3, but a tournament plays them as double
    # in and double out, which cannot.
    with pytest.raises(ServiceValidationError) as error:
        await action(
            hass, "start_tournament", players=PLAYERS, game="101", start_scores=[3]
        )
    assert error.value.translation_key == "unwinnable_start"
    await action(
        hass,
        "start_tournament",
        players=PLAYERS,
        game="101",
        start_scores=[3],
        double_in=False,
    )
    # Straight in wins it.
    assert 3 in coordinator.tournament.tournament.starts


async def test_the_round_limit_decides_a_leg_without_a_record(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    events = record(hass, coordinator)
    await action(
        hass,
        "start_game",
        game="501",
        players=["Alex", "Sam"],
        legs=2,
        max_rounds=2,
    )
    for _ in range(2):
        await throw(hass, coordinator, S20, S20, S20)
        await throw(hass, coordinator, S5, S5, S5)
    [won] = [details for kind, details in events if kind == "leg_won"]
    assert won["name"] == "Alex" and won["rounds"] == 2 and won["checkout"] is None
    assert won["remaining"] == 381 and won["darts"] == 6
    bests = coordinator.records.bests
    assert "highest_checkout" not in bests and "fewest_darts_501" not in bests
    practice = coordinator.practice
    assert practice.legs[0]["rounds"] == 2 and practice.players[0].legs == 1
    profile = practice.profiles.players["alex"]
    assert profile.legs_won == 1 and profile.fewest_darts == {}
    remaining = hass.states.get(entity_id(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["round"] == 1 and remaining.state == "501"
    # A checkout still sets its records.
    practice.players[1].remaining = 40
    practice.current = 1
    await throw(hass, coordinator, ("D20", 20, 2))
    assert bests["highest_checkout"]["value"] == 40
