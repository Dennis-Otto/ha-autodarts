"""Party games, X01 variants and the bull-off."""

from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.party import (
    HALVE_IT_START,
    KILLER_LIVES,
    BullOff,
    distance_mm,
    make_party,
)
from custom_components.autodarts.practice import MAX_PLAYERS, PracticeGame

from .test_practice import dart, throw


def game_of(kind: str | int, players: int = 1, **names: str) -> PracticeGame:
    game = PracticeGame()
    game.set_players(players)
    for index, name in names.items():
        game.set_name(int(index[1:]) - 1, name)
    game.play(kind)
    return game


def kinds(events: list) -> list[str]:
    return [kind for kind, _ in events]


def missed(number: int) -> dict:
    """A miss next to a number, as the board reports it."""
    return {"number": number, "multiplier": 0, "name": f"M{number}"}


def test_x01_starts_from_101_to_1001():
    for start in (101, 901, 1001):
        assert game_of(start).snapshot()["remaining"] == start
    assert game_of(401).snapshot()["game"] is None


def test_double_in_scores_from_the_first_double():
    game = game_of(301)
    game.double_in = True
    game.new_match()
    game.track([dart("S20"), dart("T20")])
    snapshot = game.snapshot()
    assert snapshot["remaining"] == 301 and snapshot["opened"] is False
    assert snapshot["checkout"] is None
    throw(game, "S20", "T20")
    # The single before the double scores nothing; the double and later darts do.
    throw(game, "S1", "D10", "T20")
    player = game.players[0]
    assert player.remaining == 221 and player.opened is True
    assert (player.first9_darts, player.first9_points) == (5, 80)
    assert game.snapshot()["scores"][0]["opened"] is True


def test_a_bust_takes_the_opening_double_back():
    game = game_of(301)
    game.double_in = True
    game.new_match()
    game.players[0].remaining = 50
    game.track([dart("D20"), dart("T20")])
    # The card shows the double taken back while the bust is on the board.
    assert game.snapshot()["opened"] is False
    assert game.snapshot()["scores"][0]["opened"] is False
    assert kinds(game.finish_visit()) == ["turn_changed"]
    assert game.players[0].remaining == 50 and game.players[0].opened is False


def test_shanghai_wins_at_once_with_single_double_and_treble():
    game = game_of("shanghai", 2, p1="Alex", p2="Sam")
    assert game.snapshot()["target"] == "1" and game.snapshot()["round"] == 1
    throw(game, "S1", "D1", "S5")
    throw(game, "T1")
    snapshot = game.snapshot()
    assert [score["points"] for score in snapshot["scores"]] == [3, 3]
    assert snapshot["target"] == "2" and snapshot["round"] == 2
    events = throw(game, "S2", "T2", "D2")
    assert kinds(events) == ["leg_won", "match_won"]
    won = dict(events)["leg_won"]
    assert (won["game"], won["name"], won["points"], won["darts"]) == (
        "shanghai",
        "Alex",
        15,
        6,
    )
    assert game.snapshot()["winner"] == 1


def test_shanghai_ends_after_seven_rounds_and_a_tie_replays_the_leg():
    game = game_of("shanghai")
    for number in range(1, 7):
        assert throw(game, f"S{number}") == []
    events = throw(game, "D7")
    assert kinds(events) == ["leg_won"]
    assert dict(events)["leg_won"]["points"] == sum(range(1, 7)) + 14
    # The next leg starts again at the 1.
    assert game.snapshot()["target"] == "1"

    tied = game_of("shanghai", 2)
    for _ in range(7):
        throw(tied, "MISS")
        throw(tied, "MISS")
    assert tied.winner is None and tied.starter == 1
    assert tied.snapshot()["player"] == 2 and tied.snapshot()["round"] == 1


