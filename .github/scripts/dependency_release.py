"""Publish merged dependency updates through protected, fully checked release PRs,
and the version a merged release PR brings to main.

Uses a repository-scoped GitHub App token for release branches and PRs so GitHub
starts normal PR checks. No candidate code execution, main pushes or bypasses.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path

MANIFEST = "custom_components/autodarts/manifest.json"
CHANGELOG = "CHANGELOG.md"
# The version PRs of the dependency releases, which publish themselves.
DEPENDENCY_BRANCH = "automation/dependency-release-v"
# A merged release PR waits this long for the checks of main, the end-to-end tests too.
MAIN_CHECKS_TIMEOUT = 2700
MARKER = "<!-- autodarts-automated-dependency-release -->"
WORKFLOWS = (
    "tests.yml",
    "validate.yml",
    "codeql.yml",
    "secret-scan.yml",
    "e2e.yml",
    "dependency-review.yml",
)
E2E_CHECKS = {"e2e (Board Manager 1)", "e2e (Board Manager 2)"}
CHECKS = {
    "test",
    "hacs",
    "hassfest",
    "workflow-lint",
    "codeql",
    "gitleaks",
    *E2E_CHECKS,
    "dependency-review",
}
MAIN_CHECKS = {
    "tests.yml": {"test"},
    "validate.yml": {"hacs", "hassfest", "workflow-lint"},
    "codeql.yml": {"codeql"},
    "secret-scan.yml": {"gitleaks"},
    "e2e.yml": E2E_CHECKS,
}
# Only these paths reach users; updates of tests and CI alone never release.
SHIPPED = ("custom_components/", "hacs.json")


class GitHub:
    def __init__(self, repository: str):
        self.repository = repository

    def api(self, path, *, method=None, data=None, pages=False, release_write=False):
        command = ["gh", "api", f"repos/{self.repository}/{path}"]
        if method:
            command += ["--method", method]
        if pages:
            command += ["--paginate", "--slurp"]
        if data is not None:
            command += ["--input", "-"]
        environment = os.environ.copy()
        if release_write:
            if not environment.get("GH_RELEASE_TOKEN"):
                raise RuntimeError(
                    "Configure the release GitHub App before publishing automatically."
                )
            environment["GH_TOKEN"] = environment["GH_RELEASE_TOKEN"]
        environment.pop("GH_RELEASE_TOKEN", None)
        result = subprocess.run(
            command,
            input=json.dumps(data) if data is not None else None,
            text=True,
            capture_output=True,
            check=True,
            env=environment,
        )
        return json.loads(result.stdout) if result.stdout.strip() else None

    def items(self, path, key=None):
        pages = self.api(path, pages=True)
        return [item for page in pages for item in (page[key] if key else page)]

    def manifest(self, ref):
        result = self.api(f"contents/{MANIFEST}?ref={ref}")
        return json.loads(base64.b64decode(result["content"])), result["sha"]

    def text(self, path, ref):
        result = self.api(f"contents/{path}?ref={ref}")
        return base64.b64decode(result["content"]).decode("utf-8")

    def dispatch(self, workflow, ref, inputs=None):
        self.api(
            f"actions/workflows/{workflow}/dispatches",
            method="POST",
            data={"ref": ref, "inputs": inputs or {}},
        )


def version_tuple(version):
    value = version.removeprefix("v")
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", value):
        raise ValueError(
            f"Automatic maintenance releases require an x.y.z version: {version}"
        )
    return tuple(map(int, value.split(".")))


def release_tuple(tag):
    """The x.y.z of a release tag; a prerelease such as v1.8.0-rc.1 counts as 1.8.0."""
    return version_tuple(tag.split("-", 1)[0])


def next_version(version):
    major, minor, patch = version_tuple(version)
    return f"{major}.{minor}.{patch + 1}"


def dependency_prs(pulls, commits, repository):
    return [
        pr
        for pr in pulls
        if (
            pr.get("merged_at")
            and pr["merge_commit_sha"] in commits
            and pr["user"]["login"] == "dependabot[bot]"
            and pr["base"]["ref"] == "main"
            and (pr["head"].get("repo") or {}).get("full_name") == repository
        )
    ]


def changed_files(github, pr):
    return [
        f["filename"] for f in github.items(f"pulls/{pr['number']}/files?per_page=100")
    ]


def ships_integration(files):
    return any(name.startswith(SHIPPED) for name in files)


def owned_release_pr(pr, branch, repository):
    authors = {"github-actions[bot]"}  # Resume version PRs from the earlier workflow.
    if slug := os.environ.get("GH_RELEASE_APP_SLUG"):
        authors.add(f"{slug}[bot]")
    return (
        pr["user"]["login"] in authors
        and pr["head"]["ref"] == branch
        and (pr["head"].get("repo") or {}).get("full_name") == repository
        and pr["base"]["ref"] == "main"
        and MARKER in (pr.get("body") or "")
    )


def validate_version_only(base, candidate, version, files):
    expected = dict(base, version=version)
    if candidate != expected or files != [MANIFEST]:
        raise RuntimeError(
            "Release PR must change only the manifest version; refusing to merge."
        )


def latest_checks(runs):
    result = {}
    for run in runs:
        if run["name"] in CHECKS and run["app"]["id"] == 15368:
            if run["id"] > result.get(run["name"], {}).get("id", 0):
                result[run["name"]] = run
    return result


def checks_ready(runs, previous):
    current = latest_checks(runs)
    for name in CHECKS:
        check = current.get(name)
        if not check or check["id"] <= previous.get(name, {}).get("id", 0):
            return False
        if check["status"] != "completed":
            return False
        if check["conclusion"] != "success":
            raise RuntimeError(f"Required check failed: {name} ({check['conclusion']})")
    return True


def pr_workflow_runs(runs, number, head_sha):
    """Select only actual PR runs, never unrelated workflow_dispatch checks."""
    selected = {}
    for run in runs:
        workflow = run["path"].removeprefix(".github/workflows/")
        if (
            run["event"] == "pull_request"
            and run["head_sha"] == head_sha
            and workflow in WORKFLOWS
            and any(pr["number"] == number for pr in run["pull_requests"])
            and run["id"] > selected.get(workflow, {}).get("id", 0)
        ):
            selected[workflow] = run
    return selected if set(selected) == set(WORKFLOWS) else None


def start_pr_checks(github, number, head_sha):
    # App-authored changes start real PR checks without a GITHUB_TOKEN approval gate.
    # GitHub can take several minutes to register those runs after creating a PR.
    summary(
        f"Waiting up to 30 minutes for GitHub to register PR #{number}'s workflows."
    )
    runs = wait_until(
        lambda: pr_workflow_runs(
            github.items(
                f"actions/runs?event=pull_request&head_sha={head_sha}&per_page=100",
                "workflow_runs",
            ),
            number,
            head_sha,
        ),
        "PR workflow registration",
        timeout=1800,
    )
    attempts = {}
    for run in runs.values():
        current = github.api(f"actions/runs/{run['id']}")
        attempt = current["run_attempt"]
        if current["conclusion"] == "action_required":
            raise RuntimeError(
                "PR checks require approval. Verify the release App configuration; "
                "never substitute separately dispatched checks."
            )
        elif current["status"] == "completed" and current["conclusion"] != "success":
            github.api(f"actions/runs/{run['id']}/rerun", method="POST")
            attempt += 1
        attempts[run["id"]] = attempt
    return attempts


def pr_checks_ready(github, attempts):
    checks = []
    for run_id, attempt in attempts.items():
        run = github.api(f"actions/runs/{run_id}")
        if (
            run["run_attempt"] < attempt
            or run["status"] != "completed"
            or run["conclusion"] == "action_required"
        ):
            return False
        if run["conclusion"] != "success":
            raise RuntimeError(
                f"Required PR workflow failed: {run['path']} ({run['conclusion']})"
            )
        checks.extend(
            github.items(
                f"check-suites/{run['check_suite_id']}/check-runs?per_page=100&filter=latest",
                "check_runs",
            )
        )
    return checks_ready(checks, {})


def merge_ready(github, number, head_sha, base_sha):
    """Wait for GitHub's aggregate protection result, including parallel push CI."""
    pr = github.api(f"pulls/{number}")
    if pr["head"]["sha"] != head_sha or pr["state"] != "open":
        raise RuntimeError(
            "Release candidate changed while waiting for merge readiness."
        )
    if github.api("git/ref/heads/main")["object"]["sha"] != base_sha:
        return True  # Let the caller update the branch and validate the new candidate.
    if pr.get("mergeable") is False:
        raise RuntimeError("Release PR has conflicts; resolve them before retrying.")
    return pr.get("mergeable_state") == "clean"


