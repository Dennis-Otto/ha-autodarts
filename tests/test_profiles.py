"""Player profiles, the match history and head-to-head records."""

from custom_components.autodarts.practice import PracticeGame
from custom_components.autodarts.profiles import MATCH_HISTORY, Profiles

from .local_helpers import throw
from .test_teams_and_handicap import teams


def named(game: int | str, *names: str, legs: int = 1) -> PracticeGame:
    practice = PracticeGame()
    practice.set_players(len(names))
    for index, name in enumerate(names):
        practice.set_name(index, name)
    practice.set_format(legs=legs)
    practice.play(game)
    return practice


def win_leg(practice: PracticeGame) -> None:
    """The player at the board checks out 40 with a double 20."""
    practice.players[practice.current].remaining = 40
    throw(practice, "D20")


def by_name(practice: PracticeGame) -> dict[str, dict]:
    return {
        player["name"]: player for player in practice.profiles.snapshot()["players"]
    }


def test_a_match_fills_the_profiles_the_history_and_head_to_head():
    practice = named(501, "Alex", "Lea", legs=2)
    throw(practice, "T20", "T20", "T20")
    win_leg(practice)  # Lea wins the first leg.
    win_leg(practice)  # Lea starts the second leg... and wins it too.
    players = by_name(practice)
    assert practice.winner == 1
    assert (players["Lea"]["legs_won"], players["Lea"]["matches_won"]) == (2, 1)
    assert (players["Alex"]["legs_played"], players["Alex"]["matches_played"]) == (2, 1)
    assert (
        players["Alex"]["highest_visit"] == 180 and players["Alex"]["average"] == 180.0
    )
    assert players["Lea"]["fewest_darts"] == {"501": 1}
    assert players["Lea"]["highest_checkout"] == 40
    assert players["Lea"]["checkout_rate"] == 100.0
    snapshot = practice.profiles.snapshot()
    assert snapshot["head_to_head"] == [{"players": ["Alex", "Lea"], "wins": [0, 1]}]
    match = snapshot["matches"][0]
    assert (match["game"], match["winner"], match["legs_to_win"]) == (501, 2, 2)
    assert [(entry["name"], entry["sets"]) for entry in match["players"]] == [
        ("Alex", 0),
        ("Lea", 1),
    ]


def test_names_ignore_case_and_unnamed_players_have_no_profile():
    practice = named(301, "Dennis", "")
    win_leg(practice)
    assert list(by_name(practice)) == ["Dennis"]
    again = named(301, "  dennis ", "Lea")
    again.profiles = practice.profiles
    win_leg(again)
    players = by_name(again)
    assert players["Dennis"]["matches_won"] == 2 and "Lea" in players
    # A match against an unnamed player has no head-to-head record.
    assert again.profiles.snapshot()["head_to_head"] == [
        {"players": ["Dennis", "Lea"], "wins": [1, 0]}
    ]
    assert practice.profiles.snapshot()["matches"][1]["players"][1]["name"] is None


def test_cricket_and_party_legs_count_and_keep_their_numbers():
    practice = named("cricket", "Alex", "Sam")
    practice.players[0].marks = [3, 3, 3, 3, 3, 3, 2]
    practice.players[0].marks_hit = 20
    practice.players[0].darts = 21
    throw(practice, "BULL")
    alex = by_name(practice)["Alex"]
    assert alex["mpr"] == round(22 * 3 / 22, 2) and alex["best_mpr"] == 3.0
    # The match counts only the bullseye thrown in it: two marks with one dart.
    assert practice.profiles.snapshot()["matches"][0]["players"][0]["mpr"] == 6.0
    shanghai = named("shanghai", "Kim")
    for number in range(1, 8):
        throw(shanghai, f"S{number}")
    kim = by_name(shanghai)["Kim"]
    assert (kim["legs_played"], kim["legs_won"], kim["average"]) == (1, 1, None)


def test_profiles_can_be_deleted_and_survive_a_restart():
    practice = named(501, "Alex", "Lea")
    win_leg(practice)
    assert practice.profiles.delete("LEA") is True
    assert practice.profiles.delete("Nobody") is False
    assert list(by_name(practice)) == ["Alex"]
    assert practice.profiles.snapshot()["head_to_head"] == []
    # The history keeps the match with both names.
    assert len(practice.profiles.matches) == 1
    restored = PracticeGame()
    restored.restore(practice.stored())
    assert restored.profiles.stored() == practice.profiles.stored()


def test_invalid_stored_profiles_are_dropped():
    profiles = Profiles()
    profiles.restore(
        {
            "players": [
                {"name": "Alex", "legs_played": 5, "legs_won": -1, "best_mpr": "x"},
                {"name": " "},
                {"legs_played": 3},
                "x",
                {"name": "Sam", "fewest_darts": {"501": 18, "x": 3, "301": 0}},
            ],
            "matches": [{"ended": "2026-09-26T20:00:00", "players": []}, {"ended": 1}],
            "head_to_head": {"alex\x00sam": [2, 1], "bad": [1, 1], "a\x00b": [1]},
        }
    )
    snapshot = profiles.snapshot()
    players = {player["name"]: player for player in snapshot["players"]}
    assert players["Alex"]["legs_played"] == 5 and players["Alex"]["legs_won"] == 0
    assert players["Alex"]["best_mpr"] is None
    assert players["Sam"]["fewest_darts"] == {"501": 18}
    assert len(snapshot["matches"]) == 1
    assert snapshot["head_to_head"] == [{"players": ["Alex", "Sam"], "wins": [2, 1]}]
    profiles.restore(None)
    assert profiles.snapshot()["head_to_head"]


def test_the_history_keeps_the_last_matches():
    profiles = Profiles()
    for index in range(MATCH_HISTORY + 5):
        profiles.match(501, [{"name": "A"}, {"name": "B"}], index % 2, 1, 1)
    assert len(profiles.matches) == MATCH_HISTORY
    assert profiles.snapshot()["head_to_head"][0]["wins"] == [13, 12]


def test_in_a_team_the_checkout_counts_for_the_player_who_threw_it():
    game = teams()
    for player in game.players:
        player.remaining = 40
    throw(game, "MISS", "D20")
    players = by_name(game)
    assert players["Alex"]["legs_won"] == players["Kim"]["legs_won"] == 1
    assert (players["Alex"]["checkout_rate"], players["Alex"]["highest_checkout"]) == (
        50.0,
        40,
    )
    # Kim threw no dart at a double and checked nothing out.
    assert game.profiles.players["kim"].checkouts == 0
    assert (players["Kim"]["checkout_rate"], players["Kim"]["highest_checkout"]) == (
        None,
        None,
    )


def test_a_team_cricket_leg_sets_no_best_marks_per_round():
    game = teams("cricket")
    for player in game.players[0::2]:
        player.marks = [3, 3, 3, 3, 3, 3, 2]
    throw(game, "BULL")
    assert game.legs[0]["team"] == 1
    assert all(profile.best_mpr == 0 for profile in game.profiles.players.values())
    assert by_name(game)["Alex"]["legs_won"] == 1


def test_names_never_keep_template_characters():
    """Linking and restoring clean a name as the games do."""
    profiles = Profiles()
    assert profiles.link("{{ Alex }}", "person.alex")
    assert [profile.name for profile in profiles.players.values()] == ["Alex"]
    assert not profiles.link("{%#}", "person.sam")
    restored = Profiles()
    restored.restore({"players": [{"name": "Sam{#}"}, {"name": "{}"}]})
    assert [profile.name for profile in restored.players.values()] == ["Sam"]
