"""The launch posts of the creator kit can be posted as they are.

Each text sits in a code block with a title, under a heading that names where it
goes, so that the copy button takes exactly the text. A text stays short and within
the limits of the place it goes to, every link in it leads to a page, heading or file
that exists, and a German text leads to the German website.
"""

import re
from pathlib import Path

import pytest

from .test_docs_links import MARKDOWN_LINK, WEBSITE, anchors, resolve, slug

ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs"
# The section of the launch posts in each creator kit, and where each of its texts
# goes: the heading of the place, and the titles of its code blocks.
SECTIONS = {
    "creator-kit.md": "Launch posts",
    "creator-kit.de.md": "Beiträge zum Start",
}
POSTS = {
    "creator-kit.md": {
        "Home Assistant forum": ["Title", "Post"],
        "r/homeassistant": ["Title", "Post"],
        "r/Darts": ["Title", "Post"],
        "Autodarts Discord": ["Message"],
        "Tools for Autodarts and darts-hub": ["Tools for Autodarts", "darts-hub"],
    },
    "creator-kit.de.md": {
        "Deutschsprachige Foren": ["Titel", "Beitrag"],
        "Autodarts-Discord": ["Nachricht"],
        "Tools for Autodarts und darts-hub": ["Tools for Autodarts", "darts-hub"],
    },
}
TITLES = {"Title", "Titel"}
FULL = {"Post", "Beitrag", "Message", "Nachricht"}
# The limits: under 300 words for every text, a title as long as the forum takes
# one (Reddit takes 300 characters), and a message as long as Discord takes one
# without Nitro. A line for another community is two sentences and a link.
WORDS = 300
TITLE = 255
DISCORD = 2000
LINE = 60
HACS = (
    "https://my.home-assistant.io/redirect/hacs_repository/"
    "?owner=Dennis-Otto&repository=ha-autodarts&category=integration"
)
DISCUSSION = "https://github.com/Dennis-Otto/ha-autodarts/discussions/new?category="
FORMS = ROOT / ".github" / "DISCUSSION_TEMPLATE"
HEADING = re.compile(r"^(#{2,3}) (.+)$", re.MULTILINE)
BLOCK = re.compile(r'^```(\w+) title="([^"]+)"\n(.*?)^```$', re.MULTILINE | re.DOTALL)
URL = re.compile(r"https?://[^\s<>()\[\]]+")


def section(kit: str) -> str:
    """The text of the launch posts in a creator kit, up to the next section."""
    text = (DOCS / kit).read_text(encoding="utf-8")
    start = text.index(f"\n## {SECTIONS[kit]}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end > 0 else None]


def headings(kit: str) -> list[tuple[str, str, str]]:
    """The headings of the section of the launch posts, with the text under each."""
    parts = HEADING.split(section(kit))
    return list(zip(parts[1::3], parts[2::3], parts[3::3], strict=True))


def places(kit: str) -> dict[str, str]:
    """The text under the heading of each place in the section of the launch posts."""
    return {name: body for level, name, body in headings(kit) if level == "###"}


def posts() -> list[tuple[str, str, str, str]]:
    """Every text of the launch posts: its kit, its place, its title and its text."""
    return [
        (kit, place, title, text)
        for kit in POSTS
        for place, body in places(kit).items()
        for _, title, text in BLOCK.findall(body)
    ]


def links(text: str) -> set[str]:
    """The addresses in a text, as Markdown links and as plain addresses."""
    found = set(MARKDOWN_LINK.findall(text)) | set(URL.findall(text))
    return {link.rstrip(".,;:!?") for link in found if link.startswith("http")}


def ids(post: tuple[str, str, str, str]) -> str:
    kit, place, title, _ = post
    return f"{kit}: {place}: {title}"


@pytest.mark.parametrize("kit", POSTS)
def test_the_creator_kit_has_every_launch_post(kit):
    found = {
        place: [title for _, title, _ in BLOCK.findall(body)]
        for place, body in places(kit).items()
    }
    assert found == POSTS[kit]


def test_the_overview_of_each_kit_names_the_places_of_both():
    for kit in POSTS:
        overview = headings(kit)[0][2]
        for other, names in POSTS.items():
            for place in names:
                target = f"#{slug(place)}" if other == kit else f"{other}#{slug(place)}"
                assert f"]({target})" in overview, f"{kit} names no {other} {place}"


@pytest.mark.parametrize("post", posts(), ids=ids)
def test_a_launch_post_fits_where_it_goes(post):
    _, place, title, text = post
    assert len(text.split()) < WORDS
    if title in TITLES:
        assert "\n" not in text.strip() and len(text.strip()) <= TITLE
    elif title not in FULL:
        assert len(text.split()) <= LINE
    if "Discord" in place:
        assert len(text) <= DISCORD


@pytest.mark.parametrize("post", posts(), ids=ids)
def test_every_link_of_a_launch_post_works(post):
    kit, _, _, text = post
    broken = []
    for link in links(text):
        if link.startswith(DISCUSSION):
            category = link.removeprefix(DISCUSSION)
            if not (FORMS / f"{category}.yml").is_file():
                broken.append(f"{link}: no form for the category {category}")
            continue
        resolved = resolve(DOCS / kit, link)
        if resolved is None:
            continue
        file, anchor = resolved
        if not file.exists():
            broken.append(f"{link}: no such file")
        elif anchor and file.suffix == ".md" and anchor not in anchors(file):
            broken.append(f"{link}: no heading #{anchor}")
    assert not broken, "\n".join(broken)


@pytest.mark.parametrize("post", posts(), ids=ids)
def test_a_launch_post_leads_to_the_website_in_its_language(post):
    kit, _, _, text = post
    german = kit.endswith(".de.md")
    pages = [
        link.removeprefix(WEBSITE) for link in links(text) if link.startswith(WEBSITE)
    ]
    for page in pages:
        if page.startswith("demo/"):
            assert ("lang=de" in page) == german, page
        else:
            assert page.startswith("de/") == german, page


@pytest.mark.parametrize("post", [post for post in posts() if post[2] in FULL], ids=ids)
def test_a_full_post_has_the_demo_the_comparison_and_the_hacs_button(post):
    kit, place, _, text = post
    language = "de/" if kit.endswith(".de.md") else ""
    assert HACS in text
    assert f"{WEBSITE}demo/index.html" in text
    assert f"{WEBSITE}{language}coming-from.html" in text
    assert f"{DISCUSSION}show-and-tell" in text
    # The animation of a match: in the text, or attached as the place says.
    assert "media/hero-" in places(kit)[place]


@pytest.mark.parametrize("readme", ["README.md", "docs/README.de.md"])
def test_the_readme_invites_everyone_to_show_their_board(readme):
    text = (ROOT / readme).read_text(encoding="utf-8")
    assert f"]({DISCUSSION}show-and-tell)" in text


def test_the_website_wraps_the_lines_of_the_texts_to_copy():
    """A post is one long line per paragraph, which the website shows wrapped."""
    assert "  - stylesheets/extra.css" in (ROOT / "mkdocs.yml").read_text("utf-8")
    style = (DOCS / "stylesheets" / "extra.css").read_text("utf-8")
    assert ".highlight:has(> .filename) code" in style and "pre-wrap" in style
