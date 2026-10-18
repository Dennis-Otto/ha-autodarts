"""The blueprints that come with the integration.

HACS updates the integration alone, and a blueprint imported from the repository
stays as it was imported, so the two drift apart. The release package therefore
carries the blueprints, and each start of Home Assistant puts them where Home
Assistant's import saves those of this repository: a blueprint the user never
changed follows every update of the integration, one they changed stays theirs,
with a repair that offers the blueprint of the installed release.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.automation import automations_with_blueprint
from homeassistant.components.automation.helpers import async_get_blueprints
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import selector
from homeassistant.helpers.storage import Store
from homeassistant.util.yaml import Input, parse_yaml

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# The blueprints of the release, the same files as blueprints/ of the repository.
SHIPPED = Path(__file__).parent / "blueprints" / "automation" / "autodarts"
# The fingerprint of every version of each blueprint that main has had, oldest
# first: a file with one of them is a blueprint of this repository nobody changed.
VERSIONS = Path(__file__).parent / "blueprint_versions.json"
# Home Assistant's import saves a blueprint of github.com/<owner>/<repository> as
# <owner>/<file>, so the import buttons of the guide and the integration share it.
NAMESPACE = "Dennis-Otto"
# The repair of a changed blueprint: <ISSUE><file name without .yaml>_<version>.
ISSUE = "blueprint_edited_"
STORAGE_KEY = f"{DOMAIN}.blueprints"


class State(Enum):
    """How a blueprint in the configuration relates to the one of the release."""

    CURRENT = "current"
    OUTDATED = "outdated"
    EDITED = "edited"


@dataclass(slots=True)
class Outcome:
    """What one installation did with the blueprints of the release."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    # A changed blueprint: its file, with the version of the release and the
    # placeholders of its repair.
    edited: dict[str, tuple[str, dict[str, str]]] = field(default_factory=dict)
    # The files in the configuration afterwards, changed or not.
    present: set[str] = field(default_factory=set)


def folder(hass: HomeAssistant) -> Path:
    """The folder of Home Assistant that holds the blueprints of this repository."""
    return Path(hass.config.path("blueprints", "automation", NAMESPACE))


def shipped() -> list[str]:
    """The file names of the blueprints of the release."""
    return sorted(path.name for path in SHIPPED.glob("*.yaml"))


def _plain(value: Any) -> Any:
    """Parsed YAML as plain JSON values, an !input as an object of its own."""
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, Input):
        return {"!input": value.name}
    return value


def _inputs(inputs: Any) -> Iterator[dict[str, Any]]:
    """Every input of a blueprint, also those of its sections."""
    if not isinstance(inputs, dict):
        return
    for spec in inputs.values():
        if isinstance(spec, dict) and "input" in spec:
            yield from _inputs(spec["input"])
        elif isinstance(spec, dict):
            yield spec


