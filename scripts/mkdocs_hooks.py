"""A hook of MkDocs for the website of the documentation (mkdocs.yml).

MkDocs turns the links of the Markdown, such as [Games](games.md), into links to
the pages of the website, but leaves the links in HTML as they are: those of the
tables of the start pages, such as <a href="games.md">, would lead to the .md
files there, which the website doesn't have. This hook gives them the address of
the page, as MkDocs does for the Markdown. On GitHub, both kinds lead to the .md
files. A link to a page that doesn't exist fails the build, as it does in the
Markdown.
"""

from __future__ import annotations

import logging
import posixpath
import re
from typing import Any

# The warnings of MkDocs, which mkdocs build --strict counts.
log = logging.getLogger("mkdocs.hooks.html_links")

# A relative link in HTML to a Markdown file, with an optional anchor.
LINK = re.compile(r'href="(?![a-z][a-z0-9+.-]*:|/|#)([^"#]+\.md)(#[^"]*)?"')


def on_page_content(html: str, page: Any, config: Any, files: Any) -> str:
    """The HTML of the page, with its links to Markdown files leading to pages."""
    source = page.file.src_uri

    def replace(match: re.Match[str]) -> str:
        path, anchor = match.group(1), match.group(2) or ""
        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        file = files.get_file_from_path(target)
        if file is None:
            log.warning("%s links in its HTML to %s, which isn't a page", source, path)
            return match.group(0)
        return f'href="{file.url_relative_to(page.file)}{anchor}"'

    return LINK.sub(replace, html)
