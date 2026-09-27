"""Every link of the documentation leads to a file and a heading that exist.

Relative links and the repository's own absolute GitHub links are checked against
the working tree; other external links are not fetched. The README is also what
HACS shows, so it may only use absolute links and plain images.
"""

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).parents[1]
DOCUMENTS = sorted(
    path
    for pattern in ("*.md", "docs/**/*.md", ".github/*.md", "tests/e2e/*.md")
    for path in ROOT.glob(pattern)
)
IMAGES = ROOT / "docs" / "images"
CARD = ROOT / "custom_components" / "autodarts" / "frontend" / "autodarts-card.js"
# The repository's own addresses, which HACS needs instead of relative links.
OWN = re.compile(
    r"^https://(?:github\.com/Dennis-Otto/ha-autodarts/(?:blob|tree)/main"
    r"|raw\.githubusercontent\.com/Dennis-Otto/ha-autodarts/main)/"
)
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)"
)
HTML_LINK = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")
SRCSET = re.compile(r"""\bsrcset=["']([^"']+)["']""")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
HTML_ANCHOR = re.compile(r"""<a\s+(?:[^>]*\s)?(?:id|name)=["']([^"']+)["']""")


def prose(text: str) -> str:
    """The text without code, whose brackets and parentheses are no links."""
    return CODE.sub("", FENCE.sub("", text))


def slug(heading: str) -> str:
    """The anchor GitHub gives a heading."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    """The anchors of a document: its headings, numbered when repeated, and HTML anchors."""
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    found: set[str] = set(HTML_ANCHOR.findall(text))
    seen: dict[str, int] = {}
    for _, heading in HEADING.findall(text):
        base = slug(heading)
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def targets(path: Path) -> list[str]:
    text = prose(path.read_text(encoding="utf-8"))
    links = MARKDOWN_LINK.findall(text) + HTML_LINK.findall(text)
    for srcset in SRCSET.findall(text):
        links += [part.split()[0] for part in srcset.split(",") if part.strip()]
    return links


def resolve(document: Path, target: str) -> tuple[Path, str] | None:
    """The local file and anchor a link points to, or None for a foreign link."""
    if match := OWN.match(target):
        target = target[match.end() :]
        base = ROOT
    elif re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
        return None
    else:
        base = document.parent
    location, _, anchor = target.partition("#")
    location = unquote(location.split("?", 1)[0])
    file = (base / location).resolve() if location else document
    return file, unquote(anchor)


def test_the_documents_are_found():
    names = {path.relative_to(ROOT).as_posix() for path in DOCUMENTS}
    assert {"README.md", "docs/README.md", "docs/de/README.md"} <= names


@pytest.mark.parametrize(
    "document", DOCUMENTS, ids=lambda path: path.relative_to(ROOT).as_posix()
)
def test_links_lead_to_files_and_headings(document):
    broken = []
    for target in targets(document):
        resolved = resolve(document, target)
        if resolved is None:
            continue
        file, anchor = resolved
        if not file.exists():
            broken.append(f"{target}: no such file")
        elif anchor and file.suffix == ".md" and anchor not in anchors(file):
            broken.append(f"{target}: no heading #{anchor}")
    assert not broken, "\n".join(broken)


def test_the_readme_works_in_hacs():
    """HACS shows the README outside GitHub: absolute links and no <picture>."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "<picture" not in text
    relative = [
        target
        for target in targets(ROOT / "README.md")
        if not target.startswith(("https://", "http://", "#", "mailto:"))
    ]
    assert not relative, relative


def test_every_image_has_a_description():
    missing = []
    for document in DOCUMENTS:
        text = prose(document.read_text(encoding="utf-8"))
        for tag in re.findall(r"<img\b[^>]*>", text):
            alt = re.search(r"""\balt=["']([^"']*)["']""", tag)
            if not alt or len(alt.group(1).split()) < 2:
                missing.append(f"{document.name}: {tag[:80]}")
        for alt in re.findall(r"!\[([^\]]*)\]\(", text):
            if alt.strip() in ("", "Import", "Image"):
                missing.append(f"{document.name}: ![{alt}]")
    assert not missing, "\n".join(missing)


def test_every_image_is_shown_in_both_languages():
    """The images of the documentation exist in English and German, and are used."""
    english = {path.name for path in (IMAGES / "en").iterdir()}
    german = {path.name for path in (IMAGES / "de").iterdir()}
    assert english == german
    used = set()
    for document in DOCUMENTS:
        for target in targets(document):
            if resolved := resolve(document, target):
                used.add(resolved[0])
    unused = sorted(
        f"{language}/{name}"
        for language in ("en", "de")
        for name in english
        if (IMAGES / language / name).resolve() not in used
    )
    assert not unused, unused


def test_the_card_picker_links_to_the_card_guide():
    """Each card in the card picker opens its section of the card guide."""
    pages = re.findall(
        r'"((?:de/)?[a-z-]+\.md#[^"]+)"', CARD.read_text(encoding="utf-8")
    )
    assert len(pages) >= 14
    for page in pages:
        file, _, anchor = page.partition("#")
        assert anchor in anchors(ROOT / "docs" / file), page
