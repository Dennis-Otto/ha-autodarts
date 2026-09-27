"""Translations, action descriptions, icons and card texts agree with the code,
and tool versions kept in two places agree with each other."""

import json
import re
from pathlib import Path

import pytest
import yaml

from custom_components.autodarts.binary_sensor import MOTION_SENSORS
from custom_components.autodarts.local_api import STANDBY_MINUTES
from custom_components.autodarts.local_coordinator import EVENT_TYPES, ISSUES
from custom_components.autodarts.practice import (
    GAME_OPTIONS,
    MAX_LEGS,
    MAX_PLAYERS,
    MAX_SETS,
)
from custom_components.autodarts.sensor import BOARD_STATES, LOCAL_STATES, MATCH_STATES
from custom_components.autodarts.services import (
    DELETE_PLAYER_SCHEMA,
    START_GAME_SCHEMA,
)

from .local_helpers import entity_id, setup_local

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "autodarts"
STRINGS = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
# Every translation file counts, so a new language joins every check below.
TRANSLATIONS = {
    path.stem: json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((INTEGRATION / "translations").glob("*.json"))
}
LANGUAGES = sorted(TRANSLATIONS)
SERVICES = yaml.safe_load((INTEGRATION / "services.yaml").read_text(encoding="utf-8"))
ICONS = json.loads((INTEGRATION / "icons.json").read_text(encoding="utf-8"))
SOURCES = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted(INTEGRATION.glob("*.py"))
)
CARD = (INTEGRATION / "frontend" / "autodarts-card.js").read_text(encoding="utf-8")
# Entities whose device class brings the icon.
DEVICE_CLASS_ICONS = {
    ("binary_sensor", "camera_problem"),
    ("binary_sensor", "individual_camera_problem"),
    ("binary_sensor", "local_connected"),
    ("button", "restart"),
    ("camera", "board_camera"),
    ("update", "board_software"),
}
# Abort reasons Home Assistant raises itself.
HOME_ASSISTANT_ABORTS = {"already_configured", "already_in_progress"}
# Words of the wrong form of address: German, Dutch and Spanish speak to the
# user informally, French formally, as Home Assistant does in these languages.
WRONG_ADDRESS = {
    "de": r"\b(Sie|Ihr|Ihre|Ihren|Ihrem)\b",
    "nl": r"\b(u|uw|U|Uw)\b",
    "fr": r"\b(tu|toi|ton|ta|tes|Tu|Toi|Ton|Ta|Tes)\b",
    "es": r"\b(usted|ustedes|Usted|Ustedes)\b",
}


def texts(tree: object, path: str = "") -> dict[str, str]:
    """Every translated text by its path, such as entity.sensor.round.name."""
    if isinstance(tree, str):
        return {path: tree}
    assert isinstance(tree, dict), path
    result: dict[str, str] = {}
    for key, value in tree.items():
        result |= texts(value, f"{path}.{key}" if path else key)
    return result


def placeholders(text: str) -> set[str]:
    return set(re.findall(r"{(\w+)}", text))


def states(platform: str, key: str, language: str = "en") -> set[str]:
    return set(TRANSLATIONS[language]["entity"][platform][key]["state"])


def test_english_translation_is_the_source_strings():
    assert TRANSLATIONS["en"] == STRINGS


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_has_every_text_with_its_placeholders(language):
    source, translated = texts(STRINGS), texts(TRANSLATIONS[language])
    # The texts of strings.json in its order, so the files compare line by line.
    assert list(translated) == list(source)
    for path, text in source.items():
        assert placeholders(translated[path]) == placeholders(text), path
        assert translated[path].strip(), path


def assert_tidy(language: str, path: str, text: str) -> None:
    """No stray spaces, the form of address and the punctuation of the language."""
    assert text == text.strip() and "  " not in text, path
    if language in WRONG_ADDRESS and not path.startswith("selector"):
        assert not re.search(WRONG_ADDRESS[language], text), path
    # The words only, without code, placeholders, links and addresses.
    prose = re.sub(
        r"```.*?```|`[^`]*`|{\w+}|\]\([^)]*\)|https?://", "", text, flags=re.S
    )
    if language == "fr":
        # A no-break space goes before : ; ? and !, as in Home Assistant's French.
        assert not re.search(r"\S[;?!]| [:;?!]|\w:", prose), path
    if language == "es":
        assert prose.count("¿") == prose.count("?"), path


