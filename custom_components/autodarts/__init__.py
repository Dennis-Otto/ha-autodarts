"""The Autodarts integration, with independent local and cloud connections."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from . import const
from .api import AutodartsCloudClient
from .button import V1_BUTTONS
from .card import async_register_card
from .const import (
    CONF_BOARD_ID,
    CONF_CLIENT_ID,
    CONF_HOST,
    CONF_LOCAL_ONLY,
    CONF_PORT,
    CONF_TOKEN,
    DEFAULT_PORT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AutodartsDataUpdateCoordinator
from .discovery import cloud_addresses
from .errors import AutodartsApiError
from .local_api import AutodartsLocalClient
from .local_coordinator import ISSUES, AutodartsLocalCoordinator
from .online import async_setup_bridge
from .report import BoardReports
from .runtime import AutodartsConfigEntry, AutodartsRuntimeData
from .sensor import SYSTEM_SENSORS
from .services import async_setup_services
from .storage import TrainingStore
from .websocket import async_setup_websocket

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Entities that only one Board Manager generation provides.
V1_ONLY = (("switch", "upstream"), *(("button", key) for key in V1_BUTTONS))
V2_ONLY = (
    ("binary_sensor", "cloud_link"),
    *(("sensor", description.key) for description in SYSTEM_SENSORS),
    ("update", "board_software"),
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Provide the dashboard card, the actions and the positions for the cards
    once, independent of entries."""
    await async_register_card(hass)
    async_setup_services(hass)
    async_setup_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AutodartsConfigEntry) -> bool:
    """Local controls remain usable even if cloud authentication fails."""
    session = async_get_clientsession(hass)
    runtime = AutodartsRuntimeData()
    local_failed = False

    def local_coordinator(host: str, port: int) -> AutodartsLocalCoordinator:
        return AutodartsLocalCoordinator(
            hass,
            AutodartsLocalClient(host, port, session),
            entry.data[CONF_BOARD_ID],
            entry,
        )

    async def discover_local(addresses: object) -> None:
        """Adopt the first address reported by the cloud that answers as this board."""
        for host, port in cloud_addresses(addresses):
            if (host, port) == (
                entry.data.get(CONF_HOST),
                entry.data.get(CONF_PORT, DEFAULT_PORT),
            ):
                continue
            candidate = local_coordinator(host, port)
            try:
                await candidate.async_config_entry_first_refresh()
            except ConfigEntryNotReady:
                # Discard failed candidates, including their timers and store.
                await candidate.async_shutdown()
                continue
            if runtime.local is not None:
                await runtime.local.async_shutdown()
            runtime.local = candidate
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_HOST: host, CONF_PORT: port}
            )
            return

    if host := entry.data.get(CONF_HOST):
        runtime.local = local_coordinator(host, entry.data.get(CONF_PORT, DEFAULT_PORT))
        try:
            await runtime.local.async_config_entry_first_refresh()
        except ConfigEntryNotReady:
            # Entities stay and recover when the board answers again.
            local_failed = True

    # Without an obtainable client ID, a relink could never be completed.
    if not entry.data.get(CONF_LOCAL_ONLY, False) and (
        const.CLOUD_LINK_AVAILABLE or entry.data.get(CONF_CLIENT_ID)
    ):

        def persist_token(token: dict[str, Any]) -> None:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_TOKEN: token}
            )

        try:
            if not entry.data.get(CONF_CLIENT_ID):
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN, translation_key="relink_required"
                )
            runtime.cloud = AutodartsDataUpdateCoordinator(
                hass,
                cloud=AutodartsCloudClient(
                    session,
                    entry.data[CONF_TOKEN],
                    entry.data[CONF_CLIENT_ID],
                    persist_token,
                ),
                board_id=entry.data[CONF_BOARD_ID],
                entry=entry,
            )
            await runtime.cloud.async_config_entry_first_refresh()
        except ConfigEntryAuthFailed:
            if runtime.local is None:
                raise
            # A configured board keeps working locally while the login is renewed.
            entry.async_start_reauth(hass)
        except ConfigEntryNotReady:
            # A configured board works locally while the cloud is away.
            if runtime.local is None:
                raise

        # The cloud knows the board's current address: use it when none is set or
        # the stored one no longer answers, e.g. after a DHCP change.
        if (runtime.local is None or local_failed) and (
            runtime.cloud and runtime.cloud.data
        ):
            await discover_local(runtime.cloud.data.get("board", {}).get("ip"))
    elif runtime.local is None:
        # Retrying cannot help: the user has to enter the address first.
        raise ConfigEntryError(
            translation_domain=DOMAIN, translation_key="no_local_address"
        )
    # A board that is switched off does not stop the setup: the entities of
    # training and games work without it, and the others recover with the board.
    entry.runtime_data = runtime
    if runtime.local:
        device = next(
            (
                device
                for device in dr.async_entries_for_config_entry(
                    dr.async_get(hass), entry.entry_id
                )
                if (DOMAIN, entry.data[CONF_BOARD_ID]) in device.identifiers
            ),
            None,
        )
        board = (runtime.cloud.data or {}).get("board", {}) if runtime.cloud else {}
        # The name from Autodarts, else the one found by the board search.
        runtime.local.device_name = (
            board.get("name")
            or entry.data.get(CONF_NAME)
            or (device.name if device and device.name else "Autodarts Board")
        )
    if runtime.local:
        runtime.local.setup_generation = runtime.local.generation or 1
        # An unknown generation keeps the entities and their customizations.
        if runtime.local.generation is not None:
            _remove_other_generation(hass, entry, runtime.local.board_manager_2)
    # Moments of online matches arrive as board events, if switched on.
    runtime.bridge = await async_setup_bridge(hass, entry, runtime.local)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if runtime.local:
        runtime.local.async_start()
    return True


