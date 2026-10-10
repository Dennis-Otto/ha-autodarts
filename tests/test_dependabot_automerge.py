"""Keep the privileged Dependabot auto-merge narrow and free of repository code."""

from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).parents[1] / ".github/workflows"
JOB = yaml.safe_load((WORKFLOWS / "dependabot-automerge.yml").read_text())["jobs"][
    "auto-merge"
]


def test_privileged_job_runs_no_repository_code():
    # Harden-Runner records the network traffic; no step checks out the pull request.
    actions = [step["uses"].split("@")[0] for step in JOB["steps"] if "uses" in step]
    assert actions == ["step-security/harden-runner", "dependabot/fetch-metadata"]


def test_every_merge_is_bound_to_the_checked_head_commit():
    # Renovate merges the new commits of the HACS and hassfest actions itself; the
    # one merge left is that of Dependabot's routine updates.
    runs = [step.get("run", "") for step in JOB["steps"]]
    merges = [run for run in runs if "gh pr merge" in run]
    assert len(merges) == 1
    assert all('--match-head-commit "$PR_HEAD_SHA"' in run for run in merges)
