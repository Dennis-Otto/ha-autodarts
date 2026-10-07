"""The issue assistant: event handling, Claude's answer, the sweep and the labels.

A fake of the GitHub API answers the REST and GraphQL calls of the script, so the
real request code runs; only `gh` itself is replaced.
"""

import importlib.util
import json
import re
import runpy
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "issue_assistant", ROOT / ".github/scripts/issue_assistant.py"
)
assistant = importlib.util.module_from_spec(SPEC)
# Dataclasses look up their module while the script loads.
sys.modules[SPEC.name] = assistant
SPEC.loader.exec_module(assistant)

REPOSITORY = "Dennis-Otto/ha-autodarts"
LABELS = assistant.load_labels()
NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)
BOT_USER = {"login": "github-actions[bot]", "type": "Bot"}
BUG_BODY = """### What happened?

The live card stays empty after a throw.

### Steps to reproduce

1. Throw a dart

### Area

Live card

### Integration version

1.9.0

### Last version that worked

_No response_
"""


def at(days_ago: float = 0) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def make_issue(
    number=12,
    *,
    author="reporter",
    association="NONE",
    labels=("bug", "needs-triage"),
    state="open",
    body=BUG_BODY,
    days_ago=1,
    **extra,
):
    return {
        "number": number,
        "node_id": f"I_{number}",
        "title": f"Issue {number}",
        "user": {"login": author, "type": "User"},
        "author_association": association,
        "labels": [{"name": name} for name in labels],
        "state": state,
        "state_reason": None,
        "locked": False,
        "body": body,
        "created_at": at(days_ago),
        "closed_at": None,
        "comments": 0,
        **extra,
    }


def make_comment(comment_id, author, body, days_ago, association="NONE"):
    user = BOT_USER if author == "bot" else {"login": author, "type": "User"}
    return {
        "id": comment_id,
        "user": user,
        "body": body,
        "created_at": at(days_ago),
        "author_association": association,
    }


def make_answer(**changes):
    answer = {
        "language": "en",
        "kind": "bug",
        "areas": ["area: cards"],
        "topics": [],
        "label_rationale": "The live card shows nothing after a throw.",
        "summary": "The live card stays empty after a throw.",
        "analysis": "The card probably misses the `throw` event.",
        "next_steps": ["Reload the dashboard."],
        "missing_information": [],
        "duplicates": [],
        "related": [],
        "references": [],
        "sensitive_data": False,
        "security_report": False,
    }
    answer.update(changes)
    return answer


def make_follow_up(**changes):
    answer = {
        "language": "en",
        "kind": "bug",
        "areas": [],
        "topics": [],
        "label_rationale": "Still a bug of the live card.",
        "reply": "The log shows that the event arrives.",
        "missing_information": [],
        "references": [],
        "sensitive_data": False,
    }
    answer.update(changes)
    return answer


def analysis(comment_id=1, days_ago=1, **attributes):
    marker = assistant.render_marker("analysis", lang="en", **attributes)
    return make_comment(comment_id, "bot", f"{marker}\nFirst analysis", days_ago)


class FakeGitHub(assistant.GitHub):
    """The REST and GraphQL endpoints the script uses, in memory."""

    def __init__(self, *issues, dry_run=False):
        super().__init__(REPOSITORY, dry_run=dry_run)
        self.store = {issue["number"]: deepcopy(issue) for issue in issues}
        self.comment_store: dict[int, list] = {}
        self.event_store: dict[int, list] = {}
        self.reaction_store: dict[int, list] = {}
        self.discussion_store: list[dict] = []
        self.label_store = [
            {
                "name": label.name,
                "color": label.color,
                "description": label.description,
                "node_id": f"L_{label.name}",
            }
            for label in LABELS
        ]
        self.release = "v1.9.0"
        self.calls: list[tuple] = []
        self.suggestions: list[dict] = []
        self.rationales: dict[tuple[int, str], str] = {}
        self.graphql_error: str | None = None
        self.next_id = 1000

    def _issue(self, number):
        if number not in self.store:
            raise assistant.GitHubError("gh api: Not Found (HTTP 404)")
        return self.store[number]

    def _add(self, number, names):
        issue = self._issue(number)
        for name in names:
            if name not in assistant.label_names(issue):
                issue["labels"].append({"name": name})
                self.event_store.setdefault(number, []).append(
                    {
                        "event": "labeled",
                        "label": {"name": name},
                        "actor": BOT_USER,
                        "created_at": at(),
                    }
                )

    def rest(self, path, *, method="GET", data=None, pages=False):
        self.calls.append((method, path, deepcopy(data)))
        parts = urlsplit(path)
        route, query = parts.path, parse_qs(parts.query)
        if method == "GET":
            if match := re.fullmatch(r"issues/(\d+)", route):
                return deepcopy(self._issue(int(match[1])))
            if match := re.fullmatch(r"issues/(\d+)/comments", route):
                return deepcopy(self.comment_store.get(int(match[1]), []))
            if match := re.fullmatch(r"issues/(\d+)/events", route):
                return deepcopy(self.event_store.get(int(match[1]), []))
            if match := re.fullmatch(r"issues/comments/(\d+)/reactions", route):
                return deepcopy(self.reaction_store.get(int(match[1]), []))
            if route == "issues":
                items = [
                    issue
                    for issue in self.store.values()
                    if query["state"][0] in ("all", issue["state"])
                    and (
                        "labels" not in query
                        or query["labels"][0] in assistant.label_names(issue)
                    )
                ]
                return deepcopy(sorted(items, key=lambda item: -item["number"]))
            if route == "labels":
                return deepcopy(self.label_store)
            if route == "releases/latest":
                if not self.release:
                    raise assistant.GitHubError("gh api: Not Found (HTTP 404)")
                return {"tag_name": self.release}
        if method == "POST":
            if match := re.fullmatch(r"issues/(\d+)/comments", route):
                self.next_id += 1
                comment = make_comment(self.next_id, "bot", data["body"], 0)
                self.comment_store.setdefault(int(match[1]), []).append(comment)
                return comment
            if match := re.fullmatch(r"issues/(\d+)/labels", route):
                self._add(int(match[1]), data["labels"])
                return []
            if route == "labels":
                self.label_store.append({**data, "node_id": f"L_{data['name']}"})
                return data
        if method == "DELETE":
            if match := re.fullmatch(r"issues/(\d+)/labels/(.+)", route):
                issue = self._issue(int(match[1]))
                name = unquote(match[2])
                if name not in assistant.label_names(issue):
                    raise assistant.GitHubError(
                        "gh api: Label does not exist (HTTP 404)"
                    )
                issue["labels"] = [
                    label for label in issue["labels"] if label["name"] != name
                ]
                return None
        if method == "PATCH":
            if match := re.fullmatch(r"issues/(\d+)", route):
                issue = self._issue(int(match[1]))
                issue.update(data)
                if data["state"] == "open":
                    issue["state_reason"] = "reopened"
                return issue
            if match := re.fullmatch(r"labels/(.+)", route):
                label = next(
                    item
                    for item in self.label_store
                    if item["name"] == unquote(match[1])
                )
                label.update(data)
                return label
        raise AssertionError(f"unexpected call {method} {path}")

    def graphql(self, query, variables):
        self.calls.append(("GRAPHQL", query, deepcopy(variables)))
        if self.graphql_error:
            raise assistant.GitHubError(self.graphql_error)
        if "discussions(" in query:
            return {"repository": {"discussions": {"nodes": self.discussion_store}}}
        if "discussion(number" in query:
            found = [
                item
                for item in self.discussion_store
                if item["number"] == variables["number"]
            ]
            return {"repository": {"discussion": found[0] if found else None}}
        number = int(variables["issue"].removeprefix("I_"))
        if "addLabelsToLabelable" in query:
            names = [item["labelId"].removeprefix("L_") for item in variables["labels"]]
            self._add(number, names)
            for item in variables["labels"]:
                self.rationales[(number, item["labelId"])] = item["rationale"]
            return {"addLabelsToLabelable": {"clientMutationId": None}}
        if "isSuggestion: true" in query:
            self.suggestions.append(variables)
            return {"closeIssue": {"issue": {"number": number}}}
        if "closeIssue" in query:
            issue = self._issue(number)
            issue["state"] = "closed"
            issue["state_reason"] = variables["reason"].lower()
            issue["duplicate_of"] = variables["duplicate"]
            issue["rationale"] = variables["rationale"]
            self.event_store.setdefault(number, []).append(
                {"event": "closed", "actor": BOT_USER, "created_at": at()}
            )
            return {"closeIssue": {"issue": {"number": number}}}
        raise AssertionError(f"unexpected query {query}")

    # Helpers for the tests

    def labels_of(self, number):
        return assistant.label_names(self.store[number])

    def posted(self, number):
        return [
            comment["body"]
            for comment in self.comment_store.get(number, [])
            if comment["user"] == BOT_USER and comment["created_at"] == at()
        ]

    def writes_made(self):
        return [call for call in self.calls if call[0] not in ("GET",)]


