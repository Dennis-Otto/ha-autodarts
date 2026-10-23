"""Shared exceptions of the Board Manager's API and the board search."""

import aiohttp


class AutodartsApiError(Exception):
    """Base exception for Autodarts API errors."""


class AutodartsConnectionError(AutodartsApiError):
    """Transport, service or malformed response error."""


def open_session(session: aiohttp.ClientSession) -> aiohttp.ClientSession:
    """The shared session, unless Home Assistant closed it while stopping.

    aiohttp answers a request on a closed session with a RuntimeError; for the
    integration it is a lost connection like any other, not an unexpected error.
    """
    if session.closed:
        raise AutodartsConnectionError("Home Assistant closed its HTTP session")
    return session
