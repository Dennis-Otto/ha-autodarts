"""Training games on the local board.

Around the Clock, doubles, checkouts, Bob's 27, the 121 checkout ladder,
Catch 40, the JDC Challenge and the singles training.

Every game follows the darts of the current visit like the X01 game does, and
books a visit when the darts are pulled. A finished game stays on the card
until the next dart, which starts it again.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any

from homeassistant.util import dt as dt_util

from .checkout import checkout
from .doubles import double_of
from .doubles import hits as hits_double
from .scoring import BULL, VISIT_DARTS, evaluate_visit, is_double
from .training import hit_key

DRILLS = (
    "around_the_clock",
    "doubles",
    "checkout",
    "bobs_27",
    "checkout_121",
    "catch_40",
    "jdc_challenge",
    "singles",
)
RESULTS = 10
# The targets in order: 1 to 20, then the bull.
TARGETS = (*range(1, 21), BULL)
BOBS_START = 27
CHECKOUT_VISITS = 3
# Every score from 2 to 170 that three darts can finish on a double.
CHECKOUT_SCORES = tuple(score for score in range(2, 171) if checkout(score))
# The 121 ladder climbs from 121 to 170 over the scores that have a checkout.
LADDER = tuple(score for score in CHECKOUT_SCORES if score >= 121)
# Catch 40: the checkouts 61 to 100, two visits each.
CATCH_TARGETS = tuple(range(61, 101))
CATCH_VISITS = 2
# The JDC Challenge: a Shanghai visit at every number from 10 to 15, one dart
# at every double and the bullseye, then a Shanghai visit at 15 to 20.
JDC_STEPS = (
    *(("shanghai", number) for number in range(10, 16)),
    *(("double", number) for number in TARGETS),
    *(("shanghai", number) for number in range(15, 21)),
)
JDC_PARTS = (6, 27)
JDC_SHANGHAI = 100
JDC_DOUBLE = 50
JDC_BULL = 100


def _rate(hits: int, darts: int) -> float | None:
    return round(hits * 100 / darts, 1) if darts else None


def _count(value: object, default: int = 0) -> int:
    return value if type(value) is int and value >= 0 else default


def _results(saved: object) -> list[dict[str, Any]]:
    return [
        dict(result)
        for result in (saved if isinstance(saved, list) else [])
        if isinstance(result, dict) and isinstance(result.get("ended"), str)
    ][:RESULTS]


class Drill(ABC):
    """One training game, restarted by the first dart after it ended."""

    kind = ""

    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.finished = False
        self._visit: list[dict[str, Any]] = []
        self._skip = 0
        self._announced = False
        self.reset()

    def reset(self, on_board: int = 0) -> None:
        """Start again; darts already on the board do not count."""
        self.finished = False
        self._skip = on_board
        self._announced = False

    def _thrown(self) -> list[dict[str, Any]]:
        return self._visit[self._skip : VISIT_DARTS]

    def _record(self, result: dict[str, Any]) -> None:
        self.results.insert(0, {**result, "ended": dt_util.utcnow().isoformat()})
        del self.results[RESULTS:]

    def track(self, visit: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
        self._visit = list(visit)
        self._skip = min(self._skip, len(self._visit))
        if self.finished and self._thrown():
            self.reset()
        return self._announce()

    def _announce(self) -> list[tuple[str, dict[str, Any]]]:
        return []

    def double_attempts(self) -> list[tuple[str, bool]]:
        """Darts of the visit thrown at a double, and whether they hit it."""
        return []

    def finish_visit(self) -> list[tuple[str, dict[str, Any]]]:
        events = self._book() if not self.finished and self._thrown() else []
        self._visit, self._skip, self._announced = [], 0, False
        return events

    @abstractmethod
    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        """Count the darts of the visit; the events if it ends the game."""

    def restore(self, saved: dict[str, Any]) -> None:
        self.results = _results(saved.get("results"))
        self.finished = saved.get("finished") is True

    def stored(self) -> dict[str, Any]:
        return {"finished": self.finished, "results": [dict(r) for r in self.results]}

    def snapshot(self) -> dict[str, Any]:
        return {
            "drill": self.kind,
            "finished": self.finished,
            "visit": [hit_key(dart) for dart in self._thrown()],
            # A copy: Home Assistant keeps the attributes of every state it wrote.
            "results": [dict(result) for result in self.results],
        }


class TargetDrill(Drill):
    """Hit 1 to 20 and the bull in order: any bed, or only the doubles.

    Around the Clock names its targets by number, 1 to 20 and 25 for the bull,
    where the outer bull and the bullseye both count; the doubles training
    names the double, D1 to D20 and BULL for the bullseye.
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.doubles = kind == "doubles"
        self.index = 0
        self.darts = 0
        self.hits = 0
        super().__init__()

    def reset(self, on_board: int = 0) -> None:
        super().reset(on_board)
        self.index, self.darts, self.hits = 0, 0, 0

    def _hit(self, dart: dict[str, Any], number: int) -> bool:
        if dart["number"] != number or dart["multiplier"] == 0:
            return False
        return is_double(dart) if self.doubles else True

    def _progress(self) -> tuple[int, int]:
        """Target index and counted darts after the darts of this visit."""
        index = self.index
        for count, dart in enumerate(self._thrown(), 1):
            if index == len(TARGETS):
                break
            if self._hit(dart, TARGETS[index]):
                index += 1
                if index == len(TARGETS):
                    return index, count
        return index, len(self._thrown())

    def double_attempts(self) -> list[tuple[str, bool]]:
        if not self.doubles or self.finished:
            return []
        result: list[tuple[str, bool]] = []
        index = self.index
        for dart in self._thrown():
            if index == len(TARGETS):
                break
            double = double_of(TARGETS[index])
            hit = hits_double(dart, double)
            result.append((double, hit))
            index += int(hit)
        return result

    def _summary(self, darts: int, hits: int) -> dict[str, Any]:
        return {
            "drill": self.kind,
            "darts": darts,
            "hits": hits,
            "hit_rate": _rate(hits, darts),
        }

    def _announce(self) -> list[tuple[str, dict[str, Any]]]:
        index, darts = self._progress()
        if index < len(TARGETS) or self._announced:
            return []
        self._announced = True
        hits = self.hits + index - self.index
        return [("drill_finished", self._summary(self.darts + darts, hits))]

    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        index, darts = self._progress()
        self.hits += index - self.index
        self.darts += darts
        self.index = index
        if index == len(TARGETS):
            self.finished = True
            self._record(self._summary(self.darts, self.hits))
        return []

    def restore(self, saved: dict[str, Any]) -> None:
        super().restore(saved)
        self.index = min(_count(saved.get("index")), len(TARGETS))
        self.darts, self.hits = _count(saved.get("darts")), _count(saved.get("hits"))
        self.hits = min(self.hits, self.index)

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "index": self.index,
            "darts": self.darts,
            "hits": self.hits,
        }

    def snapshot(self) -> dict[str, Any]:
        index, darts = self._progress()
        target = None if index == len(TARGETS) else TARGETS[index]
        hits = self.hits + index - self.index
        name = None
        if target is not None:
            name = double_of(target) if self.doubles else str(target)
        finished = [result["darts"] for result in self.results]
        return {
            **super().snapshot(),
            "target": name,
            "progress": index,
            "targets": len(TARGETS),
            "darts": self.darts + darts,
            "hits": hits,
            "hit_rate": _rate(hits, self.darts + darts),
            "best": min(finished) if finished else None,
        }


