"""Attributes stay small where it matters: in the recorder, for a busy home with
eight players, a full history and a tournament."""

from datetime import timedelta

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.json import json_bytes
from homeassistant.util import dt as dt_util

from custom_components.autodarts.achievements import CATALOGUE
from custom_components.autodarts.doubles import DOUBLES
from custom_components.autodarts.positions import AIMS
from custom_components.autodarts.practice import GAMES
from custom_components.autodarts.progress import TREND_WEEKS, WEEK_FIELDS
from custom_components.autodarts.records import RECORDS
from custom_components.autodarts.report import REPORT_BESTS
from custom_components.autodarts.training import COUNTERS

from .local_helpers import board, setup_local

# What the recorder keeps of a state, at most; Home Assistant drops more than
# 16 KiB, and a state is written with every change.
RECORDED_BYTES = 4096
# Attributes that only cards read may be larger, within reason.
FULL_BYTES = 64 * 1024
# Names as long as a player name can be.
NAMES = [f"Player Number {index:02d} xx"[:20] for index in range(8)]
BEDS = [
    "MISS",
    "25",
    "BULL",
    *(f"{bed}{number}" for bed in "SDT" for number in range(1, 21)),
]


def iso(days: float = 0) -> str:
    return (dt_util.utcnow() - timedelta(days=days)).isoformat()


def session(index: int) -> dict:
    return {
        "started": iso(index + 0.1),
        "ended": iso(index),
        **dict.fromkeys(COUNTERS, 999),
        "highest_visit": 180,
        "manual_darts": 99,
    }


def match(index: int) -> dict:
    return {
        "started": iso(index + 0.1),
        "ended": iso(index),
        "game": 1001,
        "legs_to_win": 11,
        "sets_to_win": 7,
        "winner": 1,
        "players": [
            {
                "name": name,
                "legs": 11,
                "sets": 7,
                "match_legs": 77,
                "average": 99.99,
                "team": seat % 2 + 1,
            }
            for seat, name in enumerate(NAMES[:4])
        ],
        "winners": [1, 3],
    }


def profile(name: str) -> dict:
    return {
        "name": name,
        **dict.fromkeys(
            (
                "legs_played",
                "legs_won",
                "matches_played",
                "matches_won",
                "x01_darts",
                "x01_points",
                "first9_points",
                "first9_darts",
                "at_double",
                "checkouts",
                "cricket_darts",
                "cricket_marks",
            ),
            99999,
        ),
        "highest_visit": 180,
        "highest_checkout": 170,
        "best_mpr": 8.88,
        "fewest_darts": {str(game): 9 for game in GAMES},
        "doubles": {double: [999, 500] for double in DOUBLES},
        "last_played": iso(),
        "person": "person.someone_with_a_long_name",
    }


def progress(name: str) -> dict:
    monday = dt_util.now().date() - timedelta(days=dt_util.now().weekday())
    return {
        "name": name,
        "hits": dict.fromkeys(BEDS, 9999),
        "log": [1234, -1234, len(AIMS)] * 1000,
        "weeks": {
            (monday - timedelta(weeks=week)).isoformat(): [9999] * len(WEEK_FIELDS)
            for week in range(TREND_WEEKS)
        },
        "counters": {},
        "streak": 99,
        "best_streak": 99,
        "last_day": monday.isoformat(),
        "badges": {
            achievement.key: [iso()] * len(achievement.tiers)
            for achievement in CATALOGUE
        },
    }


def best(record: str, index: int) -> dict:
    return {"record": record, "value": 170, "name": NAMES[index % 8]}


def leg(index: int) -> dict:
    return {
        "game": 1001,
        "player": 1,
        "name": NAMES[index % 4],
        "players": 4,
        "team": 1,
        "team_name": f"{NAMES[0]} & {NAMES[2]}",
        "darts": 99,
        "average": 99.99,
        "checkout": 170,
        "start": 1001,
        "double_out": True,
        "double_in": True,
        "ended": iso(index),
    }


