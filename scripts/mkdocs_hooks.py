"""Hooks of MkDocs for the website of the documentation (mkdocs.yml).

The pages read the same on GitHub and on the website, with their links written for
GitHub. The hooks lead them to the pages of the website where MkDocs alone can't:

- MkDocs turns the links of the Markdown, such as [Games](games.md), into links to
  the pages of the website, but leaves the links in HTML as they are: those of a
  table, such as <a href="games.md">, would lead to the .md files there, which the
  website doesn't have. They get the address of the page, as the Markdown does.
- README.md and README.de.md are the start pages on GitHub and stay off the
  website, which starts with index.md and index.de.md. A link to them leads to the
  start page of the website.
- The German pages sit next to the English ones, named like them with .de, such as
  games.de.md next to games.md, and the plugin i18n builds the German website in
  de/ from them, with the English page where no German one exists. Each website is
  built on its own and knows only its own pages, so a link to the other language,
  such as [Deutsch](games.de.md) on an English page or [English](games.md) on a
  German one, leads to that page of the other website. So do the links of an
  English page on the German website, whose anchors are those of English pages.
- A page of the German website lies one folder deeper than its file, in de/, so
  the pictures of its HTML, such as <img src="images/de/card.png">, get the path
  from there, as those of the Markdown do.
- The live demo in demo/ plays the cards of the integration, which the website
  takes from the integration as they are, so that it always shows the cards of its
  version: after the build, they join the page of the demo.

They also give search engines and the previews of shared links what they need:

- A start page is titled with the name of the website alone. Material does so on
  the English one, but titles the German one "Start - Autodarts für Home
  Assistant", after its tab.
- A page that moved, such as LOCAL-CONTROL.md, keeps the old links of GitHub
  working. Its front matter names the page that took its place, moved:
  installation.md, and the hooks make it lead there at once, in the language of
  its website: search engines take that page for it and leave the old one out, and
  so does the search of the website.
- A page that asks search engines to leave it out, with <meta name="robots"
  content="noindex">, leaves the sitemap too, which lists the pages to index.

A link to a page that doesn't exist fails the build, as it does in the Markdown.
"""

from __future__ import annotations

import gzip
import logging
import posixpath
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.html_links")

# The language of the pages named with .de, and the one of the others.
GERMAN = "de"
ENGLISH = "en"
# The start pages on GitHub, and those of the website that take their place.
START = {"README.md": "index.md", f"README.{GERMAN}.md": f"index.{GERMAN}.md"}

# The cards of the integration, and where the live demo loads them from.
CARDS = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "autodarts"
    / "frontend"
    / "autodarts-card.js"
)
DEMO = "demo"

# The key of the front matter of a page that moved, with the page that took its
# place, and the one that the hooks give it with the address of that page.
MOVED_TO = "moved"
REDIRECT = "redirect"
# The head of a page that moved, as the redirects of MkDocs have it: search engines
# leave it out and follow its links, and the browser goes on to the address at once.
REDIRECT_HEAD = (
    '<meta name="robots" content="noindex, follow">'
    '<meta http-equiv="refresh" content="0; url={address}">'
)
# The title of a page, and the titles of the previews of a shared link, which the
# social plugin of Material writes.
TITLE = re.compile(r"<title>[^<]*</title>")
SHARED_TITLE = re.compile(r'(<meta property="(?:og|twitter):title" content=")[^"]*"')
# The canonical address of a page, which Material writes in its head.
CANONICAL = re.compile(r'(<link rel="canonical" href=")([^"]*)"')
# A page that asks search engines to leave it out.
NOINDEX = re.compile(r'<meta\s+name="robots"\s+content="[^"]*\bnoindex\b', re.I)
# A page in the sitemap: its address and everything else MkDocs says about it.
LISTED = re.compile(r"[ \t]*<url>\s*<loc>([^<]+)</loc>.*?</url>[ \t]*\n?", re.DOTALL)

