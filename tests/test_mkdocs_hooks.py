"""The hooks of the documentation website lead the links written for GitHub to its pages."""

import gzip
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
SITE = "https://dennis-otto.github.io/ha-autodarts/"


def page(source: str, url: str, **meta: object) -> SimpleNamespace:
    """A page as MkDocs gives it to the hooks: its file in docs/, its address and
    its front matter."""
    return SimpleNamespace(file=SimpleNamespace(src_uri=source, url=url), meta=meta)


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


def test_the_live_demo_gets_the_cards_of_the_integration(tmp_path):
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "index.html").write_text("<!doctype html>", encoding="utf-8")
    hooks.on_post_build(SimpleNamespace(site_dir=str(tmp_path), site_url=SITE))
    cards = ROOT / "custom_components" / "autodarts" / "frontend" / "autodarts-card.js"
    assert (tmp_path / "demo" / "autodarts-card.js").read_bytes() == cards.read_bytes()
    # The texts that the card module imports, beside it as in the integration.
    texts = sorted((cards.parent / "text").glob("*.js"))
    assert len(texts) == 5
    for text in texts:
        assert (tmp_path / "demo" / "text" / text.name).read_bytes() == text.read_bytes()
    # Again into a site that has the texts already, as mkdocs serve builds it.
    hooks.on_post_build(SimpleNamespace(site_dir=str(tmp_path), site_url=SITE))
    assert (tmp_path / "demo" / "text" / texts[0].name).is_file()


def test_a_website_without_the_demo_gets_no_cards(tmp_path):
    hooks.on_post_build(SimpleNamespace(site_dir=str(tmp_path), site_url=SITE))
    assert list(tmp_path.iterdir()) == []


def head(title: str, canonical: str, shared: str = "") -> str:
    """A page as Material writes it, with the previews of the social plugin."""
    return (
        f'<html><head><title>{title}</title><link rel="canonical" href="{canonical}">'
        f"{shared}</head><body><h1>{title}</h1></body></html>"
    )


def shared(title: str) -> str:
    """The titles of the previews of a shared link, as the social plugin writes them."""
    return (
        f'<meta property="og:title" content="{title}" />'
        f'<meta property="twitter:title" content="{title}" />'
    )


def test_a_start_page_is_titled_with_the_name_of_its_website():
    """Material titles the German one after its tab, Start."""
    config = SimpleNamespace(site_name="Autodarts für Home Assistant")
    title = "Start - Autodarts für Home Assistant"
    output = hooks.on_post_page(
        head(title, f"{SITE}de/index.html", shared(title)),
        page("index.de.md", "de/index.html"),
        config,
    )
    assert output == (
        "<html><head><title>Autodarts für Home Assistant</title>"
        f'<link rel="canonical" href="{SITE}de/index.html">'
        + shared("Autodarts für Home Assistant")
        + f"</head><body><h1>{title}</h1></body></html>"
    )


def test_the_name_of_the_website_is_written_as_html():
    output = hooks.on_post_page(
        head("Home", SITE, shared("Home")),
        page("index.md", "index.html"),
        SimpleNamespace(site_name='Darts & "more"'),
    )
    assert "<title>Darts &amp; &quot;more&quot;</title>" in output
    assert 'og:title" content="Darts &amp; &quot;more&quot;" />' in output


def test_any_other_page_keeps_its_head():
    config = SimpleNamespace(site_name="Autodarts for Home Assistant")
    title = "Cards - Autodarts for Home Assistant"
    for other in (ENGLISH, GERMAN, page("decisions/README.md", "decisions/index.html")):
        output = head(title, f"{SITE}cards.html", shared(title))
        assert hooks.on_post_page(output, other, config) == output


def test_a_moved_page_leads_to_the_page_that_took_its_place():
    moved = page("LOCAL-CONTROL.md", "LOCAL-CONTROL.html", moved="installation.md")
    installation = page("installation.md", "installation.html")
    text = "# Lokale Steuerung\n\n[Installation](installation.de.md)\n"
    assert hooks.on_page_markdown(text, moved, CONFIG, Files(installation)) == (
        '# Lokale Steuerung\n\n<a href="de/installation.html">Installation</a>\n'
    )
    assert moved.meta == {
        "moved": "installation.md",
        "redirect": "<installation.html from LOCAL-CONTROL.html>",
        "search": {"exclude": True},
    }


def test_the_head_of_a_moved_page_leads_on_and_keeps_it_out_of_search_engines():
    output = hooks.on_post_page(
        head("Lokale Steuerung", f"{SITE}de/LOCAL-CONTROL.html", shared("Alt")),
        page("LOCAL-CONTROL.md", "de/LOCAL-CONTROL.html", redirect="installation.html"),
        SimpleNamespace(site_name="Autodarts für Home Assistant"),
    )
    assert output == (
        "<html><head><title>Lokale Steuerung</title>"
        f'<link rel="canonical" href="{SITE}de/installation.html">'
        + shared("Alt")
        + '<meta name="robots" content="noindex, follow">'
        '<meta http-equiv="refresh" content="0; url=installation.html"></head>'
        "<body><h1>Lokale Steuerung</h1></body></html>"
    )