class BobsDrill(Drill):
    """Bob's 27: one visit at each double; a visit without a hit costs its value.

    The game is lost as soon as the score drops to zero or below.
    """

    kind = "bobs_27"

    def __init__(self) -> None:
        self.index = 0
        self.score = BOBS_START
        self.darts = 0
        self.hits = 0
        super().__init__()

    def reset(self, on_board: int = 0) -> None:
        super().reset(on_board)
        self.index, self.score, self.darts, self.hits = 0, BOBS_START, 0, 0

    def _value(self) -> int:
        return 50 if TARGETS[self.index] == BULL else 2 * TARGETS[self.index]

    def _visit_hits(self) -> int:
        target = TARGETS[self.index]
        return sum(
            dart["number"] == target and is_double(dart) for dart in self._thrown()
        )

    def double_attempts(self) -> list[tuple[str, bool]]:
        if self.finished:
            return []
        double = double_of(TARGETS[self.index])
        return [(double, hits_double(dart, double)) for dart in self._thrown()]

    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        hits = self._visit_hits()
        self.score += hits * self._value() if hits else -self._value()
        self.hits += hits
        self.darts += len(self._thrown())
        lost = self.score <= 0
        if not lost and self.index < len(TARGETS) - 1:
            self.index += 1
            return []
        self.finished = True
        result = {
            "drill": self.kind,
            "score": self.score,
            "completed": not lost,
            "darts": self.darts,
            "hits": self.hits,
            "hit_rate": _rate(self.hits, self.darts),
        }
        self._record(result)
        return [("drill_finished", result)]

    def restore(self, saved: dict[str, Any]) -> None:
        super().restore(saved)
        self.index = min(_count(saved.get("index")), len(TARGETS) - 1)
        score = saved.get("score")
        self.score = score if type(score) is int else BOBS_START
        self.darts, self.hits = _count(saved.get("darts")), _count(saved.get("hits"))

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "index": self.index,
            "score": self.score,
            "darts": self.darts,
            "hits": self.hits,
        }

    def snapshot(self) -> dict[str, Any]:
        hits = 0 if self.finished else self._visit_hits()
        target = TARGETS[self.index]
        scores = [result["score"] for result in self.results if "score" in result]
        return {
            **super().snapshot(),
            "target": None
            if self.finished
            else "BULL"
            if target == BULL
            else f"D{target}",
            "progress": self.index + (1 if self.finished else 0),
            "targets": len(TARGETS),
            "score": self.score + hits * self._value(),
            "darts": self.darts + (0 if self.finished else len(self._thrown())),
            "hits": self.hits + hits,
            "hit_rate": _rate(
                self.hits + hits,
                self.darts + (0 if self.finished else len(self._thrown())),
            ),
            "best": max(scores) if scores else None,
        }