@pytest.mark.parametrize("language", LANGUAGES)
def test_texts_are_tidy(language):
    for path, text in texts(TRANSLATIONS[language]).items():
        assert_tidy(language, path, text)


async def test_the_game_options_agree_everywhere(hass, aioclient_mock):
    game = SERVICES["start_game"]["fields"]["game"]["selector"]["select"]
    assert [str(option) for option in game["options"]] == list(GAME_OPTIONS)
    assert set(STRINGS["selector"][game["translation_key"]]["options"]) == set(
        GAME_OPTIONS
    )
    await setup_local(hass, aioclient_mock)
    select = hass.states.get(entity_id(hass, "select", "practice_game"))
    assert select.attributes["options"] == ["off", *GAME_OPTIONS]
    assert states("select", "practice_game") == {"off", *GAME_OPTIONS}
    standby = hass.states.get(entity_id(hass, "select", "standby_minutes"))
    assert set(standby.attributes["options"]) == states("select", "standby_minutes")


def test_action_limits_agree_with_the_schema():
    fields = SERVICES["start_game"]["fields"]
    assert set(fields) == {str(key) for key in START_GAME_SCHEMA.schema}
    assert set(SERVICES["delete_player"]["fields"]) == {
        str(key) for key in DELETE_PLAYER_SCHEMA.schema
    }
    for field, limit in (("legs", MAX_LEGS), ("sets", MAX_SETS)):
        number = fields[field]["selector"]["number"]
        assert (number["min"], number["max"]) == (1, limit), field
    assert fields["players"]["selector"]["text"]["multiple"] is True
    # The description names the number of players the schema accepts.
    description = STRINGS["services"]["start_game"]["fields"]["players"]["description"]
    assert f"one to {['one', 'two', 'three', 'four'][MAX_PLAYERS - 1]}" in description


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_action_and_field_is_described(language):
    services = TRANSLATIONS[language]["services"]
    assert set(services) == set(SERVICES)
    for service, spec in SERVICES.items():
        assert services[service]["name"] and services[service]["description"]
        assert set(services[service]["fields"]) == set(spec["fields"]), service


def test_select_sensor_and_event_states_are_translated():
    assert states("select", "standby_minutes") == {str(m) for m in STANDBY_MINUTES}
    assert states("sensor", "local_status") == set(LOCAL_STATES)
    assert states("sensor", "match_state") == set(MATCH_STATES)
    assert states("sensor", "board_status") == set(BOARD_STATES)
    event = TRANSLATIONS["en"]["entity"]["event"]["board_events"]
    assert set(event["state_attributes"]["event_type"]["state"]) == set(EVENT_TYPES)


def test_icons_cover_every_entity_and_action():
    for platform, keys in STRINGS["entity"].items():
        icons = set(ICONS["entity"].get(platform, {}))
        assert icons <= set(keys), platform
        missing = {(platform, key) for key in keys} - {(platform, key) for key in icons}
        assert missing <= DEVICE_CLASS_ICONS, missing
    assert set(ICONS["services"]) == set(SERVICES)
    assert set(MOTION_SENSORS) <= set(ICONS["entity"]["binary_sensor"])


def test_every_message_is_raised_and_every_raised_message_exists():
    for key in STRINGS["exceptions"]:
        assert f'"{key}"' in SOURCES, f"exception {key} is never raised"
    for key in re.findall(r'translation_key="(\w+)"', SOURCES):
        assert (
            key in STRINGS["exceptions"]
            or key in STRINGS["issues"]
            or any(key in keys for keys in STRINGS["entity"].values())
        ), key
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    for kind in ("error", "abort"):
        for key in STRINGS["config"][kind]:
            assert f'"{key}"' in flow or key in HOME_ASSISTANT_ABORTS, key


