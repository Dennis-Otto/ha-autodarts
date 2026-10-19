"""The jobs of the project's own workflows reach only the hosts that their steps need.

Harden-Runner, the first step of every job, blocks every other host: in the bots,
which may write, and in the tests and the images, which run the code of pull
requests. A job that starts no container also runs without sudo and Docker, so that
no step can lift the block, and a job that may write reaches GitHub alone. A new job,
a new host or a job back in audit mode fails here until this list and the comment
of the job say why (docs/development.md#network-of-the-jobs). The workflows that the
blueprint keeps follow its own rules."""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
PROJECT_WORKFLOWS = (
    "e2e.yml",
    "screenshots.yml",
    "translations.yml",
    "visual-comment.yml",
    "visual.yml",
)

GITHUB = {"api.github.com", "github.com"}
# Home Assistant from GitHub's registry, Playwright from Microsoft's.
HOME_ASSISTANT = {"ghcr.io", "pkg-containers.githubusercontent.com"}
PLAYWRIGHT = {"mcr.microsoft.com", "*.data.mcr.microsoft.com"}
PYTHON_PACKAGES = {"pypi.org", "files.pythonhosted.org"}
BROWSER_TEST = {
    "github.com",
    *HOME_ASSISTANT,
    *PLAYWRIGHT,
    *PYTHON_PACKAGES,
    # axe-core of package-lock.json
    "registry.npmjs.org",
}
IMAGES = {
    "github.com",
    *HOME_ASSISTANT,
    *PLAYWRIGHT,
    *PYTHON_PACKAGES,
    # pngquant of tests/e2e/pngquant.sh
    "launchpad.net",
    "launchpadlibrarian.net",
    # the icons of Home Assistant's other integrations, which the images show
    "brands.home-assistant.io",
}
COMPARISON = {"github.com", *PYTHON_PACKAGES}

HOSTS = {
    ("e2e.yml", "changes"): {"api.github.com"},
    ("e2e.yml", "scenario"): {"github.com", *HOME_ASSISTANT},
    ("e2e.yml", "browser"): BROWSER_TEST,
    # The explanations of the PR coach, which the gate checks out after a failure.
    ("e2e.yml", "gate"): {"github.com"},
    ("e2e.yml", "live-demo"): {"github.com", *PLAYWRIGHT, *PYTHON_PACKAGES},
    ("e2e.yml", "beta"): BROWSER_TEST,
    ("screenshots.yml", "render"): IMAGES,
    ("screenshots.yml", "collect"): COMPARISON,
    ("screenshots.yml", "pull-request"): GITHUB,
    # The recording of the live demo, by the integration in the Home Assistant of
    # the tests, whose packages it installs.
    ("screenshots.yml", "timeline"): {"github.com", *PYTHON_PACKAGES},
    ("translations.yml", "issues"): GITHUB,
    ("visual-comment.yml", "comment"): {"api.github.com"},
    ("visual.yml", "render"): IMAGES,
    ("visual.yml", "compare"): COMPARISON,
}
# The scripts that start containers: Home Assistant, the simulated board, Playwright.
CONTAINERS = re.compile(
    r"\bbash tests/e2e/(run|browser|screenshots|visual|demo|live_demo)\.sh\b"
)


def jobs() -> dict[tuple[str, str], dict]:
    """Every job of the project's own workflows, by workflow and job."""
    found = {}
    for name in PROJECT_WORKFLOWS:
        workflow = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
        for job, definition in workflow["jobs"].items():
            found[(name, job)] = definition
    return found


JOBS = jobs()


def harden_runner(job: dict) -> dict:
    """The settings of Harden-Runner, the first step of the job."""
    first = job["steps"][0]
    assert first.get("uses", "").startswith("step-security/harden-runner@")
    return first.get("with", {})


def allowed(settings: dict) -> list[str]:
    """The hosts of allowed-endpoints, each of which must name port 443."""
    endpoints = settings.get("allowed-endpoints", "").split()
    assert all(endpoint.endswith(":443") for endpoint in endpoints), endpoints
    return [endpoint.removesuffix(":443") for endpoint in endpoints]


def test_every_job_has_its_hosts_here():
    assert set(JOBS) == set(HOSTS)


@pytest.mark.parametrize("key", sorted(HOSTS), ids="/".join)
def test_harden_runner_blocks_every_host_that_the_job_does_not_need(key):
    settings = harden_runner(JOBS[key])
    assert settings["egress-policy"] == "block"
    hosts = allowed(settings)
    assert len(hosts) == len(set(hosts)), f"{key} names a host twice: {hosts}"
    assert set(hosts) == HOSTS[key]


@pytest.mark.parametrize("key", sorted(HOSTS), ids="/".join)
def test_a_job_without_containers_runs_without_sudo_and_docker(key):
    job = JOBS[key]
    containers = any(CONTAINERS.search(step.get("run", "")) for step in job["steps"])
    # Docker needs both; every other job gives them up, so no step lifts the block.
    assert harden_runner(job).get("disable-sudo-and-containers", False) is (
        not containers
    )


def may_write(job: dict) -> bool:
    """Whether the job holds a token that writes or the secrets of an environment."""
    return "environment" in job or "write" in job.get("permissions", {}).values()


WRITING = sorted(key for key, job in JOBS.items() if may_write(job))


def test_the_bots_are_the_jobs_that_may_write():
    assert WRITING == [
        ("screenshots.yml", "pull-request"),
        ("translations.yml", "issues"),
        ("visual-comment.yml", "comment"),
    ]


@pytest.mark.parametrize("key", WRITING, ids="/".join)
def test_a_job_that_may_write_reaches_github_alone(key):
    settings = harden_runner(JOBS[key])
    assert set(allowed(settings)) <= GITHUB
    assert settings.get("disable-sudo-and-containers") is True
