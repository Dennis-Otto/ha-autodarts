"""The issue assistant's workflows keep the AI engine read-only and every write in checked code.

Issues come from anyone. These tests fail when a change gives the job that runs an
engine a write permission, a tool that runs code or reaches the network, when an
engine has no rules here, or when untrusted text reaches a shell script.
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
ANALYZE = JOBS["analyze"]
STEPS = {step.get("id"): step for step in ANALYZE["steps"]}


def claude_reads_only(step):
    inputs = step["with"]
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
    assert step["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
    assert "show_full_output" not in inputs and "display_report" not in inputs


# Every engine of the script needs its rules here: the action of its step, its
# secrets, the output with its answer and the check that keeps it read-only.
ENGINE_RULES = {
    "claude": {
        "action": "anthropics/claude-code-action",
        "secrets": ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"),
        "output": "structured_output",
        "reads_only": claude_reads_only,
    },
}


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


def test_every_engine_has_rules_a_step_and_credentials():
    assert set(ENGINE_RULES) == set(assistant.ENGINES)
    credentials = STEPS["engine"]["env"]
    for engine, rules in ENGINE_RULES.items():
        step = STEPS[engine]
        assert step["uses"].split("@")[0] == rules["action"]
        assert step["if"] == (
            "steps.engine.outputs.ready == 'true' && "
            f"steps.engine.outputs.engine == '{engine}'"
        )
        expected = " || ".join(f"secrets.{secret} != ''" for secret in rules["secrets"])
        assert credentials[f"CREDENTIALS_{engine.upper()}"] == f"${{{{ {expected} }}}}"


@pytest.mark.parametrize("engine", sorted(ENGINE_RULES))
def test_each_engine_can_only_read_the_checkout(engine):
    ENGINE_RULES[engine]["reads_only"](STEPS[engine])


def test_only_the_analyze_job_runs_an_engine_and_only_with_read_permissions():
    actions = {rules["action"] for rules in ENGINE_RULES.values()}
    runs_engine = {
        name
        for name, job in JOBS.items()
        if any(step.get("uses", "").split("@")[0] in actions for step in job["steps"])
    }
    assert runs_engine == {"analyze"}
    assert ANALYZE["permissions"] == {
        "contents": "read",
        "issues": "read",
        "discussions": "read",
    }
    assert ANALYZE["runs-on"] == "ubuntu-24.04-firewall"
    assert ANALYZE["environment"] == {"name": "issue-assistant", "deployment": False}
    for name in ("event", "apply"):
        assert JOBS[name]["runs-on"] == "ubuntu-latest"
        assert "environment" not in JOBS[name]
    # The jobs that write never see an engine's secret.
    for rules in ENGINE_RULES.values():
        for secret in rules["secrets"]:
            for name in ("event", "apply"):
                assert secret not in yaml.safe_dump(JOBS[name])


def test_the_script_chooses_the_engine():
    step = STEPS["engine"]
    assert step["run"] == "python3 .github/scripts/issue_assistant.py engine"
    assert step["env"]["ISSUE_ASSISTANT_ENGINE"] == "${{ vars.ISSUE_ASSISTANT_ENGINE }}"
    assert "vars.ISSUE_ASSISTANT_AI != 'off'" in ANALYZE["if"]
    assert STEPS["context"]["if"] == "steps.engine.outputs.ready == 'true'"
    order = [step.get("id") for step in ANALYZE["steps"]]
    assert (
        order.index("engine")
        < order.index("context")
        < order.index(min(ENGINE_RULES, key=order.index))
    )


def test_the_answer_reaches_github_only_through_the_checks():
    answers = " || ".join(
        f"steps.{engine}.outputs.{rules['output']}"
        for engine, rules in ENGINE_RULES.items()
    )
    assert ANALYZE["outputs"] == {
        "engine": "${{ steps.engine.outputs.engine }}",
        "answer": f"${{{{ {answers} }}}}",
    }
    (apply_step,) = [step for step in JOBS["apply"]["steps"] if "run" in step]
    assert apply_step["env"]["RESULT"] == "${{ needs.analyze.outputs.answer }}"
    assert apply_step["env"]["ISSUE_ASSISTANT_ENGINE"] == (
        "${{ needs.analyze.outputs.engine }}"
    )
    assert apply_step["run"].startswith(
        "python3 .github/scripts/issue_assistant.py apply"
    )
    assert JOBS["apply"]["needs"] == ["event", "analyze"]
    assert JOBS["apply"]["permissions"] == {
        "contents": "read",
        "issues": "write",
        "discussions": "read",
    }


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
    assert ANALYZE["runs-on"] in config["self-hosted-runner"]["labels"]


# Names of AI vendors and their products; only the engine table may name one.
VENDORS = re.compile(r"Claude|Anthropic|OpenAI|Codex|Copilot|GPT|Gemini", re.IGNORECASE)


def test_only_the_engine_table_names_a_vendor():
    source = (ROOT / ".github/scripts/issue_assistant.py").read_text(encoding="utf-8")
    table = re.search(r"^ENGINES = \{.*?\}$", source, re.MULTILINE | re.DOTALL)
    assert table and VENDORS.search(table[0])
    rest = re.sub(
        r"^DEFAULT_ENGINE = .*$", "", source.replace(table[0], ""), flags=re.M
    )
    assert not VENDORS.search(rest)
    for prompt in (ROOT / ".github/issue-assistant").glob("*.md"):
        assert not VENDORS.search(prompt.read_text(encoding="utf-8")), prompt.name


def test_the_users_learn_which_engine_reads_their_issue():
    engine = assistant.ENGINES[assistant.DEFAULT_ENGINE]
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    german = (ROOT / "docs/de/fehlerbehebung.md").read_text(encoding="utf-8")
    assert f"{engine.name}, an AI by {engine.vendor}" in support
    assert f"{engine.name}, eine KI von {engine.vendor}" in german
    # The workflow runs the default engine unless the variable chooses another.
    assert "ISSUE_ASSISTANT_ENGINE: ${{ vars.ISSUE_ASSISTANT_ENGINE }}" in (
        WORKFLOWS / "issue-assistant.yml"
    ).read_text(encoding="utf-8")