def main_checks_ready(github, sha):
    """Require successful push checks for the exact commit being published."""
    selected = {}
    for run in github.items(
        f"actions/runs?event=push&branch=main&head_sha={sha}&per_page=100",
        "workflow_runs",
    ):
        workflow = run["path"].removeprefix(".github/workflows/")
        if (
            run["event"] == "push"
            and run["head_branch"] == "main"
            and run["head_sha"] == sha
            and workflow in MAIN_CHECKS
            and run["id"] > selected.get(workflow, {}).get("id", 0)
        ):
            selected[workflow] = run
    if set(selected) != set(MAIN_CHECKS):
        return False
    for workflow, run in selected.items():
        if run["status"] != "completed":
            return False
        if run["conclusion"] != "success":
            raise RuntimeError(
                f"Main workflow {workflow}: {run['conclusion']}; release blocked."
            )
        checks = latest_checks(
            github.items(
                f"check-suites/{run['check_suite_id']}/check-runs?per_page=100&filter=latest",
                "check_runs",
            )
        )
        for name in MAIN_CHECKS[workflow]:
            check = checks.get(name)
            if not check or check["status"] != "completed":
                return False
            if check["conclusion"] != "success":
                raise RuntimeError(
                    f"Main check {name}: {check['conclusion']}; release blocked."
                )
    return True