def test_every_repair_issue_is_translated():
    # Issue names are those of the translation, except the calibration.
    translated = set(STRINGS["issues"])
    assert set(ISSUES) - {"calibration"} <= translated
    assert "calibration_recommended" in translated
    repairs = (INTEGRATION / "repairs.py").read_text(encoding="utf-8")
    for issue, spec in STRINGS["issues"].items():
        if "fix_flow" in spec:
            # A fixable issue explains itself in its flow, not in a description.
            assert "description" not in spec, issue
            for reason in spec["fix_flow"]["abort"]:
                assert f'"{reason}"' in repairs, reason
        else:
            assert spec["description"], issue


TEXT_BLOCK = CARD[
    CARD.index("const TEXT = {\n") : CARD.index("\n};\n", CARD.index("const TEXT"))
]


def card_texts() -> dict[str, dict[str, str]]:
    """TEXT of the card module: every text by its key, per language."""
    # "  en: {", its texts, "  de: {", its texts, …
    parts = re.split(r"^  (\w+): \{$", TEXT_BLOCK, flags=re.M)[1:]
    return {
        language: {
            key: json.loads(value)
            for key, value in re.findall(r'^    (\w+):\s+(".*"),$', body, re.M)
        }
        for language, body in zip(parts[::2], parts[1::2], strict=True)
    }


CARD_TEXTS = card_texts()


def test_the_cards_speak_every_language_of_the_integration():
    assert list(CARD_TEXTS) == ["en", "de", "es", "fr", "nl"]
    assert set(CARD_TEXTS) == set(LANGUAGES)
    # Every key of TEXT is one text; none escaped the parser.
    keys = re.findall(r"^    \w+:", TEXT_BLOCK, re.M)
    assert len(keys) == sum(len(texts) for texts in CARD_TEXTS.values())


@pytest.mark.parametrize("language", LANGUAGES)
def test_card_texts_exist_in_every_language(language):
    english, translated = CARD_TEXTS["en"], CARD_TEXTS[language]
    assert len(english) > 100
    # The keys of TEXT.en in their order, each text with the same placeholders.
    assert list(translated) == list(english)
    for key, text in english.items():
        assert placeholders(translated[key]) == placeholders(text), key
        assert translated[key], key
        assert_tidy(language, key, translated[key])


# Dependabot bumps the requirements files; the copies elsewhere follow by hand.
ROOT = INTEGRATION.parents[1]
E2E = ROOT / "tests" / "e2e"


def pinned(path: Path, package: str) -> str:
    """The version of a package pinned as ``package==version`` in a requirements file."""
    text = path.read_text(encoding="utf-8")
    versions = re.findall(rf"^{re.escape(package)}==(\S+)", text, re.M | re.I)
    assert len(versions) == 1, (path.name, versions)
    return versions[0]


def test_pre_commit_runs_the_ruff_of_the_test_requirements():
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    # A rev is a tag, or a commit with the tag as "# frozen: v1.2.3".
    rev = re.search(
        r"repo: https://github\.com/astral-sh/ruff-pre-commit\n"
        r"\s+rev: (\S+)(?: # frozen: (\S+))?\n",
        config,
    )
    assert rev, "the Ruff hook is missing"
    version = (rev[2] or rev[1]).removeprefix("v")
    assert version == pinned(ROOT / "requirements-test.in", "ruff")
    assert version == pinned(ROOT / "requirements-test.txt", "ruff")


@pytest.mark.parametrize("script", ["browser.sh", "screenshots.sh"])
def test_the_playwright_image_matches_the_playwright_package(script):
    text = (E2E / script).read_text(encoding="utf-8")
    images = re.findall(
        r"^PLAYWRIGHT_IMAGE=\"mcr\.microsoft\.com/playwright/python:"
        r"v([\d.]+)-\w+@sha256:[0-9a-f]{64}\"$",
        text,
        re.M,
    )
    # The browsers of the image fit only the same version of the package.
    assert images == [pinned(E2E / "requirements-browser.in", "playwright")]
    assert images == [pinned(E2E / "requirements-browser.txt", "playwright")]
