"""The diagrams of the documentation: Mermaid sources in docs/diagrams, drawn by
scripts/render_diagrams.sh as pictures for a light and a dark theme in each
language, because the GitHub app and HACS show Mermaid only as its code.

The script runs here with a stand-in for docker, as the tests of the screenshot tool
run theirs."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SOURCES = ROOT / "docs" / "diagrams"
IMAGES = ROOT / "docs" / "images"
SCRIPT = ROOT / "scripts" / "render_diagrams.sh"
LANGUAGES = ("en", "de")
THEMES = ("light", "dark")

# The front matter of a source, such as a wider wrapping of its labels.
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
# A <picture> of the documentation: its dark source and its light image.
PICTURE = re.compile(
    r"<picture>\s*<source [^>]*srcset=\"(?P<dark>[^\"]+)\">\s*"
    r"<img src=\"(?P<light>[^\"]+)\" alt=\"(?P<alt>[^\"]*)\"[^>]*>\s*</picture>"
)


def names() -> list[str]:
    """Every diagram, by the name its pictures carry."""
    return sorted({path.name.split(".")[0] for path in SOURCES.glob("*.mmd")})


def source(name: str, language: str) -> str:
    return (SOURCES / f"{name}.{language}.mmd").read_text(encoding="utf-8")


def accessible(text: str, key: str) -> str:
    """The accTitle or accDescr of a source."""
    found = re.findall(rf"^  {key}: (.+)$", text, re.MULTILINE)
    assert len(found) == 1, f"{key} once, found {len(found)}"
    return found[0]


def pages() -> list[Path]:
    return sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").glob("*.md"))


def test_the_diagrams_are_found():
    assert {"add-board", "connection", "choose-blueprint", "dart-journey"} <= set(
        names()
    )


@pytest.mark.parametrize("name", names())
def test_every_diagram_has_a_source_in_each_language(name):
    for language in LANGUAGES:
        assert (SOURCES / f"{name}.{language}.mmd").is_file(), language


@pytest.mark.parametrize("name", names())
def test_every_diagram_runs_from_top_to_bottom_with_a_title_for_screen_readers(name):
    """A diagram keeps its size in a narrow column; its picture repeats the title."""
    for language in LANGUAGES:
        text = FRONT_MATTER.sub("", source(name, language), count=1)
        assert text.startswith("flowchart TB\n"), language
        assert accessible(text, "accTitle")
        description = accessible(text, "accDescr")
        # The alt of a picture repeats it inside double quotes.
        assert '"' not in description, language


@pytest.mark.parametrize("name", names())
def test_every_diagram_has_a_picture_for_each_theme(name):
    for language in LANGUAGES:
        for theme in THEMES:
            assert (IMAGES / language / f"{name}-{theme}.png").is_file(), (
                language,
                theme,
            )


def test_every_picture_of_a_diagram_names_it_and_follows_the_theme():
    """The alt of a picture starts with the title of its source, in the language of
    the picture, and the dark theme gets the dark picture."""
    diagrams = set(names())
    wrong, shown = [], set()
    for page in pages():
        text = page.read_text(encoding="utf-8")
        for match in PICTURE.finditer(text):
            light = re.search(r"images/(en|de)/([\w-]+)-light\.png$", match["light"])
            if not light or light[2] not in diagrams:
                continue
            language, name = light[1], light[2]
            shown.add((name, language))
            title = accessible(source(name, language), "accTitle")
            if not match["alt"].startswith(f"{title}: "):
                wrong.append(f"{page.name}: {name}: {match['alt'][:60]!r}")
            if match["dark"] != match["light"].replace("-light.png", "-dark.png"):
                wrong.append(f"{page.name}: {name}: dark picture {match['dark']}")
    assert not wrong, "\n".join(wrong)
    for name in ("add-board", "connection", "choose-blueprint", "dart-journey"):
        assert {(name, language) for language in LANGUAGES} <= shown, name


# render_diagrams.sh ------------------------------------------------------------------

DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$CALLS"
"""

# The bash of the PATH, which on Windows is that of Git rather than WSL's.
BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="the script runs in bash")


def render(
    tmp_path: Path, *arguments: str
) -> tuple[subprocess.CompletedProcess[str], list[tuple[str, str, str]]]:
    """Run render_diagrams.sh with a stand-in for docker: the result and the
    pictures it asked docker for, as (language, diagram, theme)."""
    docker = tmp_path / "docker"
    docker.write_text(DOCKER, encoding="utf-8", newline="\n")
    docker.chmod(0o755)
    calls = tmp_path / "calls"
    calls.touch()
    result = subprocess.run(
        [str(BASH), SCRIPT.as_posix(), *arguments],
        env={**os.environ, "DOCKER_BIN": docker.as_posix(), "CALLS": str(calls)},
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    pictures = []
    for call in calls.read_text(encoding="utf-8").splitlines():
        found = re.search(
            r"--input /data/docs/diagrams/([\w-]+)\.(\w+)\.mmd"
            r" --output /data/docs/images/(\w+)/([\w-]+)-(\w+)\.png"
            r" --configFile /data/docs/diagrams/(\w+)\.json",
            call,
        )
        assert found, call
        diagram, language, folder, picture, theme, config = found.groups()
        assert (diagram, language, theme) == (picture, folder, config), call
        pictures.append((language, diagram, theme))
    return result, pictures


@needs_bash
def test_the_script_draws_every_diagram_in_both_themes(tmp_path):
    result, pictures = render(tmp_path)

    assert result.returncode == 0, result.stderr
    assert sorted(pictures) == sorted(
        (language, name, theme)
        for name in names()
        for language in LANGUAGES
        for theme in THEMES
    )


@needs_bash
def test_the_script_draws_only_the_diagrams_it_is_given(tmp_path):
    result, pictures = render(tmp_path, "connection", "add-board")

    assert result.returncode == 0, result.stderr
    assert sorted(pictures) == sorted(
        (language, name, theme)
        for name in ("add-board", "connection")
        for language in LANGUAGES
        for theme in THEMES
    )
    assert "rendered docs/images/de/connection-dark.png" in result.stdout


@needs_bash
def test_the_script_refuses_a_diagram_that_does_not_exist(tmp_path):
    result, pictures = render(tmp_path, "connection", "no-such-diagram")

    assert result.returncode == 2
    assert "No diagram no-such-diagram" in result.stderr
    assert not pictures