# The labels


def test_labels_are_unique_and_valid():
    names = [label.name for label in LABELS]
    assert len(names) == len(set(names))
    groups = {"type", "area", "topic", "lifecycle", "decision", "release", "dependabot"}
    for label in LABELS:
        assert re.fullmatch(r"[0-9a-f]{6}", label.color), label.name
        # GitHub refuses descriptions longer than 100 characters.
        assert 0 < len(label.description) <= 100, label.name
        assert label.group in groups, label.name


def form(name):
    return yaml.safe_load((ROOT / ".github/ISSUE_TEMPLATE" / name).read_text("utf-8"))


def test_every_area_of_the_bug_report_has_exactly_one_label():
    field = next(
        item for item in form("bug_report.yml")["body"] if item.get("id") == "area"
    )
    assert field["attributes"]["label"] == "Area"
    options = field["attributes"]["options"]
    for option in options:
        owners = [label.name for label in LABELS if option in label.form_options]
        assert len(owners) == (0 if option == "Other" else 1), option
    mapped = {option for label in LABELS for option in label.form_options}
    assert mapped <= set(options), (
        "an area label names an option the form no longer has"
    )


def test_every_label_in_use_is_defined():
    defined = {label.name for label in LABELS}
    used = set()
    for path in (ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml"):
        used |= set(yaml.safe_load(path.read_text("utf-8")).get("labels", []))
    notes = yaml.safe_load((ROOT / ".github/release.yml").read_text("utf-8"))
    used |= set(notes["changelog"]["exclude"]["labels"])
    for category in notes["changelog"]["categories"]:
        used |= set(category["labels"]) - {"*"}
    pr_labels = (ROOT / ".github/workflows/pr-labels.yml").read_text("utf-8")
    used |= set(re.search(r"managed=\(([^)]*)\)", pr_labels)[1].split())
    used |= {
        assistant.NEEDS_TRIAGE,
        assistant.NEEDS_INFO,
        assistant.STALE,
        assistant.POSSIBLE_DUPLICATE,
        assistant.DUPLICATE,
        assistant.INVALID,
    }
    used |= assistant.ASKING_KINDS
    assert used <= defined, used - defined


def test_the_descriptions_name_the_real_timeouts():
    described = {label.name: label.description for label in LABELS}
    assert f"{assistant.REMIND_AFTER.days} days" in described["needs-info"]
    assert f"{assistant.CLOSE_AFTER.days} days" in described["needs-info"]
    assert f"{assistant.WARNING_PERIOD.days} days" in described["stale"]
    assert f"{assistant.DUPLICATE_GRACE.days} days" in described["possible-duplicate"]
    for language in ("en", "de"):
        outro = assistant.TEXT[language]["missing.outro"]
        assert str(assistant.REMIND_AFTER.days) in outro
        assert str(assistant.CLOSE_AFTER.days) in outro
        assert (
            str(assistant.DUPLICATE_GRACE.days)
            in assistant.TEXT[language]["duplicate.close"]
        )


def test_both_languages_have_the_same_texts():
    english, german = assistant.TEXT["en"], assistant.TEXT["de"]
    assert english.keys() == german.keys()
    for key in english:
        placeholders = [
            set(re.findall(r"\{(\w+)\}", text[key])) for text in (english, german)
        ]
        assert placeholders[0] == placeholders[1], key
    kinds = assistant.group(LABELS, "type")
    assert {f"thanks.{kind}" for kind in kinds} <= english.keys()


# Reading issues


def test_form_answers_are_read_by_their_label():
    fields = assistant.form_fields(BUG_BODY)
    assert fields["Area"] == "Live card"
    assert fields["Integration version"] == "1.9.0"
    assert fields["Last version that worked"] == ""
    assert assistant.form_fields("Just text") == {}


def test_the_area_of_the_form_becomes_a_label():
    assert assistant.form_labels(make_issue(), LABELS) == ["area: cards"]
    assert assistant.form_labels(make_issue(body="### Area\n\nOther\n"), LABELS) == []
    assert assistant.form_labels(make_issue(body=None), LABELS) == []


@pytest.mark.parametrize(
    ("text", "language"),
    [
        (
            "Die Karte zeigt nichts an, wenn ich einen Dart werfe und das ist komisch.",
            "de",
        ),
        ("The card shows nothing when I throw a dart, and it is not right.", "en"),
        ("", "en"),
    ],
)
def test_the_language_is_guessed_from_the_words(text, language):
    assert assistant.detect_language(text) == language


def test_the_language_of_the_last_analysis_wins():
    comments = [
        make_comment(1, "bot", assistant.render_marker("analysis", lang="de"), 2),
        make_comment(2, "reporter", "The card is empty.", 1),
    ]
    assert assistant.issue_language(make_issue(), comments) == "de"
    odd = [make_comment(1, "bot", assistant.render_marker("analysis", lang="fr"), 2)]
    assert assistant.issue_language(make_issue(), odd) == "en"


def test_without_an_analysis_the_reporter_s_words_decide():
    german = make_issue(
        body="### What happened?\n\nDie Karte bleibt leer, wenn ich werfe.\n"
    )
    comments = [
        make_comment(1, "reporter", "Ich habe das auch mit der neuen Version.", 1)
    ]
    assert assistant.issue_language(german, comments) == "de"
    assert (
        assistant.issue_language(make_issue(body="Plain text, not a form."), []) == "en"
    )


def test_dates_read_naturally():
    moment = datetime(2026, 10, 22, tzinfo=UTC)
    assert assistant.format_date(moment, "en") == "October 22, 2026"
    assert assistant.format_date(moment, "de") == "22. Oktober 2026"


def test_only_the_assistant_s_own_comments_carry_markers():
    body = assistant.render_marker("analysis", lang="en", questions=1)
    assert assistant.marker(make_comment(1, "bot", body, 0)) == (
        "analysis",
        {"lang": "en", "questions": "1"},
    )
    # A person who copies the marker does not speak for the assistant.
    assert assistant.marker(make_comment(2, "reporter", body, 0)) is None
    assert assistant.marker(make_comment(3, "bot", "No marker", 0)) is None


def test_bots_and_maintainers_are_recognized():
    assert assistant.is_bot(BOT_USER)
    assert assistant.is_bot({"login": "renovate[bot]"})
    assert not assistant.is_bot({"login": "reporter", "type": "User"})
    assert not assistant.is_bot(None)
    assert assistant.is_maintainer({"author_association": "OWNER"})
    assert assistant.is_maintainer({"author_association": "COLLABORATOR"})
    assert not assistant.is_maintainer({"author_association": "CONTRIBUTOR"})


def test_a_follow_up_is_due_only_after_the_assistant_s_own_questions():
    asked = analysis(questions=1)
    answer = make_comment(2, "reporter", "Here it is", 0)
    assert assistant.follow_up_due([asked, answer], "reporter")
    assert not assistant.follow_up_due([analysis(questions=0), answer], "reporter")
    assert not assistant.follow_up_due([answer], "reporter")
    maintainer = make_comment(3, "maintainer", "Thanks, I'll look", 0.5, "OWNER")
    assert not assistant.follow_up_due([asked, maintainer, answer], "reporter")


def test_follow_ups_are_limited():
    asked = analysis(questions=1)
    follow = [
        make_comment(
            index,
            "bot",
            assistant.render_marker("follow-up", lang="en", questions=1),
            1,
        )
        for index in range(2, 2 + assistant.MAX_FOLLOW_UPS)
    ]
    assert not assistant.follow_up_due([asked, *follow], "reporter")
    assert assistant.follow_up_due([asked, *follow[:-1]], "reporter")


# Events


def event(action, issue, sender="reporter", comment=None):
    payload = {
        "action": action,
        "issue": issue,
        "sender": {
            "login": sender,
            "type": "Bot" if sender.endswith("[bot]") else "User",
        },
    }
    if comment:
        payload["comment"] = comment
    return payload


def test_a_new_issue_gets_its_area_and_an_analysis():
    issue = make_issue(labels=("bug",))
    github = FakeGitHub(issue)
    plan = assistant.handle_event(github, "issues", event("opened", issue), LABELS)
    assert (plan.issue, plan.mode) == (12, "triage")
    assert github.labels_of(12) == {"bug", "area: cards", "needs-triage"}


def test_a_maintainer_s_issue_gets_labels_but_no_analysis():
    issue = make_issue(author="Dennis-Otto", association="OWNER")
    github = FakeGitHub(issue)
    plan = assistant.handle_event(
        github, "issues", event("opened", issue, "Dennis-Otto"), LABELS
    )
    assert plan.mode == "none"
    assert "area: cards" in github.labels_of(12)


@pytest.mark.parametrize("kind", ["pull request", "bot"])
def test_pull_requests_and_bots_are_ignored(kind):
    issue = make_issue(pull_request={"url": "x"} if kind == "pull request" else None)
    if kind == "bot":
        issue.pop("pull_request")
    github = FakeGitHub(issue)
    sender = "dependabot[bot]" if kind == "bot" else "reporter"
    plan = assistant.handle_event(
        github, "issues", event("opened", issue, sender), LABELS
    )
    assert plan.mode == "none"
    assert not github.writes_made()


def test_an_edit_by_the_reporter_answers_the_assistant_s_questions():
    issue = make_issue(labels=("bug", "needs-info", "stale"))
    github = FakeGitHub(issue)
    github.comment_store[12] = [analysis(questions=1)]
    plan = assistant.handle_event(github, "issues", event("edited", issue), LABELS)
    assert plan.mode == "follow-up"
    assert github.labels_of(12) == {"bug"}


def test_other_edits_change_nothing():
    issue = make_issue(labels=("bug", "needs-info"))
    github = FakeGitHub(issue)
    plan = assistant.handle_event(
        github, "issues", event("edited", issue, "someone"), LABELS
    )
    assert plan.mode == "none"
    plan = assistant.handle_event(
        github, "issues", event("edited", make_issue()), LABELS
    )
    assert plan.mode == "none"
    assert not github.writes_made()


def test_the_reporter_s_comment_ends_the_waiting():
    issue = make_issue(labels=("bug", "needs-info"))
    github = FakeGitHub(issue)
    answer = make_comment(5, "reporter", "Version 2.0.2", 0)
    github.comment_store[12] = [analysis(questions=1), answer]
    plan = assistant.handle_event(
        github, "issue_comment", event("created", issue, comment=answer), LABELS
    )
    assert plan.mode == "follow-up"
    assert "needs-info" not in github.labels_of(12)


def test_the_answer_to_the_maintainer_needs_no_follow_up():
    issue = make_issue(labels=("bug", "needs-info"))
    github = FakeGitHub(issue)
    question = make_comment(4, "Dennis-Otto", "Which version?", 1, "OWNER")
    answer = make_comment(5, "reporter", "2.0.2", 0)
    github.comment_store[12] = [analysis(questions=1, days_ago=2), question, answer]
    plan = assistant.handle_event(
        github, "issue_comment", event("created", issue, comment=answer), LABELS
    )
    assert plan.mode == "none"
    assert "needs-info" not in github.labels_of(12)


def test_a_comment_without_a_pending_question_changes_nothing():
    issue = make_issue()
    github = FakeGitHub(issue)
    comment = make_comment(5, "reporter", "Any news?", 0)
    plan = assistant.handle_event(
        github, "issue_comment", event("created", issue, comment=comment), LABELS
    )
    assert plan.mode == "none"
    assert not github.writes_made()


def test_any_comment_stops_the_duplicate_closing():
    issue = make_issue(labels=("bug", "possible-duplicate"))
    github = FakeGitHub(issue)
    comment = make_comment(5, "someone", "Mine is different", 0)
    plan = assistant.handle_event(
        github,
        "issue_comment",
        event("created", issue, "someone", comment),
        LABELS,
    )
    assert plan.mode == "none"
    assert "possible-duplicate" not in github.labels_of(12)


def test_a_maintainer_s_comment_is_checked_for_a_question():
    issue = make_issue(labels=("bug", "stale"))
    github = FakeGitHub(issue)
    comment = make_comment(5, "Dennis-Otto", "Can you send the log?", 0, "OWNER")
    plan = assistant.handle_event(
        github,
        "issue_comment",
        event("created", issue, "Dennis-Otto", comment),
        LABELS,
    )
    assert plan.mode == "maintainer-reply"
    # A new question starts a new waiting period.
    assert "stale" not in github.labels_of(12)


def test_a_maintainer_s_comment_on_a_waiting_or_own_issue_is_not_checked():
    comment = make_comment(5, "Dennis-Otto", "Any news?", 0, "OWNER")
    for issue in (
        make_issue(labels=("bug", "needs-info")),
        make_issue(author="Dennis-Otto", association="OWNER"),
    ):
        github = FakeGitHub(issue)
        plan = assistant.handle_event(
            github,
            "issue_comment",
            event("created", issue, "Dennis-Otto", comment),
            LABELS,
        )
        assert plan.mode == "none"


def test_other_people_s_comments_change_nothing():
    issue = make_issue(labels=("bug", "needs-info"))
    github = FakeGitHub(issue)
    comment = make_comment(5, "someone", "Same here", 0)
    plan = assistant.handle_event(
        github,
        "issue_comment",
        event("created", issue, "someone", comment),
        LABELS,
    )
    assert plan.mode == "none"
    assert github.labels_of(12) == {"bug", "needs-info"}


def closed_unanswered(**changes):
    issue = make_issue(labels=("bug", "needs-info", "stale"), state="closed", **changes)
    issue["state_reason"] = "not_planned"
    github = FakeGitHub(issue)
    github.comment_store[12] = [
        analysis(questions=1, days_ago=31),
        make_comment(
            2, "bot", assistant.render_closed_unanswered("reporter", "en"), 0.5
        ),
    ]
    github.event_store[12] = [
        {"event": "closed", "actor": BOT_USER, "created_at": at(0.5)}
    ]
    return github


def test_an_answer_reopens_an_issue_closed_without_one():
    github = closed_unanswered()
    answer = make_comment(9, "reporter", "Sorry, here is the log", 0)
    github.comment_store[12].append(answer)
    plan = assistant.handle_event(
        github,
        "issue_comment",
        event("created", github.issue(12), comment=answer),
        LABELS,
    )
    assert plan.mode == "follow-up"
    issue = github.store[12]
    assert issue["state"] == "open"
    assert github.labels_of(12) == {"bug", "needs-triage"}
    (reopened,) = github.posted(12)
    assert "I reopened the issue" in reopened and "@reporter" in reopened


def test_a_reopened_issue_without_questions_of_the_assistant_goes_to_the_maintainer():
    github = closed_unanswered()
    github.comment_store[12][0] = analysis(questions=0, days_ago=31)
    answer = make_comment(9, "reporter", "Here is the log", 0)
    github.comment_store[12].append(answer)
    plan = assistant.handle_event(
        github,
        "issue_comment",
        event("created", github.issue(12), comment=answer),
        LABELS,
    )
    assert plan.mode == "none"
    assert github.store[12]["state"] == "open"


@pytest.mark.parametrize(
    "case", ["other person", "closed by a person", "no marker", "no stale"]
)
def test_other_closed_issues_stay_closed(case):
    github = closed_unanswered()
    commenter = "someone" if case == "other person" else "reporter"
    if case == "closed by a person":
        github.event_store[12][-1]["actor"] = {"login": "Dennis-Otto", "type": "User"}
    if case == "no marker":
        github.comment_store[12] = github.comment_store[12][:1]
    if case == "no stale":
        github.store[12]["labels"] = [{"name": "bug"}]
    comment = make_comment(9, commenter, "Hello", 0)
    plan = assistant.handle_event(
        github,
        "issue_comment",
        event("created", github.issue(12), commenter, comment),
        LABELS,
    )
    assert plan.mode == "none"
    assert github.store[12]["state"] == "closed"


def test_a_run_by_hand_starts_the_chosen_task():
    github = FakeGitHub(make_issue(labels=("bug",)))
    payload = {"inputs": {"issue": "12", "mode": "follow-up"}}
    plan = assistant.handle_event(github, "workflow_dispatch", payload, LABELS)
    assert (plan.issue, plan.mode) == (12, "follow-up")
    assert "area: cards" in github.labels_of(12)
    payload = {"inputs": {"issue": "12"}}
    assert (
        assistant.handle_event(github, "workflow_dispatch", payload, LABELS).mode
        == "triage"
    )


@pytest.mark.parametrize(
    ("issue", "mode"),
    [(make_issue(pull_request={"url": "x"}), "triage"), (make_issue(), "chat")],
)
def test_a_run_by_hand_refuses_pull_requests_and_unknown_tasks(issue, mode):
    github = FakeGitHub(issue)
    with pytest.raises(assistant.AssistantError):
        assistant.handle_event(
            github,
            "workflow_dispatch",
            {"inputs": {"issue": "12", "mode": mode}},
            LABELS,
        )


def test_unknown_events_are_noted():
    github = FakeGitHub(make_issue())
    plan = assistant.handle_event(
        github, "issues", event("labeled", make_issue()), LABELS
    )
    assert plan.mode == "none" and "not handled" in plan.notes[0]


# The context for Claude


def test_the_context_holds_the_issue_the_other_issues_and_discussions():
    folder = assistant.ROOT / ".issue-assistant-test"
    issue = make_issue(
        body="### What happened?\n\nThe card <!-- hidden --> is empty.\n"
    )
    older = make_issue(
        7, body="### What happened?\n\nOld\n\n### Area\n\n_No response_\n"
    )
    older.update(state="closed", state_reason="completed", closed_at=at(5))
    pull = make_issue(8, pull_request={"url": "x"})
    github = FakeGitHub(issue, older, pull)
    github.discussion_store = [
        {
            "number": 104,
            "title": "Testers",
            "category": {"name": "Announcements"},
            "isAnswered": None,
            "closed": False,
            "body": "Please test",
            "answer": None,
        }
    ]
    github.comment_store[12] = [
        analysis(questions=1),
        make_comment(2, "Dennis-Otto", "Which version?", 0.5, "OWNER"),
        make_comment(3, "reporter", "1.9.0", 0.2),
    ]
    try:
        written = assistant.write_context(github, 12, "triage", LABELS, folder)
        text = (folder / "issue.md").read_text("utf-8")
        assert "# Issue #12: Issue 12" in text
        assert "hidden" not in text
        assert "the issue assistant (you, earlier)" in text
        assert "@Dennis-Otto (maintainer)" in text
        assert "@reporter (reporter)" in text
        others = [
            json.loads(line)
            for line in (folder / "issues.jsonl").read_text("utf-8").splitlines()
        ]
        assert [item["number"] for item in others] == [7]
        assert others[0]["excerpt"] == "What happened?: Old"
        assert others[0]["closed"] == at(5)[:10]
        discussion = json.loads((folder / "discussions.jsonl").read_text("utf-8"))
        assert discussion["number"] == 104 and discussion["answer"] is None
        assert "`area: cards`" in (folder / "labels.md").read_text("utf-8")
        prompt = written["prompt"]
        assert "issue #12" in prompt and ".issue-assistant-test/issues.jsonl" in prompt
        assert "v1.9.0" in prompt
        assert not re.search(r"\{(issue|context|version|release|repository)\}", prompt)
        assert json.loads(written["schema"]) == assistant.answer_schema(
            "triage", LABELS
        )
        assert (folder / "prompt.md").read_text("utf-8") == prompt
    finally:
        for path in folder.glob("*"):
            path.unlink()
        folder.rmdir()


def test_the_context_says_when_there_is_no_release():
    folder = assistant.ROOT / ".issue-assistant-test"
    github = FakeGitHub(make_issue())
    github.release = None
    try:
        written = assistant.write_context(github, 12, "triage", LABELS, folder)
        assert "the latest release is none yet." in written["prompt"]
        written = assistant.write_context(
            github, 12, "maintainer-reply", LABELS, folder
        )
        assert "does issue #12 now wait for its reporter?" in written["prompt"]
    finally:
        for path in folder.glob("*"):
            path.unlink()
        folder.rmdir()
    with pytest.raises(assistant.AssistantError):
        assistant.write_context(github, 12, "chat", LABELS, folder)


def test_excerpts_are_short_and_without_empty_answers():
    long = "word " * 1000
    text = assistant.excerpt(long, 100)
    assert len(text) == 100 and text.endswith("…")
    assert assistant.excerpt("a   b\n\n\n\nc", 100) == "a b\n\nc"


# Claude's answer


@pytest.mark.parametrize("mode", assistant.MODES)
def test_the_schemas_fit_into_the_claude_arguments(mode):
    schema = json.dumps(assistant.answer_schema(mode, LABELS), separators=(",", ":"))
    # The workflow wraps the schema in single quotes.
    assert "'" not in schema
    assert assistant.validate(json.loads(schema), None) == ["answer is not an object"]


def test_a_complete_answer_fits_the_schema():
    for mode, answer in (
        ("triage", make_answer()),
        ("follow-up", make_follow_up()),
        (
            "maintainer-reply",
            {"waiting_for_reporter": True, "reason": "Asked for logs."},
        ),
    ):
        assert assistant.validate(assistant.answer_schema(mode, LABELS), answer) == []


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"kind": "feature"}, "answer.kind is not one of"),
        ({"areas": ["area: cards"] * 4}, "answer.areas has more than 3 items"),
        ({"areas": ["area: nowhere"]}, "answer.areas[0] is not one of"),
        ({"summary": "x" * 701}, "answer.summary is longer than 700 characters"),
        ({"summary": 5}, "answer.summary is not text"),
        ({"next_steps": "Reload"}, "answer.next_steps is not a list"),
        ({"sensitive_data": "no"}, "answer.sensitive_data is not true or false"),
        ({"extra": 1}, "answer.extra is not expected"),
        (
            {"duplicates": [{"number": 0, "confidence": "high", "reason": "x"}]},
            "answer.duplicates[0].number is below 1",
        ),
        (
            {"duplicates": [{"number": True, "confidence": "high", "reason": "x"}]},
            "answer.duplicates[0].number is not a whole number",
        ),
    ],
)
def test_an_answer_that_breaks_the_schema_is_refused(change, problem):
    answer = make_answer(**change)
    problems = assistant.validate(assistant.answer_schema("triage", LABELS), answer)
    assert any(item.startswith(problem) for item in problems), problems
    with pytest.raises(assistant.AssistantError, match="breaks the schema"):
        assistant.parse_answer("triage", json.dumps(answer), LABELS)