def test_shanghai_counts_no_miss_next_to_the_number():
    game = game_of("shanghai", 2)
    game.track([missed(1), missed(1), dart("S1")])
    assert game.snapshot()["points"] == 1
    game.finish_visit()
    game.track([])
    assert game.party.hits == [1, 0] and game.party.points == [1, 0]
    # A miss next to the number completes no Shanghai either.
    game.party.restore({"turns": 2})
    game.track([dart("S2"), dart("D2"), missed(2)])
    assert game.snapshot()["won"] is False and game.snapshot()["darts"] == 3


def test_halve_it_halves_a_round_without_a_hit():
    game = game_of("halve_it")
    assert game.snapshot()["points"] == HALVE_IT_START
    throw(game, "S15", "T15", "MISS")
    assert game.snapshot()["points"] == 100 and game.snapshot()["target"] == "16"
    throw(game, "S5", "S5", "S5")
    assert game.snapshot()["points"] == 50 and game.snapshot()["target"] == "D"
    throw(game, "D10")
    assert game.snapshot()["points"] == 70 and game.snapshot()["target"] == "17"
    # Pulling the darts early after a miss halves as well.
    throw(game, "S5")
    assert game.snapshot()["points"] == 35 and game.snapshot()["target"] == "18"
    throw(game, "T18")
    throw(game, "T5")
    throw(game, "S19")
    throw(game, "S20")
    # The bull round is named by its number: the outer bull and the bullseye count.
    assert game.snapshot()["target"] == "25"
    events = throw(game, "25", "BULL")
    assert kinds(events) == ["leg_won"]
    # 35 + 54 + 15 (any treble) + 19 + 20 + 75 (the bull)
    assert dict(events)["leg_won"]["points"] == 218


def test_killer_needs_two_players():
    game = game_of("killer")
    snapshot = game.snapshot()
    assert snapshot["needs_players"] == 2 and snapshot["target"] is None
    assert throw(game, "D20") == [] and game.party.numbers == [None]


def test_killer_picks_numbers_then_the_killers_take_lives():
    game = game_of("killer", 3, p1="Alex", p2="Sam", p3="Kim")
    assert game.snapshot()["phase"] == "choose"
    throw(game, "S7")
    # Sam hits the 7 as well: taken, so Sam throws again.
    throw(game, "S7")
    assert game.snapshot()["player"] == 2
    throw(game, "S12")
    throw(game, "BULL")
    throw(game, "S3")
    snapshot = game.snapshot()
    assert snapshot["phase"] == "play" and snapshot["player"] == 1
    assert [score["number"] for score in snapshot["scores"]] == [7, 12, 3]
    assert snapshot["target"] == "D7"
    # Alex becomes a killer and hunts the others from the next dart on.
    game.track([dart("D7")])
    assert game.snapshot()["target"] is None
    # ... and takes two of Sam's lives.
    throw(game, "D7", "D12", "D12")
    scores = game.snapshot()["scores"]
    assert scores[0]["killer"] is True and scores[1]["lives"] == KILLER_LIVES - 2
    throw(game, "S1")
    throw(game, "D3")
    # A killer hitting their own double loses a life.
    throw(game, "D12", "D7")
    scores = game.snapshot()["scores"]
    assert scores[1]["lives"] == 0 and scores[0]["lives"] == KILLER_LIVES - 1
    # Sam is out: Kim throws next.
    assert game.snapshot()["player"] == 3
    throw(game, "S1")
    events = throw(game, "D3", "D3", "D3")
    assert kinds(events) == ["leg_won", "match_won"]
    assert dict(events)["leg_won"]["name"] == "Alex"


def test_killer_numbers_need_a_bed_of_the_number():
    game = game_of("killer", 2)
    # A miss next to the 7 picks nothing: throw again.
    game.track([missed(7)])
    game.finish_visit()
    game.track([])
    assert game.party.numbers == [None, None] and game.snapshot()["player"] == 1
    throw(game, "T7")
    assert game.party.numbers == [7, None]


