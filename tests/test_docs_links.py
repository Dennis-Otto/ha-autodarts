"""Every link of the documentation leads to a file and a heading that exist.

Relative links, the repository's own absolute GitHub links and the links to its
documentation website are checked against the working tree; other external links
are not fetched. The README is also what HACS shows, so it may only use absolute
links and plain images. Where the text counts the blueprints, the dashboard cards
or the actions, the number is the one the code has.
"""

import json
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

import pytest
import yaml

ROOT = Path(__file__).parents[1]
DOCUMENTS = sorted(
    path
    for pattern in ("*.md", "docs/**/*.md", ".github/*.md", "tests/e2e/*.md")
    for path in ROOT.glob(pattern)
)
IMAGES = ROOT / "docs" / "images"
DOCS = ROOT / "docs"
# The front matter of a page of the website, which MkDocs reads: a description that
# search engines show under its title, as long as Google shows one, or the page that
# took the place of a page that moved (scripts/mkdocs_hooks.py).
FRONT_MATTER = re.compile(r"\A---\n(.*?)^---$", re.MULTILINE | re.DOTALL)
DESCRIPTION = range(50, 161)
MOVED = "moved"
CARD = ROOT / "custom_components" / "autodarts" / "frontend" / "autodarts-card.js"
# The repository's own addresses, which HACS needs instead of relative links.
OWN = re.compile(
    r"^https://(?:github\.com/Dennis-Otto/ha-autodarts/(?:blob|tree)/main"
    r"|raw\.githubusercontent\.com/Dennis-Otto/ha-autodarts/main)/"
)
# The documentation website (mkdocs.yml): docs/<page>.md is <page>.html, and its
# German page docs/<page>.de.md is de/<page>.html, or the English page where no
# German one exists; index.md is the start page.
WEBSITE = "https://dennis-otto.github.io/ha-autodarts/"
WEBSITE_PAGE = re.compile(r"^(?:(de)/)?([^#?]*)")
# A line of a page of the website that includes a file of the repository, or a
# section of one, with pymdownx.snippets, such as --8<-- "CHANGELOG.md".
INCLUDE = re.compile(r'^--8<-- "([^":]+)(?::([\w-]+))?"$', re.MULTILINE)
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)"
)
HTML_LINK = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")
SRCSET = re.compile(r"""\bsrcset=["']([^"']+)["']""")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
HTML_ANCHOR = re.compile(r"""<a\s+(?:[^>]*\s)?(?:id|name)=["']([^"']+)["']""")
# A file or folder of the repository named in the text, such as `tests/test_api.py`.
REPOSITORY_PATH = re.compile(
    r"`((?:tests|custom_components|blueprints|scripts|\.github|\.devcontainer|docs)"
    r"/[\w./-]*)`"
)
# Folders the tests create while they run, with everything in them.
GENERATED = ("tests/e2e/artifacts/",)
# The number words of both languages, which the text uses for counts.
NUMBERS = {
    word: number
    for words in (
        "one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen twenty",
        "eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn "
        "vierzehn fünfzehn sechzehn siebzehn achtzehn neunzehn zwanzig",
    )
    for number, word in enumerate(words.split(), start=1)
}
NUMBER = r"(\d+|" + "|".join(NUMBERS) + r")"
# A count starts a word: counts above twenty are written in digits, and the end of
# a compound such as "twenty-one" or "einundzwanzig" is no count of its own.
START = r"(?<![\w-])"
# What the text counts, as it says it in English and German: "thirteen blueprints",
# "sieben Dashboard-Karten", "the fourteen `autodarts.*` actions" and "die
# vierzehn Aktionen `autodarts.*`". A count of some of them, such as "two voice
# blueprints", names no total and is left alone.
COUNTED = {
    kind: re.compile(pattern, re.IGNORECASE)
    for kind, pattern in {
        "blueprints": rf"{START}{NUMBER}\s+(?:Autodarts[\s-]+)?Blueprints\b",
        "cards": rf"{START}{NUMBER}\s+(?:Dashboard[\s-]+)?(?:cards|Karten)\b",
        "actions": rf"{START}{NUMBER}\s+(?:`autodarts\.\*`\s+actions|Aktionen\s+`autodarts\.\*`)",
    }.items()
}
# Code blocks, also the indented ones of tabs and admonitions, count nothing.
COUNTED_FENCE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1", re.MULTILINE | re.DOTALL)
# Where the text counts them: the documents and the descriptions of the website,
# the repository and the project. The roadmap counts what a release brought and a
# decision record the state of its day, so neither has to follow the code.
COUNTING = [
    path
    for path in DOCUMENTS
    if path.name != "CHANGELOG.md"
    and not path.name.startswith("roadmap.")
    and path.parent.name != "decisions"
] + [
    ROOT / "mkdocs.yml",
    ROOT / ".github" / "repository.toml",
    ROOT / ".copier-answers.yml",
]