def test_a_missing_field_is_refused():
    answer = make_answer()
    del answer["summary"]
    assert "answer.summary is missing" in assistant.validate(
        assistant.answer_schema("triage", LABELS), answer
    )


def test_an_answer_that_is_no_json_is_refused():
    with pytest.raises(assistant.AssistantError, match="no JSON"):
        assistant.parse_answer("triage", "", LABELS)


# The examples are put together at runtime, so that the secret scan of the
# repository doesn't take them for real secrets.
@pytest.mark.parametrize(
    "secret",
    [
        "ghp_" + "a1B2" * 9,
        "github_pat_" + "a1B2" * 9,
        "sk-ant-oat01-" + "abcd" * 10,
        "xoxb-1234567890-abcdef",
        "AKIA" + "ABCDEFGHIJKLMNOP",
        ".".join(
            [
                "eyJ" + "hbGciOiJIUzI1NiJ9",
                "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0",
                "c2ln" * 5,
            ]
        ),
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "Zx8Kq2mP9vL4tR7wY1bN6cJ3hF5gD0sA8eU2iO4p",
    ],
)
def test_an_answer_with_something_like_a_secret_is_never_posted(secret):
    answer = make_answer(analysis=f"The token is {secret}.")
    assert assistant.looks_secret(secret)
    with pytest.raises(assistant.AssistantError, match="looks like a token"):
        assistant.parse_answer("triage", json.dumps(answer), LABELS)