def test_a_moved_page_leads_to_the_german_page_on_the_german_website():
    moved = page("SETUP-DE.md", "de/SETUP-DE.html", moved="installation.md")
    german = page("installation.de.md", "de/installation.html")
    hooks.on_page_markdown("# Einrichtung\n", moved, CONFIG, Files(german))
    assert moved.meta["redirect"] == "<de/installation.html from de/SETUP-DE.html>"
    # A page without a German version is the page of both websites.
    moved = page("old.md", "de/old.html", moved="releases.md")
    hooks.on_page_markdown("# Alt\n", moved, CONFIG, Files(FALLBACK))
    assert moved.meta["redirect"] == "<de/releases.html from de/old.html>"


def test_a_page_that_moved_nowhere_warns(caplog):
    moved = page("SETUP-DE.md", "SETUP-DE.html", moved="nothing.md")
    with caplog.at_level(logging.WARNING):
        hooks.on_page_markdown("# Einrichtung\n", moved, CONFIG, Files())
    assert "SETUP-DE.md moved to nothing.md, which isn't a page" in caplog.text
    assert moved.meta == {"moved": "nothing.md"}


SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{site}index.html</loc>
        <xhtml:link rel="alternate" hreflang="de" href="{site}de/index.html"/>
    </url>
    <url>
        <loc>{site}LOCAL-CONTROL.html</loc>
        <xhtml:link rel="alternate" hreflang="de" href="{site}de/LOCAL-CONTROL.html"/>
    </url>
    <url>
        <loc>{site}de/LOCAL-CONTROL.html</loc>
        <lastmod>2026-10-17</lastmod>
    </url>
    <url>
        <loc>{site}de/index.html</loc>
    </url>
</urlset>
""".replace("{site}", SITE)
# The sitemap without the moved page, in both languages.
UNLISTED = SITEMAP.replace(
    f"""    <url>
        <loc>{SITE}LOCAL-CONTROL.html</loc>
        <xhtml:link rel="alternate" hreflang="de" href="{SITE}de/LOCAL-CONTROL.html"/>
    </url>
    <url>
        <loc>{SITE}de/LOCAL-CONTROL.html</loc>
        <lastmod>2026-10-17</lastmod>
    </url>
""",
    "",
)


def built(tmp_path: Path, **pages: str) -> Path:
    """A website with pages of the given heads, and the sitemap of all of them."""
    for name, page_head in pages.items():
        path = tmp_path / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"<html><head>{page_head}</head><body></body></html>", "utf-8")
    (tmp_path / "sitemap.xml").write_bytes(SITEMAP.encode())
    (tmp_path / "sitemap.xml.gz").write_bytes(gzip.compress(SITEMAP.encode()))
    return tmp_path


def build(site: Path) -> None:
    hooks.on_post_build(SimpleNamespace(site_dir=str(site), site_url=SITE))


def test_the_sitemap_leaves_out_the_pages_that_search_engines_are_to_leave_out(
    tmp_path,
):
    site = built(
        tmp_path,
        **{
            "index.html": "<title>Home</title>",
            "LOCAL-CONTROL.html": '<meta name="robots" content="noindex, follow">',
            "de__LOCAL-CONTROL.html": '<META NAME="robots" content="NOINDEX">',
            "de__index.html": '<meta name="robots" content="index, follow">',
        },
    )
    build(site)
    assert (site / "sitemap.xml").read_bytes() == UNLISTED.encode()
    assert gzip.decompress((site / "sitemap.xml.gz").read_bytes()) == UNLISTED.encode()


def test_a_sitemap_of_pages_to_index_stays_as_it_is(tmp_path):
    site = built(tmp_path, **{"index.html": "", "LOCAL-CONTROL.html": ""})
    written = (site / "sitemap.xml.gz").read_bytes()
    build(site)
    assert (site / "sitemap.xml").read_bytes() == SITEMAP.encode()
    assert (site / "sitemap.xml.gz").read_bytes() == written


def test_a_noindex_in_the_text_of_a_page_lists_it_still(tmp_path):
    """Only the head of a page speaks to search engines."""
    site = built(tmp_path)
    (site / "LOCAL-CONTROL.html").write_text(
        '<html><head></head><body><meta name="robots" content="noindex"></body>',
        "utf-8",
    )
    build(site)
    assert (site / "sitemap.xml").read_bytes() == SITEMAP.encode()


def test_a_sitemap_without_its_compressed_copy_is_written_alone(tmp_path):
    site = built(
        tmp_path, **{"LOCAL-CONTROL.html": '<meta name="robots" content="noindex">'}
    )
    (site / "sitemap.xml.gz").unlink()
    build(site)
    assert f"<loc>{SITE}LOCAL-CONTROL.html</loc>" not in (
        site / "sitemap.xml"
    ).read_text("utf-8")
    assert not (site / "sitemap.xml.gz").exists()
