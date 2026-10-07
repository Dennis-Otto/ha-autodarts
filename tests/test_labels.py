"""Every label that the issue forms, the release notes and the pull request labels use is
defined in .github/labels.toml, which the issue assistant's Labels workflow applies.

The issue assistant's check in the Integration validation workflow covers the issue
forms and its own labels; this test covers the release notes and pull requests.
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
    notes = yaml.safe_load((ROOT / ".github/release.yml").read_text("utf-8"))
    used |= set(notes["changelog"]["exclude"]["labels"])
    for category in notes["changelog"]["categories"]:
        used |= set(category["labels"]) - {"*"}
    pr_labels = (ROOT / ".github/workflows/pr-labels.yml").read_text("utf-8")
    used |= set(re.search(r"managed=\(([^)]*)\)", pr_labels)[1].split())
    assert used <= defined, used - defined


def test_the_kinds_of_feature_requests_and_feedback_are_never_asked():
    labels = tomllib.loads((ROOT / ".github/labels.toml").read_text(encoding="utf-8"))
    asked = {
        label["name"]
        for label in labels["label"]
        if label["group"] == "type" and label.get("ask", True)
    }
    assert asked == {"bug", "question", "documentation", "compatibility", "maintenance"}