@pytest.mark.parametrize(
    "harmless",
    [
        "677b136666dc555b19b50d237c5234f66d2847e8",
        "custom_components/autodarts/frontend/autodarts-card.js",
        "test_the_assistant_never_posts_text_that_looks_like_a_secret",
        "sensor.autodarts_board_practice_legs_played_in_the_last_session",
    ],
)
def test_ordinary_long_words_are_no_secrets(harmless):
    assert not assistant.looks_secret(harmless)


# Cleaning Claude's text


def test_mentions_images_html_and_headings_are_removed():
    text = (
        "# Title\nAsk @maintainer or @org/team.\n![shot](https://evil.example/x.png)"
        "<img src=x><b>bold</b><!-- hidden -->\nMail me at a@b.de"
    )
    cleaned = assistant.sanitize(text)
    assert cleaned == (
        "Title\nAsk `@maintainer` or `@org/team`.\nshot" + "bold\nMail me at a@b.de"
    )


def test_only_links_to_known_places_stay_links():
    text = (
        "[docs](https://github.com/Dennis-Otto/ha-autodarts/blob/main/README.md), "
        "[HA](https://www.home-assistant.io/integrations/), "
        "[issue](https://github.com/Dennis-Otto/ha-autodarts/issues/3), "
        "[evil](https://evil.example/), [plain](http://autodarts.io/) "
        "https://evil.example/path and https://docs.autodarts.io/x"
    )
    assert assistant.sanitize(text) == (
        "[docs](https://github.com/Dennis-Otto/ha-autodarts/blob/main/README.md), "
        "[HA](https://www.home-assistant.io/integrations/), issue, evil, plain "
        "`https://evil.example/path` and https://docs.autodarts.io/x"
    )