class CheckoutDrill(Drill):
    """A random finish from 2 to 170, checked out on a double in three visits."""

    kind = "checkout"
    scores = CHECKOUT_SCORES

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.target = 0
        self.start = 0
        self.visits = 0
        self.attempt_darts = 0
        self.attempts = 0
        self.successes = 0
        super().__init__()

    def reset(self, on_board: int = 0) -> None:
        super().reset(on_board)
        self.attempts, self.successes = 0, 0
        self._next(None)

    def _choose(self, success: bool | None) -> int:
        """The target after an attempt, or the first one."""
        return self._rng.choice(self.scores)

    def _next(self, success: bool | None) -> None:
        self.target = self.start = self._choose(success)
        self.visits, self.attempt_darts = 0, 0

    def _attempt(self, result: dict[str, Any]) -> dict[str, Any]:
        """What the checkout_attempt event tells about the attempt."""
        return {
            **result,
            "attempts": self.attempts,
            "successes": self.successes,
            "rate": _rate(self.successes, self.attempts),
        }

    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        remaining, outcome, darts = evaluate_visit(self.start, self._thrown(), True)
        self.visits += 1
        self.attempt_darts += darts
        if outcome is None and self.visits < CHECKOUT_VISITS:
            self.start = remaining
            return []
        success = outcome == "won"
        self.attempts += 1
        self.successes += success
        result = {
            "drill": self.kind,
            "target": self.target,
            "success": success,
            "darts": self.attempt_darts,
        }
        self._record(result)
        self._next(success)
        return [("checkout_attempt", self._attempt(result))]

    def restore(self, saved: dict[str, Any]) -> None:
        super().restore(saved)
        # A checkout drill never ends; every attempt books its own result.
        self.finished = False
        target, start = saved.get("target"), saved.get("start")
        if target in self.scores and type(start) is int and 0 < start <= target:
            self.target, self.start = target, start
            self.visits = min(_count(saved.get("visits")), CHECKOUT_VISITS - 1)
            self.attempt_darts = _count(saved.get("attempt_darts"))
        self.attempts = _count(saved.get("attempts"))
        self.successes = min(_count(saved.get("successes")), self.attempts)

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "target": self.target,
            "start": self.start,
            "visits": self.visits,
            "attempt_darts": self.attempt_darts,
            "attempts": self.attempts,
            "successes": self.successes,
        }

    def snapshot(self) -> dict[str, Any]:
        remaining, outcome, _ = evaluate_visit(self.start, self._thrown(), True)
        thrown = len(self._thrown())
        return {
            **super().snapshot(),
            "target": str(self.target),
            **_finish(remaining, outcome, thrown, self.visits, CHECKOUT_VISITS),
            "attempts": self.attempts,
            "successes": self.successes,
            "rate": _rate(self.successes, self.attempts),
        }


