"""Async clients for the Autodarts device-link, cloud and local APIs."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import aiohttp

from .errors import AutodartsApiError as AutodartsApiError
from .errors import AutodartsAuthError as AutodartsAuthError
from .errors import AutodartsConnectionError as AutodartsConnectionError
from .local_api import AutodartsLocalClient as AutodartsLocalClient

DEFAULT_TIMEOUT = 10
API_BASE = "https://api.autodarts.io"
AUTH_BASE = f"{API_BASE}/auth/v1"
DEVICE_CODE_URL = f"{AUTH_BASE}/device/code"
DEVICE_TOKEN_URL = f"{AUTH_BASE}/device/token"
REFRESH_URL = f"{AUTH_BASE}/refresh"
DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


@dataclass(frozen=True)
class DeviceAuthorization:
    """A short-lived device grant. Never expose the private device code."""

    device_code: str = field(repr=False)
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_at: float
    interval: float


def _positive_number(value: Any) -> float:
    """Validate server-provided lifetimes and intervals."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AutodartsConnectionError("Invalid authentication response")
    if not math.isfinite(value) or value <= 0:
        raise AutodartsConnectionError("Invalid authentication response")
    return float(value)


def _required_string(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value:
        raise AutodartsConnectionError("Incomplete authentication response")
    return value


async def _auth_request(
    session: aiohttp.ClientSession, url: str, payload: dict[str, str]
) -> dict[str, Any]:
    """Send JSON to the new auth service, without logging tokens or responses."""
    try:
        async with asyncio.timeout(DEFAULT_TIMEOUT):
            async with session.post(url, json=payload) as response:
                if response.status >= 500 or response.status == 429:
                    raise AutodartsConnectionError("Authentication service unavailable")
                body = await response.json()
                if not isinstance(body, dict):
                    raise AutodartsConnectionError("Invalid authentication response")
                if response.status in (400, 401, 403):
                    error = body.get("error")
                    known_errors = {
                        "authorization_pending",
                        "slow_down",
                        "access_denied",
                        "expired_token",
                        "invalid_client",
                        "unauthorized_client",
                        "invalid_grant",
                        "invalid_token",
                        "invalid_request",
                    }
                    raise AutodartsAuthError(
                        error
                        if isinstance(error, str) and error in known_errors
                        else "invalid_token"
                    )
                response.raise_for_status()
                return body
    except (TimeoutError, aiohttp.ClientError, ValueError) as err:
        raise AutodartsConnectionError(
            "Could not contact authentication service"
        ) from err


def _segment(value: str) -> str:
    """One path segment; an identifier can never reach another route."""
    if not isinstance(value, str) or not value:
        raise AutodartsConnectionError("Invalid identifier")
    return quote(value, safe="")


def normalize_token(body: dict[str, Any]) -> dict[str, Any]:
    """Require both tokens: the new service rotates refresh tokens on every use."""
    return {
        "access_token": _required_string(body, "access_token"),
        "refresh_token": _required_string(body, "refresh_token"),
        "expires_at": time.time() + _positive_number(body.get("expires_in", 900)),
    }


async def request_device_code(
    session: aiohttp.ClientSession, client_id: str
) -> DeviceAuthorization:
    """Request a code using a public client registered for device authorization."""
    body = await _auth_request(session, DEVICE_CODE_URL, {"client_id": client_id})
    verification_uri = _required_string(body, "verification_uri")
    return DeviceAuthorization(
        device_code=_required_string(body, "device_code"),
        user_code=_required_string(body, "user_code"),
        verification_uri=verification_uri,
        verification_uri_complete=body.get("verification_uri_complete")
        or verification_uri,
        expires_at=time.monotonic() + _positive_number(body.get("expires_in", 600)),
        interval=_positive_number(body.get("interval", 5)),
    )


async def wait_for_device_token(
    session: aiohttp.ClientSession,
    client_id: str,
    device: DeviceAuthorization,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, Any]:
    """Poll until approval, cancellation or expiry, respecting RFC 8628 backoff."""
    interval = device.interval
    remaining = device.expires_at - time.monotonic()
    if remaining <= 0:
        raise AutodartsAuthError("expired_token")
    try:
        async with asyncio.timeout(remaining):
            while True:
                await sleep(interval)
                try:
                    body = await _auth_request(
                        session,
                        DEVICE_TOKEN_URL,
                        {
                            "grant_type": DEVICE_GRANT_TYPE,
                            "device_code": device.device_code,
                            "client_id": client_id,
                        },
                    )
                except AutodartsAuthError as err:
                    if err.code == "authorization_pending":
                        continue
                    if err.code == "slow_down":
                        interval += 5
                        continue
                    raise
                except AutodartsConnectionError:
                    # A temporary outage must not discard the code already shown.
                    interval = min(max(interval * 2, 5), max(interval, 60))
                    continue
                return normalize_token(body)
    except TimeoutError as err:
        raise AutodartsAuthError("expired_token") from err


class AutodartsCloudClient:
    """Cloud API client with serialized refresh and immediate token persistence."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: dict[str, Any],
        client_id: str,
        on_token_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._session = session
        self._token = dict(token)
        self._client_id = client_id
        self._on_token_update = on_token_update
        self._refresh_lock = asyncio.Lock()

    @property
    def token(self) -> dict[str, Any]:
        """Return a copy of the current credentials for persistence."""
        return dict(self._token)

    async def _ensure_token(self, rejected_token: str | None = None) -> None:
        async with self._refresh_lock:
            if rejected_token is not None:
                if self._token.get("access_token") != rejected_token:
                    return  # Another request has already refreshed this token.
            elif time.time() < self._token.get("expires_at", 0) - 30:
                return
            refresh_token = self._token.get("refresh_token")
            if not refresh_token:
                raise AutodartsAuthError("invalid_grant")
            body = await _auth_request(
                self._session,
                REFRESH_URL,
                {
                    "client_id": self._client_id,
                    "refresh_token": refresh_token,
                },
            )
            self._token = normalize_token(body)
            # Persist BEFORE any following API request can fail or HA can restart.
            if self._on_token_update is not None:
                self._on_token_update(self.token)

    async def _fetch(self, path: str, access_token: str) -> tuple[bool, Any]:
        """Read once: whether the access token was rejected, otherwise the answer."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with self._session.get(
                    f"{API_BASE}{path}",
                    headers={"Authorization": f"Bearer {access_token}"},
                ) as response:
                    if response.status == 401:
                        return True, None
                    if response.status == 403:
                        raise AutodartsAuthError("access_denied")
                    response.raise_for_status()
                    return False, await response.json()
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise AutodartsConnectionError(f"Could not fetch {path}") from err

    async def _get(self, path: str) -> Any:
        await self._ensure_token()
        access_token = self._token["access_token"]
        rejected, answer = await self._fetch(path, access_token)
        if rejected:
            # A token can be revoked before it expires: refresh once, then retry.
            await self._ensure_token(rejected_token=access_token)
            rejected, answer = await self._fetch(path, self._token["access_token"])
            if rejected:
                raise AutodartsAuthError("invalid_token")
        return answer

    async def get_boards(self) -> list[dict[str, Any]]:
        """List boards belonging to the authenticated user."""
        boards = await self._get("/bs/v0/boards/")
        if not isinstance(boards, list) or any(
            not isinstance(board, dict) or not isinstance(board.get("id"), str)
            for board in boards
        ):
            raise AutodartsConnectionError("Invalid boards response")
        return boards

    async def _get_object(self, path: str) -> dict[str, Any]:
        result = await self._get(path)
        if not isinstance(result, dict):
            raise AutodartsConnectionError("Invalid Autodarts response")
        return result

    async def get_board(self, board_id: str) -> dict[str, Any]:
        """Fetch a board's connection and match status."""
        return await self._get_object(f"/bs/v0/boards/{_segment(board_id)}")

    async def get_match(self, match_id: str) -> dict[str, Any]:
        """Fetch match metadata."""
        return await self._get_object(f"/gs/v0/matches/{_segment(match_id)}")

    async def get_match_state(self, match_id: str) -> dict[str, Any]:
        """Fetch live game state."""
        return await self._get_object(f"/gs/v0/matches/{_segment(match_id)}/state")
