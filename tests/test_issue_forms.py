"""The issue and discussion forms are valid GitHub forms, so none silently disappears.

GitHub hides a form with an invalid body from the "new issue" page without an
error, and starts a discussion without its form, so the structure is checked here.
"""

from pathlib import Path

import pytest
import yaml

GITHUB = Path(__file__).parents[1] / ".github"
FORMS = sorted((GITHUB / "ISSUE_TEMPLATE").glob("*.yml"))
FORMS = [form for form in FORMS if form.name != "config.yml"]
# A discussion form is named after the slug of its category, such as show-and-tell.
DISCUSSION_FORMS = sorted((GITHUB / "DISCUSSION_TEMPLATE").glob("*.yml"))
DISCUSSION_KEYS = {"title", "labels", "body"}
TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes"}


@pytest.mark.parametrize("form", FORMS, ids=lambda path: path.name)
def test_issue_form_is_valid(form):
    data = yaml.safe_load(form.read_text(encoding="utf-8"))
    assert data["name"] and data["description"]
    assert_valid_body(data["body"])


@pytest.mark.parametrize("form", DISCUSSION_FORMS, ids=lambda path: path.name)
def test_discussion_form_is_valid(form):
    data = yaml.safe_load(form.read_text(encoding="utf-8"))
    assert set(data) <= DISCUSSION_KEYS
    assert_valid_body(data["body"])


def assert_valid_body(body):
    """The fields of a form are what GitHub can show."""
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


def test_show_and_tell_asks_for_the_board_and_its_setup():
    """The "Show your board" call of the README leads to this form."""
    form = GITHUB / "DISCUSSION_TEMPLATE" / "show-and-tell.yml"
    body = yaml.safe_load(form.read_text("utf-8"))["body"]
    fields = {field.get("id"): field for field in body}
    assert {"photo", "board_software", "screen", "automations"} <= set(fields)
    assert fields["photo"]["validations"]["required"] is True