def _finish(
    remaining: int, outcome: str | None, thrown: int, visits: int, limit: int
) -> dict[str, Any]:
    """The remaining score, route and visit of a checkout attempt."""
    if outcome is not None or (thrown >= VISIT_DARTS and visits + 1 >= limit):
        # A finish, a bust or the last visit ends the attempt: the next
        # target follows when the darts are pulled.
        route: tuple[str, ...] = ()
    elif thrown >= VISIT_DARTS:
        route = checkout(remaining, VISIT_DARTS)
    else:
        route = checkout(remaining, VISIT_DARTS - thrown)
    return {
        "remaining": remaining,
        "checkout": " ".join(route) or None,
        "bust": outcome == "bust",
        "won": outcome == "won",
        "attempt_visit": visits + 1,
        "attempt_visits": limit,
    }


class LadderDrill(CheckoutDrill):
    """121: nine darts to check out, starting at 121.

    A finish climbs to the next score, a miss steps one down, never below 121;
    the scores without a checkout are left out, and 170 is the top.
    """

    kind = "checkout_121"
    scores = LADDER

    def _choose(self, success: bool | None) -> int:
        if success is None:
            return LADDER[0]
        step = LADDER.index(self.target) + (1 if success else -1)
        return LADDER[min(max(step, 0), len(LADDER) - 1)]

    def _attempt(self, result: dict[str, Any]) -> dict[str, Any]:
        return {**super()._attempt(result), "next": self.target}

    def snapshot(self) -> dict[str, Any]:
        reached = [
            result["target"]
            for result in self.results
            if result.get("success") is True and type(result.get("target")) is int
        ]
        return {**super().snapshot(), "best": max(reached) if reached else None}


def catch_points(darts: int) -> int:
    """Catch 40 points for a checkout in this many darts."""
    return 3 if darts <= 2 else 2 if darts == 3 else 1


class CatchDrill(Drill):
    """Catch 40: check out 61 to 100 in turn, with two visits each.

    Two darts score 3 points, three darts 2 and four to six darts 1; a bust
    ends the number without points, like two visits without the finish.
    """

    kind = "catch_40"

    def __init__(self) -> None:
        self.index = 0
        self.start = CATCH_TARGETS[0]
        self.visits = 0
        self.target_darts = 0
        self.score = 0
        self.checkouts = 0
        self.darts = 0
        super().__init__()

    def reset(self, on_board: int = 0) -> None:
        super().reset(on_board)
        self.score, self.checkouts, self.darts = 0, 0, 0
        self._target(0)

    def _target(self, index: int) -> None:
        self.index = index
        self.start = CATCH_TARGETS[min(index, len(CATCH_TARGETS) - 1)]
        self.visits, self.target_darts = 0, 0

    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        remaining, outcome, darts = evaluate_visit(self.start, self._thrown(), True)
        self.visits += 1
        self.target_darts += darts
        self.darts += darts
        if outcome is None and self.visits < CATCH_VISITS:
            self.start = remaining
            return []
        if outcome == "won":
            self.score += catch_points(self.target_darts)
            self.checkouts += 1
        if self.index < len(CATCH_TARGETS) - 1:
            self._target(self.index + 1)
            return []
        self.finished = True
        result = {
            "drill": self.kind,
            "score": self.score,
            "checkouts": self.checkouts,
            "darts": self.darts,
        }
        self._record(result)
        return [("drill_finished", result)]

    def restore(self, saved: dict[str, Any]) -> None:
        super().restore(saved)
        index = min(_count(saved.get("index")), len(CATCH_TARGETS) - 1)
        self._target(index)
        start = saved.get("start")
        if type(start) is int and 0 < start <= CATCH_TARGETS[index]:
            self.start = start
            self.visits = min(_count(saved.get("visits")), CATCH_VISITS - 1)
            self.target_darts = _count(saved.get("target_darts"))
        self.checkouts = min(_count(saved.get("checkouts")), index + 1)
        self.score = min(_count(saved.get("score")), 3 * self.checkouts)
        self.darts = _count(saved.get("darts"))

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "index": self.index,
            "start": self.start,
            "visits": self.visits,
            "target_darts": self.target_darts,
            "score": self.score,
            "checkouts": self.checkouts,
            "darts": self.darts,
        }

    def snapshot(self) -> dict[str, Any]:
        scores = [result["score"] for result in self.results if "score" in result]
        common = {
            **super().snapshot(),
            "progress": self.index + int(self.finished),
            "targets": len(CATCH_TARGETS),
            "best": max(scores) if scores else None,
        }
        if self.finished:
            return {
                **common,
                "target": None,
                "score": self.score,
                "checkouts": self.checkouts,
                "darts": self.darts,
            }
        remaining, outcome, darts = evaluate_visit(self.start, self._thrown(), True)
        won = outcome == "won"
        thrown = len(self._thrown())
        return {
            **common,
            "target": str(CATCH_TARGETS[self.index]),
            **_finish(remaining, outcome, thrown, self.visits, CATCH_VISITS),
            "score": self.score
            + (catch_points(self.target_darts + darts) if won else 0),
            "checkouts": self.checkouts + int(won),
            "darts": self.darts + darts,
        }


