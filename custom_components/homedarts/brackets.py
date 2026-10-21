"""The draws of a tournament: the round robin, the groups, and the brackets of a
knockout and of a double elimination, as matches in their order of play.

A bracket is a list of matches whose players come from the seeds of the draw or
from earlier matches: the winner of a match goes on to a later one, and in a
double elimination the loser too, into the losers' bracket. A place that no
player can reach is a bye for the other player of its match, who goes on without
playing; a match that neither player can reach is left out.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

# Knockout rounds counted back from the final; 32 players need five.
KNOCKOUT_STAGES = ("final", "semi_final", "quarter_final", "round_of_16", "round_of_32")
THIRD_PLACE = "third_place"
WINNERS_FINAL = "winners_final"
LOSERS_FINAL = "losers_final"
GRAND_FINAL = "grand_final"
# The second grand final, when the winner of the losers' bracket wins the first.
GRAND_FINAL_RESET = "grand_final_reset"
# The most places of a bracket: 32 players.
BRACKET_PLACES = 32
# The rounds of a double elimination of 32 players: five of the winners' bracket
# and eight of the losers' bracket, the last of each its final.
WINNERS_ROUNDS = BRACKET_PLACES.bit_length() - 1
LOSERS_ROUNDS = 2 * WINNERS_ROUNDS - 2
# The names of the groups.
GROUP_NAMES = "ABCDEFGH"

# Where a side of a planned match gets its player: ("seed", seed) of the draw, or
# ("winner", match) or ("loser", match) of an earlier planned match.
Source = tuple[str, int]


def _pair() -> list[int]:
    return [0, 0]


def _sides() -> list[int | None]:
    return [None, None]


@dataclass
class Match:
    """A match between two players, given by their place in the draw."""

    round: int
    stage: str
    # The place of a knockout match in its round, for the bracket.
    slot: int = 0
    # A player is None until an earlier match decides them, and for a bye.
    players: list[int | None] = field(default_factory=_sides)
    bye: bool = False
    winner: int | None = None
    # Per player: the legs of the whole match and the sets, and the points of
    # X01 or the marks of Cricket with the darts they took, for the averages.
    legs: list[int] = field(default_factory=_pair)
    sets: list[int] = field(default_factory=_pair)
    points: list[int] = field(default_factory=_pair)
    marks: list[int] = field(default_factory=_pair)
    darts: list[int] = field(default_factory=_pair)
    ended: str | None = None
    # The group of a match of the group stage, from 0.
    group: int | None = None
    # When a board began the match, and in a tournament on several boards the
    # board, from 0, that plays or played it.
    started: str | None = None
    board: int | None = None
    # Where the winner and the loser go on: a later match and its side. Every draw
    # makes them anew, so they are not stored.
    winner_to: tuple[int, int] | None = field(default=None, compare=False, repr=False)
    loser_to: tuple[int, int] | None = field(default=None, compare=False, repr=False)
    # The seeds of the draw that play this match of a first round, per side.
    seeds: list[int | None] = field(default_factory=_sides, compare=False, repr=False)

    @property
    def ready(self) -> bool:
        """Both players are known and the match is still to be played."""
        return not self.bye and self.winner is None and None not in self.players

    @property
    def played(self) -> bool:
        return not self.bye and self.winner is not None

    @property
    def loser(self) -> int | None:
        if not self.played:
            return None
        return self.players[1] if self.players[0] == self.winner else self.players[0]


# The fields of a match that every draw makes anew.
ROUTES = ("winner_to", "loser_to", "seeds")


def round_robin(count: int) -> list[Match]:
    """Everyone against everyone, in rounds of the circle method.

    With an odd number of players, one of them has a bye in every round. The
    player with fewer matches as the first to throw throws first; the players
    of a round's last match open the next round only when nobody else can.
    """
    seats: list[int | None] = [*range(count), *([None] if count % 2 else [])]
    size = len(seats)
    first = [0] * count
    last: set[int] = set()
    matches: list[Match] = []
    for number in range(1, size):
        pairs: list[tuple[int, int]] = []
        for index in range(size // 2):
            one, two = seats[index], seats[size - 1 - index]
            if one is None or two is None:
                continue
            if first[two] < first[one] or (
                first[two] == first[one] and (number + index) % 2 == 0
            ):
                one, two = two, one
            first[one] += 1
            pairs.append((one, two))
        pairs.sort(key=lambda pair: bool(last & set(pair)))
        matches.extend(
            Match(round=number, stage=f"round_{number}", players=[one, two])
            for one, two in pairs
        )
        last = set(pairs[-1])
        seats = [seats[0], seats[-1], *seats[1:-1]]
    return matches


def snake(count: int, groups: int) -> list[list[int]]:
    """The players of every group, drawn like a snake: the first seed into the
    first group, the next ones into the next groups and back from the last, so
    that every group gets one of the top seeds and the groups differ by one
    player at most."""
    members: list[list[int]] = [[] for _ in range(groups)]
    for seed in range(count):
        row, place = divmod(seed, groups)
        members[place if row % 2 == 0 else groups - 1 - place].append(seed)
    return members


def group_stage(groups: list[list[int]]) -> list[Match]:
    """A round robin in every group, played round by round: the first round of
    every group, then the second one, so that a player rests between matches."""
    schedules = [round_robin(len(members)) for members in groups]
    rounds = max(match.round for schedule in schedules for match in schedule)
    return [
        Match(
            round=number,
            stage=match.stage,
            group=group,
            players=[members[player] for player in match.players if player is not None],
        )
        for number in range(1, rounds + 1)
        for group, (members, schedule) in enumerate(zip(groups, schedules, strict=True))
        for match in schedule
        if match.round == number
    ]


def places(size: int) -> list[int]:
    """The seed at every place of a bracket, as professional draws place them:
    seed 1 meets the last seed first, seeds 1 and 2 meet in the final at the
    earliest, and seeds 1 to 4 not before the semi-finals."""
    seats = [0]
    while len(seats) < size:
        seats = [seat for top in seats for seat in (top, 2 * len(seats) - 1 - top)]
    return seats


def bracket_size(count: int) -> int:
    """The places of a bracket for this many players: the next power of two."""
    return 1 << (count - 1).bit_length()


class _Plan:
    """The matches of a bracket in their order of play, with the source of
    each side, before the number of players decides which can be played."""

    def __init__(self) -> None:
        self.matches: list[Match] = []
        self.sources: list[tuple[Source, Source]] = []

    def add(self, number: int, stage: str, slot: int, one: Source, two: Source) -> int:
        self.matches.append(Match(round=number, stage=stage, slot=slot))
        self.sources.append((one, two))
        return len(self.matches) - 1

    def first_round(self, size: int, stage: str) -> list[int]:
        seeds = places(size)
        return [
            self.add(
                1, stage, slot, ("seed", seeds[2 * slot]), ("seed", seeds[2 * slot + 1])
            )
            for slot in range(size // 2)
        ]

    def winners(self, number: int, stage: str, earlier: list[int]) -> list[int]:
        """A round of the winners of the matches before, two by two."""
        return [
            self.add(
                number,
                stage,
                slot,
                ("winner", earlier[2 * slot]),
                ("winner", earlier[2 * slot + 1]),
            )
            for slot in range(len(earlier) // 2)
        ]

    def build(self, count: int) -> list[Match]:
        """The matches for this many seeds, with where their players go on.

        A side whose source is a seed beyond the players, the loser of a bye or
        the winner of a match left out stays empty. A match with one empty side
        is a bye, its player on the first side; one with two is left out.
        """
        reach: list[tuple[bool, bool]] = []
        for one, two in self.sources:
            reach.append(
                (self._reaches(one, count, reach), self._reaches(two, count, reach))
            )
        kept: dict[int, int] = {}
        matches: list[Match] = []
        for number, match in enumerate(self.matches):
            sides = list(zip(self.sources[number], reach[number], strict=True))
            if not any(reached for _, reached in sides):
                continue
            if not sides[0][1]:
                sides.reverse()
            match.bye = not all(reached for _, reached in sides)
            kept[number] = len(matches)
            for side, ((kind, value), reached) in enumerate(sides):
                if not reached:
                    continue
                if kind == "seed":
                    match.seeds[side] = value
                elif kind == "winner":
                    matches[kept[value]].winner_to = (len(matches), side)
                else:
                    matches[kept[value]].loser_to = (len(matches), side)
            matches.append(match)
        return matches

    @staticmethod
    def _reaches(source: Source, count: int, reach: list[tuple[bool, bool]]) -> bool:
        """Whether a player can ever come to a side from this source."""
        kind, value = source
        if kind == "seed":
            return value < count
        # A bye has a winner, but only a match played has a loser.
        return any(reach[value]) if kind == "winner" else all(reach[value])


def enter(matches: list[Match], qualifiers: Iterable[int]) -> list[int]:
    """The players of the seeds into the first round; the matches that got one."""
    players = list(qualifiers)
    entered = []
    for index, match in enumerate(matches):
        if match.seeds != [None, None]:
            match.players = [
                None if seed is None else players[seed] for seed in match.seeds
            ]
            entered.append(index)
    return entered


def knockout_plan(count: int, third_place: bool) -> list[Match]:
    """A bracket for the next power of two, with the seeds of its first round;
    the top seeds get the byes. With third place, the losers of the semi-finals
    play for it before the final."""
    size = bracket_size(count)
    rounds = size.bit_length() - 1
    plan = _Plan()
    earlier = plan.first_round(size, KNOCKOUT_STAGES[rounds - 1])
    for number in range(2, rounds + 1):
        if number == rounds and third_place:
            plan.add(
                number, THIRD_PLACE, 1, ("loser", earlier[0]), ("loser", earlier[1])
            )
        earlier = plan.winners(number, KNOCKOUT_STAGES[rounds - number], earlier)
    return plan.build(count)


def knockout(count: int, third_place: bool) -> list[Match]:
    """A knockout bracket with the players in its first round."""
    matches = knockout_plan(count, third_place)
    enter(matches, range(count))
    return matches


def winners_stage(number: int, rounds: int) -> str:
    return WINNERS_FINAL if number == rounds else f"winners_round_{number}"


def losers_stage(number: int, rounds: int) -> str:
    return LOSERS_FINAL if number == 2 * rounds - 2 else f"losers_round_{number}"


def double_knockout(count: int) -> list[Match]:
    """A double elimination: nobody is out before losing two matches.

    The winners' bracket is a knockout. Its losers drop into the losers'
    bracket, whose rounds take turns: the winners of the round before among
    themselves, then against the players who just dropped from the winners'
    bracket, crossed every other round so that two players meet again as late
    as they can. The winner of each bracket meets in the grand final. If the
    winner of the losers' bracket wins it, both have lost once, and a second
    grand final decides; it waits as a bye until then.
    """
    size = bracket_size(count)
    rounds = size.bit_length() - 1
    plan = _Plan()
    winners = plan.first_round(size, winners_stage(1, rounds))
    losers = [
        plan.add(
            1,
            losers_stage(1, rounds),
            slot,
            ("loser", winners[2 * slot]),
            ("loser", winners[2 * slot + 1]),
        )
        for slot in range(len(winners) // 2)
    ]
    for number in range(2, rounds + 1):
        winners = plan.winners(number, winners_stage(number, rounds), winners)
        stage = 2 * number - 2
        crossed = number % 2 == 0
        dropped: dict[int, int] = {}
        # Who dropped first in a crossed round plays first, after a rest.
        for slot in reversed(range(len(winners))) if crossed else range(len(winners)):
            dropped[slot] = plan.add(
                stage,
                losers_stage(stage, rounds),
                slot,
                ("winner", losers[slot]),
                ("loser", winners[len(winners) - 1 - slot if crossed else slot]),
            )
        losers = [dropped[slot] for slot in range(len(winners))]
        if number < rounds:
            losers = plan.winners(stage + 1, losers_stage(stage + 1, rounds), losers)
    final = plan.add(
        rounds + 1, GRAND_FINAL, 0, ("winner", winners[0]), ("winner", losers[0])
    )
    plan.add(rounds + 1, GRAND_FINAL_RESET, 0, ("winner", final), ("loser", final))
    matches = plan.build(count)
    matches[-1].bye = True
    enter(matches, range(count))
    return matches


# For each number of groups and of players going on from each group, in which
# order the groups fill the seeds of the second place, of the third and of the
# fourth (see group_seeds). Worked out once, by trying every order of the groups,
# which takes too long for the event loop of a small Home Assistant host; the
# tests work the table out anew. With one player going on, the group winners are
# all the seeds.
GROUP_ORDERS: dict[tuple[int, int], tuple[tuple[int, ...], ...]] = {
    (2, 2): ((0, 1),),
    (2, 3): ((0, 1), (0, 1)),
    (2, 4): ((0, 1), (0, 1), (0, 1)),
    (3, 2): ((1, 2, 0),),
    (3, 3): ((1, 2, 0), (0, 1, 2)),
    (3, 4): ((1, 2, 0), (0, 1, 2), (2, 1, 0)),
    (4, 2): ((1, 0, 3, 2),),
    (4, 3): ((1, 0, 3, 2), (1, 0, 3, 2)),
    (4, 4): ((1, 0, 3, 2), (1, 0, 3, 2), (0, 1, 2, 3)),
    (5, 2): ((0, 3, 1, 2, 4),),
    (5, 3): ((0, 3, 1, 2, 4), (3, 0, 1, 4, 2)),
    (5, 4): ((0, 3, 1, 2, 4), (3, 0, 1, 4, 2), (3, 4, 0, 1, 2)),
    (6, 2): ((0, 1, 2, 3, 4, 5),),
    (6, 3): ((0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5)),
    (6, 4): ((0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5)),
    (7, 2): ((1, 2, 0, 3, 5, 6, 4),),
    (7, 3): ((1, 2, 0, 3, 5, 6, 4), (2, 3, 4, 5, 6, 0, 1)),
    (8, 2): ((1, 0, 3, 2, 5, 4, 7, 6),),
    (8, 3): ((1, 0, 3, 2, 5, 4, 7, 6), (2, 3, 0, 1, 6, 7, 4, 5)),
}


def group_seeds(groups: int, advance: int) -> tuple[tuple[int, int], ...]:
    """The group and the place in it of every seed of the knockout after the
    groups: the group winners first, in the order of the groups, then the
    second places, and so on. The players of one place go to the seeds of their
    place where they meet the players of their own group as late as the bracket
    allows: as few of them as can in the first round, then in the second, and so
    on; of equal draws, the one with the earlier groups on the higher seeds."""
    orders = GROUP_ORDERS[groups, advance] if advance > 1 else ()
    seeds = [(group, 0) for group in range(groups)]
    for rank, order in enumerate(orders, start=1):
        seeds.extend((group, rank) for group in order)
    return tuple(seeds)


def shifted(matches: list[Match], offset: int) -> list[Match]:
    """The matches behind others, where their players go on moved along."""
    for match in matches:
        if match.winner_to is not None:
            match.winner_to = (match.winner_to[0] + offset, match.winner_to[1])
        if match.loser_to is not None:
            match.loser_to = (match.loser_to[0] + offset, match.loser_to[1])
    return matches
