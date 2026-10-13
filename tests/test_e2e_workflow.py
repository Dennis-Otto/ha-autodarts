"""The Docker E2E runs for a pull request only when it can change a result, and its
one required check, e2e, passes only when every test that had to run passed.

The steps of e2e.yml run here as GitHub runs them, in bash with a stand-in for gh
that answers as the API does, through the same jq filter."""

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
JOBS = yaml.safe_load(
    (ROOT / ".github" / "workflows" / "e2e.yml").read_text(encoding="utf-8")
)["jobs"]

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="the steps run in bash"
)
# The runners of GitHub have jq; gh applies --jq with the same language.
needs_jq = pytest.mark.skipif(
    shutil.which("jq") is None, reason="the steps filter with jq"
)

# gh answers with the pages of the API, filtered by the --jq of the call.
GH = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$CALLS"
if [[ -n "${GH_FAILS:-}" ]]; then
  echo "HTTP 502: Bad Gateway" >&2
  exit 1
fi
filter="${@: -1}"
for page in "$PAGES"/*.json; do
  jq -r "$filter" "$page"
done
"""


def run_step(
    tmp_path: Path, job: str, env: dict[str, str]
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], str, str]:
    """Run the step of a job; the result, its outputs, its summary and the calls of gh."""
    (run,) = [step["run"] for step in JOBS[job]["steps"] if "run" in step]
    (tmp_path / "step.sh").write_text(run, encoding="utf-8", newline="\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(GH, encoding="utf-8", newline="\n")
    gh.chmod(0o755)
    files = {name: tmp_path / name for name in ("output", "summary", "calls")}
    for path in files.values():
        path.touch()
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(files["output"]),
        "GITHUB_STEP_SUMMARY": str(files["summary"]),
        "CALLS": str(files["calls"]),
        "PAGES": str(tmp_path / "pages"),
        **env,
    }
    # As GitHub runs a step of bash.
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "step.sh"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=20,
    )
    outputs = dict(
        line.split("=", 1)
        for line in files["output"].read_text(encoding="utf-8").splitlines()
    )
    return (
        result,
        outputs,
        files["summary"].read_text(encoding="utf-8"),
        files["calls"].read_text(encoding="utf-8"),
    )


def decide(
    tmp_path: Path, pages: list[list[dict[str, str]]], **env: str
) -> tuple[str, str, str]:
    """Whether the tests have to run, with the summary and the calls of gh."""
    (tmp_path / "pages").mkdir()
    for number, page in enumerate(pages):
        (tmp_path / "pages" / f"{number}.json").write_text(
            json.dumps(page), encoding="utf-8"
        )
    event = {
        "GH_REPO": "o/r",
        "EVENT": "pull_request",
        "NUMBER": "7",
        "CHANGED": str(sum(map(len, pages))),
    }
    result, outputs, summary, calls = run_step(tmp_path, "changes", event | env)
    assert result.returncode == 0, result.stderr
    return outputs["run"], summary, calls


def changed(*names: str) -> list[list[dict[str, str]]]:
    return [[{"filename": name, "status": "modified"} for name in names]]


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_dispatch"])
def test_main_the_night_and_a_manual_run_test_everything(tmp_path, event):
    run, summary, calls = decide(tmp_path, [], EVENT=event, NUMBER="", CHANGED="")

    assert run == "true"
    assert f"A run of {event} tests everything." in summary
    assert calls == ""


@needs_jq
@pytest.mark.parametrize(
    "names",
    [
        ("README.md", "README.de.md", "docs/development.md", "docs/images/en/x.png"),
        ("CHANGELOG.md", ".github/workflows/ci.yml", ".github/renovate.json5"),
        ("requirements-test.txt", "hacs.json", "tests/test_card.py"),
        # Only the package files of the root install axe-core.
        ("docs/package.json", "tests/frontend/package-lock.json"),
    ],
)
def test_a_pull_request_that_changes_nothing_the_tests_use_skips_them(tmp_path, names):
    run, summary, calls = decide(tmp_path, changed(*names))

    assert run == "false"
    assert "changes nothing that the tests run or mount; they are skipped" in summary
    assert calls.startswith("api repos/o/r/pulls/7/files --paginate --jq ")


@needs_jq
@pytest.mark.parametrize(
    "name",
    [
        "custom_components/autodarts/sensor.py",
        "custom_components/autodarts/frontend/autodarts-card.js",
        "blueprints/automation/autodarts/weekly_report.yaml",
        "tests/e2e/scenario.py",
        "tests/e2e/demo_progress.py",
        "tests/e2e/requirements-browser.txt",
        "package.json",
        "package-lock.json",
        ".github/workflows/e2e.yml",
    ],
)
def test_a_pull_request_that_changes_what_the_tests_use_runs_them(tmp_path, name):
    run, summary, _ = decide(tmp_path, changed("README.md", name))

    assert run == "true"
    assert f"changes {name}, which the tests run or mount; they run." in summary


@needs_jq
def test_a_file_moved_away_from_the_tests_runs_them(tmp_path):
    moved = {
        "filename": "docs/old_sensor.py",
        "previous_filename": "custom_components/autodarts/old_sensor.py",
        "status": "renamed",
    }
    # The second page of the API: every page counts.
    run, _, _ = decide(tmp_path, changed("README.md") + [[moved]])

    assert run == "true"


def test_unknown_files_run_the_tests(tmp_path):
    run, summary, calls = decide(tmp_path, changed("README.md"), GH_FAILS="1")

    assert run == "true"
    assert "The files of the pull request are unknown; the tests run." in summary
    assert calls.startswith("api repos/o/r/pulls/7/files")


def test_more_files_than_the_api_lists_run_the_tests(tmp_path):
    run, summary, calls = decide(tmp_path, changed("README.md"), CHANGED="3000")

    assert run == "true"
    assert "changes 3000 files, more than the API lists" in summary
    assert calls == ""


def needs(wanted: str, changes: str, e2e: str) -> dict[str, str]:
    """The environment of the gate, as GitHub fills toJSON(needs)."""
    jobs = {
        "changes": {"result": changes, "outputs": {"run": wanted} if wanted else {}},
        "e2e": {"result": e2e, "outputs": {}},
    }
    return {"WANTED": wanted, "NEEDS": json.dumps(jobs)}


@needs_jq
@pytest.mark.parametrize(
    ("wanted", "changes", "e2e", "summary"),
    [
        ("true", "success", "success", "Every end-to-end test passed."),
        ("false", "success", "skipped", "none had to run"),
    ],
)
def test_the_required_check_passes_when_every_test_that_had_to_run_passed(
    tmp_path, wanted, changes, e2e, summary
):
    result, _, written, _ = run_step(tmp_path, "gate", needs(wanted, changes, e2e))

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"- e2e: {e2e}" in result.stdout
    assert summary in written


@needs_jq
@pytest.mark.parametrize(
    ("wanted", "changes", "e2e"),
    [
        # The tests had to run but were skipped.
        ("true", "success", "skipped"),
        ("true", "success", "failure"),
        # A newer push, a person or the time limit cancelled them.
        ("true", "success", "cancelled"),
        # Without a decision nothing may count as passed.
        ("", "failure", "skipped"),
        ("", "cancelled", "skipped"),
        ("false", "success", "failure"),
    ],
)
def test_the_required_check_fails_when_a_test_that_had_to_run_did_not_pass(
    tmp_path, wanted, changes, e2e
):
    result, _, written, _ = run_step(tmp_path, "gate", needs(wanted, changes, e2e))

    assert result.returncode == 1
    assert "::error::An end-to-end test that had to run didn't pass" in result.stdout
    assert f"- changes: {changes}\n- e2e: {e2e}\n" in written


def test_the_required_check_waits_for_every_test_of_a_pull_request():
    gate = JOBS["gate"]
    project = tomllib.loads(
        (ROOT / ".github" / "repository.project.toml").read_text(encoding="utf-8")
    )
    assert gate["name"] in project["branch"]["required_checks"]
    # A skipped job counts as passed, so the gate must never be skipped.
    assert gate["if"] == "always()"
    # Every job but the beta, which runs only at night and on demand.
    tests = {
        name
        for name, job in JOBS.items()
        if name != "gate" and "github.event_name == 'schedule'" not in job.get("if", "")
    }
    assert "e2e" in tests
    assert set(gate["needs"]) == tests
