"""One board for everything: the cards, the bot, the dart log, the aim map, the
games and the actions share its rings, numbers and names of beds."""

import re
from pathlib import Path

import pytest

from custom_components.homedarts import (
    aim,
    bot,
    cricket,
    party,
    positions,
    practice,
    scoring,
    services,
    training,
)
from custom_components.homedarts.board import (
    BULL_MM,
    DOUBLE_MM,
    OUTER_BULL_MM,
    RADIUS_MM,
    SECTORS,
    TREBLE_MM,
    aim_point,
    bed_name,
    distance_mm,
    segment_at,
    top_bed,
)
from custom_components.homedarts.scoring import SCORE_BEDS, bounded_count
from custom_components.homedarts.training import hit_key

CARD = (
    Path(__file__).parents[1] / "custom_components/homedarts/frontend/homedarts-card.js"
).read_text(encoding="utf-8")


def _card_rings() -> dict[str, int]:
    block = CARD[
        CARD.index("const R = {") : CARD.index("};", CARD.index("const R = {"))
    ]
    return {name: int(value) for name, value in re.findall(r"(\w+): (\d+)", block)}


def test_the_cards_draw_the_board_of_the_integration():
    rings = _card_rings()
    assert (rings["bull"], rings["outerBull"]) == (BULL_MM, OUTER_BULL_MM)
    assert (rings["trebleIn"], rings["trebleOut"]) == TREBLE_MM
    assert (rings["doubleIn"], rings["doubleOut"]) == DOUBLE_MM
    # Dart positions are scaled to the outer edge of the double ring.
    assert re.search(r"^const NORM = (\d+);$", CARD, re.M)[1] == str(RADIUS_MM)
    numbers = re.search(r"^const NUMBERS = \[([\d, ]+)\];$", CARD, re.M)[1]
    assert tuple(int(number) for number in numbers.split(", ")) == SECTORS


def test_every_module_uses_the_one_board():
    # The bot, the dart log, the aim map, the party games and the actions take
    # the geometry and the names of the beds from the board, not copies of them.
    assert bot.aim_point is positions.aim_point is aim_point
    assert bot.segment_at is aim.segment_at is services.segment_at is segment_at
    assert bot.bed_name is aim.bed_name is services.bed_name is bed_name
    assert scoring.bed_name is training.bed_name is bed_name
    assert bot.top_bed is cricket.top_bed is top_bed
    assert party.distance_mm is practice.distance_mm is distance_mm
    assert aim.SECTORS is SECTORS and party.TREBLE_MM is TREBLE_MM


def test_the_rings_lie_inside_each_other():
    assert 0 < BULL_MM < OUTER_BULL_MM < TREBLE_MM[0] < TREBLE_MM[1]
    assert TREBLE_MM[1] < DOUBLE_MM[0] < DOUBLE_MM[1] == RADIUS_MM
    assert sorted(SECTORS) == list(range(1, 21))


@pytest.mark.parametrize(
    ("number", "multiplier", "name"),
    [
        (20, 1, "S20"),
        (16, 2, "D16"),
        (19, 3, "T19"),
        (25, 1, "25"),
        (25, 2, "BULL"),
        (0, 0, "MISS"),
        (0, 1, "MISS"),
        (5, 0, "MISS"),
    ],
)
def test_every_bed_has_one_name(number, multiplier, name):
    assert bed_name(number, multiplier) == name
    assert hit_key({"number": number, "multiplier": multiplier}) == name


def test_the_beds_of_a_visit_entered_as_its_score_have_the_same_names():
    for bed in SCORE_BEDS:
        assert bed["name"] == bed_name(bed["number"], bed["multiplier"])


def test_a_number_is_aimed_at_where_it_counts_most():
    assert top_bed(20) == "T20" and top_bed(15) == "T15"
    assert top_bed(25) == "BULL"


def test_distances_are_millimetres_from_the_centre():
    assert distance_mm((0.6, 0.8)) == RADIUS_MM
    assert distance_mm((0.0, 0.0)) == 0
    assert distance_mm(None) is None


def test_a_stored_count_is_a_whole_number_within_its_bounds():
    assert bounded_count(3, 1, 5, 0) == 3
    assert bounded_count(1, 1, 5, 0) == 1 and bounded_count(5, 1, 5, 0) == 5
    assert bounded_count(0, 1, 5, 2) == 2 and bounded_count(6, 1, 5, 2) == 2
    # A damaged file can hold anything; a truth value or text is no count.
    assert bounded_count(True, 0, 5, 2) == 2
    assert bounded_count("3", 0, 5, 2) == 2 and bounded_count(3.0, 0, 5, 2) == 2
    assert bounded_count(None, 0, 5, 2) == 2
