"""The issue forms are valid GitHub issue forms, so none of them silently disappears.

GitHub hides a form with an invalid body from the "new issue" page without an
error, so the structure is checked here.
"""

from pathlib import Path

import pytest
import yaml

FORMS = sorted((Path(__file__).parents[1] / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
FORMS = [form for form in FORMS if form.name != "config.yml"]
TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes"}


@pytest.mark.parametrize("form", FORMS, ids=lambda path: path.name)
def test_issue_form_is_valid(form):
    data = yaml.safe_load(form.read_text(encoding="utf-8"))
    assert data["name"] and data["description"]
    body = data["body"]
    assert any(field["type"] != "markdown" for field in body)
    ids = [field["id"] for field in body if "id" in field]
    assert len(ids) == len(set(ids)), "field ids must be unique"
    for field in body:
        assert field["type"] in TYPES
        if field["type"] == "markdown":
            assert field["attributes"]["value"].strip()
            continue
        assert "id" in field and field["attributes"]["label"]
        if field["type"] == "dropdown":
            options = field["attributes"]["options"]
            assert options and len(options) == len(set(options))
        if field["type"] == "checkboxes":
            assert all(option["label"] for option in field["attributes"]["options"])


def test_the_tester_report_asks_the_questions_of_the_tester_call():
    form = next(form for form in FORMS if form.name == "tester_report.yml")
    ids = {field.get("id") for field in yaml.safe_load(form.read_text("utf-8"))["body"]}
    assert {"board_software", "tried", "helped", "problems", "missing"} <= ids
