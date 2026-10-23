"""How tests/e2e/run.sh starts the scenario, checked without Docker.

run.sh runs here with a stand-in for docker that only notes what it is asked to do,
and whose pull of the images fails as often as a test asks, as one does that the
registry cuts off with "unexpected EOF".
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

E2E = Path(__file__).parent / "e2e"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="run.sh runs in bash"
)

# Notes every call; the first $PULL_FAILURES pulls fail.
DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$CALLS"
if [[ "$*" == *" pull "* ]]; then
  failed=$(grep -c ' pull ' "$CALLS")
  if ((failed <= ${PULL_FAILURES:-0})); then
    echo "unexpected EOF" >&2
    exit 1
  fi
fi
"""


def run_sh(
    tmp_path: Path, pull_failures: int
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run run.sh with the stand-in for docker; the result and the calls of docker."""
    docker = tmp_path / "docker"
    docker.write_text(DOCKER, encoding="utf-8", newline="\n")
    docker.chmod(0o755)
    calls = tmp_path / "calls"
    calls.touch()
    environment = {
        **os.environ,
        "DOCKER_BIN": str(docker),
        "CALLS": str(calls),
        "PULL_FAILURES": str(pull_failures),
        "E2E_PULL_PAUSE": "0",
    }
    for name in ("E2E_ARTIFACTS", "KEEP_E2E"):
        environment.pop(name, None)
    result = subprocess.run(
        ["bash", str(E2E / "run.sh")],
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=20,
    )
    return result, calls.read_text(encoding="utf-8").splitlines()


def commands(calls: list[str]) -> list[str]:
    """What run.sh asked Compose to do, such as "pull" or "up", in its order."""
    return [call.split(" --file compose.yaml ", 1)[1].split()[0] for call in calls]


@pytest.mark.parametrize("pull_failures", [0, 1, 2])
def test_the_scenario_starts_once_the_images_are_pulled(tmp_path, pull_failures):
    result, calls = run_sh(tmp_path, pull_failures)

    assert result.returncode == 0, result.stderr
    assert commands(calls) == [
        "down",
        *["pull"] * (pull_failures + 1),
        "up",
        "exec",
        "down",
    ]
    assert "pull --quiet --policy missing" in calls[1]
    assert result.stderr.count("trying again in 0 s") == pull_failures


def test_images_that_fail_to_pull_three_times_start_no_scenario(tmp_path):
    result, calls = run_sh(tmp_path, 3)

    assert result.returncode != 0
    # The logs of the failed run, as after any failure, and no scenario.
    assert commands(calls) == [
        "down",
        "pull",
        "pull",
        "pull",
        "ps",
        "logs",
        "exec",
        "down",
    ]
    assert not any("scenario.py" in call for call in calls)
    assert result.stderr.count("trying again in 0 s") == 2
    assert "Pulling the images failed 3 times; the scenario did not start" in (
        result.stderr
    )
