"""The Home Assistant of the end-to-end tests stays off the internet.

Onboarding sets up Radio Browser, which looks up radio stations on the internet as
soon as it starts. tests/e2e/offline/radio_browser takes its place in the container
and turns every setup of it down; scenario.py checks in the container that no entry
of it exists."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

E2E = Path(__file__).parents[1] / "tests" / "e2e"
STAND_IN = E2E / "offline" / "radio_browser"


def test_home_assistant_finds_the_stand_in_among_its_custom_integrations():
    compose = yaml.safe_load((E2E / "compose.yaml").read_text(encoding="utf-8"))
    volumes = compose["services"]["homeassistant"]["volumes"]
    assert (
        "./offline/radio_browser:/config/custom_components/radio_browser:ro" in volumes
    )


def test_the_stand_in_takes_the_place_of_radio_browser():
    manifest = json.loads((STAND_IN / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "radio_browser"
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == []
    # Home Assistant refuses to load a custom integration without a version.
    assert manifest["version"]


@pytest.fixture
def stand_in(monkeypatch):
    """The config flow of the stand-in, registered for Radio Browser in this test
    alone."""
    monkeypatch.setitem(config_entries.HANDLERS, "radio_browser", None)
    spec = importlib.util.spec_from_file_location(
        "e2e_offline_radio_browser", STAND_IN / "config_flow.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LeftOut


@pytest.mark.parametrize("step", ["async_step_onboarding", "async_step_user"])
async def test_onboarding_and_the_user_get_no_entry(stand_in, step):
    assert config_entries.HANDLERS["radio_browser"] is stand_in
    result = await getattr(stand_in(), step)()
    assert result["type"] is FlowResultType.ABORT
    texts = json.loads(
        (STAND_IN / "translations" / "en.json").read_text(encoding="utf-8")
    )
    assert "internet" in texts["config"]["abort"][result["reason"]]
