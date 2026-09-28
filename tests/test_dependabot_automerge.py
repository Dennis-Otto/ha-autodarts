"""Keep the privileged Dependabot auto-merge narrow and free of repository code."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parents[1] / ".github/workflows"
JOB = yaml.safe_load((WORKFLOWS / "dependabot-automerge.yml").read_text())["jobs"][
    "auto-merge"
]
COMMIT_STEP = next(
    step for step in JOB["steps"] if step["name"].endswith("of listed actions")
)
OLD = "58bff37c8947f690ace498be413a9b78d6f30f93"
NEW = "06749dd8c0b54f350bc69c8752456cee498808a3"
PR_URL = "https://github.com/Dennis-Otto/ha-autodarts/pull/91"


def test_privileged_job_runs_no_repository_code():
    actions = [step["uses"].split("@")[0] for step in JOB["steps"] if "uses" in step]
    assert actions == ["dependabot/fetch-metadata"]


def test_every_merge_is_bound_to_the_checked_head_commit():
    runs = [step.get("run", "") for step in JOB["steps"]]
    merges = [run for run in runs if "gh pr merge" in run]
    assert len(merges) == 2
    assert all('--match-head-commit "$PR_HEAD_SHA"' in run for run in merges)


def test_commit_updates_need_the_actions_ecosystem_and_one_listed_action():
    # contains() on an array compares whole elements: a group of several
    # dependencies, or a name that only starts like a listed one, never matches.
    assert " ".join(COMMIT_STEP["if"].split()) == (
        "steps.metadata.outputs.package-ecosystem == 'github_actions' && "
        "contains(fromJSON(env.COMMIT_PINNED_ACTIONS), "
        "steps.metadata.outputs.dependency-names)"
    )


def test_listed_actions_are_pinned_to_a_branch_commit():
    listed = json.loads(JOB["env"]["COMMIT_PINNED_ACTIONS"])
    pins = re.findall(
        r"uses: ([\w./-]+)@[0-9a-f]{40} # (\S+)",
        "\n".join(path.read_text() for path in WORKFLOWS.glob("*.yml")),
    )
    assert listed
    for action in listed:
        refs = {ref for name, ref in pins if name == action}
        # Once an action publishes releases, its patch and minor updates merge
        # on their own and the action leaves the list.
        assert refs and refs <= {"main", "master"}, action


@pytest.mark.skipif(os.name == "nt", reason="GitHub runs the step with bash on Linux")
@pytest.mark.parametrize(
    ("previous", "new", "merges"),
    [
        (OLD, NEW, True),
        ("v1.2.3", "v2.0.0", False),
        (OLD, "v2.0.0", False),
        ("v1.2.3", NEW, False),
        (OLD[:7], NEW[:7], False),
        (OLD, f"{NEW}\nv2.0.0", False),
        ("", "", False),
    ],
)
def test_only_commit_to_commit_updates_merge(tmp_path, previous, new, merges):
    gh = tmp_path / "gh"
    gh.write_text('#!/usr/bin/env bash\necho "gh $*"\n')
    gh.chmod(0o755)
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", COMMIT_STEP["run"]],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "PREVIOUS_VERSION": previous,
            "NEW_VERSION": new,
            "PR_URL": PR_URL,
            "PR_HEAD_SHA": "head",
        },
        text=True,
        capture_output=True,
        check=True,
    )
    merge = f"gh pr merge --auto --squash --match-head-commit head {PR_URL}"
    assert (merge in result.stdout) is merges