def test_only_checked_issue_numbers_stay_links():
    text = "Like #7 and #8, see other/repo#3 and the color #fff."
    assert assistant.sanitize(text, {7}) == (
        "Like #7 and `#8`, see `other/repo#3` and the color #fff."
    )


def test_code_stays_as_it_is():
    text = "Run `@decorator #5` and\n```yaml\n# comment @user #9\n```\nthen @user"
    assert assistant.sanitize(text) == (
        "Run `@decorator #5` and\n```yaml\n# comment @user #9\n```\nthen `@user`"
    )


# Links to the repository


def test_references_link_to_existing_files_lines_and_headings():
    tracked = assistant.tracked_files()
    link = assistant.reference_link(
        {
            "path": "docs/troubleshooting.md",
            "anchor": "#No-realtime-updates",
            "reason": "",
        },
        tracked,
        "abc",
        "en",
    )
    assert link == (
        "[No realtime updates](https://github.com/Dennis-Otto/ha-autodarts/blob/main/"
        "docs/troubleshooting.md#no-realtime-updates) in `docs/troubleshooting.md`"
    )
    link = assistant.reference_link(
        {
            "path": "./custom_components/autodarts/manifest.json",
            "line": 2,
            "reason": "",
        },
        tracked,
        "abc",
        "de",
    )
    assert link == (
        "[`custom_components/autodarts/manifest.json`, Zeile 2](https://github.com/"
        "Dennis-Otto/ha-autodarts/blob/abc/custom_components/autodarts/manifest.json#L2)"
    )
    link = assistant.reference_link(
        {"path": "docs/troubleshooting.md", "anchor": "nowhere", "reason": ""},
        tracked,
        "abc",
        "en",
    )
    assert link.endswith("blob/main/docs/troubleshooting.md)")


@pytest.mark.parametrize(
    "reference",
    [
        {"path": "../etc/passwd"},
        {"path": "/etc/passwd"},
        {"path": "docs/missing.md"},
        {"path": ".issue-assistant/issue.md"},
        {"path": "custom_components/autodarts/manifest.json", "line": 99999},
    ],
)
def test_references_outside_the_repository_are_dropped(reference):
    tracked = assistant.tracked_files()
    assert (
        assistant.reference_link({**reference, "reason": ""}, tracked, "abc", "en")
        is None
    )


def test_headings_get_github_s_anchors(tmp_path):
    file = tmp_path / "page.md"
    file.write_text(
        "# Page\n\n## Set up [the board](x.md)\n\n## FAQ\n\n## FAQ\n\n```\n# not a heading\n```\n",
        encoding="utf-8",
    )
    assert assistant.headings(file) == {
        "page": "Page",
        "set-up-the-board": "Set up the board",
        "faq": "FAQ",
        "faq-1": "FAQ",
    }


# Applying the first analysis


def test_the_first_analysis_is_posted_with_labels_and_a_rationale():
    issue = make_issue()
    github = FakeGitHub(issue)
    done = assistant.apply_answer(
        github,
        "triage",
        12,
        json.dumps(make_answer(areas=["area: cards", "area: games"])),
        LABELS,
        "abc",
    )
    (body,) = github.posted(12)
    assert body.startswith("<!-- issue-assistant:analysis lang=en questions=0 -->")
    assert "Thanks for the report, @reporter!" in body
    assert "### Summary\n\nThe live card stays empty after a throw." in body
    assert "### Worth trying\n\n- Reload the dashboard." in body
    assert "### Information needed" not in body
    assert "Labels: `area: cards`, `area: games`." in body
    assert github.labels_of(12) == {"bug", "needs-triage", "area: cards", "area: games"}
    assert (
        github.rationales[(12, "L_area: games")]
        == "The live card shows nothing after a throw."
    )
    assert done[0] == "Analysis on #12; labels added: area: cards, area: games."


def test_the_kind_is_corrected_while_nobody_triaged_the_issue():
    github = FakeGitHub(make_issue())
    assistant.apply_answer(
        github,
        "triage",
        12,
        json.dumps(make_answer(kind="question", areas=[])),
        LABELS,
        "abc",
    )
    assert github.labels_of(12) == {"question", "needs-triage"}
    triaged = FakeGitHub(make_issue(labels=("bug",)))
    assistant.apply_answer(
        triaged,
        "triage",
        12,
        json.dumps(make_answer(kind="question", areas=[])),
        LABELS,
        "abc",
    )
    assert triaged.labels_of(12) == {"bug", "question"}


