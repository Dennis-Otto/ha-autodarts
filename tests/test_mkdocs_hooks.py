"""The hooks of the documentation website lead the links written for GitHub to its pages."""

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mkdocs_hooks", ROOT / "scripts" / "mkdocs_hooks.py"
)
hooks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hooks)
CONFIG = SimpleNamespace(docs_dir=str(ROOT / "docs"))


def page(source: str, url: str) -> SimpleNamespace:
    """A page as MkDocs gives it to the hooks: its file in docs/ and its address."""
    return SimpleNamespace(file=SimpleNamespace(src_uri=source, url=url))


ENGLISH = page("cards.md", "cards.html")
GERMAN = page("cards.de.md", "de/cards.html")
# A page without a German version, on the German website.
FALLBACK = page("releases.md", "de/releases.html")


class Files:
    """The pages of one website, by their file in docs/."""

    def __init__(self, *pages: SimpleNamespace) -> None:
        self.pages = {known.file.src_uri: known.file for known in pages}

    def get_file_from_path(self, path: str) -> SimpleNamespace | None:
        file = self.pages.get(path)
        if file is None:
            return None
        return SimpleNamespace(
            url_relative_to=lambda other: f"<{file.url} from {other.url}>"
        )


def markdown(text: str, of: SimpleNamespace) -> str:
    return hooks.on_page_markdown(text, of, CONFIG, None)


def test_a_link_to_the_other_language_leads_to_its_website():
    assert markdown("[Deutsch](cards.de.md#live-karte)", ENGLISH) == (
        '<a href="de/cards.html#live-karte">Deutsch</a>'
    )
    assert (
        markdown("[**English**](cards.md)", GERMAN)
        == '<a href="../cards.html">**English**</a>'
    )
    assert markdown(
        "[Spiele](../games.de.md)", page("decisions/x.md", "decisions/x.html")
    ) == ('<a href="../de/games.html">Spiele</a>')


def test_an_english_page_on_the_german_website_links_to_english_pages():
    """Its anchors are those of the English pages."""
    assert markdown("[Betas](installation.md#betas-for-testers)", FALLBACK) == (
        '<a href="../installation.html#betas-for-testers">Betas</a>'
    )


def test_a_link_in_the_language_of_the_website_stays_for_mkdocs():
    for text, of in [
        ("[Spiele](games.de.md#turniere)", GERMAN),
        ("[Games](games.md)", ENGLISH),
        ("[Releases](releases.md)", GERMAN),
        ("[Spiele](games.de.md)", FALLBACK),
        ("[Changelog](../CHANGELOG.md)", ENGLISH),
        ("[GitHub](https://github.com/Dennis-Otto/ha-autodarts)", ENGLISH),
        ("[Below](#live-card)", ENGLISH),
    ]:
        assert markdown(text, of) == text


def test_a_link_to_a_start_page_of_github_leads_to_the_one_of_the_website():
    assert markdown("[Geräte](README.de.md#unterstützte-geräte)", GERMAN) == (
        "[Geräte](index.de.md#unterstützte-geräte)"
    )
    assert markdown(
        "[Docs](../README.md)", page("decisions/x.md", "decisions/x.html")
    ) == ("[Docs](../index.md)")
    assert (
        markdown("[Decisions](decisions/README.md)", ENGLISH)
        == "[Decisions](decisions/README.md)"
    )
    assert markdown("[Devices](README.md#supported-devices)", FALLBACK) == (
        '<a href="../index.html#supported-devices">Devices</a>'
    )


def test_code_and_pictures_keep_their_links():
    text = "`[x](cards.de.md)`\n\n```md\n[x](cards.de.md)\n```\n\n![Karte](images/de/card.png)\n"
    assert markdown(text, ENGLISH) == text


def test_the_pictures_of_the_html_of_a_german_page_lead_from_de():
    text = (
        '<picture><source srcset="images/de/card-light.png, images/de/card@2x.png 2x">'
        '<img src="images/de/card.png" alt="Karte"></picture>'
        '<a href="games.de.md">Spiele</a> <a href="media/hero-de.mp4">Video</a>'
        ' <img src="https://example.com/x.png"> <a href="#oben">Oben</a>'
    )
    assert markdown(text, GERMAN) == (
        '<picture><source srcset="../images/de/card-light.png, ../images/de/card@2x.png 2x">'
        '<img src="../images/de/card.png" alt="Karte"></picture>'
        '<a href="games.de.md">Spiele</a> <a href="../media/hero-de.mp4">Video</a>'
        ' <img src="https://example.com/x.png"> <a href="#oben">Oben</a>'
    )
    english = '<img src="images/en/card.png" alt="Card">'
    assert markdown(english, ENGLISH) == english


def test_a_missing_page_of_the_other_language_warns(caplog):
    with caplog.at_level(logging.WARNING):
        assert markdown("[x](missing.de.md)", ENGLISH) == "[x](missing.de.md)"
    assert "cards.md links to missing.de.md, which isn't a page" in caplog.text


def test_the_links_of_the_html_lead_to_pages():
    games = page("games.de.md", "de/games.html")
    html = '<a href="games.de.md#turniere">Turniere</a> <a href="cards.md">English</a>'
    assert hooks.on_page_content(html, GERMAN, CONFIG, Files(games)) == (
        '<a href="<de/games.html from de/cards.html>#turniere">Turniere</a>'
        ' <a href="../cards.html">English</a>'
    )
    assert hooks.on_page_content(
        '<a href="README.md">', ENGLISH, CONFIG, Files(page("index.md", "index.html"))
    ) == ('<a href="<index.html from cards.html>">')


def test_a_link_of_the_html_to_no_page_warns(caplog):
    with caplog.at_level(logging.WARNING):
        html = '<a href="nothing.md">'
        assert hooks.on_page_content(html, ENGLISH, CONFIG, Files()) == html
    assert "cards.md links in its HTML to nothing.md, which isn't a page" in caplog.text
