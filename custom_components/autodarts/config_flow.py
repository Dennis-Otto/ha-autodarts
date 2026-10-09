"""Home Assistant device-link setup and reauthentication for Autodarts."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Mapping
from ipaddress import IPv4Address, ip_address
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from . import const
from .api import (
    AutodartsAuthError,
    AutodartsCloudClient,
    AutodartsConnectionError,
    DeviceAuthorization,
    request_device_code,
    wait_for_device_token,
)
from .const import (
    CONF_API_GENERATION,
    CONF_BOARD_ID,
    CONF_CLIENT_ID,
    CONF_HOST,
    CONF_LOCAL_ONLY,
    CONF_MANUAL_BOARD,
    CONF_PORT,
    CONF_TOKEN,
    DEFAULT_PORT,
    DOMAIN,
)
from .discovery import async_discover_boards
from .errors import AutodartsApiError
from .local_api import AutodartsLocalAuthError, AutodartsLocalClient, board_generation
from .online import (
    CONF_NEW_ADDRESS,
    CONF_ONLINE_BRIDGE,
    CONF_ONLINE_REMOTE,
    CONF_WEBHOOK_ID,
    bridge_url,
    effects_csv,
)
from .repairs import address_title, async_offer_address


def _valid_host(host: str) -> bool:
    if not host or any(char.isspace() or char in "/?#@\\[]" for char in host):
        return False
    if ":" in host:
        try:
            return ip_address(host).version == 6
        except ValueError:
            return False
    return True


def _announced_host(discovery_info: ZeroconfServiceInfo) -> str | None:
    """The board's address; its own "ip" property only if it is the sender's.

    Any device can announce the service, so an address outside the
    announcement never makes Home Assistant contact another host.
    """
    usable = [
        address
        for address in discovery_info.ip_addresses
        if not (
            address.is_loopback
            or address.is_unspecified
            or address.is_multicast
            or address.is_link_local
        )
    ]
    advertised = discovery_info.properties.get("ip")
    for address in usable:
        if str(address) == advertised:
            return str(address)
    # Prefer IPv4, which works without a zone or router advertisements.
    usable.sort(key=lambda address: not isinstance(address, IPv4Address))
    return str(usable[0]) if usable else None


def _announced_port(discovery_info: ZeroconfServiceInfo) -> int:
    """Board Manager 2 may announce its HTTPS port; the plain HTTP one is used."""
    for value in (discovery_info.properties.get("insecurePort"), discovery_info.port):
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if type(value) is int and 0 < value < 65536:
            return value
    return DEFAULT_PORT


# The name a dartboard without Autodarts gets unless the user chooses another.
MANUAL_BOARD_NAME = "Dartboard"


def _menu_options(manual: bool = False) -> list[str]:
    """Offer the cloud link only while a client ID can actually be obtained,
    and a dartboard without Autodarts when one is set up."""
    options = ["discover", "local"]
    if const.CLOUD_LINK_AVAILABLE:
        options.append("cloud")
    if manual:
        options.append("manual")
    return options


def _auth_error(error: AutodartsAuthError) -> str:
    """Map server errors to translated, actionable messages."""
    if error.code in ("invalid_client", "unauthorized_client"):
        return "invalid_client"
    if error.code in ("expired_token", "access_denied"):
        return error.code
    return "invalid_auth"


class AutodartsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Link an account using a registered public OAuth client and a short code."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AutodartsOptionsFlow:
        return AutodartsOptionsFlow()

    @classmethod
    @callback
    def async_supports_options_flow(cls, config_entry: ConfigEntry) -> bool:
        """The options switch the bridge for online matches, which delivers its
        moments as events of the local board; without one, nothing receives them."""
        return bool(config_entry.data.get(CONF_HOST))

    def __init__(self) -> None:
        self._token: dict[str, Any] = {}
        self._boards: dict[str, str] = {}
        self._user_input: dict[str, Any] = {}
        self._device: DeviceAuthorization | None = None
        self._auth_task: asyncio.Task[dict[str, Any]] | None = None
        self._auth_error: str | None = None
        self._found: dict[str, dict[str, Any]] = {}
        self._discovered: dict[str, Any] = {}
        # Names the board search reported, by board ID.
        self._names: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Search the network, enter a board address, link a cloud account or
        set up a dartboard without Autodarts."""
        return self.async_show_menu(
            step_id="user", menu_options=_menu_options(manual=True)
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """A dartboard without Autodarts, whose darts are all entered by hand.

        It has no board ID of its own, so every one gets a new one: a home
        may have several.
        """
        if user_input is not None:
            name = user_input[CONF_NAME]
            board_id = f"manual_{uuid.uuid4().hex}"
            await self.async_set_unique_id(board_id)
            return self.async_create_entry(
                title=f"Autodarts ({name})",
                data={
                    CONF_BOARD_ID: board_id,
                    CONF_MANUAL_BOARD: True,
                    CONF_LOCAL_ONLY: True,
                    CONF_NAME: name,
                },
            )
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=MANUAL_BOARD_NAME): vol.All(
                        str, vol.Strip, vol.Length(min=1, max=50)
                    )
                }
            ),
        )

    async def _async_identify(self, host: str, port: int) -> dict[str, Any]:
        client = AutodartsLocalClient(host, port, async_get_clientsession(self.hass))
        return await client.identify()

    def _entry_elsewhere(
        self, board_id: str, host: str, port: int
    ) -> ConfigEntry | None:
        """The entry of this board, when it has another address than this one."""
        entry = self.hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, board_id
        )
        if entry is None or entry.source == SOURCE_IGNORE:
            return None
        configured = (
            entry.data.get(CONF_HOST),
            entry.data.get(CONF_PORT, DEFAULT_PORT),
        )
        return None if configured == (host, port) else entry

    async def _async_still_answers(self, entry: ConfigEntry) -> bool:
        """Whether the board of the entry still answers at the entry's address."""
        if not entry.data.get(CONF_HOST):
            return False
        try:
            identity = await self._async_identify(
                entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT)
            )
        except (AutodartsApiError, ValueError):
            return False
        return bool(identity["board_id"] == entry.unique_id)

    def _local_entry(
        self, host: str, port: int, identity: dict[str, Any]
    ) -> ConfigFlowResult:
        data = {
            CONF_BOARD_ID: identity["board_id"],
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_LOCAL_ONLY: True,
        }
        if generation := board_generation(identity.get("version")):
            data[CONF_API_GENERATION] = generation
        # The name given in Autodarts names the entry and the device.
        if name := self._names.get(identity["board_id"]):
            data[CONF_NAME] = name
        return self.async_create_entry(title=f"Autodarts ({name or host})", data=data)

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer the boards Autodarts lists for this network."""
        if user_input is not None:
            board = self._found[user_input[CONF_BOARD_ID]]
            # The address form keeps the found address if the board does not answer.
            self._user_input.update(
                {CONF_HOST: board["host"], CONF_PORT: board["port"]}
            )
            return await self.async_step_local(
                {CONF_HOST: board["host"], CONF_PORT: board["port"]}
            )
        try:
            boards = await async_discover_boards(async_get_clientsession(self.hass))
        except AutodartsConnectionError:
            return await self.async_step_local(error="discovery_failed")
        configured = {entry.unique_id for entry in self._async_current_entries()}
        if self.source == SOURCE_RECONFIGURE:
            # The board being reconfigured may have moved; keep offering it.
            configured.discard(self._get_reconfigure_entry().unique_id)
        self._found = {
            board["board_id"]: board
            for board in boards
            if board["board_id"] not in configured
        }
        if not self._found:
            return await self.async_step_local(error="no_boards_found")
        self._names = {
            board_id: board["name"]
            for board_id, board in self._found.items()
            if board["name"]
        }
        return self.async_show_form(
            step_id="discover",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BOARD_ID): vol.In(
                        {
                            board_id: (
                                f"{board['name'] or 'Autodarts'} · {board['host']}"
                                + (f" · {board['version']}" if board["version"] else "")
                            )
                            for board_id, board in self._found.items()
                        }
                    )
                }
            ),
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Board Manager 2 announces itself as _autodarts-board._tcp."""
        host = _announced_host(discovery_info)
        if host is None:
            return self.async_abort(reason="cannot_connect_local")
        port = _announced_port(discovery_info)
        try:
            identity = await self._async_identify(host, port)
        except (AutodartsApiError, ValueError):
            return self.async_abort(reason="cannot_connect_local")
        board_id = identity["board_id"]
        if not board_id:
            return self.async_abort(reason="board_not_configured")
        await self.async_set_unique_id(board_id)
        entry = self._entry_elsewhere(board_id, host, port)
        if entry is not None and not await self._async_still_answers(entry):
            # Any device can announce the board ID, so a board that left its
            # address moves only once the user confirms the repair.
            async_offer_address(self.hass, entry, host, port)
        self._abort_if_unique_id_configured()
        self._async_abort_entries_match({CONF_BOARD_ID: identity["board_id"]})
        self._discovered = {"host": host, "port": port, **identity}
        self.context["title_placeholders"] = {"name": host}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        found = self._discovered
        if user_input is not None:
            return self._local_entry(found["host"], found["port"], found)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "host": found["host"],
                "version": found.get("version") or "?",
                "cameras": str(found.get("camera_count") or "?"),
            },
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_setup_form("cloud", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if entry.data.get(CONF_MANUAL_BOARD):
            return self.async_abort(reason="manual_board")
        self._user_input = {
            key: entry.data[key]
            for key in (CONF_HOST, CONF_PORT, CONF_CLIENT_ID)
            if key in entry.data
        }
        return self.async_show_menu(step_id="reconfigure", menu_options=_menu_options())

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None, error: str | None = None
    ) -> ConfigFlowResult:
        """Create a local entry, or update an existing entry's local address."""
        errors = {"base": error} if error else {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().lower()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            if not _valid_host(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    identity = await self._async_identify(host, port)
                except AutodartsLocalAuthError:
                    errors["base"] = "board_access_denied"
                except (AutodartsApiError, ValueError):
                    errors["base"] = "cannot_connect_local"
                else:
                    board_id = identity[CONF_BOARD_ID]
                    if not board_id:
                        errors["base"] = "board_not_configured"
                    elif self.source == SOURCE_RECONFIGURE:
                        entry = self._get_reconfigure_entry()
                        if board_id != entry.data[CONF_BOARD_ID]:
                            return self.async_abort(reason="wrong_board")
                        return self.async_update_reload_and_abort(
                            entry,
                            title=address_title(entry, host),
                            data_updates={CONF_HOST: host, CONF_PORT: port},
                            reason="reconfigure_successful",
                        )
                    else:
                        await self.async_set_unique_id(board_id)
                        known = self._entry_elsewhere(board_id, host, port)
                        if known is not None:
                            # The board answers where the user says it is now.
                            return self.async_update_reload_and_abort(
                                known,
                                title=address_title(known, host),
                                data_updates={CONF_HOST: host, CONF_PORT: port},
                                reason="address_updated",
                            )
                        self._abort_if_unique_id_configured()
                        self._async_abort_entries_match({CONF_BOARD_ID: board_id})
                        return self._local_entry(host, port, identity)
        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self._user_input.get(CONF_HOST, "")
                    ): str,
                    vol.Required(
                        CONF_PORT, default=self._user_input.get(CONF_PORT, DEFAULT_PORT)
                    ): vol.All(int, vol.Range(min=1, max=65535)),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Relink an existing board, including entries using retired Keycloak tokens."""
        self._user_input = {
            key: entry_data[key]
            for key in (CONF_CLIENT_ID, CONF_HOST, CONF_PORT)
            if key in entry_data
        }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm relinking while retaining board and local settings."""
        return await self._async_setup_form("reauth_confirm", user_input)

    async def _async_setup_form(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors = {}
        if user_input is not None and step_id == "cloud" and user_input.get(CONF_HOST):
            user_input = {
                **user_input,
                CONF_HOST: user_input[CONF_HOST].strip().lower(),
            }
            if not _valid_host(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
                self._user_input.update(user_input)
                user_input = None
        if user_input is not None:
            self._user_input.update(user_input)
            self._user_input[CONF_CLIENT_ID] = user_input[CONF_CLIENT_ID].strip()
            try:
                self._device = await request_device_code(
                    async_get_clientsession(self.hass),
                    self._user_input[CONF_CLIENT_ID],
                )
            except AutodartsAuthError as err:
                errors["base"] = _auth_error(err)
            except AutodartsConnectionError:
                errors["base"] = "cannot_connect"
            else:
                self._auth_task = None
                self._auth_error = None
                return await self.async_step_auth()

        schema: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_CLIENT_ID, default=self._user_input.get(CONF_CLIENT_ID, "")
            ): vol.All(str, vol.Strip, vol.Length(min=1)),
        }
        if step_id == "cloud":
            schema.update(
                {
                    vol.Optional(
                        CONF_HOST, default=self._user_input.get(CONF_HOST, "")
                    ): str,
                    vol.Optional(
                        CONF_PORT, default=self._user_input.get(CONF_PORT, DEFAULT_PORT)
                    ): vol.All(int, vol.Range(min=1, max=65535)),
                }
            )
        return self.async_show_form(
            step_id=step_id, data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the public code while Home Assistant polls in the background."""
        assert self._device is not None
        if self._auth_task is None:
            self._auth_task = self.hass.async_create_task(
                wait_for_device_token(
                    async_get_clientsession(self.hass),
                    self._user_input[CONF_CLIENT_ID],
                    self._device,
                )
            )
        if self._auth_task.done():
            try:
                self._token = self._auth_task.result()
            except AutodartsAuthError as err:
                self._auth_error = _auth_error(err)
            except AutodartsConnectionError:
                self._auth_error = "cannot_connect"
            if self._auth_error:
                return self.async_show_progress_done(next_step_id="auth_retry")
            return self.async_show_progress_done(next_step_id="boards")

        return self.async_show_progress(
            step_id="auth",
            progress_action="wait_for_device",
            description_placeholders={
                "user_code": self._device.user_code,
                "verification_uri": self._device.verification_uri,
                "verification_uri_complete": self._device.verification_uri_complete,
            },
            progress_task=self._auth_task,
        )

    async def async_step_auth_retry(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user restart linking after expiry or denial."""
        if user_input is not None:
            if self.source == SOURCE_REAUTH:
                return await self.async_step_reauth_confirm()
            return await self.async_step_cloud()
        return self.async_show_form(
            step_id="auth_retry",
            data_schema=vol.Schema({}),
            errors={"base": self._auth_error or "invalid_auth"},
        )

    async def async_step_boards(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fetch boards after approval; retry outages without consuming a new code."""
        cloud = AutodartsCloudClient(
            async_get_clientsession(self.hass),
            self._token,
            self._user_input[CONF_CLIENT_ID],
            on_token_update=self._update_token,
        )
        try:
            boards = await cloud.get_boards()
        except AutodartsAuthError as err:
            self._auth_error = _auth_error(err)
            return await self.async_step_auth_retry()
        except AutodartsConnectionError:
            return self.async_show_form(
                step_id="boards",
                data_schema=vol.Schema({}),
                errors={"base": "cannot_connect"},
            )
        self._boards = {
            board["id"]: board.get("name") or board["id"] for board in boards
        }

        if self.source in (SOURCE_REAUTH, SOURCE_RECONFIGURE):
            entry = (
                self._get_reauth_entry()
                if self.source == SOURCE_REAUTH
                else self._get_reconfigure_entry()
            )
            if entry.data[CONF_BOARD_ID] not in self._boards:
                return self.async_abort(reason="wrong_account")
            updates = {
                CONF_TOKEN: self._token,
                CONF_CLIENT_ID: self._user_input[CONF_CLIENT_ID],
                CONF_LOCAL_ONLY: False,
            }
            for key in (CONF_HOST, CONF_PORT):
                if key in self._user_input:
                    updates[key] = self._user_input[key]
            return self.async_update_reload_and_abort(
                entry,
                reason="reauth_successful"
                if self.source == SOURCE_REAUTH
                else "reconfigure_successful",
                data_updates=updates,
            )
        if not self._boards:
            return self.async_abort(reason="no_boards")
        if len(self._boards) == 1:
            return await self._async_create_board_entry(next(iter(self._boards)))
        return await self.async_step_board()

    def _update_token(self, token: dict[str, Any]) -> None:
        self._token = token

    async def async_step_board(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a board when the account has several."""
        if user_input is not None:
            return await self._async_create_board_entry(user_input[CONF_BOARD_ID])
        return self.async_show_form(
            step_id="board",
            data_schema=vol.Schema({vol.Required(CONF_BOARD_ID): vol.In(self._boards)}),
        )

    async def _async_create_board_entry(self, board_id: str) -> ConfigFlowResult:
        """Preserve legacy board identifiers and prevent duplicate entries."""
        await self.async_set_unique_id(board_id)
        self._abort_if_unique_id_configured()
        self._async_abort_entries_match({CONF_BOARD_ID: board_id})
        data = {
            CONF_TOKEN: self._token,
            CONF_CLIENT_ID: self._user_input[CONF_CLIENT_ID],
            CONF_BOARD_ID: board_id,
        }
        if self._user_input.get(CONF_HOST):
            data[CONF_HOST] = self._user_input[CONF_HOST]
            data[CONF_PORT] = self._user_input.get(CONF_PORT, DEFAULT_PORT)
        return self.async_create_entry(
            title=f"Autodarts ({self._boards[board_id]})", data=data
        )


class AutodartsOptionsFlow(OptionsFlowWithReload):
    """Switch the bridge for online matches on or off and show its address."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        options = self.config_entry.options
        if user_input is not None:
            enabled = user_input[CONF_ONLINE_BRIDGE]
            self._options = {
                **options,
                CONF_ONLINE_BRIDGE: enabled,
                CONF_ONLINE_REMOTE: user_input[CONF_ONLINE_REMOTE],
            }
            # The address stays when the bridge is switched off, so that the
            # effects in the browser work again after switching it on; a new
            # one replaces it at once, so a leaked address never works again.
            if user_input.get(CONF_NEW_ADDRESS) or (
                enabled and not options.get(CONF_WEBHOOK_ID)
            ):
                self._options[CONF_WEBHOOK_ID] = webhook.async_generate_id()
            if enabled:
                return await self.async_step_online_bridge()
            return self.async_create_entry(data=self._options)
        schema: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_ONLINE_BRIDGE, default=options.get(CONF_ONLINE_BRIDGE, False)
            ): bool,
            vol.Required(
                CONF_ONLINE_REMOTE, default=options.get(CONF_ONLINE_REMOTE, False)
            ): bool,
        }
        if options.get(CONF_WEBHOOK_ID):
            schema[vol.Required(CONF_NEW_ADDRESS, default=False)] = bool
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

    async def async_step_online_bridge(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The address and the effects to import into Tools for Autodarts."""
        if user_input is not None:
            return self.async_create_entry(data=self._options)
        url = bridge_url(
            self.hass, self._options[CONF_WEBHOOK_ID], self._options[CONF_ONLINE_REMOTE]
        )
        return self.async_show_form(
            step_id="online_bridge",
            data_schema=vol.Schema({}),
            description_placeholders={"url": url, "effects": effects_csv(url)},
        )
