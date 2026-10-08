"""The frozen clock and the fixed random numbers of the screenshot demo.

tests/e2e/frozen/sitecustomize.py freezes the clock of every Python process in the
demo's Home Assistant container, so that two runs of the screenshots render the same
images. Its Clock is tested here directly; what it does to a whole process, in a
process of its own.
"""

import importlib.util
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

FROZEN = Path(__file__).parent / "e2e" / "frozen"
SPEC = importlib.util.spec_from_file_location("demo_clock", FROZEN / "sitecustomize.py")
demo_clock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo_clock)

START = "2026-09-29T20:30:00+02:00"
STARTED = datetime.fromisoformat(START).timestamp()


class Monotonic:
    """A monotonic clock that the test moves by hand."""

    def __init__(self) -> None:
        self.seconds = 50.0

    def __call__(self) -> float:
        return self.seconds


def exactly(seconds: float):
    """Seconds since the epoch, to the microsecond."""
    return pytest.approx(seconds, abs=0.000001)


def test_the_clock_stands_still_until_it_is_moved(tmp_path):
    monotonic = Monotonic()
    file = tmp_path / "clock"
    now = demo_clock.Clock(START, str(file), monotonic)
    # No file yet: the clock stands at the demo time.
    assert now() == STARTED
    slept = []
    demo_clock.move(file, STARTED + demo_clock.STEP, slept.append)
    assert file.read_text() == repr(STARTED + 2)
    assert not (tmp_path / "clock.new").exists()
    # The move waits for what Home Assistant does, then until every process read it.
    assert slept == [demo_clock.SETTLE, demo_clock.REREAD + demo_clock.SETTLE]
    # A process reads the file again only after a twentieth of a second.
    monotonic.seconds += 0.01
    assert now() == STARTED
    monotonic.seconds += 0.05
    assert now() == exactly(STARTED + 2)
    # A file being written at this very moment keeps the time as it was.
    file.write_text("")
    monotonic.seconds += 1
    assert now() == exactly(STARTED + 2)


def test_a_clock_without_a_file_stands_still():
    now = demo_clock.Clock(START)
    assert now() == now() == STARTED


def run(code: str, **environ: str) -> list[str]:
    """The lines a Python process prints with the frozen clock on its path."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DEMO_") and key != "PYTHONPATH"
    }
    env |= {"PYTHONPATH": str(FROZEN), **environ}
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return result.stdout.splitlines()


PROCESS = """
import datetime, pickle, random, time
from datetime import date, datetime as D, timedelta, timezone
a = time.time(); time.sleep(0.2); b = time.time()
made = D(2026, 1, 2, 3, 4, 5)
print(D.now(timezone.utc).isoformat(timespec='seconds'))
print(D.utcnow().isoformat(timespec='seconds'))
print(D.today().date(), date.today())
print(round(b - a, 4), time.time_ns() // 10**9 == int(time.time()))
print(time.strftime('%Y-%m-%d %H:%M', time.gmtime()), time.localtime().tm_year, time.ctime()[-4:], time.asctime()[-4:])
print(time.strftime('%Y', time.gmtime(0)), time.gmtime(0).tm_year, time.ctime(0)[-4:])
print(isinstance(made, D), isinstance(D.now(), D), isinstance(made, date), issubclass(D, date))
print(isinstance(date(2026, 1, 1), date), issubclass(bool, date), isinstance(1, D))
print(pickle.loads(pickle.dumps(made)) == made, repr(type(made)))
print(random.random(), random.Random().random(), random.Random(5).random() == random.Random(5).random())
print(isinstance(random.SystemRandom().random(), float))
"""


def test_every_process_of_the_demo_sees_the_frozen_clock():
    lines = run(PROCESS, DEMO_TIME=START)
    assert lines[0].startswith("2026-09-29T18:30:00")
    assert lines[1] == "2026-09-29T18:30:00"
    assert lines[2] == "2026-09-29 2026-09-29"
    # The clock stands still while real time passes.
    assert lines[3].split()[0] == "0.0"
    assert lines[3].split()[1] == "True"
    assert lines[4] == "2026-09-29 18:30 2026 2026 2026"
    assert lines[5] == "1970 1970 1970"
    assert lines[6] == "True True True True"
    assert lines[7] == "True False False"
    assert lines[8] == "True <class 'datetime.datetime'>"
    # Generators without a seed of their own give the same numbers in every run.
    first, second, seeded = lines[9].split()
    assert first == second and seeded == "True"
    assert run(PROCESS, DEMO_TIME=START)[9] == lines[9]
    assert lines[10] == "True"


def test_a_process_without_demo_time_keeps_the_real_clock():
    year = datetime.now(UTC).year
    lines = run("import time, random; print(time.gmtime().tm_year, random.random())")
    assert lines[0].split()[0] == str(year)
    other = run("import time, random; print(time.gmtime().tm_year, random.random())")
    assert lines[0].split()[1] != other[0].split()[1]