def wait_until(predicate, description, timeout=900):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(15)
    raise TimeoutError(f"Timed out waiting for {description}; rerun to resume.")


def summary(message):
    print(message, flush=True)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a") as output:
            output.write(message + "\n\n")


def prepare_pr(github, version, base_sha, dependencies, pulls):
    branch = f"automation/dependency-release-v{version}"
    matches = [pr for pr in pulls if pr["head"]["ref"] == branch]
    for pr in matches:
        if not owned_release_pr(pr, branch, github.repository):
            raise RuntimeError(
                f"Unexpected owner or contents for release PR #{pr['number']}."
            )
        if pr.get("merged_at") or pr["state"] == "open":
            return pr
    if matches:
        raise RuntimeError(
            "The release PR was closed without merging; reopen it to resume."
        )

    refs = github.api(f"git/matching-refs/heads/{branch}")
    if not any(ref["ref"] == f"refs/heads/{branch}" for ref in refs):
        github.api(
            "git/refs",
            method="POST",
            data={"ref": f"refs/heads/{branch}", "sha": base_sha},
            release_write=True,
        )
    base, _ = github.manifest(base_sha)
    candidate, blob_sha = github.manifest(branch)
    if candidate == base:
        candidate["version"] = version
        content = base64.b64encode(
            (json.dumps(candidate, indent=2) + "\n").encode()
        ).decode()
        # The Contents API creates a GitHub-signed bot commit. Never impersonate
        # a maintainer or store a signing key in the workflow.
        github.api(
            f"contents/{MANIFEST}",
            method="PUT",
            data={
                "branch": branch,
                "sha": blob_sha,
                "content": content,
                "message": f"chore(release): prepare v{version}",
            },
            release_write=True,
        )
    comparison = github.api(f"compare/{base_sha}...{branch}")
    candidate, _ = github.manifest(branch)
    validate_version_only(
        base, candidate, version, [f["filename"] for f in comparison["files"]]
    )
    references = ", ".join(f"#{pr['number']}" for pr in dependencies)
    body = (
        f"{MARKER}\n\nPrepare maintenance release **v{version}** after merged Dependabot "
        f"updates: {references}. Only the integration manifest version changes here.\n\n"
        "The release workflow runs every required check and merges this PR through normal "
        "branch protection. It then publishes release notes in the existing stable or "
        "prerelease channel. Closing this PR without merging pauses this release."
    )
    pr = github.api(
        "pulls",
        method="POST",
        data={
            "head": branch,
            "base": "main",
            "title": f"chore(release): prepare v{version}",
            "body": body,
        },
        release_write=True,
    )
    github.api(
        f"issues/{pr['number']}/labels",
        method="POST",
        data={"labels": ["release"]},
        release_write=True,
    )
    return pr