def test_questions_mark_the_issue_as_waiting():
    github = FakeGitHub(make_issue())
    answer = make_answer(
        missing_information=["Which version runs on the board PC?", " "]
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "questions=1" in body
    assert "### Information needed" in body
    assert "- Which version runs on the board PC?\n\nWithout an answer" in body
    assert "needs-info" in github.labels_of(12)


def test_feature_requests_and_feedback_are_never_asked():
    github = FakeGitHub(make_issue(labels=("enhancement", "needs-triage")))
    answer = make_answer(kind="enhancement", missing_information=["Why?"])
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "questions=0" in body and "Information needed" not in body
    assert "Thanks for the suggestion" in body
    assert "needs-info" not in github.labels_of(12)


def test_a_german_issue_gets_a_german_analysis():
    github = FakeGitHub(make_issue())
    answer = make_answer(language="de", missing_information=["Welche Version?"])
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "Danke für deine Meldung, @reporter!" in body
    assert "### Fehlende Informationen" in body
    assert "Automatische Erstanalyse" in body


def test_a_sure_duplicate_of_an_open_older_issue_gets_the_notice():
    original = make_issue(7)
    github = FakeGitHub(original, make_issue())
    answer = make_answer(
        duplicates=[
            {"number": 7, "confidence": "high", "reason": "Same empty card as @x."}
        ]
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "duplicate=7" in body.splitlines()[0]
    assert (
        "### Possible duplicate\n\nThis looks like a duplicate of #7: Same empty card as `@x`."
        in body
    )
    assert "closes as a duplicate of #7 in 3 days" in body
    assert "possible-duplicate" in github.labels_of(12)
    assert not github.suggestions


def test_other_duplicate_candidates_become_one_suggestion_and_related_issues():
    closed = make_issue(5, state="closed")
    closed["state_reason"] = "completed"
    unplanned = make_issue(6, state="closed")
    unplanned["state_reason"] = "not_planned"
    github = FakeGitHub(
        closed, unplanned, make_issue(7), make_issue(12), make_issue(20)
    )
    answer = make_answer(
        duplicates=[
            {"number": 6, "confidence": "high", "reason": "Closed as not planned."},
            {"number": 5, "confidence": "high", "reason": "Fixed before."},
            {"number": 7, "confidence": "medium", "reason": "Similar."},
        ]
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "Possible duplicate" not in body
    assert "- #6: Closed as not planned.\n- #5: Fixed before.\n- #7: Similar." in body
    # The first candidate that may become a duplicate is suggested to the maintainer.
    assert [item["duplicate"] for item in github.suggestions] == ["I_5"]
    assert "possible-duplicate" not in github.labels_of(12)


def test_a_candidate_named_twice_is_listed_once():
    github = FakeGitHub(make_issue(7), make_issue(12))
    answer = make_answer(
        next_steps=[],
        duplicates=[
            {"number": 7, "confidence": "medium", "reason": "Similar."},
            {"number": 7, "confidence": "medium", "reason": "Again."},
        ],
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert body.count("- #7:") == 1 and "Again" not in body
    assert "Worth trying" not in body


def test_newer_unknown_and_the_same_issue_are_no_duplicates():
    github = FakeGitHub(make_issue(12), make_issue(20))
    answer = make_answer(
        duplicates=[
            {"number": 20, "confidence": "high", "reason": "Newer issue."},
            {"number": 12, "confidence": "high", "reason": "Itself."},
            {"number": 99, "confidence": "high", "reason": "Does not exist."},
        ]
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "Possible duplicate" not in body and "Related" not in body
    assert not github.suggestions


def test_related_issues_and_discussions_are_checked():
    github = FakeGitHub(
        make_issue(3), make_issue(12), make_issue(4, pull_request={"url": "x"})
    )
    github.discussion_store = [{"number": 104}]
    answer = make_answer(
        related=[
            {"kind": "issue", "number": 3, "reason": "Same card, see #3 and #104."},
            {"kind": "discussion", "number": 104, "reason": "The call for testers."},
            {"kind": "discussion", "number": 105, "reason": "Missing."},
            {"kind": "issue", "number": 4, "reason": "A pull request."},
            {"kind": "issue", "number": 3, "reason": "Twice."},
        ]
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert (
        "### Related\n\n- #3: Same card, see #3 and #104.\n- #104 (discussion): The call for testers.\n\n"
        in body
    )
    assert "#105" not in body and "#4" not in body and "Twice" not in body


def test_references_are_listed_once():
    github = FakeGitHub(make_issue())
    answer = make_answer(
        references=[
            {
                "path": "docs/troubleshooting.md",
                "anchor": "no-realtime-updates",
                "reason": "Checks.",
            },
            {
                "path": "docs/troubleshooting.md",
                "anchor": "no-realtime-updates",
                "reason": "Again.",
            },
            {"path": "nowhere.md", "reason": "Missing."},
        ]
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert body.count("troubleshooting.md#no-realtime-updates") == 1
    assert "### Where to look" in body and "nowhere" not in body


def test_personal_data_gets_a_warning():
    github = FakeGitHub(make_issue())
    assistant.apply_answer(
        github,
        "triage",
        12,
        json.dumps(make_answer(sensitive_data=True)),
        LABELS,
        "abc",
    )
    (body,) = github.posted(12)
    assert "> [!WARNING]" in body


def test_a_possible_vulnerability_is_not_discussed_in_public():
    github = FakeGitHub(make_issue(7), make_issue())
    answer = make_answer(
        security_report=True,
        missing_information=["Which endpoint?"],
        duplicates=[{"number": 7, "confidence": "high", "reason": "Same."}],
    )
    assistant.apply_answer(github, "triage", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert "> [!CAUTION]" in body and "SECURITY.md" in body
    assert "Summary" not in body and "First analysis" not in body
    assert github.labels_of(12) & {"needs-info", "possible-duplicate"} == set()


def test_spam_is_marked_without_a_comment():
    github = FakeGitHub(make_issue())
    done = assistant.apply_answer(
        github, "triage", 12, json.dumps(make_answer(kind="spam")), LABELS, "abc"
    )
    assert not github.posted(12)
    assert "invalid" in github.labels_of(12)
    assert "spam" in done[0]


def test_an_issue_is_analyzed_once_unless_started_by_hand():
    github = FakeGitHub(make_issue())
    github.comment_store[12] = [analysis()]
    done = assistant.apply_answer(
        github, "triage", 12, json.dumps(make_answer()), LABELS, "abc"
    )
    assert done == ["#12 already has this triage; nothing posted."]
    assistant.apply_answer(
        github, "triage", 12, json.dumps(make_answer()), LABELS, "abc", repeat=True
    )
    assert len(github.posted(12)) == 1


@pytest.mark.parametrize("change", [{"state": "closed"}, {"locked": True}])
def test_closed_and_locked_issues_get_nothing(change):
    github = FakeGitHub(make_issue(**change))
    done = assistant.apply_answer(
        github, "triage", 12, json.dumps(make_answer()), LABELS, "abc"
    )
    assert done == ["#12 is closed or locked; nothing posted."]
    assert not github.writes_made()


def test_an_answer_for_a_pull_request_is_refused():
    github = FakeGitHub(make_issue(pull_request={"url": "x"}))
    with pytest.raises(assistant.AssistantError, match="pull request"):
        assistant.apply_answer(
            github, "triage", 12, json.dumps(make_answer()), LABELS, "abc"
        )


def test_a_dry_run_only_previews_the_comment():
    github = FakeGitHub(make_issue(), dry_run=True)
    assistant.apply_answer(
        github,
        "triage",
        12,
        json.dumps(make_answer(missing_information=["Log?"])),
        LABELS,
        "abc",
    )
    assert not github.writes_made()
    assert github.writes == [
        "comment on #12",
        "add area: cards to #12",
        "add needs-info to #12",
    ]
    assert github.previews[0].startswith("<!-- issue-assistant:analysis")


# Follow-ups and the maintainer's questions


def test_a_follow_up_thanks_and_asks_what_is_still_missing():
    github = FakeGitHub(make_issue(labels=("bug",)))
    github.comment_store[12] = [
        analysis(questions=1, days_ago=2),
        make_comment(2, "reporter", "Log", 1),
    ]
    answer = make_follow_up(
        missing_information=["The diagnostics, please."],
        references=[{"path": "docs/troubleshooting.md", "reason": "Diagnostics."}],
        sensitive_data=True,
        areas=["area: setup"],
    )
    assistant.apply_answer(github, "follow-up", 12, json.dumps(answer), LABELS, "abc")
    (body,) = github.posted(12)
    assert body.startswith("<!-- issue-assistant:follow-up lang=en questions=1 -->")
    assert "Thanks for your answer, @reporter!" in body
    assert "The log shows that the event arrives." in body
    assert "### Still needed\n\nPlease also add:\n\n- The diagnostics, please." in body
    assert "### Where to look" in body and "> [!WARNING]" in body
    assert github.labels_of(12) == {"bug", "area: setup", "needs-info"}


def test_a_follow_up_without_open_questions_leaves_the_issue_to_the_maintainer():
    github = FakeGitHub(make_issue(labels=("bug",)))
    github.comment_store[12] = [
        analysis(questions=1, days_ago=2),
        make_comment(2, "reporter", "Log", 1),
    ]
    assistant.apply_answer(
        github,
        "follow-up",
        12,
        json.dumps(make_follow_up(language="de")),
        LABELS,
        "abc",
    )
    (body,) = github.posted(12)
    assert "Danke für deine Antwort" in body and "Noch offen" not in body
    assert github.labels_of(12) == {"bug"}


def test_a_follow_up_is_posted_once_per_answer():
    github = FakeGitHub(make_issue(labels=("bug",)))
    follow = make_comment(
        3, "bot", assistant.render_marker("follow-up", lang="en", questions=0), 0.5
    )
    github.comment_store[12] = [
        analysis(questions=1, days_ago=2),
        make_comment(2, "reporter", "Log", 1),
        follow,
    ]
    done = assistant.apply_answer(
        github, "follow-up", 12, json.dumps(make_follow_up()), LABELS, "abc"
    )
    assert done == ["#12 already has this follow-up; nothing posted."]


def test_a_question_of_the_maintainer_marks_the_issue_as_waiting():
    github = FakeGitHub(make_issue())
    github.comment_store[12] = [
        make_comment(1, "Dennis-Otto", "Which version?", 0, "OWNER")
    ]
    answer = {"waiting_for_reporter": True, "reason": "Asked for the version."}
    done = assistant.apply_answer(
        github, "maintainer-reply", 12, json.dumps(answer), LABELS, "abc"
    )
    assert "needs-info" in github.labels_of(12)
    assert done == ["#12 waits for the reporter: Asked for the version."]
    assert not github.posted(12)


@pytest.mark.parametrize("case", ["no question", "already waiting", "already answered"])
def test_a_maintainer_s_comment_that_needs_no_answer_changes_nothing(case):
    labels = ("bug", "needs-info") if case == "already waiting" else ("bug",)
    github = FakeGitHub(make_issue(labels=labels))
    github.comment_store[12] = [
        make_comment(1, "Dennis-Otto", "Which version?", 1, "OWNER")
    ]
    if case == "already answered":
        github.comment_store[12].append(make_comment(2, "reporter", "1.9.0", 0))
    answer = {"waiting_for_reporter": case != "no question", "reason": "Because."}
    assistant.apply_answer(
        github, "maintainer-reply", 12, json.dumps(answer), LABELS, "abc"
    )
    assert github.labels_of(12) == set(labels)


# The daily sweep


def waiting(days, *, labels=("bug", "needs-info"), comments=(), language="en"):
    issue = make_issue(labels=labels, days_ago=days + 1)
    github = FakeGitHub(issue)
    github.event_store[12] = [
        {
            "event": "labeled",
            "label": {"name": "needs-info"},
            "actor": BOT_USER,
            "created_at": at(days),
        }
    ]
    github.comment_store[12] = [
        make_comment(
            1,
            "bot",
            assistant.render_marker("analysis", lang=language, questions=1),
            days,
        ),
        *comments,
    ]
    return github


def test_nothing_happens_in_the_first_15_days():
    github = waiting(14.9)
    assert assistant.sweep(github, NOW) == []
    assert not github.writes_made()


def test_the_reporter_is_reminded_after_15_days():
    github = waiting(15)
    assert assistant.sweep(github, NOW) == ["#12: reminded the reporter after 15 days."]
    (body,) = github.posted(12)
    assert body.startswith("<!-- issue-assistant:reminder -->")
    assert "@reporter" in body and "October 22, 2026" in body
    assert "stale" in github.labels_of(12)


def test_a_german_reporter_is_reminded_in_german():
    github = waiting(16, language="de")
    assistant.sweep(github, NOW)
    (body,) = github.posted(12)
    assert "eine freundliche Erinnerung" in body and "22. Oktober 2026" in body


def reminded(days_waiting, days_since_reminder, **options):
    reminder = make_comment(
        2, "bot", assistant.render_reminder("reporter", "en", NOW), days_since_reminder
    )
    return waiting(
        days_waiting,
        labels=("bug", "needs-info", "stale"),
        comments=(reminder,),
        **options,
    )


def test_the_issue_closes_30_days_after_the_question():
    github = reminded(30, 15)
    assert assistant.sweep(github, NOW) == [
        "#12: closed after 30 days without an answer."
    ]
    issue = github.store[12]
    assert (issue["state"], issue["state_reason"]) == ("closed", "not_planned")
    assert issue["rationale"].startswith("No answer to the questions for 30 days")
    (body,) = github.posted(12)
    assert body.startswith("<!-- issue-assistant:closed-unanswered -->")
    # The labels stay, so that an answer can reopen the issue.
    assert {"needs-info", "stale"} <= github.labels_of(12)


def test_a_late_reminder_still_gives_15_days():
    github = reminded(40, 10)
    assert assistant.sweep(github, NOW) == []
    assert github.store[12]["state"] == "open"


def test_the_stale_label_is_restored_while_the_reminder_runs():
    github = reminded(20, 5)
    github.store[12]["labels"] = [{"name": "bug"}, {"name": "needs-info"}]
    assistant.sweep(github, NOW)
    assert "stale" in github.labels_of(12)


def test_a_new_question_of_the_maintainer_starts_a_new_period():
    question = make_comment(3, "Dennis-Otto", "And the log?", 2, "OWNER")
    github = reminded(20, 5)
    github.comment_store[12].append(question)
    assert assistant.sweep(github, NOW) == []
    assert "stale" not in github.labels_of(12)


def test_an_answer_the_event_missed_ends_the_waiting():
    answer = make_comment(3, "reporter", "Here", 1)
    github = reminded(20, 5)
    github.comment_store[12].append(answer)
    assert assistant.sweep(github, NOW) == [
        "#12: the reporter answered; no longer waiting."
    ]
    assert github.labels_of(12) == {"bug"}


def test_an_answer_before_the_reminder_ends_the_waiting_too():
    github = waiting(10, comments=(make_comment(3, "reporter", "Here", 1),))
    assistant.sweep(github, NOW)
    assert github.labels_of(12) == {"bug"}


def test_a_label_set_by_hand_counts_from_the_issue():
    github = waiting(20)
    github.event_store[12] = []
    github.comment_store[12] = []
    assert assistant.sweep(github, NOW) == ["#12: reminded the reporter after 21 days."]


def test_locked_issues_are_left_alone():
    github = waiting(40)
    github.store[12]["locked"] = True
    assert assistant.sweep(github, NOW) == []


def notice(days_ago, original=7):
    body = assistant.render_marker(
        "analysis", lang="en", questions=0, duplicate=original
    )
    return make_comment(50, "bot", f"{body}\nPossible duplicate", days_ago)


def possible_duplicate(days_ago=3, *comments, original_state="open"):
    original = make_issue(7, state=original_state)
    issue = make_issue(labels=("bug", "needs-triage", "possible-duplicate"))
    github = FakeGitHub(original, issue)
    github.comment_store[12] = [notice(days_ago), *comments]
    return github


def test_a_duplicate_closes_three_days_after_the_notice():
    github = possible_duplicate()
    assert assistant.sweep(github, NOW) == ["#12: closed as a duplicate of #7."]
    issue = github.store[12]
    assert (issue["state"], issue["state_reason"], issue["duplicate_of"]) == (
        "closed",
        "duplicate",
        "I_7",
    )
    assert github.labels_of(12) == {"bug", "duplicate"}
    (body,) = github.posted(12)
    assert body.startswith("<!-- issue-assistant:closed-duplicate of=7 -->")


def test_a_duplicate_waits_for_the_three_days():
    github = possible_duplicate(2.9)
    assert assistant.sweep(github, NOW) == []
    assert github.store[12]["state"] == "open"


@pytest.mark.parametrize("who", ["reporter", "Dennis-Otto"])
def test_a_thumbs_down_of_the_reporter_or_maintainer_keeps_the_issue_open(who):
    github = possible_duplicate()
    github.reaction_store[50] = [{"content": "-1", "user": {"login": who}}]
    assert assistant.sweep(github, NOW) == [
        "#12: stays open, the duplicate notice was objected to or is outdated."
    ]
    assert github.store[12]["state"] == "open"
    assert "possible-duplicate" not in github.labels_of(12)


def test_other_reactions_do_not_object():
    github = possible_duplicate()
    github.reaction_store[50] = [
        {"content": "-1", "user": {"login": "someone"}},
        {"content": "+1", "user": {"login": "reporter"}},
    ]
    assistant.sweep(github, NOW)
    assert github.store[12]["state"] == "closed"


def test_a_comment_after_the_notice_keeps_the_issue_open():
    github = possible_duplicate(3, make_comment(51, "someone", "It's different", 1))
    assistant.sweep(github, NOW)
    assert github.store[12]["state"] == "open"


def test_a_closed_original_keeps_the_issue_open():
    github = possible_duplicate(original_state="closed")
    assistant.sweep(github, NOW)
    assert github.store[12]["state"] == "open"
    assert "possible-duplicate" not in github.labels_of(12)


def test_a_label_without_a_notice_is_left_to_the_maintainer():
    github = possible_duplicate()
    github.comment_store[12] = []
    assert assistant.sweep(github, NOW) == []
    assert "possible-duplicate" in github.labels_of(12)
    github.store[12]["locked"] = True
    assert assistant.sweep(github, NOW) == []


# Labels as code


def test_labels_are_created_and_updated_but_never_deleted(capsys):
    github = FakeGitHub()
    github.label_store = [
        {
            "name": "bug",
            "color": "D73A4A",
            "description": "Something isn't working",
            "node_id": "L_bug",
        },
        {
            "name": "question",
            "color": "d876e3",
            "description": "Old text",
            "node_id": "L_q",
        },
        {"name": "custom", "color": "ffffff", "description": "", "node_id": "L_c"},
    ]
    done = assistant.sync_labels(github, LABELS)
    assert "updated question" in done
    assert "created area: cards" in done
    assert not any(item.endswith(" bug") for item in done)
    assert {label["name"] for label in github.label_store} >= {"custom", "area: cards"}
    assert "Label custom is not in .github/labels.toml" in capsys.readouterr().out
    patch = next(call for call in github.calls if call[0] == "PATCH")
    assert patch[1] == "labels/question"


# The gh calls


class Completed:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def test_rest_calls_build_the_gh_command(monkeypatch):
    calls = []

    def run(command, **options):
        calls.append((command, options))
        return Completed(json.dumps([[{"number": 1}], [{"number": 2}]]))

    monkeypatch.setattr(assistant.subprocess, "run", run)
    github = assistant.GitHub(REPOSITORY)
    assert github.rest("issues?state=all", pages=True) == [{"number": 1}, {"number": 2}]
    command, options = calls[0]
    assert command == [
        "gh",
        "api",
        f"repos/{REPOSITORY}/issues?state=all",
        "--paginate",
        "--slurp",
    ]
    assert options["encoding"] == "utf-8" and options["input"] is None
    github.rest("issues/1/labels", method="POST", data={"labels": ["bug"]})
    command, options = calls[1]
    assert command[-4:] == ["--method", "POST", "--input", "-"]
    assert json.loads(options["input"]) == {"labels": ["bug"]}


def test_failed_gh_calls_raise(monkeypatch):
    monkeypatch.setattr(
        assistant.subprocess,
        "run",
        lambda *a, **k: Completed(stderr="HTTP 404", returncode=1),
    )
    github = assistant.GitHub(REPOSITORY)
    with pytest.raises(assistant.GitHubError, match="HTTP 404"):
        github.issue(1)
    assert github.latest_release() is None
    assert github.discussion_exists(3) is False


def test_graphql_errors_raise(monkeypatch):
    responses = iter(
        [
            Completed(json.dumps({"errors": [{"message": "Bad field"}]})),
            Completed(json.dumps({"data": {"ok": True}})),
            Completed(""),
        ]
    )
    monkeypatch.setattr(assistant.subprocess, "run", lambda *a, **k: next(responses))
    github = assistant.GitHub(REPOSITORY)
    with pytest.raises(assistant.GitHubError, match="Bad field"):
        github.graphql("query", {})
    assert github.graphql("query", {}) == {"ok": True}
    assert github.rest("issues/1", method="DELETE") is None


def test_labels_fall_back_to_plain_labels_without_rationale():
    github = FakeGitHub(make_issue())
    github.graphql_error = "Field 'labels' doesn't exist"
    github.add_explained_labels(github.issue(12), ["area: cards"], "Because.")
    assert "area: cards" in github.labels_of(12)
    assert ("POST", "issues/12/labels", {"labels": ["area: cards"]}) in github.calls
    github.add_explained_labels(github.issue(12), [], "Nothing.")


def test_closing_falls_back_to_rest():
    github = FakeGitHub(make_issue(7), make_issue())
    github.graphql_error = "Field 'rationale' doesn't exist"
    github.close(github.issue(12), "DUPLICATE", "Same.", duplicate_of=github.issue(7))
    assert (github.store[12]["state"], github.store[12]["state_reason"]) == (
        "closed",
        "duplicate",
    )


def test_a_failed_suggestion_is_only_noted(capsys):
    github = FakeGitHub(make_issue(7), make_issue())
    github.graphql_error = "Suggestions are not available"
    github.suggest_duplicate(github.issue(12), github.issue(7), "Similar.")
    assert "No duplicate suggestion on #12" in capsys.readouterr().out


def test_removing_a_missing_label_is_fine_but_other_errors_are_not():
    github = FakeGitHub(make_issue())
    github.remove_label(12, "stale")
    with pytest.raises(assistant.GitHubError):
        github.remove_label(99, "stale")


def test_the_label_list_is_read_once():
    github = FakeGitHub()
    github._labels = None
    github.labels()
    github.labels()
    assert sum(call[1].startswith("labels") for call in github.calls) == 1


# The command line


def run_main(monkeypatch, tmp_path, github, *argv, **env):
    outputs = tmp_path / "output"
    summary = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(outputs))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(assistant, "GitHub", lambda repository, dry_run: github)
    code = assistant.main(list(argv))
    text = outputs.read_text("utf-8") if outputs.exists() else ""
    return code, text, summary.read_text("utf-8") if summary.exists() else ""


def test_the_event_command_writes_the_next_task(monkeypatch, tmp_path):
    issue = make_issue(labels=("bug",))
    payload = tmp_path / "event.json"
    payload.write_text(json.dumps(event("opened", issue)), encoding="utf-8")
    github = FakeGitHub(issue)
    code, outputs, summary = run_main(
        monkeypatch,
        tmp_path,
        github,
        "event",
        GITHUB_EVENT_NAME="issues",
        GITHUB_EVENT_PATH=str(payload),
    )
    assert code == 0
    assert outputs == "issue=12\nmode=triage\n"
    assert "### Issue assistant: #12, next task triage" in summary


def test_the_context_command_writes_multiline_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(assistant, "CONTEXT", assistant.ROOT / ".issue-assistant-test")
    github = FakeGitHub(make_issue())
    try:
        code, outputs, _ = run_main(
            monkeypatch,
            tmp_path,
            github,
            "context",
            "--issue",
            "12",
            "--mode",
            "triage",
        )
    finally:
        folder = assistant.ROOT / ".issue-assistant-test"
        for path in folder.glob("*"):
            path.unlink()
        folder.rmdir()
    assert code == 0
    assert re.match(r"prompt<<EOF_[0-9a-f]{16}\nYou are the issue assistant", outputs)
    assert re.search(r"\nschema=\{.*\}\n$", outputs)


def test_the_apply_command_previews_a_dry_run(monkeypatch, tmp_path):
    github = FakeGitHub(make_issue(), dry_run=True)
    code, _, summary = run_main(
        monkeypatch,
        tmp_path,
        github,
        "apply",
        "--issue",
        "12",
        "--mode",
        "triage",
        RESULT=json.dumps(make_answer()),
        GITHUB_EVENT_NAME="workflow_dispatch",
        GITHUB_SHA="abc",
        DRY_RUN="true",
    )
    assert code == 0
    assert "### Issue assistant: triage of #12 (dry run)" in summary
    assert "<details><summary>Comment</summary>" in summary
    assert "````markdown\n<!-- issue-assistant:analysis" in summary


def test_the_apply_command_fails_on_a_bad_answer(monkeypatch, tmp_path, capsys):
    github = FakeGitHub(make_issue())
    code, _, _ = run_main(
        monkeypatch,
        tmp_path,
        github,
        "apply",
        "--issue",
        "12",
        "--mode",
        "triage",
        RESULT="{}",
    )
    assert code == 1
    assert "::error::Claude's answer breaks the schema" in capsys.readouterr().out
    assert not github.writes_made()


def test_the_sweep_and_label_commands_report_what_they_did(monkeypatch, tmp_path):
    # The command uses the real clock, which may be hours before the tests' NOW.
    github = waiting(16)
    code, _, summary = run_main(monkeypatch, tmp_path, github, "sweep")
    assert code == 0 and "### Issue lifecycle\n\n- #12: reminded" in summary
    code, _, summary = run_main(monkeypatch, tmp_path, FakeGitHub(), "sync-labels")
    assert code == 0 and "### Labels\n\nNothing to do." in summary


def test_without_a_summary_file_the_outputs_are_printed(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assistant.output("mode", "triage")
    assistant.summary("Title", [], False)
    assert capsys.readouterr().out == "mode=triage\n### Title\n\nNothing to do.\n"


def test_the_script_runs_as_a_program(monkeypatch, capsys):
    script = ROOT / ".github/scripts/issue_assistant.py"
    monkeypatch.setattr(sys, "argv", [str(script), "--help"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(script), run_name="__main__")
    assert stop.value.code == 0
    assert "sync-labels" in capsys.readouterr().out