def test_a_killer_out_of_lives_does_nothing_with_the_rest_of_the_visit():
    game = game_of("killer", 3)
    game.party.restore(
        {"numbers": [1, 2, 3], "lives": [1, 3, 3], "killers": [True, False, False]}
    )
    # The own double takes the last life; the next double would make a killer
    # again and the last one would take a life of player 2.
    throw(game, "D1", "D1", "D2")
    assert game.party.lives == [0, 3, 3]
    assert game.party.killers == [False, False, False]
    assert game.snapshot()["player"] == 2


def test_darts_after_the_winning_dart_do_not_count():
    game = game_of("killer", 2)
    game.party.restore({"numbers": [1, 2], "lives": [3, 1], "killers": [True, False]})
    game.track([dart("D2")])
    assert game.snapshot()["darts"] == 1
    game.track([dart("D2"), dart("S5"), dart("S5")])
    snapshot = game.snapshot()
    assert snapshot["won"] and snapshot["darts"] == 1
    events = game.finish_visit()
    assert kinds(events) == []
    assert game.players[0].darts == 1 and game.legs[0]["darts"] == 1


def test_only_killers_take_lives_and_a_killer_can_lose_the_last_one():
    game = game_of("killer", 2, p1="Alex", p2="Sam")
    throw(game, "S7")
    throw(game, "S12")
    # Alex is no killer yet: Sam's double takes no life.
    throw(game, "D12")
    assert game.party.lives == [KILLER_LIVES] * 2
    throw(game, "MISS")
    game.party.killers[0], game.party.lives[0] = True, 1
    # With the last life, Alex hits the own double: Sam is the last one left.
    events = game.track([dart("D7")])
    assert kinds(events) == ["leg_won", "match_won"]
    assert dict(events)["leg_won"]["name"] == "Sam"
    alex = game.snapshot()["scores"][0]
    assert alex["lives"] == 0 and alex["killer"] is False


def test_a_correction_can_take_a_shanghai_back():
    game = game_of("shanghai", 2)
    shanghai = [dart("S1"), dart("D1"), dart("T1")]
    assert kinds(game.track(shanghai)) == ["leg_won", "match_won"]
    # The board corrects the treble to a single: no Shanghai after all.
    assert game.track([dart("S1"), dart("D1"), dart("S1")]) == []
    assert game.snapshot()["winner"] is None
    assert kinds(game.finish_visit()) == ["turn_changed"]
    assert game.snapshot()["player"] == 2 and game.winner is None


def test_killer_turns_skip_players_who_picked_or_are_out():
    killer = make_party("killer", 3)
    killer.restore({"numbers": [7, None, 3]})
    # Whoever still needs a number picks next; a failed pick is thrown again.
    assert killer.next(2) == 1
    assert killer.next(1) == 1
    killer.restore({"numbers": [7, 12, 3], "lives": [0, 2, 0]})
    assert killer.next(1) == 1
    # A stored leg without anybody alive keeps the turn instead of failing.
    killer.restore({"lives": [0, 0, 0]})
    assert killer.next(2) == 2


def test_a_party_game_without_usable_scores_starts_the_leg_fresh():
    game = game_of("killer", 2)
    throw(game, "S5")
    saved = game.stored()
    saved["party"] = "broken"
    restored = PracticeGame()
    restored.restore(saved)
    assert restored.party.kind == "killer"
    assert restored.party.numbers == [None, None]
    assert restored.party.lives == [KILLER_LIVES] * 2


def test_a_restored_bull_off_drops_throws_it_cannot_trust():
    kept = BullOff.restored(
        {
            "order": [2, 0],
            "index": 1,
            "hits": {"2": "25"},
            "distances": {"2": 5},
            "rethrow": True,
        },
        3,
    )
    assert kept.index == 1 and kept.distances == {2: 5.0} and kept.hits == {2: "25"}
    assert kept.thrower == 0 and kept.rethrow
    unmeasured = BullOff.restored(
        {"order": [0, 1], "index": 1, "hits": {"0": "BULL"}, "distances": {"0": None}},
        2,
    )
    assert unmeasured.index == 1 and unmeasured.distances == {0: None}
    for saved in (
        # Up to version 1.5, only the distances were kept: the round starts again.
        {"order": [0, 1, 2], "index": 2, "distances": {"0": 11.0, "1": 0.0}},
        {"order": [0, 1, 2], "index": 2, "hits": "broken", "distances": "broken"},
        # Player 3 has not thrown yet; player 2 threw no bed and no distance.
        {
            "order": [0, 1, 2],
            "index": 2,
            "hits": {"0": "25", "1": 5, "2": "BULL"},
            "distances": {"0": 11.0, "1": True, "x": 1.0},
        },
    ):
        restored = BullOff.restored(saved, 3)
        assert restored.index == 0 and restored.distances == {} and restored.hits == {}
        assert restored.thrower == 0 and not restored.rethrow


