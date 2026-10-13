"""Pin Assist's packages for the tests at the versions Home Assistant installs.

`tests/test_voice_blueprints.py` talks to Home Assistant's own Assist, whose
packages (hassil, home-assistant-intents, gazetteer-matcher) the conversation
manifest of Home Assistant names with exact versions. Renovate leaves them alone.
When pytest-homeassistant-custom-component brings a new Home Assistant, that test
fails, and this script writes the versions of its manifest into
`requirements-test.in` and compiles `requirements-test.txt` again with the command
in its header, which needs pip-tools and the Python named there:

    python scripts/pin_assist.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "requirements-test.in"
LOCK = ROOT / "requirements-test.txt"


def manifest_pins() -> dict[str, str]:
    """The packages and versions the installed Home Assistant installs for Assist."""
    spec = importlib.util.find_spec("homeassistant")
    if spec is None or spec.origin is None:
        raise SystemExit("Home Assistant is missing: install requirements-test.txt.")
    manifest = Path(spec.origin).parent / "components/conversation/manifest.json"
    requirements = json.loads(manifest.read_text(encoding="utf-8"))["requirements"]
    return dict(requirement.split("==", 1) for requirement in requirements)


def pin(text: str, wanted: dict[str, str]) -> str:
    """`requirements-test.in` with each package at its version; one it lacks at the
    end."""
    for name, version in sorted(wanted.items()):
        line = f"{name}=={version}"
        text, found = re.subn(rf"^{re.escape(name)}==\S+$", line, text, flags=re.M)
        if not found:
            text = f"{text.rstrip()}\n{line}\n"
    return text


def locked(lock: str, wanted: dict[str, str]) -> bool:
    """Whether `requirements-test.txt` holds each package at its version."""
    return all(
        re.search(rf"^{re.escape(f'{name}=={version}')}(?= |$)", lock, re.M)
        for name, version in wanted.items()
    )


def compile_command(lock: str) -> list[str]:
    """The command in the header of `requirements-test.txt` that compiled it."""
    match = re.search(r"^# by the following command:\n#\n#    (.+)$", lock, re.M)
    if match is None:
        raise SystemExit(f"{LOCK.name} names no command that compiled it.")
    return shlex.split(match.group(1))


def main() -> int:
    wanted = manifest_pins()
    text = SOURCE.read_text(encoding="utf-8")
    lock = LOCK.read_text(encoding="utf-8")
    pinned = pin(text, wanted)
    if pinned == text and locked(lock, wanted):
        print(f"{SOURCE.name} and {LOCK.name} pin Assist as Home Assistant does.")
        return 0
    SOURCE.write_text(pinned, encoding="utf-8", newline="\n")
    command = compile_command(lock)
    print("Pinned", ", ".join(f"{n}=={v}" for n, v in sorted(wanted.items())))
    print("Compiling:", shlex.join(command), flush=True)
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except FileNotFoundError:
        print(f"Install pip-tools, then run: {shlex.join(command)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
