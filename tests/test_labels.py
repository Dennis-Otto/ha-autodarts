"""Every label that the issue forms, the pull request title check and the bots use is
defined in .github/labels.toml, which the issue assistant's Labels workflow applies.

The issue assistant's check in the Lint workflow covers the issue forms and its own
labels; this test covers the pull requests and the bots of the blueprint.
"""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_every_label_in_use_is_defined():
    labels = tomllib.loads((ROOT / ".github/labels.toml").read_text(encoding="utf-8"))
    defined = {label["name"] for label in labels["label"]}
    used = set()
    for path in (ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml"):
        used |= set(yaml.safe_load(path.read_text("utf-8")).get("labels", []))
    titles = (ROOT / ".github/workflows/pull-request-title.yml").read_text("utf-8")
    used |= set(re.search(r"managed=\(([^)]*)\)", titles)[1].split())
    # The release bot, the branch bot and Dependabot.
    used |= {"autorelease: pending", "autorelease: tagged", "merge-conflict"}
    used |= {"dependencies", "github_actions", "python", "docker", "javascript"}
    assert used <= defined, used - defined


def test_the_kinds_of_feature_requests_and_feedback_are_never_asked():
    labels = tomllib.loads((ROOT / ".github/labels.toml").read_text(encoding="utf-8"))
    asked = {
        label["name"]
        for label in labels["label"]
        if label["group"] == "type" and label.get("ask", True)
    }
    assert asked == {"bug", "question", "documentation", "compatibility", "maintenance"}
