"""Ship the blueprints with the integration, after a change of one of them.

Copies blueprints/automation/homedarts/ into the integration, whose release
package carries it, and adds the fingerprint of each blueprint to
custom_components/homedarts/blueprint_versions.json. With the fingerprints of
every earlier version, the integration recognises a blueprint nobody changed and
brings it up to date (custom_components/homedarts/shipped_blueprints.py).

    python scripts/ship_blueprints.py
    python scripts/ship_blueprints.py --history   # also every version in Git

tests/test_shipped_blueprints.py fails until it has run.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("blueprints", "automation", "homedarts")
sys.path.insert(0, str(ROOT))

from homeassistant.util.yaml import parse_yaml  # noqa: E402

from custom_components.homedarts.shipped_blueprints import (  # noqa: E402
    SHIPPED,
    VERSIONS,
    fingerprint,
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def history(name: str) -> list[str]:
    """The fingerprint of each version of a blueprint on this branch, oldest first."""
    path = (SOURCE / name).as_posix()
    commits = _git("log", "--reverse", "--format=%H", "HEAD", "--", path).split()
    return [
        fingerprint(parse_yaml(_git("show", f"{commit}:{path}"))) for commit in commits
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--history", action="store_true", help="add every version in Git as well"
    )
    args = parser.parse_args()
    names = sorted(path.name for path in (ROOT / SOURCE).glob("*.yaml"))
    SHIPPED.mkdir(parents=True, exist_ok=True)
    for path in SHIPPED.glob("*.yaml"):
        if path.name not in names:
            path.unlink()
    known: dict[str, list[str]] = (
        json.loads(VERSIONS.read_text(encoding="utf-8")) if VERSIONS.exists() else {}
    )
    versions: dict[str, list[str]] = {}
    for name in names:
        shutil.copyfile(ROOT / SOURCE / name, SHIPPED / name)
        found = (history(name) if args.history else []) + known.get(name, [])
        found.append(fingerprint(parse_yaml((ROOT / SOURCE / name).read_text("utf-8"))))
        # Each version once, at its first appearance.
        versions[name] = list(dict.fromkeys(found))
    VERSIONS.write_text(
        json.dumps(versions, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Shipped {len(names)} blueprints with the integration.")


if __name__ == "__main__":
    main()
