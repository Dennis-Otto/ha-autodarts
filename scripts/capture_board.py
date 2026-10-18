"""Record what a real Board Manager answers, for tests/fixtures/board_manager.

The unit tests and the Docker end-to-end test answer like the recordings in
tests/fixtures/board_manager, and tests/test_board_contract.py holds both to them.
This script makes such a recording of a board in your network:

    python scripts/capture_board.py 192.168.1.50
    python scripts/capture_board.py dartboard.local --seconds 120
    python scripts/capture_board.py 192.168.1.50 --frames 40 --out /tmp/boards

It reads every route of the Board Manager that the integration reads and records
the frames of its socket for a while: start the detection, throw a few darts and
take them out meanwhile. It writes them to tests/fixtures/board_manager/<version>/,
one file per route, the frames in ws-frames.jsonl and what it recorded in
capture.json. A route the board doesn't have is listed there as absent.

The answers carry the board's ID and API key, its TLS key and the name and
addresses of the board PC. They are replaced by the placeholders of PLACEHOLDERS,
like every value of a key that names a secret and every private IPv4 address,
before anything is written, and the script writes nothing if one of them is left.
Look through the files all the same before you share them.

It needs Python 3.13 or newer and aiohttp (`pip install aiohttp`), which the test
environment of requirements-test.txt has.
"""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import re
import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import aiohttp

ROOT = Path(__file__).parents[1]
RECORDINGS = ROOT / "tests" / "fixtures" / "board_manager"
PORT = 3180
SECONDS = 60
# The routes the integration reads, by the file that keeps the answer.
ROUTES = {
    "state.json": "/api/state",
    "config.json": "/api/config",
    "version.txt": "/api/version",
    "state-stats.json": "/api/state/stats",
    "state-motion.json": "/api/state/motion",
    "cams-stats.json": "/api/cams/stats",
    "cams-state.json": "/api/cams/state",
    "system.json": "/api/system",
    "host.json": "/api/host",
}
EVENTS = "/api/events"
REQUEST = aiohttp.ClientTimeout(total=10)
FRAMES = "ws-frames.jsonl"
CAPTURE = "capture.json"
# What a recording says in place of the identity and the secrets of a board.
PLACEHOLDERS = {
    "board_id": "board-1",
    "api_key": "private-board-api-key",
    "tls_key": "private-tls-key",
    "tls_cert": "private-tls-cert",
    "hostname": "dartboard-pc",
    "ip": "198.51.100.7",
}
# A key whose value is a secret, also one a later Board Manager adds.
SECRET = re.compile(r"(key|token|secret|password|cert)$", re.IGNORECASE)
# Shorter values are replaced only at their keys, not wherever they appear, so that
# a short ID can't change numbers or names that happen to contain it.
SHORTEST_SECRET = 6
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
# The addresses for documentation (RFC 5737), such as the placeholder, may stay.
DOCUMENTATION = tuple(
    ipaddress.IPv4Network(network)
    for network in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)
# Board Manager versions as they name a folder of recordings.
VERSION = re.compile(r"v?(\d{1,4}(?:\.\d{1,6}){0,3}(?:-[0-9A-Za-z.]{1,32})?)")


def placeholder(key: str) -> str:
    """The placeholder of a secret, by the key that holds it."""
    return PLACEHOLDERS.get(key, f"private-{key}")


def is_secret(key: str) -> bool:
    return key in PLACEHOLDERS or bool(SECRET.search(key))


def is_placeholder(value: str) -> bool:
    """A value that a recording already says in place of a secret."""
    return value in PLACEHOLDERS.values() or value.startswith("private-")


def secrets(answers: object, host: str = "") -> dict[str, str]:
    """The secrets of the answers, each with its placeholder, and the address that
    reached the board."""
    found: dict[str, str] = {}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if (
                    isinstance(item, str)
                    and item
                    and is_secret(key)
                    and not is_placeholder(item)
                ):
                    found.setdefault(item, placeholder(key))
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(answers)
    if host and not is_placeholder(host):
        found.setdefault(host, PLACEHOLDERS["ip" if is_ip(host) else "hostname"])
    return found


def is_ip(text: str) -> bool:
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


def private(address: str) -> bool:
    """An address of a home network, which a recording must not keep."""
    try:
        ip = ipaddress.IPv4Address(address)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_unspecified or any(ip in net for net in DOCUMENTATION):
        return False
    return ip.is_private


def redact(value: Any, found: dict[str, str]) -> Any:
    """The value with every secret, at its key or anywhere in a text, and every
    private IPv4 address replaced by its placeholder."""
    replacements = sorted(
        (item for item in found.items() if len(item[0]) >= SHORTEST_SECRET),
        key=lambda item: -len(item[0]),
    )

    def text(item: str) -> str:
        if item in found:
            return found[item]
        for secret, replacement in replacements:
            item = item.replace(secret, replacement)
        return IPV4.sub(
            lambda match: (
                PLACEHOLDERS["ip"] if private(match.group()) else match.group()
            ),
            item,
        )

    def walk(item: Any, key: str = "") -> Any:
        if isinstance(item, dict):
            return {text(name): walk(entry, name) for name, entry in item.items()}
        if isinstance(item, list):
            return [walk(entry) for entry in item]
        if isinstance(item, str):
            return placeholder(key) if item and is_secret(key) else text(item)
        return item

    return walk(value)