class JdcDrill(Drill):
    """The JDC Challenge of the Junior Darts Corporation: 57 darts in three parts.

    A Shanghai visit at every number from 10 to 15: each dart in a bed of the
    number scores its value, and a single, double and treble of it in the
    visit add 100. Then one dart at every double from 1 to 20, 50 points a
    hit, and one at the bullseye for 100. Then a Shanghai visit at every
    number from 15 to 20. The most points are 3,380.
    """

    kind = "jdc_challenge"

    def __init__(self) -> None:
        self.step = 0
        self.parts = [0, 0, 0]
        self.darts = 0
        super().__init__()

    def reset(self, on_board: int = 0) -> None:
        super().reset(on_board)
        self.step, self.parts, self.darts = 0, [0, 0, 0], 0

    @staticmethod
    def _part(step: int) -> int:
        return sum(step >= start for start in JDC_PARTS)

    def _doubles(self) -> list[tuple[int, str, bool]]:
        """Step, double and hit of every dart of the visit in the doubles part;
        darts beyond the last double do not count."""
        step, result = self.step, []
        for dart in self._thrown():
            if step == len(JDC_STEPS) or JDC_STEPS[step][0] != "double":
                break
            double = double_of(JDC_STEPS[step][1])
            result.append((step, double, hits_double(dart, double)))
            step += 1
        return result

    def _play(self) -> tuple[int, list[int], int]:
        """Step, points per part and counted darts after the darts of the visit.

        A Shanghai number takes the whole visit and is done when the visit is
        booked; a double takes one dart.
        """
        parts, thrown = list(self.parts), self._thrown()
        kind, number = JDC_STEPS[self.step]
        if kind == "shanghai":
            hits = [
                dart["multiplier"]
                for dart in thrown
                if dart["number"] == number and dart["multiplier"]
            ]
            bonus = JDC_SHANGHAI if {1, 2, 3} <= set(hits) else 0
            parts[self._part(self.step)] += number * sum(hits) + bonus
            return self.step, parts, len(thrown)
        doubles = self._doubles()
        for _, double, hit in doubles:
            parts[1] += (JDC_BULL if double == "BULL" else JDC_DOUBLE) * hit
        return self.step + len(doubles), parts, len(doubles)

    def double_attempts(self) -> list[tuple[str, bool]]:
        if self.finished:
            return []
        return [(double, hit) for _, double, hit in self._doubles()]

    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        shanghai = JDC_STEPS[self.step][0] == "shanghai"
        step, self.parts, darts = self._play()
        self.darts += darts
        self.step = step + int(shanghai)
        if self.step < len(JDC_STEPS):
            return []
        self.finished = True
        result = {
            "drill": self.kind,
            "score": sum(self.parts),
            "parts": list(self.parts),
            "darts": self.darts,
        }
        self._record(result)
        return [("drill_finished", result)]

    def restore(self, saved: dict[str, Any]) -> None:
        super().restore(saved)
        last = len(JDC_STEPS) - int(not self.finished)
        self.step = min(_count(saved.get("step")), last)
        parts = saved.get("parts")
        if isinstance(parts, list) and len(parts) == len(self.parts):
            self.parts = [_count(part) for part in parts]
        self.darts = _count(saved.get("darts"))

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "step": self.step,
            "parts": list(self.parts),
            "darts": self.darts,
        }

    def snapshot(self) -> dict[str, Any]:
        if self.finished:
            step, parts, darts = len(JDC_STEPS), list(self.parts), 0
        else:
            step, parts, darts = self._play()
        target = None
        if step < len(JDC_STEPS):
            kind, number = JDC_STEPS[step]
            target = str(number) if kind == "shanghai" else double_of(number)
        scores = [result["score"] for result in self.results if "score" in result]
        return {
            **super().snapshot(),
            "target": target,
            "part": self._part(min(step, len(JDC_STEPS) - 1)) + 1,
            "progress": step,
            "targets": len(JDC_STEPS),
            "score": sum(parts),
            "parts": parts,
            "darts": self.darts + darts,
            "best": max(scores) if scores else None,
        }


