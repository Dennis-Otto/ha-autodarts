"""What every player did over a practice match, for the summary once it ends.

The practice game counts the darts, points, marks, legs and sets of a match
itself; a tally adds what the summary shows on top: the first nine darts and
the darts at a double of every leg, the legs checked out, the highest finish,
the high visits and the best leg.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Visits of 100 to 139, 140 to 179 and 180 points, as the training counts them.
HIGH_VISITS = ((180, "scores_180"), (140, "scores_140"), (100, "scores_100"))


@dataclass
class Tally:
    """One player's numbers of the match that the legs do not keep."""

    first9_points: int = 0
    first9_darts: int = 0
    at_double: int = 0
    # Legs finished on a double, with double out.
    checkouts: int = 0
    # The highest score a player finished a leg with, and their fewest darts
    # for a leg they won.
    highest_checkout: int = 0
    best_leg: int = 0
    scores_100: int = 0
    scores_140: int = 0
    scores_180: int = 0

    def visit(self, points: int) -> None:
        """An X01 visit, with the points it scored."""
        for low, key in HIGH_VISITS:
            if points >= low:
                setattr(self, key, getattr(self, key) + 1)
                return

    def leg(self, first9_points: int, first9_darts: int, at_double: int) -> None:
        """A leg that ended, with the player's first nine darts and darts at a double."""
        self.first9_points += first9_points
        self.first9_darts += first9_darts
        self.at_double += at_double

    def won(self, darts: int, checkout: int = 0, double_out: bool = False) -> None:
        """A leg the player won in this many darts, finishing on this score."""
        self.best_leg = min(self.best_leg or darts, darts)
        self.highest_checkout = max(self.highest_checkout, checkout)
        self.checkouts += int(bool(checkout) and double_out)

    def stored(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def restored(cls, saved: object) -> Tally:
        data = saved if isinstance(saved, dict) else {}
        return cls(
            **{
                key: value
                for key in asdict(cls())
                if type(value := data.get(key)) is int and value >= 0
            }
        )