def prose(text: str) -> str:
    """The text without code, whose brackets and parentheses are no links."""
    return CODE.sub("", FENCE.sub("", text))


def slug(heading: str) -> str:
    """The anchor GitHub gives a heading."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


def included(text: str) -> str:
    """The text with the files and sections it includes, as the website shows it."""

    def include(match: re.Match[str]) -> str:
        source = (ROOT / match[1]).read_text(encoding="utf-8")
        if section := match[2]:
            source = source.partition(f"[start:{section}]")[2]
            source = source.partition(f"[end:{section}]")[0]
        return source

    return INCLUDE.sub(include, text)


def anchors(path: Path, website: bool = False) -> set[str]:
    """The anchors of a document: its headings, numbered when repeated, and HTML
    anchors, with those of the files it includes on the website."""
    text = path.read_text(encoding="utf-8")
    text = FENCE.sub("", included(text) if website else text)
    found: set[str] = set(HTML_ANCHOR.findall(text))
    seen: dict[str, int] = {}
    for _, heading in HEADING.findall(text):
        base = slug(heading)
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def targets(path: Path) -> list[str]:
    return targets_of(path.read_text(encoding="utf-8"))


def targets_of(text: str) -> list[str]:
    """The addresses of the links and pictures of a text."""
    text = prose(text)
    links = MARKDOWN_LINK.findall(text) + HTML_LINK.findall(text)
    for srcset in SRCSET.findall(text):
        links += [part.split()[0] for part in srcset.split(",") if part.strip()]
    return links


def website_page(address: str) -> tuple[Path, str]:
    """The file of docs/ and the anchor of an address of the documentation website."""
    german, page = WEBSITE_PAGE.match(address).groups()
    # A file that the website serves as it is, such as the page of the live demo.
    if not german and page.endswith(".html") and (ROOT / "docs" / page).is_file():
        return ROOT / "docs" / page, ""
    name = (page or "index.html").removesuffix(".html")
    anchor = address.partition("#")[2]
    file = ROOT / "docs" / f"{name}.de.md"
    if not german or not file.is_file():
        file = ROOT / "docs" / f"{name}.md"
    return file, unquote(anchor)


def resolve(document: Path, target: str) -> tuple[Path, str] | None:
    """The local file and anchor a link points to, or None for a foreign link."""
    if target.startswith(WEBSITE):
        return website_page(target.removeprefix(WEBSITE))
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
    assert {
        "README.md",
        "docs/README.md",
        "docs/README.de.md",
        "docs/index.md",
    } <= names


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
        website = target.startswith(WEBSITE)
        if not file.exists():
            broken.append(f"{target}: no such file")
        elif anchor and file.suffix == ".md" and anchor not in anchors(file, website):
            broken.append(f"{target}: no heading #{anchor}")
    assert not broken, "\n".join(broken)


def test_the_repository_paths_in_the_text_exist():
    """Evidence such as the tests named in the security guide can be found."""
    missing = [
        f"{document.relative_to(ROOT).as_posix()}: {path}"
        for document in DOCUMENTS
        for path in REPOSITORY_PATH.findall(FENCE.sub("", document.read_text("utf-8")))
        if not path.startswith(GENERATED) and not (ROOT / path).exists()
    ]
    assert not missing, "\n".join(missing)


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
    """Each card in the card picker opens its section of the card guide on the website."""
    text = CARD.read_text(encoding="utf-8")
    assert f'const DOCUMENTATION = "{WEBSITE.rstrip("/")}";' in text
    pages = re.findall(r'"((?:de/)?[a-z-]+\.html#[^"]+)"', text)
    assert len(pages) >= 16
    for page in pages:
        file, anchor = website_page(page)
        assert file.exists() and anchor in anchors(file), page


def test_the_manifest_links_to_the_website():
    manifest = json.loads((CARD.parent.parent / "manifest.json").read_text("utf-8"))
    assert manifest["documentation"] == WEBSITE


def test_every_german_page_sits_next_to_its_english_page():
    """A German page is named like its English page with .de (decision 0009)."""
    german = sorted((ROOT / "docs").glob("**/*.de.md"))
    assert len(german) >= 18
    lonely = [
        path.relative_to(ROOT).as_posix()
        for path in german
        if not path.with_name(path.name.removesuffix(".de.md") + ".md").exists()
    ]
    assert not lonely, lonely


def front_matter(path: Path) -> dict[str, object]:
    """The front matter of a page, between two lines --- at its start."""
    match = FRONT_MATTER.match(path.read_text("utf-8"))
    return yaml.safe_load(match[1]) if match else {}


def website_pages() -> list[Path]:
    """The pages of the website: the Markdown in docs/ but what mkdocs.yml excludes."""
    excluded = yaml.safe_load((ROOT / "mkdocs.yml").read_text("utf-8"))["exclude_docs"]
    patterns = excluded.split()
    # Each pattern starts at docs/, and one that ends with / is a folder.
    assert all(pattern.startswith("/") for pattern in patterns), patterns
    pages = []
    for path in sorted(DOCS.glob("**/*.md")):
        name = "/" + path.relative_to(DOCS).as_posix()
        if not any(
            name == pattern or (pattern.endswith("/") and name.startswith(pattern))
            for pattern in patterns
        ):
            pages.append(path)
    return pages


def test_every_page_of_the_website_has_a_description_of_its_own():
    """Search engines and the previews of shared links show it under the title.

    A page that moved leads on to another page and needs none. A copy of the
    template of a decision says what it decided instead of the template's words.
    """
    pages = [path for path in website_pages() if MOVED not in front_matter(path)]
    assert len(pages) >= 50
    template = front_matter(DOCS / "decisions" / "0000-template.md")["description"]
    seen: dict[object, str] = {template: "the template of a decision"}
    wrong = []
    for path in pages:
        name = path.relative_to(ROOT).as_posix()
        description = front_matter(path).get("description")
        if not isinstance(description, str) or len(description) not in DESCRIPTION:
            wrong.append(f"{name}: {description!r} is not 50 to 160 characters long")
        elif description in seen:
            wrong.append(f"{name} has the description of {seen[description]}")
        seen[description] = name
    assert not wrong, wrong


def test_a_page_that_moved_leads_to_a_page_of_the_website():
    pages = website_pages()
    moved = {path: front_matter(path).get(MOVED) for path in pages}
    moved = {path: target for path, target in moved.items() if target}
    assert [path.name for path in moved] == ["LOCAL-CONTROL.md", "SETUP-DE.md"]
    lost = [
        f"{path.name} moved to {target}"
        for path, target in moved.items()
        if not isinstance(target, str)
        or (path.parent / target).resolve() not in pages
        or MOVED in front_matter(path.parent / target)
    ]
    assert not lost, lost


def test_the_repository_has_the_topics_that_github_shows():
    """GitHub shows twenty topics at most, each of small letters, digits and -."""
    settings = tomllib.loads((ROOT / ".github" / "repository.toml").read_text("utf-8"))
    project = ROOT / ".github" / "repository.project.toml"
    extra = tomllib.loads(project.read_text("utf-8"))
    topics = settings["repository"]["topics"]
    topics += [t for t in extra["repository"]["topics"] if t not in topics]
    assert len(topics) == len(set(topics)) <= 20, topics
    assert all(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", topic) for topic in topics)
    assert {"autodarts", "home-assistant", "wled", "darts-scoreboard"} <= set(topics)


def counts_in_the_code() -> dict[str, int]:
    """How many blueprints, dashboard cards and actions the integration brings."""
    blueprints = ROOT / "blueprints" / "automation" / "autodarts"
    cards = re.search(
        r"^const CARDS = \[$(.*?)^\];$",
        CARD.read_text("utf-8"),
        re.MULTILINE | re.DOTALL,
    )
    assert cards, "autodarts-card.js has no list CARDS for the card picker"
    services = (CARD.parent.parent / "services.yaml").read_text("utf-8")
    return {
        "blueprints": len(list(blueprints.glob("*.yaml"))),
        "cards": len(re.findall(r"^\s*\{ type: ", cards.group(1), re.MULTILINE)),
        "actions": len(re.findall(r"^[a-z_]+:", services, re.MULTILINE)),
    }


def claims(text: str):
    """The counts a text names: what it counts, the number, the line and the words."""
    # Examples in code blocks count nothing; their lines stay for the line numbers.
    text = COUNTED_FENCE.sub(lambda fence: "\n" * fence.group().count("\n"), text)
    for kind, pattern in COUNTED.items():
        for match in pattern.finditer(text):
            word = match.group(1).lower()
            number = int(word) if word.isdigit() else NUMBERS[word]
            yield kind, number, text.count("\n", 0, match.start()) + 1, match.group()


def wrong_counts(text: str, actual: dict[str, int]) -> list[str]:
    """The counts of a text that differ from the code, with the right number."""
    return [
        f"line {line}: {words!r}, but there are {actual[kind]} {kind}"
        for kind, number, line, words in claims(text)
        if number != actual[kind]
    ]


def test_the_code_has_what_the_text_counts():
    """The counts come from the blueprint files, the card picker and the actions."""
    actual = counts_in_the_code()
    assert actual["blueprints"] >= 13
    assert actual["cards"] >= 7
    assert actual["actions"] >= 14


def test_the_counts_in_the_prose_match_the_code():
    """A new blueprint, card or action updates every sentence that counts them."""
    actual = counts_in_the_code()
    named: set[str] = set()
    wrong: list[str] = []
    for path in COUNTING:
        text = path.read_text(encoding="utf-8")
        named |= {kind for kind, *_ in claims(text)}
        name = path.relative_to(ROOT).as_posix()
        wrong += [f"{name}, {problem}" for problem in wrong_counts(text, actual)]
    assert named == set(COUNTED)
    assert not wrong, "\n".join(wrong)


@pytest.mark.parametrize(
    ("sentence", "kind", "number"),
    [
        ("Twelve blueprints: light show, callers and reports.", "blueprints", 12),
        ("Zwölf Blueprints: Lichtshow, Caller und Berichte.", "blueprints", 12),
        ("The blueprints page with the eleven Autodarts blueprints", "blueprints", 11),
        ("Die Blueprint-Seite mit den elf Autodarts-Blueprints", "blueprints", 11),
        ("It brings 12 blueprints.", "blueprints", 12),
        ("The integration includes\nsix cards.", "cards", 6),
        ("Six dashboard cards and an automatic dashboard", "cards", 6),
        ("Sechs Dashboard-Karten und ein automatisches Dashboard", "cards", 6),
        ("It brings seven dashboard\n    cards to the picker.", "cards", 7),
        ("Some day there are 21 Autodarts\nblueprints.", "blueprints", 21),
        ("the thirteen `autodarts.*` actions, which need a login", "actions", 13),
        (
            "die dreizehn Aktionen `autodarts.*`, die eine Anmeldung brauchen",
            "actions",
            13,
        ),
    ],
)
def test_a_wrong_count_is_found(sentence, kind, number):
    """The sentences the docs once had wrong, in both languages, and their kin."""
    assert [(found, said) for found, said, *_ in claims(sentence)] == [(kind, number)]
    code = {"blueprints": 0, "cards": 0, "actions": 0}
    assert not wrong_counts(sentence, {**code, kind: number})
    wrong = wrong_counts(sentence, {**code, kind: number + 1})
    assert len(wrong) == 1
    assert wrong[0].endswith(f", but there are {number + 1} {kind}")


def test_a_wrong_count_names_its_line():
    text = (
        "# Cards\n\n```yaml\ntype: custom:autodarts-card\n```\n\nSeven dashboard cards."
    )
    assert wrong_counts(text, {"cards": 8}) == [
        "line 7: 'Seven dashboard cards', but there are 8 cards"
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "Two voice blueprints start games and enter darts.",
        "Cricket on 20 to 10 and the bull, twelve numbers in all.",
        "The automation runs two actions after the takeout.",
        "One card per player, and a dashboard for all of them.",
        "```yaml\n# three blueprints\n```",
        '=== "YAML"\n\n    ```yaml\n    # three blueprints\n    ```',
        "Some day twenty-one blueprints, einundzwanzig Blueprints.",
    ],
)
def test_a_count_of_some_names_no_total(sentence):
    assert not list(claims(sentence))


COMPARE = re.compile(
    r"<!-- --8<-- \[start:compare\] -->\n(.*?)<!-- --8<-- \[end:compare\] -->",
    re.DOTALL,
)
BLOB = "https://github.com/Dennis-Otto/ha-autodarts/blob/main/"
RELATIVE_LINK = re.compile(r"\]\((?![a-z]+:)([^)#][^)]*)\)")
# A page of the documentation, written as a relative link of docs/ or as a link to
# GitHub, with its anchor.
DOCS_PAGE = re.compile(
    rf"^(?:{re.escape(BLOB)}docs/)?"
    r"(?P<page>(?![a-z][a-z0-9+.-]*:|\.\./|/)[^#]+?)\.md(?P<anchor>#.*)?$"
)
# The READMEs that link to the website: the one of the project, which HACS shows,
# and its German translation, whose links lead to the German website.
READMES = {"README.md": False, "docs/README.de.md": True}
# A section of a page that the website includes, whose links are those of docs/.
SHARED = re.compile(r"\[start:([\w-]+)\].*?\[end:\1\]", re.DOTALL)


def compare_section(name: str) -> str:
    match = COMPARE.search((ROOT / "docs" / name).read_text(encoding="utf-8"))
    assert match, f"docs/{name} has no compare snippet"
    return match.group(1).strip()


def website_address(link: str, german: bool) -> str | None:
    """The address on the website of a link of a README to a page of docs/ or to the
    changelog, for the README of one language, or None for any other link.

    A German page is in de/. A page without it is English if a German page of its
    name exists; otherwise it is the page of both websites, and the German README
    stays on the German website, as scripts/mkdocs_hooks.py does.
    """
    if link == f"{BLOB}CHANGELOG.md":
        return f"{WEBSITE}{'de/' if german else ''}changelog.html"
    match = DOCS_PAGE.match(link)
    if match is None:
        return None
    page, anchor = match["page"], match["anchor"] or ""
    if page.endswith(".de"):
        return f"{WEBSITE}de/{page.removesuffix('.de')}.html{anchor}"
    if page == "README":
        return f"{WEBSITE}{'de/' if german else ''}{anchor}"
    english = (DOCS / f"{page}.de.md").is_file()
    return f"{WEBSITE}{'de/' if german and not english else ''}{page}.html{anchor}"


def website_links(text: str, german: bool) -> str:
    """The links of a docs page to other pages as the READMEs have them."""
    return RELATIVE_LINK.sub(
        lambda link: f"]({website_address(link[1], german) or link[1]})", text
    )


@pytest.mark.parametrize(
    ("link", "german", "address"),
    [
        ("faq.md#top", False, f"{WEBSITE}faq.html#top"),
        (f"{BLOB}docs/faq.md", False, f"{WEBSITE}faq.html"),
        ("faq.de.md#oben", True, f"{WEBSITE}de/faq.html#oben"),
        ("development.md", True, f"{WEBSITE}development.html"),
        ("releases.md#x", True, f"{WEBSITE}de/releases.html#x"),
        ("decisions/0001-x.md", True, f"{WEBSITE}de/decisions/0001-x.html"),
        (f"{BLOB}docs/README.md#languages", False, f"{WEBSITE}#languages"),
        (f"{BLOB}CHANGELOG.md", True, f"{WEBSITE}de/changelog.html"),
        ("README.md", True, f"{WEBSITE}de/"),
        (f"{BLOB}SECURITY.md", False, None),
        ("../CHANGELOG.md", False, None),
        ("https://autodarts.com/", False, None),
    ],
)
def test_a_readme_link_to_a_page_has_its_address_on_the_website(link, german, address):
    assert website_address(link, german) == address


def test_website_links_leave_the_other_links():
    text = "[a](faq.md#top) [b](https://autodarts.com/) [c](#here)"
    assert website_links(text, False) == (
        f"[a]({WEBSITE}faq.html#top) [b](https://autodarts.com/) [c](#here)"
    )


def test_the_readmes_link_to_the_pages_of_the_website():
    """The website has the search, the dark mode and the switch of the language.

    GitHub shows the files of docs/ as plain Markdown; HACS can't follow relative
    links. The German README keeps the line of GitHub at its top, with the project
    page and its English overview, and the section that the website includes.
    """
    found = []
    for name, german in READMES.items():
        text = (ROOT / name).read_text(encoding="utf-8")
        if german:
            text = SHARED.sub("", text.split("\n", 3)[3])
        for target in targets_of(text):
            if (address := website_address(target, german)) is not None:
                found.append(f"{name}: {target} -> {address}")
    assert not found, "Link to the website instead:\n" + "\n".join(found)


@pytest.mark.parametrize(
    ("source", "readme"),
    [("coming-from.md", "README.md"), ("coming-from.de.md", "docs/README.de.md")],
)
def test_the_readmes_carry_the_comparison_of_the_website(source, readme):
    """GitHub and HACS can't include the snippet, so the READMEs copy it, with
    links to the website."""
    section = website_links(compare_section(source), READMES[readme])
    assert section in (ROOT / readme).read_text(encoding="utf-8"), (
        f"{readme} differs from the compare snippet of docs/{source}"
    )