def test_a_bull_off_decides_who_starts():
    game = PracticeGame()
    game.bull_off = True
    game.set_players(2)
    game.play(501)
    assert game.snapshot()["bull_off"]["player"] == 1
    assert throw(game, "25") == [
        (
            "turn_changed",
            {
                "game": 501,
                "player": 2,
                "name": None,
                "players": 2,
                "remaining": None,
                "checkout": None,
                "bull_off": True,
            },
        )
    ]
    game.track([dart("BULL")])
    throws = game.snapshot()["bull_off"]["throws"]
    assert throws == [
        {"player": 1, "name": None, "distance": None, "hit": "25"},
        {"player": 2, "name": None, "distance": None, "hit": "BULL"},
    ]
    events = throw(game, "BULL")
    assert events[0] == (
        "bull_off_won",
        {
            "game": 501,
            "player": 2,
            "name": None,
            "players": 2,
            "distance": None,
            "hit": "BULL",
        },
    )
    assert events[1][1]["player"] == 2 and events[1][1]["remaining"] == 501
    snapshot = game.snapshot()
    assert snapshot["bull_off"] is None and snapshot["player"] == 2
    assert [score["remaining"] for score in snapshot["scores"]] == [501, 501]


def test_the_same_bull_bed_throws_again_in_reverse_order():
    bull_off = BullOff([0, 1, 2])
    assert bull_off.book(dart("BULL"), (0.01, 0.0)) is None
    assert bull_off.book(dart("BULL"), (0.03, 0.0)) is None
    assert bull_off.book(dart("S20"), None) is None
    # Only the two in the bullseye throw again, the last one first; the
    # official rules do not measure inside the bed.
    assert bull_off.order == [1, 0] and bull_off.index == 0 and bull_off.rethrow
    assert bull_off.book(dart("25"), (0.05, 0.0)) is None
    assert bull_off.book(dart("BULL"), None) == 0
    assert distance_mm((0.03, 0.04)) == 8.5 and distance_mm(None) is None


def test_beds_decide_before_distances_and_unmeasured_darts_throw_again():
    bull_off = BullOff([0, 1])
    bull_off.book(dart("S20"), (0.1, 0.0))
    # Outside the bull, the measured distance decides: 17 against 34 mm.
    assert bull_off.book(dart("S1"), (0.2, 0.0)) == 0
    bull_off = BullOff([0, 1])
    bull_off.book(dart("S20"), (0.1, 0.0))
    assert bull_off.book(dart("S1"), None) is None and bull_off.order == [1, 0]
    # The outer bull beats every other bed, however close.
    bull_off = BullOff([0, 1])
    bull_off.book(dart("25"), None)
    assert bull_off.book(dart("S20"), (0.1, 0.0)) == 0


def test_by_distance_the_closer_dart_in_the_same_bull_bed_wins():
    bull_off = BullOff([0, 1])
    bull_off.book(dart("BULL"), (0.03, 0.0), True)
    assert bull_off.book(dart("BULL"), (0.0, -0.02), True) == 1
    # A dart without a position never beats a measured one: both throw again.
    bull_off = BullOff([0, 1])
    bull_off.book(dart("BULL"), (0.03, 0.0), True)
    assert bull_off.book(dart("BULL"), None, True) is None
    assert bull_off.order == [1, 0]
    # Equally close throws again, too.
    bull_off = BullOff([0, 1])
    bull_off.book(dart("25"), (0.05, 0.0), True)
    assert bull_off.book(dart("25"), (0.0, 0.05), True) is None