def _digest(data: Any, selectors: Callable[[Any], Any]) -> str:
    """The SHA-256 of a blueprint without its source and with its selectors
    replaced, so that how and from where it was saved doesn't count."""
    plain = _plain(data)
    if isinstance(blueprint := plain.get("blueprint"), dict):
        blueprint.pop("source_url", None)
        for spec in _inputs(blueprint.get("input")):
            if "selector" in spec:
                spec["selector"] = selectors(spec["selector"])
    text = json.dumps(
        plain, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(text.encode()).hexdigest()


def _selector_types(config: Any) -> Any:
    return sorted(config) if isinstance(config, dict) else config


def _validated(config: Any) -> Any:
    try:
        return selector.validate_selector(config)
    except vol.Invalid:
        return config


def fingerprint(data: dict[str, Any]) -> str:
    """The version of a blueprint, whoever saved it and with whichever release of
    Home Assistant.

    The import of Home Assistant writes the blueprint anew, without comments, with
    the address it came from and with every option of a selector that its release
    knows. The fingerprint therefore leaves out the address and keeps only the type
    of each selector.
    """
    return _digest(data, _selector_types)


def _same(data: dict[str, Any], other: dict[str, Any]) -> bool:
    """The same blueprint, also the options of its selectors, as Home Assistant
    completes them."""
    return _digest(data, _validated) == _digest(other, _validated)


def _release(content: bytes) -> dict[str, Any]:
    """A blueprint of the release, which tests/test_shipped_blueprints.py keeps
    valid."""
    return cast(dict[str, Any], parse_yaml(content.decode("utf-8")))


def state(old: bytes, new: bytes, versions: list[str]) -> State:
    """A file in the configuration, compared with the blueprint of the release."""
    if old == new:
        return State.CURRENT
    try:
        data = parse_yaml(old.decode("utf-8"))
    except (UnicodeDecodeError, HomeAssistantError):
        return State.EDITED
    if not isinstance(data, dict):
        return State.EDITED
    if _same(data, _release(new)):
        return State.CURRENT
    if fingerprint(data) in versions:
        return State.OUTDATED
    return State.EDITED


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _repair(name: str, new: bytes) -> tuple[str, dict[str, str]]:
    """The version of a blueprint of the release, and the placeholders of the
    repair of a changed one."""
    data = _release(new)
    return fingerprint(data)[:12], {
        "name": str(data["blueprint"]["name"]),
        "path": f"blueprints/automation/{NAMESPACE}/{name}",
    }


def _install(target: Path, installed: set[str]) -> Outcome:
    """Add the blueprints, and update those in the configuration nobody changed.

    A blueprint that the integration found before and that is gone was deleted by
    the user, and stays deleted.
    """
    versions: dict[str, list[str]] = json.loads(VERSIONS.read_text(encoding="utf-8"))
    outcome = Outcome()
    for name in shipped():
        new = (SHIPPED / name).read_bytes()
        path = target / name
        try:
            if not path.is_file():
                if name in installed:
                    continue
                _write(path, new)
                outcome.added.append(name)
            else:
                found = state(path.read_bytes(), new, versions.get(name, []))
                if found is State.OUTDATED:
                    _write(path, new)
                    outcome.updated.append(name)
                elif found is State.EDITED:
                    outcome.edited[name] = _repair(name, new)
        except OSError as err:
            # Tried again with the next start.
            _LOGGER.warning("Cannot install the blueprint %s: %s", path, err)
            continue
        outcome.present.add(name)
    return outcome


async def _async_reload(hass: HomeAssistant, updated: list[str]) -> None:
    """Automations made from an updated blueprint follow it at once, as they do
    after a re-import of the blueprint."""
    if not updated or "automation" not in hass.config.components:
        return
    await async_get_blueprints(hass).async_reset_cache()
    if any(automations_with_blueprint(hass, f"{NAMESPACE}/{name}") for name in updated):
        await hass.services.async_call("automation", SERVICE_RELOAD, blocking=True)


def _flag_edited(
    hass: HomeAssistant, edited: dict[str, tuple[str, dict[str, str]]]
) -> None:
    """One repair for each changed blueprint, anew for each version of it that a
    release brings, so that ignoring one does not hide the next."""
    wanted = {
        f"{ISSUE}{Path(name).stem}_{version}": (name, placeholders)
        for name, (version, placeholders) in edited.items()
    }
    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN and issue_id.startswith(ISSUE) and issue_id not in wanted:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
    for issue_id, (name, placeholders) in wanted.items():
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="blueprint_edited",
            translation_placeholders=placeholders,
            data={"file": name},
        )


async def async_install_blueprints(hass: HomeAssistant) -> None:
    """Bring the blueprints of the release into the configuration, once a start."""
    store: Store[dict[str, list[str]]] = Store(hass, 1, STORAGE_KEY)
    installed = set((await store.async_load() or {}).get("installed", []))
    outcome = await hass.async_add_executor_job(_install, folder(hass), installed)
    if outcome.added:
        _LOGGER.info("Installed the blueprints %s", ", ".join(outcome.added))
    if outcome.updated:
        _LOGGER.info("Updated the unchanged blueprints %s", ", ".join(outcome.updated))
    if not outcome.present <= installed:
        await store.async_save({"installed": sorted(installed | outcome.present)})
    _flag_edited(hass, outcome.edited)
    await _async_reload(hass, outcome.updated)


def _restore(target: Path, name: str) -> bool:
    if name not in shipped():
        return False
    _write(target / name, (SHIPPED / name).read_bytes())
    return True


async def async_restore_blueprint(hass: HomeAssistant, name: str) -> bool:
    """Replace a blueprint in the configuration with the one of the release; False
    for a file the release does not bring. Raises OSError when the file cannot
    be written."""
    if not await hass.async_add_executor_job(_restore, folder(hass), name):
        return False
    await _async_reload(hass, [name])
    return True
