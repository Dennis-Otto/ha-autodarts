"""Statistics count what was booked, once: undone visits, corrected wins, the
bot, abandoned matches and deleted players."""

from homeassistant.util import dt as dt_util

from custom_components.autodarts.progress import WEEK

from .local_helpers import MISS, S20, T20, board, record, setup_local
from .test_bot_match import against_the_bot, pass_time
from .test_play_comfort import act, kinds, receive, start

S1 = ("S1", 1, 1)
D10 = ("D10", 10, 2)
D20 = ("D20", 20, 2)


def week(coordinator, name: str) -> list[int]:
    return coordinator.progress.players[name].week(dt_util.now().date())


async def test_an_undone_visit_counts_once_booked_again(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "501", players=["Alex", "Lea"])
    # Alex's 180 reads as 140, and the darts are pulled before anybody notices.
    receive(coordinator, board(T20), board(T20, S20), board(T20, S20, T20), board())
    await hass.async_block_till_done()
    await act(hass, "undo_visit")
    await act(hass, "correct_dart", dart=2, segment="T20")
    await act(hass, "next_player")
    alex = coordinator.progress.players["alex"]
    assert alex.counters["darts"] == 3 and sum(alex.hits.values()) == 3
    assert [alex.counters[key] for key in ("tons", "ton_forties", "maximums")] == [
        1,
        1,
        1,
    ]
    assert week(coordinator, "alex")[WEEK["darts"]] == 3
    counts = coordinator.reports.report.counts
    assert [counts[key] for key in ("darts", "visits", "visit_darts", "points")] == [
        3,
        1,
        3,
        180,
    ]
    assert counts["scores_180"] == 1


async def test_a_misread_180_leaves_no_maximum_once_undone(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "501", players=["Alex", "Lea"])
    receive(coordinator, board(T20), board(T20, T20), board(T20, T20, T20), board())
    await hass.async_block_till_done()
    alex = coordinator.progress.players["alex"]
    assert alex.counters["maximums"] == 1 and "maximum" in alex.badges
    await act(hass, "undo_visit")
    await act(hass, "correct_dart", dart=2, segment="S20")
    await act(hass, "next_player")
    alex = coordinator.progress.players["alex"]
    assert alex.counters["maximums"] == 0 and "maximum" not in alex.badges
    assert coordinator.reports.report.counts["scores_180"] == 0
    assert coordinator.reports.report.highest_visit == 140


async def test_an_undone_first_visit_forgets_the_new_player(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "501", players=["Kim"])
    receive(coordinator, board(T20), board())
    await hass.async_block_till_done()
    assert "kim" in coordinator.progress.players
    await act(hass, "undo_visit")
    assert "kim" not in coordinator.progress.players


async def test_an_undone_winning_visit_leaves_one_leg_and_one_match(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    reports = coordinator.reports
    await start(hass, "101", players=["Alex", "Sam"], legs=1)
    receive(coordinator, board(T20), board(T20, S1), board(T20, S1, D20), board())
    await hass.async_block_till_done()
    assert len(reports.journal.matches) == 1
    await act(hass, "undo_visit")
    assert reports.journal.matches == []
    assert [reports.report.counts[key] for key in ("legs", "matches")] == [0, 0]
    await act(hass, "next_player")
    assert len(reports.journal.matches) == 1
    assert len(coordinator.practice.profiles.matches) == 1
    counts = reports.report.counts
    assert [
        counts[key] for key in ("legs", "matches", "darts_at_double", "checkouts")
    ] == [1, 1, 1, 1]
    alex = week(coordinator, "alex")
    assert [
        alex[WEEK[key]]
        for key in ("x01_darts", "x01_points", "legs", "legs_won", "checkouts")
    ] == [3, 101, 1, 1, 1]


async def test_a_week_that_ended_before_the_undo_stays_reported(
    hass, aioclient_mock, freezer
):
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-10-04 23:59:00+02:00")
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "501", players=["Alex", "Lea"])
    receive(coordinator, board(T20), board())
    await hass.async_block_till_done()
    await pass_time(hass, freezer, 120)
    assert coordinator.reports.report.last["visits"] == 1
    await act(hass, "undo_visit")
    await act(hass, "next_player")
    # The visit counts for the new week, too, as it was booked again.
    assert coordinator.reports.report.counts["visits"] == 1
    assert coordinator.reports.report.last["visits"] == 1