# An address that is no relative path: with a scheme, from the root, or an anchor.
ABSOLUTE = re.compile(r"[a-z][a-z0-9+.-]*:|/|#", re.IGNORECASE)
# A relative link in HTML to a Markdown file, with an optional anchor.
LINK = re.compile(r'href="(?![a-z][a-z0-9+.-]*:|/|#)([^"#]+\.md)(#[^"]*)?"')
# In the Markdown: code, whose links are examples; a relative link to a Markdown
# file, with an optional anchor, where a picture is no link; or an address in HTML.
SOURCE = re.compile(
    r"(?P<code>^[ \t]*(?P<fence>```|~~~).*?^[ \t]*(?P=fence)|`[^`\n]*`)"
    r"|(?<!!)\[(?P<text>(?:[^\[\]]|\[[^\]]*\])*)\]"
    r"\((?![a-z][a-z0-9+.-]*:|/|#)(?P<path>[^)\s#]+\.md)(?P<anchor>#[^)\s]*)?\)"
    r"|\b(?P<attribute>src|srcset|href)=(?P<quote>[\"'])(?P<value>[^\"']*)(?P=quote)",
    re.MULTILINE | re.DOTALL,
)


def website(page: Any) -> str:
    """The language of the website that page is built for, by its address."""
    return GERMAN if page.file.url.startswith(f"{GERMAN}/") else ENGLISH


def relative(target: str, source: str) -> str:
    """The path target as a link of the file source needs it."""
    return posixpath.relpath(target, posixpath.dirname(source) or ".")


def linked(page: Any, path: str) -> str:
    """The file of docs/ that a link of page leads to."""
    return posixpath.normpath(
        posixpath.join(posixpath.dirname(page.file.src_uri), path)
    )


def other_language(page: Any, target: str, docs: Path) -> str | None:
    """The address of target for a link of page, if target is in the other language.

    A page named with .de is German. A page without it is English if a German page
    of its name exists; otherwise it is the page of both websites, which the German
    one shows in English, and a link to it stays on the website of page. The
    addresses are those of use_directory_urls: false, as the blueprint sets it.
    """
    if target.endswith(f".{GERMAN}.md"):
        theirs = GERMAN
        address = f"{GERMAN}/{target.removesuffix(f'.{GERMAN}.md')}.html"
    elif (docs / f"{target.removesuffix('.md')}.{GERMAN}.md").is_file():
        theirs = ENGLISH
        address = f"{target.removesuffix('.md')}.html"
    else:
        return None
    if theirs == website(page):
        return None
    if not (docs / target).is_file():
        log.warning("%s links to %s, which isn't a page", page.file.src_uri, target)
        return None
    return relative(address, page.file.url)


def moved(page: Any, address: str) -> str:
    """A relative address of the HTML of page, from where the website puts page."""
    path, *rest = re.split(r"(?=[#?])", address, maxsplit=1)
    if not path or ABSOLUTE.match(path):
        return address
    return relative(linked(page, path), page.file.url) + "".join(rest)


def lead_on(page: Any, docs: Path, files: Any) -> None:
    """Let a page that moved lead to the page that took its place.

    The successor is the one of the website of page: on the German website its
    German page, if there is one. The head of page leads there (on_post_page), and
    the search of the website leaves page out.
    """
    target = linked(page, page.meta[MOVED_TO])
    german = f"{target.removesuffix('.md')}.{GERMAN}.md"
    if website(page) == GERMAN and (docs / german).is_file():
        target = german
    found = files.get_file_from_path(target)
    if found is None:
        log.warning(
            "%s moved to %s, which isn't a page",
            page.file.src_uri,
            page.meta[MOVED_TO],
        )
        return
    page.meta[REDIRECT] = found.url_relative_to(page.file)
    page.meta["search"] = {"exclude": True}


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    """The Markdown of the page, with its links for the website."""
    docs = Path(config.docs_dir)
    if MOVED_TO in page.meta:
        lead_on(page, docs, files)
    deeper = posixpath.dirname(page.file.url) != posixpath.dirname(page.file.src_uri)

    def replace(match: re.Match[str]) -> str:
        if match.group("code"):
            return match.group(0)
        if attribute := match.group("attribute"):
            value = match.group("value")
            if not deeper or (
                attribute == "href" and value.split("#")[0].endswith(".md")
            ):
                return match.group(0)
            if attribute == "srcset":
                value = ", ".join(
                    " ".join([moved(page, part.split()[0]), *part.split()[1:]])
                    for part in value.split(",")
                    if part.strip()
                )
            else:
                value = moved(page, value)
            quote = match.group("quote")
            return f"{attribute}={quote}{value}{quote}"
        text, anchor = match.group("text"), match.group("anchor") or ""
        file = linked(page, match.group("path"))
        target = START.get(file, file)
        if (address := other_language(page, target, docs)) is not None:
            return f'<a href="{address}{anchor}">{text}</a>'
        if target != file:
            return f"[{text}]({relative(target, page.file.src_uri)}{anchor})"
        return match.group(0)

    return SOURCE.sub(replace, markdown)