def _remove_other_generation(
    hass: HomeAssistant, entry: ConfigEntry, board_manager_2: bool
) -> None:
    """Remove entities of the other Board Manager generation after a change."""
    registry = er.async_get(hass)
    for platform, key in V1_ONLY if board_manager_2 else V2_ONLY:
        entity_id = registry.async_get_entity_id(
            platform, DOMAIN, f"{entry.data[CONF_BOARD_ID]}_{key}"
        )
        if entity_id:
            registry.async_remove(entity_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Upgrade version 1 entries, which stored a board address or a password."""
    # Home Assistant itself refuses entries of a newer major version.
    if entry.version == 2:
        return True
    data = dict(entry.data)
    board_id = data.get(CONF_BOARD_ID)
    host = data.get(CONF_HOST)
    port = data.get(CONF_PORT, DEFAULT_PORT)
    if not board_id and host:
        client = AutodartsLocalClient(host, port, async_get_clientsession(hass))
        try:
            board_id = (await client.get_config()).get(CONF_BOARD_ID)
        except AutodartsApiError:
            board_id = None
    if not board_id:
        # Retried at the next start, so a board that is switched off is no problem.
        _LOGGER.warning(
            "Cannot migrate the Autodarts entry %s yet: the board at %s does not answer",
            entry.title,
            host,
        )
        return False
    # Version 1 cloud entries stored the account password; never keep it.
    new = {CONF_BOARD_ID: board_id}
    if host:
        new |= {CONF_HOST: host, CONF_PORT: port, CONF_LOCAL_ONLY: True}
    hass.config_entries.async_update_entry(
        entry, data=new, unique_id=board_id, version=2
    )
    _LOGGER.info("Migrated the Autodarts entry %s to version 2", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AutodartsConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: AutodartsConfigEntry) -> None:
    """Deleting the integration also deletes its local training session."""
    await TrainingStore(hass, entry.entry_id).async_remove()
    await BoardReports.async_remove(hass, entry.entry_id)
    for issue in ISSUES:
        ir.async_delete_issue(hass, DOMAIN, f"{issue}_{entry.entry_id}")
