"""Record the games that the live demo of the website plays (docs/demo/).

    python scripts/record_demo.py [TIMELINE]

The integration plays them in the Home Assistant of the tests, so this needs the
packages of requirements-test.txt. The timeline goes to docs/demo/timeline.json, or
to TIMELINE. tests/demo_timeline.py describes the games and the recording; the
screenshot bot runs this script with the images, so that the demo follows the
integration and the cards.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "docs" / "demo" / "timeline.json"
TEST = "tests/test_demo_timeline.py::test_the_demo_plays_every_game_to_its_end"


def main(arguments: list[str]) -> int:
    target = Path(arguments[0]).resolve() if arguments else TIMELINE
    target.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DEMO_TIMELINE"] = str(target)
    os.chdir(ROOT)
    # The one test that records, without the cache, quietly.
    code = pytest.main(["-q", "-p", "no:cacheprovider", TEST])
    if code == 0:
        print(
            f"Recorded {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}"
        )
    return int(code)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