def on_page_content(html: str, page: Any, config: Any, files: Any) -> str:
    """The HTML of the page, with its links to Markdown files leading to pages."""
    docs = Path(config.docs_dir)

    def replace(match: re.Match[str]) -> str:
        path, anchor = match.group(1), match.group(2) or ""
        file = linked(page, path)
        target = START.get(file, file)
        address = other_language(page, target, docs)
        if address is None:
            found = files.get_file_from_path(target)
            if found is None:
                log.warning(
                    "%s links in its HTML to %s, which isn't a page",
                    page.file.src_uri,
                    path,
                )
                return match.group(0)
            address = found.url_relative_to(page.file)
        return f'href="{address}{anchor}"'

    return LINK.sub(replace, html)


def on_post_page(output: str, page: Any, config: Any) -> str:
    """The head of the page, for search engines and the previews of shared links.

    A start page is titled with the name of its website alone, and a page that moved
    leads to the page that took its place.
    """
    if page.file.src_uri in START.values():
        name = escape(config.site_name)
        output = TITLE.sub(lambda _: f"<title>{name}</title>", output, count=1)
        output = SHARED_TITLE.sub(lambda match: f'{match[1]}{name}"', output)
    if (address := page.meta.get(REDIRECT)) is not None:
        # The canonical address of the page that took its place, and not the own one,
        # which the sitemap keeps, so that unlist() finds the page there.
        output = CANONICAL.sub(
            lambda match: f'{match[1]}{escape(urljoin(match[2], address))}"', output
        )
        head = REDIRECT_HEAD.format(address=escape(address))
        output = output.replace("</head>", f"{head}</head>", 1)
    return output


def unlist(site: Path, site_url: str) -> None:
    """Leave the pages that ask search engines not to index them out of the sitemap.

    MkDocs lists every page there, in each of its languages, and writes it once as
    text and once compressed.
    """
    sitemap = site / "sitemap.xml"
    if not sitemap.is_file():
        return
    hidden = {
        urljoin(site_url, path.relative_to(site).as_posix())
        for path in site.rglob("*.html")
        if NOINDEX.search(path.read_text("utf-8").partition("</head>")[0])
    }
    listed = sitemap.read_bytes().decode("utf-8")
    kept = LISTED.sub(lambda match: "" if match[1] in hidden else match[0], listed)
    if kept == listed:
        return
    sitemap.write_bytes(kept.encode("utf-8"))
    compressed = site / "sitemap.xml.gz"
    if compressed.is_file():
        compressed.write_bytes(gzip.compress(kept.encode("utf-8"), mtime=0))


def on_post_build(config: Any) -> None:
    """The cards of the integration next to the page of the live demo, and the
    sitemap without the pages that search engines are to leave out.

    The hooks of the blueprint, listed after these in mkdocs.yml, copy the sitemap
    into every folder of pages afterwards.
    """
    site = Path(config.site_dir)
    demo = site / DEMO
    # The German website has no demo of its own; it links to the one in English.
    if (demo / "index.html").is_file():
        shutil.copyfile(CARDS, demo / CARDS.name)
    unlist(site, config.site_url or "")
