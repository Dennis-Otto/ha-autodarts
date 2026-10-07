"""The issue assistant's workflows keep Claude read-only and every write in checked code.

Issues come from anyone. These tests fail when a change gives the job that runs
Claude a write permission, a tool that runs code or reaches the network, or when
untrusted text reaches a shell script.
"""

import importlib.util
import re
import shlex
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SPEC = importlib.util.spec_from_file_location(
    "issue_assistant", ROOT / ".github/scripts/issue_assistant.py"
)
assistant = importlib.util.module_from_spec(SPEC)
# Dataclasses look up their module while the script loads.
sys.modules[SPEC.name] = assistant
SPEC.loader.exec_module(assistant)

NAMES = ("issue-assistant.yml", "issue-lifecycle.yml", "labels.yml")


def load(name):
    # PyYAML reads the key "on" as True.
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


ASSISTANT = load("issue-assistant.yml")
JOBS = ASSISTANT["jobs"]
CLAUDE_STEP = next(
    step for step in JOBS["analyze"]["steps"] if step.get("id") == "claude"
)


def steps(name):
    return [
        (job_name, step)
        for job_name, job in load(name)["jobs"].items()
        for step in job["steps"]
    ]


@pytest.mark.parametrize("name", NAMES)
def test_workflows_start_without_permissions_and_only_in_this_repository(name):
    workflow = load(name)
    assert workflow["permissions"] == {}
    for job_name, job in workflow["jobs"].items():
        assert "permissions" in job, job_name
        assert job["timeout-minutes"] <= 20, job_name
    first = next(iter(workflow["jobs"].values()))
    assert "github.repository == 'Dennis-Otto/ha-autodarts'" in first["if"]


@pytest.mark.parametrize("name", NAMES)
def test_actions_are_pinned_and_checkouts_keep_no_credentials(name):
    for job_name, step in steps(name):
        if "uses" not in step:
            continue
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", step["uses"]), step["uses"]
        if step["uses"].startswith("actions/checkout@"):
            assert step["with"]["persist-credentials"] is False, job_name
            assert "ref" not in step["with"], "issue events must run the code of main"


@pytest.mark.parametrize("name", NAMES)
def test_untrusted_text_never_reaches_a_shell_script(name):
    for job_name, step in steps(name):
        script = step.get("run", "")
        # Values reach scripts only through the environment.
        assert "${{" not in script, (job_name, step.get("name"))
        for value in (step.get("env") or {}).values():
            text = str(value)
            assert not re.search(r"github\.event\.(issue|comment)\.(title|body)", text)


def test_only_the_analyze_job_runs_claude_and_only_with_read_permissions():
    runs_claude = {
        name
        for name, job in JOBS.items()
        if any("claude-code-action" in step.get("uses", "") for step in job["steps"])
    }
    assert runs_claude == {"analyze"}
    analyze = JOBS["analyze"]
    assert analyze["permissions"] == {
        "contents": "read",
        "issues": "read",
        "discussions": "read",
    }
    assert analyze["runs-on"] == "ubuntu-24.04-firewall"
    assert analyze["environment"] == {"name": "issue-assistant", "deployment": False}
    for name in ("event", "apply"):
        assert JOBS[name]["runs-on"] == "ubuntu-latest"
        assert "environment" not in JOBS[name]
    # The jobs that write never see the Claude token.
    text = (WORKFLOWS / "issue-assistant.yml").read_text(encoding="utf-8")
    for secret in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"):
        assert text.count(f"secrets.{secret}") == 2
        for name in ("event", "apply"):
            assert secret not in yaml.safe_dump(JOBS[name])


def test_claude_can_only_read_the_checkout():
    inputs = CLAUDE_STEP["with"]
    assert inputs["github_token"] == "${{ github.token }}"
    assert inputs["allowed_non_write_users"] == "*"
    assert "allowed_bots" not in inputs
    assert inputs["prompt"] == "${{ steps.context.outputs.prompt }}"
    arguments = shlex.split(inputs["claude_args"])
    assert "--restricted" in arguments
    assert arguments[arguments.index("--tools") + 1] == "Read,Grep,Glob"
    assert arguments[arguments.index("--permission-prompts") + 1] == "none"
    assert arguments[arguments.index("--json-schema") + 1] == (
        "${{ steps.context.outputs.schema }}"
    )
    for forbidden in (
        "--allowedTools",
        "--allowed-tools",
        "--dangerously-skip-permissions",
        "--permission-mode",
        "--mcp-config",
        "--add-dir",
    ):
        assert forbidden not in arguments
    assert CLAUDE_STEP["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
    assert "show_full_output" not in inputs and "display_report" not in inputs


def test_the_answer_reaches_github_only_through_the_checks():
    assert JOBS["analyze"]["outputs"] == {
        "answer": "${{ steps.claude.outputs.structured_output }}"
    }
    (apply_step,) = [step for step in JOBS["apply"]["steps"] if "run" in step]
    assert apply_step["env"]["RESULT"] == "${{ needs.analyze.outputs.answer }}"
    assert apply_step["run"].startswith(
        "python3 .github/scripts/issue_assistant.py apply"
    )
    assert JOBS["apply"]["needs"] == ["event", "analyze"]
    assert JOBS["apply"]["permissions"] == {
        "contents": "read",
        "issues": "write",
        "discussions": "read",
    }


def test_claude_runs_only_when_a_token_exists_and_the_switch_is_on():
    analyze = JOBS["analyze"]
    assert "vars.ISSUE_ASSISTANT_AI != 'off'" in analyze["if"]
    later = [step for step in analyze["steps"] if step.get("id") != "token"]
    assert all(
        step["if"] == "steps.token.outputs.configured == 'true'" for step in later
    )


def test_the_manual_run_offers_every_task_and_starts_as_a_dry_run():
    inputs = ASSISTANT[True]["workflow_dispatch"]["inputs"]
    assert inputs["mode"]["options"] == list(assistant.MODES)
    assert inputs["dry_run"]["default"] is True
    lifecycle = load("issue-lifecycle.yml")
    assert lifecycle[True]["workflow_dispatch"]["inputs"]["dry_run"]["default"] is True


def test_the_events_the_assistant_handles_trigger_it():
    triggers = ASSISTANT[True]
    assert triggers["issues"]["types"] == ["opened", "edited"]
    assert triggers["issue_comment"]["types"] == ["created"]
    condition = " ".join(JOBS["event"]["if"].split())
    assert "!github.event.issue.pull_request" in condition
    assert "github.event.sender.type != 'Bot'" in condition


def test_the_firewall_allows_only_named_hosts():
    policy = yaml.safe_load(
        (ROOT / ".github" / "egress-firewall.yaml").read_text(encoding="utf-8")
    )
    assert policy["mode"] == "enforce"
    assert "no-default-urls" not in policy
    hosts = policy["allow"]
    assert len(hosts) == len(set(hosts))
    assert all("*" not in host and "/" not in host for host in hosts)
    assert {"api.anthropic.com", "api.github.com"} <= set(hosts)


def test_the_labels_workflow_follows_the_labels_file():
    workflow = load("labels.yml")
    assert workflow[True]["push"] == {
        "branches": ["main"],
        "paths": [".github/labels.toml"],
    }


def test_the_context_folder_is_never_committed():
    assert "/.issue-assistant/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert assistant.CONTEXT == ROOT / ".issue-assistant"


def test_actionlint_knows_the_firewall_runner():
    config = yaml.safe_load((ROOT / ".github" / "actionlint.yaml").read_text("utf-8"))
    assert JOBS["analyze"]["runs-on"] in config["self-hosted-runner"]["labels"]