def validate_and_merge(github, pr, version):
    number = pr["number"]
    branch = pr["head"]["ref"]
    for _ in range(3):
        pr = github.api(f"pulls/{number}")
        if pr.get("merged"):
            return pr["merge_commit_sha"]
        if pr["state"] != "open" or not owned_release_pr(pr, branch, github.repository):
            raise RuntimeError(
                "Release PR was closed or changed; refusing automatic publication."
            )
        base_sha = github.api("git/ref/heads/main")["object"]["sha"]
        head_sha = pr["head"]["sha"]
        if github.api(f"compare/{base_sha}...{head_sha}")["status"] != "ahead":
            github.api(
                f"pulls/{number}/update-branch",
                method="PUT",
                data={"expected_head_sha": head_sha},
                release_write=True,
            )
            wait_until(
                lambda: github.api(f"pulls/{number}")["head"]["sha"] != head_sha,
                "release branch update",
                timeout=120,
            )
            continue
        base, _ = github.manifest(base_sha)
        candidate, _ = github.manifest(head_sha)
        files = [
            f["filename"] for f in github.items(f"pulls/{number}/files?per_page=100")
        ]
        validate_version_only(base, candidate, version, files)
        attempts = start_pr_checks(github, number, head_sha)
        summary(
            f"Running required checks for [release PR #{number}]({pr['html_url']})."
        )
        wait_until(
            lambda: pr_checks_ready(github, attempts),
            "required release PR checks",
        )
        wait_until(
            lambda: merge_ready(github, number, head_sha, base_sha),
            "GitHub branch protection and parallel checks",
        )
        if github.api("git/ref/heads/main")["object"]["sha"] != base_sha:
            continue  # Rebase through the API and rerun checks on the new candidate.
        merged = github.api(
            f"pulls/{number}/merge",
            method="PUT",
            data={
                "sha": head_sha,
                "merge_method": "squash",
                "commit_title": f"chore(release): prepare v{version} (#{number})",
            },
            release_write=True,
        )
        if not merged.get("merged"):
            raise RuntimeError("GitHub did not merge the checked release PR.")
        return merged["sha"]
    raise RuntimeError(
        "Main kept changing; rerun to validate the release PR against the latest main."
    )


def publish(github, version, prerelease, dependencies):
    introduction = (
        "## Maintenance update (prerelease)\n\n"
        "This prerelease contains dependency updates of the integration. "
        "HACS offers prereleases once the beta switch of this repository is on."
        if prerelease
        else "## Maintenance update\n\nThis version contains dependency updates of the integration."
    )
    introduction += "\n\nThe generated changelog below lists every change."
    # A failed publishing run can be resumed without creating another version PR.
    github.dispatch(
        "release.yml",
        "main",
        {
            "version": version,
            "prerelease": prerelease,
            "draft": False,
            "introduction": introduction,
        },
    )
    await_release(github, version, prerelease)


def await_release(github, version, prerelease):
    """Wait until the release workflow published the version from its manifest."""
    tag = f"v{version}"

    def published():
        releases = github.items("releases?per_page=100")
        matches = [r for r in releases if r["tag_name"] == tag and not r["draft"]]
        if not matches:
            return None
        release = matches[0]
        if release["prerelease"] != prerelease:
            raise RuntimeError("Published release channel changed unexpectedly.")
        manifest, _ = github.manifest(tag)
        if manifest["version"] != version:
            raise RuntimeError("Published tag and integration version do not match.")
        return release

    release = wait_until(published, f"publication of {tag}", timeout=900)
    summary(f"Published [{tag}]({release['html_url']}) with generated release notes.")


def changelog_section(text, version):
    """The notes of a version in the changelog: its section, without the heading."""
    lines = text.splitlines()
    heading = f"## {version}"
    if heading not in lines:
        return None
    start = lines.index(heading) + 1
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end]).strip() or None


def main_head(github):
    return github.api("git/ref/heads/main")["object"]["sha"]


def settled_main(github, timeout=MAIN_CHECKS_TIMEOUT):
    """The head of main once all its push checks passed; main may move on meanwhile."""
    deadline = time.monotonic() + timeout
    head = main_head(github)
    while True:
        wait_until(
            lambda sha=head: main_checks_ready(github, sha),
            f"all main commit checks of {head[:7]}",
            timeout=max(deadline - time.monotonic(), 1),
        )
        latest = main_head(github)
        if latest == head:
            return head
        head = latest