def test_the_bull_off_rule_and_a_rethrow_show_in_the_snapshot():
    game = PracticeGame()
    game.bull_off = True
    game.set_players(2)
    game.play(501)
    throw(game, "BULL")
    game.track([dart("BULL")], [(0.02, 0.0)])
    snapshot = game.snapshot()["bull_off"]
    assert snapshot["rethrow"] is False and snapshot["by_distance"] is False
    assert snapshot["throws"][1] == {
        "player": 2,
        "name": None,
        "distance": 3.4,
        "hit": "BULL",
    }
    assert kinds(game.finish_visit()) == ["turn_changed"]
    game.track([])
    snapshot = game.snapshot()["bull_off"]
    assert snapshot["rethrow"] and snapshot["player"] == 2
    assert [item["player"] for item in snapshot["throws"]] == [2, 1]
    assert snapshot["throws"][0]["hit"] is None
    game.bull_off_distance = True
    throw(game, "BULL")
    game.track([dart("BULL")], [(0.0, 0.01)])
    events = game.finish_visit()
    # Player 2 threw without a position: the darts cannot be compared, so again.
    assert kinds(events) == ["turn_changed"] and game.bulling.order == [0, 1]
    game.track([])
    game.track([dart("BULL")], [(0.02, 0.0)])
    game.finish_visit()
    game.track([])
    game.track([dart("BULL")], [(0.0, 0.01)])
    events = game.finish_visit()
    assert events[0] == (
        "bull_off_won",
        {
            "game": 501,
            "player": 2,
            "name": None,
            "players": 2,
            "distance": 1.7,
            "hit": "BULL",
        },
    )
    assert game.starter == game.set_starter == 1


def test_party_games_and_the_bull_off_survive_a_restart():
    game = game_of("killer", 2)
    game.bull_off = True
    game.new_match()
    throw(game, "25")
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.stored() == game.stored()
    assert restored.bulling is not None and restored.bulling.distances == {0: None}
    assert restored.bulling.hits == {0: "25"}
    throw(restored, "BULL")
    throw(restored, "S5")
    throw(restored, "S9")
    saved = restored.stored()
    again = PracticeGame()
    again.restore(saved)
    # Player 2 won the bull-off, so player 2 picked first.
    assert again.party.numbers == [9, 5] and again.snapshot()["phase"] == "play"
    saved["party"] = {"numbers": [5, 5], "lives": [9, 1], "killers": "x"}
    saved["bulling"] = {"order": [0, 0]}
    again.restore(saved)
    assert again.party.numbers == [None, None] and again.bulling is None
    assert again.party.lives == [KILLER_LIVES] * 2


BEDS = [
    "S1",
    "D1",
    "T1",
    "S2",
    "D2",
    "T2",
    "S3",
    "D7",
    "D12",
    "S15",
    "T15",
    "BULL",
    "25",
    "MISS",
]


@given(
    st.sampled_from(["shanghai", "halve_it", "killer"]),
    st.integers(1, MAX_PLAYERS),
    st.booleans(),
    st.lists(st.lists(st.sampled_from(BEDS), min_size=1, max_size=3), max_size=60),
)
def test_any_party_game_keeps_its_scores_consistent(kind, players, bull_off, visits):
    game = game_of(kind, players)
    game.bull_off = bull_off
    game.new_match()
    for visit in visits:
        throw(game, *visit)
        snapshot = game.snapshot()
        assert 1 <= snapshot["player"] <= players
        for score in snapshot["scores"]:
            assert score["points"] >= 0
            if kind == "killer":
                assert 0 <= score["lives"] <= KILLER_LIVES
        if (
            kind == "killer"
            and snapshot["phase"] == "play"
            and snapshot["winner"] is None
        ):
            # Nobody who is out ever throws.
            assert snapshot["scores"][snapshot["player"] - 1]["lives"] > 0