async def test_records_and_the_report_count_the_booked_leg_only(hass, aioclient_mock):
    """A win announced with a dart can be corrected away before it is booked."""
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "101")
    coordinator.practice.players[0].remaining = 40
    events = record(hass, coordinator)
    receive(coordinator, board(D20))
    # The board reads the dart again, as a single 20: no checkout.
    receive(coordinator, board(S20), board(S20, D10), board())
    await hass.async_block_till_done()
    assert kinds(events).count("leg_won") == 2
    assert "personal_best" not in kinds(events)
    records = coordinator.records.bests
    assert records["fewest_darts_101"]["value"] == 2
    assert records["highest_checkout"]["value"] == 40
    assert coordinator.reports.report.counts["legs"] == 1


async def test_the_bot_counts_for_nobody(hass, aioclient_mock, freezer):
    entry, coordinator = await against_the_bot(hass, aioclient_mock, game="101")
    events = record(hass, coordinator)
    for _ in range(10):
        receive(coordinator, board(MISS), board())
        await hass.async_block_till_done()
        for _ in range(5):
            await pass_time(hass, freezer, 1)
        if coordinator.practice.legs_total:
            break
    assert coordinator.practice.legs[0].get("bot") is True
    # Its leg is played, but sets no record and is nobody's progress.
    assert coordinator.reports.report.counts["legs"] == 1
    assert not {"fewest_darts_101", "highest_checkout"} & set(coordinator.records.bests)
    assert set(coordinator.progress.players) == {"alex"}
    # The bot's darts have positions, Alex's none: the session has no darts.
    assert len(coordinator.progress.session) == 0
    unlocked = [details for kind, details in events if kind == "achievement_unlocked"]
    assert all(details["name"] == "Alex" for details in unlocked)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_an_abandoned_match_does_not_start_the_next_one(
    hass, aioclient_mock, freezer
):
    freezer.move_to("2026-09-20 18:00:00+00:00")
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "101", players=["Alex", "Sam"], legs=1)
    receive(coordinator, board(T20), board())
    await hass.async_block_till_done()
    # A week later, the same game starts anew and is played to the end.
    freezer.move_to("2026-09-27 20:00:00+00:00")
    await start(hass, "101", players=["Alex", "Sam"], legs=1)
    receive(coordinator, board(T20), board(T20, S1), board(T20, S1, D20), board())
    await hass.async_block_till_done()
    (match,) = coordinator.reports.journal.matches
    assert match["started"] == "2026-09-27T20:00:00+00:00"


async def test_a_deleted_player_leaves_the_weekly_report(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "101", players=["Alex"])
    # The first checkout sets the record quietly, a higher one beats it.
    for checkout, dart in ((32, ("D16", 16, 2)), (40, D20)):
        coordinator.practice.players[0].remaining = checkout
        receive(coordinator, board(dart), board())
    await hass.async_block_till_done()
    names = [best["name"] for best in coordinator.reports.report.bests]
    assert "Alex" in names
    await act(hass, "delete_player", name="alex")
    names = [best["name"] for best in coordinator.reports.report.bests]
    assert "Alex" not in names and len(names) == 2


async def test_the_bull_off_darts_are_training_darts(hass, aioclient_mock):
    """Every dart thrown counts for the training session, also in a bull-off:
    only the game decides what a dart scores."""
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start(hass, "501", players=["Alex", "Sam"], bull_off=True)
    receive(coordinator, board(("Bull", 25, 2)), board(), board(T20), board())
    await hass.async_block_till_done()
    assert coordinator.practice.bulling is None
    training = coordinator.training.snapshot()
    assert (training["darts"], training["visits"], training["bulls"]) == (2, 2, 1)
    assert coordinator.quality.snapshot()["darts"] == 2