def leftovers(content: str, found: dict[str, str]) -> list[str]:
    """What a file to be written still holds of the secrets, by their placeholders."""
    left = {
        replacement
        for secret, replacement in found.items()
        if len(secret) >= SHORTEST_SECRET
        # As written in a text, and as JSON writes it, such as a key of several lines.
        and (
            secret in content or json.dumps(secret, ensure_ascii=False)[1:-1] in content
        )
    }
    if any(private(address) for address in IPV4.findall(content)):
        left.add("a private IPv4 address")
    return sorted(left)


def folder_name(version: object) -> str:
    """The folder of a recording: the Board Manager version without its v."""
    match = VERSION.fullmatch(version.strip()) if isinstance(version, str) else None
    if match is None:
        raise SystemExit(f"The board answers no version on /api/version: {version!r}")
    return match.group(1)


def files(
    answers: dict[str, Any],
    frames: Sequence[Any],
    absent: Sequence[str],
    host: str,
    captured: str | None,
) -> tuple[str, dict[str, str]]:
    """The folder and the redacted files of a recording, by their names."""
    version = folder_name(answers.get("version.txt"))
    found = secrets(answers, host) | secrets(list(frames))
    content = {}
    for name, answer in redact(answers, found).items():
        content[name] = (
            f"{answer.strip()}\n"
            if name.endswith(".txt")
            else json.dumps(answer, indent=2, ensure_ascii=False) + "\n"
        )
    content[FRAMES] = "".join(
        json.dumps(frame, ensure_ascii=False, separators=(",", ":")) + "\n"
        for frame in redact(list(frames), found)
    )
    summary = {
        "board_manager": version,
        "captured": captured,
        "source": "scripts/capture_board.py",
        "absent": list(absent),
    }
    content[CAPTURE] = json.dumps(summary, indent=2) + "\n"
    left = sorted(
        {item for text in content.values() for item in leftovers(text, found)}
    )
    if left:
        raise SystemExit(
            f"Nothing written: the recording still holds {', '.join(left)}."
        )
    return version, content


def write(out: Path, version: str, content: dict[str, str]) -> Path:
    """Write a recording; files of an earlier recording that this one lacks go."""
    folder = out / version
    folder.mkdir(parents=True, exist_ok=True)
    for name in (*ROUTES, FRAMES, CAPTURE):
        if name not in content:
            (folder / name).unlink(missing_ok=True)
    for name, text in content.items():
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    return folder


def base_url(host: str, port: int) -> str:
    """The address of the Board Manager, an IPv6 address in brackets."""
    return f"http://[{host}]:{port}" if ":" in host else f"http://{host}:{port}"


async def read_routes(
    session: aiohttp.ClientSession, base: str
) -> tuple[dict[str, Any], list[str]]:
    """The answer of every route, and the routes the board doesn't have."""
    answers: dict[str, Any] = {}
    absent = []
    for name, path in ROUTES.items():
        async with session.get(f"{base}{path}", timeout=REQUEST) as response:
            if response.status in (404, 405):
                absent.append(path)
                continue
            response.raise_for_status()
            text = await response.text()
            answers[name] = text if name.endswith(".txt") else json.loads(text)
    return answers, absent


async def read_frames(
    session: aiohttp.ClientSession,
    base: str,
    seconds: float,
    limit: int | None = None,
    connected: Callable[[], None] = lambda: None,
) -> tuple[list[Any], int]:
    """The frames of the socket for some seconds or up to a number of them, and
    how many were no JSON."""
    frames: list[Any] = []
    skipped = 0
    async with asyncio.timeout(10):
        socket = await session.ws_connect(
            f"{base}{EVENTS}", timeout=aiohttp.ClientWSTimeout(ws_close=5)
        )
    async with socket:
        connected()
        try:
            async with asyncio.timeout(seconds):
                async for message in socket:
                    if message.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        frames.append(json.loads(message.data))
                    except ValueError:
                        skipped += 1
                    if limit is not None and len(frames) >= limit:
                        break
        except TimeoutError:
            pass
    return frames, skipped


async def capture(
    host: str,
    port: int = PORT,
    seconds: float = SECONDS,
    out: Path = RECORDINGS,
    limit: int | None = None,
    connected: Callable[[], None] = lambda: None,
) -> Path:
    """Record a board and write the recording; the folder it went to."""
    base = base_url(host, port)
    # No limit for the session, whose socket stays open while it records.
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout()) as session:
        answers, absent = await read_routes(session, base)
        frames, skipped = await read_frames(session, base, seconds, limit, connected)
    if skipped:
        print(f"Skipped {skipped} frames that were no JSON.", file=sys.stderr)
    version, content = files(answers, frames, absent, host, date.today().isoformat())
    return write(out, version, content)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record what a Board Manager answers, without its secrets."
    )
    parser.add_argument("host", help="the address or name of the board PC")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument(
        "--seconds",
        type=float,
        default=SECONDS,
        help="how long to record the socket (default: %(default)s)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        help="stop after this many frames of the socket",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=RECORDINGS,
        help="the folder of the recordings (default: tests/fixtures/board_manager)",
    )
    arguments = parser.parse_args(argv)

    def connected() -> None:
        print(
            f"Recording the socket for {arguments.seconds:g} s: start the detection, "
            "throw a few darts and take them out.",
            file=sys.stderr,
        )

    try:
        folder = asyncio.run(
            capture(
                arguments.host,
                arguments.port,
                arguments.seconds,
                arguments.out,
                arguments.frames,
                connected,
            )
        )
    except (aiohttp.ClientError, TimeoutError, ValueError) as error:
        print(f"The board did not answer as expected: {error!r}", file=sys.stderr)
        return 1
    print(f"Wrote {folder}. Look through the files before you share them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
