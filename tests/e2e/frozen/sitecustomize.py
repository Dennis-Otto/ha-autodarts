"""A frozen clock and fixed random numbers for the demo of the screenshots.

Python imports this module at startup when its folder is on PYTHONPATH, as
compose.frozen.yaml sets it for Home Assistant and every script run in its
container. Without DEMO_TIME it changes nothing.

With DEMO_TIME, such as 2026-09-29T20:30:00+02:00, the wall clock of every Python
process stands still at that moment: time.time() and its relatives, datetime.now(),
datetime.utcnow() and date.today() return it. It moves only when the demo moves it:
every move at the simulated board, a dart, a takeout or a new status, takes two
seconds (STEP), and a step that waits for a time, such as the weekly report, moves
it there. move() writes the new time into the file named by DEMO_CLOCK, in seconds
since the epoch, and every process reads it again within a twentieth of a second.
So every time Home Assistant records comes out the same in every run, to the
microsecond, and darts still come one after the other, as at a real board.
time.monotonic() stays real, so timers, timeouts and sleeps keep working.

Random numbers without a seed of their own, such as the darts of the bot, start
from the same seed in every run.
"""

from __future__ import annotations

import datetime
import os
import random
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

# The time a move at the board takes on the frozen clock, in seconds.
STEP = 2.0
# The seed of every random generator that is created without one.
SEED = 27
# How long a process trusts the time it last read from DEMO_CLOCK, in seconds.
REREAD = 0.05
# How long a move waits before and after it: what Home Assistant does keeps the time
# it began at, and every process has read the new time once the move returns.
SETTLE = 0.1


class Clock:
    """The time of the demo: DEMO_TIME, or the time last written to DEMO_CLOCK."""

    def __init__(
        self,
        start: str,
        path: str | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.seconds = datetime.datetime.fromisoformat(start).timestamp()
        self.path = path
        self.monotonic = monotonic
        self.read_at: float | None = None

    def __call__(self) -> float:
        if self.path and (
            self.read_at is None or self.monotonic() - self.read_at >= REREAD
        ):
            self.read_at = self.monotonic()
            try:
                with open(self.path, encoding="ascii") as file:
                    self.seconds = float(file.read())
            except (OSError, ValueError):
                # Not moved yet, or written at this very moment: the time stays.
                pass
        return self.seconds


def move(
    path: str | Path, seconds: float, sleep: Callable[[float], Any] = time.sleep
) -> None:
    """Move the frozen clock of every process to the given time."""
    sleep(SETTLE)
    target = Path(path)
    written = target.with_name(f"{target.name}.new")
    written.write_text(repr(seconds), encoding="ascii")
    written.replace(target)
    sleep(REREAD + SETTLE)


def freeze_time(now: Callable[[], float]) -> None:
    """Point the clocks of the time and datetime modules at the demo's time."""
    real = {
        name: getattr(time, name)
        for name in ("localtime", "gmtime", "ctime", "asctime", "strftime")
    }

    def at(seconds: float | None) -> float:
        return now() if seconds is None else seconds

    time.time = now
    time.time_ns = lambda: round(now() * 1_000_000_000)
    time.localtime = lambda seconds=None: real["localtime"](at(seconds))
    time.gmtime = lambda seconds=None: real["gmtime"](at(seconds))
    time.ctime = lambda seconds=None: real["ctime"](at(seconds))
    time.asctime = lambda moment=None: real["asctime"](
        real["localtime"](now()) if moment is None else moment
    )
    time.strftime = lambda form, moment=None: real["strftime"](
        form, real["localtime"](now()) if moment is None else moment
    )

    real_date, real_datetime = datetime.date, datetime.datetime

    class DateType(type):
        # Dates made before the clock stood still, or by C code, still count as dates.
        def __instancecheck__(cls, instance: object) -> bool:
            return isinstance(instance, real_date)

        def __subclasscheck__(cls, subclass: type) -> bool:
            return issubclass(subclass, real_date)

    class DatetimeType(DateType):
        def __instancecheck__(cls, instance: object) -> bool:
            return isinstance(instance, real_datetime)

        def __subclasscheck__(cls, subclass: type) -> bool:
            return issubclass(subclass, real_datetime)

    class FrozenDate(real_date, metaclass=DateType):
        @classmethod
        def today(cls) -> Any:
            return real_date.fromtimestamp(now())

    class FrozenDatetime(real_datetime, metaclass=DatetimeType):
        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> Any:
            return real_datetime.fromtimestamp(now(), tz)

        @classmethod
        def utcnow(cls) -> Any:
            return real_datetime.fromtimestamp(now(), datetime.UTC).replace(tzinfo=None)

        @classmethod
        def today(cls) -> Any:
            return real_datetime.fromtimestamp(now())

    # Pickled dates and times name the classes of the datetime module.
    for frozen, name in ((FrozenDate, "date"), (FrozenDatetime, "datetime")):
        frozen.__module__, frozen.__name__, frozen.__qualname__ = "datetime", name, name
    datetime.date, datetime.datetime = FrozenDate, FrozenDatetime


def fix_random(seed: int = SEED) -> None:
    """Every generator without a seed of its own starts from the same one."""
    original = random.Random.seed

    def seeded(self: random.Random, a: Any = None, version: int = 2) -> None:
        original(self, seed if a is None else a, version)

    random.Random.seed = seeded  # type: ignore[method-assign]
    random.seed(seed)


def install(environ: Mapping[str, str] = os.environ) -> bool:
    """Freeze the clock and fix the random numbers when DEMO_TIME asks for it."""
    start = environ.get("DEMO_TIME")
    if not start:
        return False
    freeze_time(Clock(start, environ.get("DEMO_CLOCK")))
    fix_random()
    return True


# Python imports the module by this name at startup; screenshots.py by another one,
# for its Clock alone.
if __name__ == "sitecustomize":
    install()