class SinglesDrill(Drill):
    """One visit at every number from 1 to 20 and the bull.

    Every dart in a bed of the number scores a point per mark: a single 1, a
    double 2 and a treble 3; at the bull, the outer bull 1 and the bullseye 2.
    """

    kind = "singles"

    def __init__(self) -> None:
        self.index = 0
        self.score = 0
        self.darts = 0
        self.hits = 0
        super().__init__()

    def reset(self, on_board: int = 0) -> None:
        super().reset(on_board)
        self.index, self.score, self.darts, self.hits = 0, 0, 0, 0

    def _scored(self) -> tuple[int, int]:
        """Points and hits of the visit at the current number."""
        number = TARGETS[self.index]
        hits = [
            dart["multiplier"]
            for dart in self._thrown()
            if dart["number"] == number and dart["multiplier"]
        ]
        return sum(hits), len(hits)

    def _book(self) -> list[tuple[str, dict[str, Any]]]:
        points, hits = self._scored()
        self.score += points
        self.hits += hits
        self.darts += len(self._thrown())
        if self.index < len(TARGETS) - 1:
            self.index += 1
            return []
        self.finished = True
        result = {
            "drill": self.kind,
            "score": self.score,
            "darts": self.darts,
            "hits": self.hits,
            "hit_rate": _rate(self.hits, self.darts),
        }
        self._record(result)
        return [("drill_finished", result)]

    def restore(self, saved: dict[str, Any]) -> None:
        super().restore(saved)
        self.index = min(_count(saved.get("index")), len(TARGETS) - 1)
        self.darts = _count(saved.get("darts"))
        self.hits = min(_count(saved.get("hits")), self.darts)
        self.score = min(_count(saved.get("score")), 3 * self.hits)

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "index": self.index,
            "score": self.score,
            "darts": self.darts,
            "hits": self.hits,
        }

    def snapshot(self) -> dict[str, Any]:
        points, hits = (0, 0) if self.finished else self._scored()
        darts = self.darts + (0 if self.finished else len(self._thrown()))
        scores = [result["score"] for result in self.results if "score" in result]
        return {
            **super().snapshot(),
            "target": None if self.finished else str(TARGETS[self.index]),
            "progress": self.index + int(self.finished),
            "targets": len(TARGETS),
            "score": self.score + points,
            "darts": darts,
            "hits": self.hits + hits,
            "hit_rate": _rate(self.hits + hits, darts),
            "best": max(scores) if scores else None,
        }


# The training games that need nothing to start with.
DRILL_RULES: dict[str, type[Drill]] = {
    "bobs_27": BobsDrill,
    "checkout_121": LadderDrill,
    "catch_40": CatchDrill,
    "jdc_challenge": JdcDrill,
    "singles": SinglesDrill,
}


def make_drill(kind: str, rng: random.Random | None = None) -> Drill:
    if kind == "checkout":
        return CheckoutDrill(rng)
    if kind in DRILL_RULES:
        return DRILL_RULES[kind]()
    return TargetDrill(kind)
