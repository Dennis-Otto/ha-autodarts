"""Shared exceptions: of the Board Manager's API and the board search, and of
the games, which know nothing of Home Assistant."""

import aiohttp


class AutodartsApiError(Exception):
    """Base exception for Autodarts API errors."""


class AutodartsConnectionError(AutodartsApiError):
    """Transport, service or malformed response error."""


class ActionRefused(ValueError):
    """An action that the games cannot take now: the key of the message that
    says why, and what the message names. The actions of Home Assistant show
    the message, see games_coordinator.refusals."""

    def __init__(self, key: str, **placeholders: str) -> None:
        super().__init__(key)
        self.key = key
        self.placeholders = placeholders


def open_session(session: aiohttp.ClientSession) -> aiohttp.ClientSession:
    """The shared session, unless Home Assistant closed it while stopping.

    aiohttp answers a request on a closed session with a RuntimeError; for the
    integration it is a lost connection like any other, not an unexpected error.
    """
    if session.closed:
        raise AutodartsConnectionError("Home Assistant closed its HTTP session")
    return session
