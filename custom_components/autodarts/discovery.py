"""Find boards on this network through the lookup the Board Manager app uses."""

from __future__ import annotations

import asyncio
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .const import DEFAULT_PORT, DISCOVERY_URL
from .errors import AutodartsConnectionError


def _port(value: Any) -> int:
    port = int(value) if isinstance(value, (int, str)) and str(value).isdigit() else 0
    return port if 0 < port < 65536 else DEFAULT_PORT


def cloud_addresses(value: object) -> list[tuple[str, int]]:
    """Plain HTTP addresses of a board, as the Autodarts cloud lists them."""
    addresses = []
    for address in value.split(",") if isinstance(value, str) else []:
        try:
            parsed = urlparse(address.strip())
            port = parsed.port or DEFAULT_PORT
        except ValueError:
            continue
        if parsed.scheme == "http" and parsed.hostname:
            addresses.append((parsed.hostname, port))
    return addresses


async def async_discover_boards(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Boards Autodarts reports behind this network's public address.

    The service needs no login; it sees this network's public IP address, as it
    does when the Board Manager app searches for boards.
    """
    try:
        async with asyncio.timeout(10):
            async with session.get(DISCOVERY_URL) as response:
                response.raise_for_status()
                listed = await response.json(content_type=None)
    except (TimeoutError, aiohttp.ClientError, ValueError) as err:
        raise AutodartsConnectionError("Board lookup unavailable") from err
    boards = []
    for board in listed if isinstance(listed, list) else []:
        if not isinstance(board, dict):
            continue
        board_id, host = board.get("boardId"), board.get("ip")
        if not isinstance(board_id, str) or not board_id or not isinstance(host, str):
            continue
        try:
            ip_address(host)
        except ValueError:
            continue
        name, version = board.get("name"), board.get("version")
        boards.append(
            {
                "board_id": board_id,
                "host": host,
                "port": _port(board.get("insecurePort") or board.get("port")),
                "name": name.strip()
                if isinstance(name, str) and name.strip()
                else None,
                "version": version if isinstance(version, str) else None,
            }
        )
    return boards