def summary() -> dict:
    return {
        "game": 1001,
        "ended": iso(),
        "winner": 1,
        "legs_to_win": 11,
        "sets_to_win": 7,
        "double_out": True,
        "players": [
            {
                "player": seat + 1,
                "name": name,
                "legs": 77,
                "sets": 7,
                "darts": 9999,
                "average": 99.99,
                "first_9_average": 99.99,
                "checkouts": 77,
                "darts_at_double": 999,
                "checkout_rate": 7.7,
                "highest_checkout": 170,
                "scores_100": 999,
                "scores_140": 999,
                "scores_180": 999,
                "best_leg": 9,
            }
            for seat, name in enumerate(NAMES[:4])
        ],
    }


def sizes(hass, entry) -> dict[str, tuple[int, int]]:
    """Bytes of every state's attributes: in the recorder, and in all."""
    result = {}
    for item in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        state = hass.states.get(item.entity_id)
        if state is None:
            continue
        unrecorded = (state.state_info or {}).get("unrecorded_attributes", set())
        recorded = {
            key: value
            for key, value in state.attributes.items()
            if key not in unrecorded
        }
        result[item.unique_id] = (
            len(json_bytes(recorded)),
            len(json_bytes(dict(state.attributes))),
        )
    return result


def within_budget(measured: dict[str, tuple[int, int]]) -> dict:
    return {
        key: size
        for key, size in measured.items()
        if size[0] > RECORDED_BYTES or size[1] > FULL_BYTES
    }


async def test_recorded_attributes_stay_small_in_a_busy_home(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    coordinator.training.restore(
        {
            "history": [session(index) for index in range(20)],
            "recent_visits": [
                {"time": iso(), "score": 180, "darts": 3, "segments": ["T20"] * 3}
            ]
            * 10,
            "hits": dict.fromkeys(BEDS, 9999),
        }
    )
    profiles = coordinator.practice.profiles
    profiles.restore(
        {
            "players": [profile(name) for name in NAMES],
            "matches": [match(index) for index in range(20)],
            "head_to_head": {
                f"{first.casefold()}\x00{second.casefold()}": [99, 99]
                for first in NAMES
                for second in NAMES
                if first < second
            },
        }
    )
    coordinator.progress.restore(
        {"players": [progress(name) for name in NAMES]}, profiles, dt_util.now()
    )
    coordinator.records.restore(
        {
            "bests": {
                record: {**best(record, index), "date": iso()}
                for index, record in enumerate(RECORDS)
            },
            "latest": {**best("highest_checkout", 0), "previous": 160, "date": iso()},
        }
    )
    report = coordinator.reports.report
    report.bests = [best("highest_visit", index) for index in range(REPORT_BESTS)]
    report.last = report.snapshot(99)

    # A tournament of eight players.
    await hass.services.async_call(
        "autodarts",
        "start_tournament",
        {"players": NAMES, "game": "501"},
        blocking=True,
    )
    await hass.async_block_till_done()
    measured = sizes(hass, entry)
    assert not within_budget(measured), within_budget(measured)
    # The big attributes are there, but not in the recorder.
    for key in ("tournament", "player_profiles", "achievements", "last_match"):
        assert measured[f"board-1_{key}"][1] > RECORDED_BYTES, key

    # Two teams of two in the longest match, with a full leg history.
    await hass.services.async_call("autodarts", "stop_tournament", {}, blocking=True)
    await coordinator.async_start_game(
        1001, names=NAMES[:4], legs=11, sets=7, teams=True
    )
    coordinator.practice.legs = [leg(index) for index in range(10)]
    coordinator.practice.summary = summary()
    await coordinator.async_new_leg()
    await hass.async_block_till_done()
    measured = sizes(hass, entry)
    assert not within_budget(measured), within_budget(measured)
    assert measured["board-1_practice_remaining"][1] > RECORDED_BYTES
