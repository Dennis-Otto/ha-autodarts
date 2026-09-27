"""Prepare the demo instance: a configured board, a dashboard and a visit in progress.

Runs inside the Home Assistant container like scenario.py and reuses its API helpers.
The resulting instance is used for previews and documentation screenshots.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import aiohttp
from board_mock import GENERATION, PORT
from pictures import avatar, board_photo
from scenario import HA, Scenario, wait_for

DASHBOARD = "autodarts-demo"
STRATEGY_DASHBOARD = "autodarts-auto"


def dart(name: str, number: int, multiplier: int, bed: str, x: float, y: float):
    return {
        "segment": {
            "name": name,
            "number": number,
            "multiplier": multiplier,
            "bed": bed,
        },
        "coords": {"x": x, "y": y},
    }


T20 = dart("T20", 20, 3, "Triple", 0.035, 0.608)
T20_LEFT = dart("T20", 20, 3, "Triple", -0.041, 0.604)
S20 = dart("S20", 20, 1, "SingleOuter", 0.02, 0.8)
S1 = dart("S1", 1, 1, "SingleOuter", 0.2, 0.74)
S5 = dart("S5", 5, 1, "SingleOuter", -0.24, 0.76)
T19 = dart("T19", 19, 3, "Triple", -0.19, -0.575)
D16 = dart("D16", 16, 2, "Double", -0.58, -0.8)
BULL = dart("Bull", 25, 2, "Double", 0.012, -0.02)
OUTER_BULL = dart("25", 25, 1, "Single", -0.06, 0.07)

# Completed visits give the session statistics realistic values.
HISTORY = [
    [T20, S20, S1],
    [T20, T20_LEFT, S5],
    [S20, OUTER_BULL, T19],
    [T20, S20, D16],
    [BULL, S20, S20],
]
CURRENT = [T20, S5, BULL]
# Earlier, finished sessions for the training card's list of past sessions.
EARLIER = [
    [[T20, T20_LEFT, S20], [S20, S1, S5]],
    [[T19, S20, S20], [BULL, OUTER_BULL, S20], [T20, S5, S1]],
]

CARDS = {
    "board": [{"type": "custom:autodarts-card", "grid_options": {"columns": "full"}}],
    "training": [
        {"type": "custom:autodarts-training-card", "grid_options": {"columns": "full"}}
    ],
    "status": [
        {"type": "custom:autodarts-status-card", "grid_options": {"columns": "full"}}
    ],
    "scoreboard": [{"type": "custom:autodarts-scoreboard-card", "caller": True}],
    "players": [{"type": "custom:autodarts-players-card", "export": True}],
    "doubles": [{"type": "custom:autodarts-doubles-card"}],
    "styles": [
        {
            "type": "custom:autodarts-card",
            "board_style": "autodarts",
            "layout": "vertical",
        },
        {"type": "custom:autodarts-card", "layout": "board", "title": "Board"},
    ],
}


# Synthetic people: Alex and Sam are at home, Kim is out.
PEOPLE = [
    ("Alex", (0, 150, 199), "home"),
    ("Sam", (156, 39, 176), "home"),
    ("Kim", (239, 108, 0), "not_home"),
]
# Highlight photos named as the highlight photo blueprint saves them.
GALLERY = Path("/media/autodarts/highlights")
HIGHLIGHTS = {
    "2026-09-26_21-05-33_Alex_180.jpg": ["T20", "T20", "T20"],
    "2026-09-26_21-19-02_Sam_checkout-121.jpg": ["T20", "T11", "D14"],
    "2026-09-12_20-44-10_Kim_140.jpg": ["T20", "T20", "S20"],
    "2026-08-29_19-30-00_Alex_checkout-170.jpg": ["T20", "T20", "BULL"],
    "2026-08-15_18-02-45_Sam_180.jpg": ["T20", "T20", "T20"],
}


def dashboard() -> dict:
    wide = {
        "board": 2,
        "training": 2,
        "status": 2,
        "scoreboard": 2,
        "players": 2,
        "doubles": 2,
        "styles": 1,
    }
    return {
        "title": "Autodarts",
        "views": [
            *(
                {
                    "title": name.title(),
                    "path": name,
                    "type": "sections",
                    "max_columns": 2,
                    "sections": [
                        {"type": "grid", "column_span": wide[name], "cards": [card]}
                        for card in cards
                    ],
                }
                for name, cards in CARDS.items()
            ),
            # The scoreboard on a screen at the board, idle after a short time.
            {
                "title": "Idle",
                "path": "idle",
                "panel": True,
                "cards": [
                    {
                        "type": "custom:autodarts-scoreboard-card",
                        "full_height": True,
                        "idle_after": 10,
                        "idle_interval": 60,
                    }
                ],
            },
        ],
    }


# A week of the training calendar before the demo day: (days ago, start, minutes,
# darts, points) of sessions, and (days ago, start, minutes, game, players,
# winner) of matches with every player's legs won and result.
WEEK_SESSIONS = [
    (6, "18:40", 45, 312, 5642),
    (5, "19:05", 35, 240, 4010),
    (3, "18:15", 50, 366, 6468),
    (2, "20:10", 25, 180, 3150),
    (1, "19:30", 60, 420, 8134),
]
WEEK_MATCHES = [
    (
        6,
        "19:40",
        32,
        501,
        [("Alex", 3, {"average": 62.4}), ("Sam", 2, {"average": 55.1})],
        1,
    ),
    (
        4,
        "20:00",
        21,
        "cricket",
        [("Alex", 1, {"mpr": 2.4}), ("Kim", 2, {"mpr": 2.7})],
        2,
    ),
    (
        3,
        "19:20",
        28,
        501,
        [("Sam", 3, {"average": 58.9}), ("Kim", 1, {"average": 49.3})],
        1,
    ),
    (
        2,
        "20:40",
        14,
        "killer",
        [
            ("Alex", 0, {"points": 1}),
            ("Sam", 0, {"points": 0}),
            ("Kim", 1, {"points": 3}),
        ],
        3,
    ),
]


def week_journal(now: datetime) -> dict:
    """The stored training journal of the week before the demo day."""

    def moment(days: int, start: str, minutes: int = 0) -> datetime:
        hour, minute = map(int, start.split(":"))
        day = (now - timedelta(days=days)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return day + timedelta(minutes=minutes)

    sessions = [
        {
            "started": moment(days, start).isoformat(),
            "ended": moment(days, start, minutes).isoformat(),
            "darts": darts,
            "points": points,
            "visits": darts // 3,
            "highest_visit": 140 if darts > 300 else 121,
            "scores_100": darts // 30,
            "scores_140": darts // 120,
            "scores_180": int(darts > 400),
        }
        for days, start, minutes, darts, points in WEEK_SESSIONS
    ]
    matches = [
        {
            "started": moment(days, start).isoformat(),
            "ended": moment(days, start, minutes).isoformat(),
            "game": game,
            "legs_to_win": {501: 3, "cricket": 2}.get(game, 1),
            "sets_to_win": 1,
            "winner": winner,
            # One set each: the legs of the set are the legs of the match.
            "players": [
                {"name": name, "legs": legs, "match_legs": legs, **result}
                for name, legs, result in players
            ],
        }
        for days, start, minutes, game, players, winner in WEEK_MATCHES
    ]
    return {
        "sessions": sorted(sessions, key=lambda entry: entry["ended"]),
        "matches": sorted(matches, key=lambda entry: entry["ended"]),
        "match_start": None,
    }


async def seed_journal(demo: Scenario, entry_id: str) -> None:
    """Give the training calendar a week, written while the entry is unloaded."""

    async def state(expected: str):
        entries = await demo.api(
            "GET", "/api/config/config_entries/entry?domain=autodarts"
        )
        return entries[0]["state"] == expected or None

    await demo.ws("config_entries/disable", entry_id=entry_id, disabled_by="user")
    await wait_for(lambda: state("not_loaded"), "the unloaded entry")
    key = f"autodarts.{entry_id}.journal"
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    journal = {"version": 1, "minor_version": 1, "key": key, "data": week_journal(now)}
    Path(f"/config/.storage/{key}").write_text(json.dumps(journal))
    await demo.ws("config_entries/disable", entry_id=entry_id, disabled_by=None)
    await wait_for(lambda: state("loaded"), "the entry with a week in its calendar")


# The weekly report blueprint of the repository; in German with the message of
# the documentation.
GERMAN_REPORT = {
    "report_title": "Deine Dartwoche",
    "report_message": (
        "{{ darts }} Darts"
        "{{ ' in ' ~ training_minutes ~ ' Minuten' if training_minutes else '' }}"
        "{{ ', 3-Dart-Average ' ~ (average | replace('.', ','))"
        " ~ (' (' ~ ('+' if average_change > 0 else '')"
        " ~ (average_change | replace('.', ',')) ~ ')'"
        " if average_change is not none else '')"
        " if average is not none else '' }}"
        "{{ ', ' ~ scores_180 ~ ' × 180' if scores_180 else '' }}"
        "{{ ', ' ~ streak ~ (' Tag' if streak == 1 else ' Tage') ~ ' in Folge'"
        " if streak else '' }}."
    ),
}


async def weekly_report(demo: Scenario) -> None:
    """An automation from the weekly report blueprint, as a user would create it."""
    inputs = {"board_events": demo.entity("board_events")}
    if os.environ.get("DEMO_LANGUAGE") == "de":
        inputs |= GERMAN_REPORT
    automation = {
        "id": "autodarts_weekly_report",
        "alias": "Weekly darts report",
        "use_blueprint": {"path": "autodarts/weekly_report.yaml", "input": inputs},
    }
    folder = Path("/config/automations")
    folder.mkdir(exist_ok=True)
    # JSON is YAML, too.
    (folder / "weekly_report.yaml").write_text(json.dumps([automation]))
    await demo.api("POST", "/api/services/automation/reload", json={})

    async def loaded():
        states = await demo.api("GET", "/api/states")
        return (
            any(
                state["entity_id"].startswith("automation.") and state["state"] == "on"
                for state in states
            )
            or None
        )

    await wait_for(loaded, "the weekly report automation")


async def people(demo: Scenario) -> None:
    """Persons with pictures, linked to the players of the demo."""
    for name, color, where in PEOPLE:
        form = aiohttp.FormData()
        form.add_field(
            "file",
            avatar(name[0], color),
            filename=f"{name.lower()}.png",
            content_type="image/png",
        )
        async with demo.session.post(
            f"{HA}/api/image/upload", data=form, headers=demo.headers
        ) as response:
            image = await response.json()
        picture = f"/api/image/serve/{image['id']}/512x512"
        person = await demo.ws("person/create", name=name, picture=picture)
        entity = f"person.{name.lower()}"
        # Without device trackers, the demo tells who is home itself.
        await demo.api(
            "POST",
            f"/api/states/{entity}",
            json={
                "state": where,
                "attributes": {
                    "friendly_name": name,
                    "entity_picture": picture,
                    "id": person["id"],
                },
            },
        )
        await demo.api(
            "POST",
            "/api/services/autodarts/link_player",
            json={"player": name, "person": entity},
        )


def gallery() -> None:
    """Highlight photos for the media browser."""
    GALLERY.mkdir(parents=True, exist_ok=True)
    for name, darts in HIGHLIGHTS.items():
        (GALLERY / name).write_bytes(board_photo(darts))


async def throw(demo: Scenario, darts: list[dict]) -> None:
    for count in range(1, len(darts) + 1):
        await demo.board("POST", "/control/state", json={"throws": darts[:count]})
        await asyncio.sleep(0.4)


async def play(demo: Scenario, visits: list[list[dict]]) -> None:
    """Throw each visit and pull the darts, as a player does."""
    for visit in visits:
        await throw(demo, visit)
        await demo.board(
            "POST",
            "/control/state",
            json={"status": "Takeout in progress", "event": "Takeout started"},
        )
        await demo.board(
            "POST",
            "/control/state",
            json={"status": "Throw", "event": "Takeout finished", "throws": []},
        )
        await asyncio.sleep(0.4)


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        demo = Scenario(session)
        await demo.onboard()
        await demo.connect()
        if GENERATION >= 2:
            result = await demo.discovered_setup()
        else:
            result = await demo.local_flow("board-mock", PORT)
        entry_id = result["result"]["entry_id"]
        await demo.registries(entry_id)
        await seed_journal(demo, entry_id)
        await weekly_report(demo)
        # A daily goal the demo darts reach halfway, for the training card.
        await demo.service("number", "set_value", "training_daily_goal", value=120)
        await demo.service("button", "press", "start")
        await demo.expect_states({"detection": "on", "realtime_connected": "on"})
        for session in EARLIER:
            await play(demo, session)
            await demo.service("switch", "turn_off", "training_session")
            await demo.expect_states({"training_session": "off"})
        await demo.service("switch", "turn_on", "training_session")
        await demo.expect_states({"training_session": "on", "training_darts": "0"})
        await play(demo, HISTORY)
        await throw(demo, CURRENT)
        await demo.expect_states({"local_visit_score": "115"})

        await demo.ws(
            "lovelace/dashboards/create",
            url_path=DASHBOARD,
            title="Autodarts",
            icon="mdi:bullseye-arrow",
            show_in_sidebar=True,
            require_admin=False,
            mode="storage",
        )
        await demo.ws("lovelace/config/save", url_path=DASHBOARD, config=dashboard())
        await people(demo)
        gallery()
        # A second dashboard generated entirely by the Autodarts strategy.
        await demo.ws(
            "lovelace/dashboards/create",
            url_path=STRATEGY_DASHBOARD,
            title="Autodarts (automatic)",
            icon="mdi:bullseye",
            show_in_sidebar=True,
            require_admin=False,
            mode="storage",
        )
        await demo.ws(
            "lovelace/config/save",
            url_path=STRATEGY_DASHBOARD,
            config={"strategy": {"type": "custom:autodarts"}},
        )
        await demo.socket.close()


if __name__ == "__main__":
    asyncio.run(main())