def release_commit(github, sha):
    """Publish the version a merged release PR brought to main.

    The merge is the approval: once every check of main passed, the release
    workflow publishes the version with its changelog section. Dependency
    releases publish themselves; prereleases and drafts stay manual.
    """
    version = github.manifest(sha)[0]["version"]
    parent = github.api(f"commits/{sha}")["parents"][0]["sha"]
    if github.manifest(parent)[0]["version"] == version:
        summary(f"{sha[:7]} keeps version {version}. Nothing to publish.")
        return
    pulls = github.api(f"commits/{sha}/pulls") or []
    if any(pr["head"]["ref"].startswith(DEPENDENCY_BRANCH) for pr in pulls):
        summary(f"The dependency release of {version} publishes itself.")
        return
    try:
        target = version_tuple(version)
    except ValueError:
        summary(f"{version} is a prerelease: publish it with Release integration.")
        return
    tag = f"v{version}"
    releases = github.items("releases?per_page=100")
    existing = [r for r in releases if r["tag_name"] == tag]
    if any(not r["draft"] for r in existing):
        summary(f"{tag} is already published.")
        return
    if existing:
        raise RuntimeError(
            f"A draft of {tag} is left from an earlier run; delete it and rerun."
        )
    if any(release_tuple(r["tag_name"]) > target for r in releases if not r["draft"]):
        raise RuntimeError(
            f"{tag} is older than a published release; refusing to publish."
        )
    notes = changelog_section(github.text(CHANGELOG, sha), version)
    if notes is None:
        raise RuntimeError(
            f"{CHANGELOG} has no '## {version}' section; add it and rerun."
        )
    # The release PR stays out of its own notes, like the dependency version PRs.
    for pr in pulls:
        github.api(
            f"issues/{pr['number']}/labels", method="POST", data={"labels": ["release"]}
        )
    head = settled_main(github)
    if github.manifest(head)[0]["version"] != version:
        raise RuntimeError(
            f"Main moved on to another version than {version}; publish it by hand."
        )
    github.dispatch(
        "release.yml",
        "main",
        {
            "version": version,
            "prerelease": False,
            "draft": False,
            "introduction": notes
            + "\n\nThe generated changelog below lists every pull request.",
        },
    )
    await_release(github, version, False)


def run(github):
    releases = [r for r in github.items("releases?per_page=100") if not r["draft"]]
    if not releases:
        summary(
            "No published release yet. Publish the first version manually to choose the release channel."
        )
        return
    latest = max(releases, key=lambda r: version_tuple(r["tag_name"]))
    version = next_version(latest["tag_name"])
    base_sha = github.api("git/ref/heads/main")["object"]["sha"]
    pages = github.api(
        f"compare/{latest['tag_name']}...{base_sha}?per_page=100", pages=True
    )
    if pages[0]["status"] == "identical":
        summary("No unreleased commits.")
        return
    if pages[0]["status"] != "ahead":
        raise RuntimeError(
            "Latest release is not an ancestor of main; refusing automatic publication."
        )
    commits = {c["sha"] for page in pages for c in page["commits"]}
    pulls = github.items("pulls?state=all&base=main&per_page=100")
    dependencies = dependency_prs(pulls, commits, github.repository)
    if not dependencies:
        summary("No merged, unreleased Dependabot updates. No release needed.")
        return
    dependencies = [
        pr for pr in dependencies if ships_integration(changed_files(github, pr))
    ]
    if not dependencies:
        summary(
            "The unreleased Dependabot updates change only tests or CI. No release needed."
        )
        return
    manifest, _ = github.manifest(base_sha)
    branch = f"automation/dependency-release-v{version}"
    resumed = any(
        owned_release_pr(pr, branch, github.repository)
        and pr.get("merged_at")
        and pr["merge_commit_sha"] in commits
        for pr in pulls
    )
    expected = version if resumed else latest["tag_name"].removeprefix("v")
    if manifest["version"] != expected:
        raise RuntimeError(
            "Main has a manually changed version; publish it manually before resuming dependency releases."
        )
    pr = prepare_pr(github, version, base_sha, dependencies, pulls)
    validate_and_merge(github, pr, version)
    publish(github, version, latest["prerelease"], dependencies)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-commit",
        help="Wait for all main-branch CI checks on this commit, without publishing.",
    )
    parser.add_argument(
        "--release-commit",
        help="Publish the version this main commit brought, once main passed its checks.",
    )
    args = parser.parse_args()
    try:
        github = GitHub(os.environ["GH_REPO"])
        if args.release_commit:
            if not re.fullmatch(r"[0-9a-f]{40}", args.release_commit):
                parser.error("--release-commit requires a full commit SHA")
            release_commit(github, args.release_commit)
        elif args.verify_commit:
            if not re.fullmatch(r"[0-9a-f]{40}", args.verify_commit):
                parser.error("--verify-commit requires a full commit SHA")
            wait_until(
                lambda: main_checks_ready(github, args.verify_commit),
                "all main commit checks",
            )
            summary(f"All main commit checks passed for {args.verify_commit}.")
        else:
            run(github)
    except subprocess.CalledProcessError as error:
        print(error.stderr, flush=True)
        raise
