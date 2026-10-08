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

A link to a page that doesn't exist fails the build, as it does in the Markdown.
"""

from __future__ import annotations

import logging
import posixpath
import re
from pathlib import Path
from typing import Any

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.html_links")

# The language of the pages named with .de, and the one of the others.
GERMAN = "de"
ENGLISH = "en"
# The start pages on GitHub, and those of the website that take their place.
START = {"README.md": "index.md", f"README.{GERMAN}.md": f"index.{GERMAN}.md"}

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


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    """The Markdown of the page, with its links for the website."""
    docs = Path(config.docs_dir)
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
