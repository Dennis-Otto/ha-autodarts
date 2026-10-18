"""scripts/capture_board.py records what a Board Manager answers for
tests/fixtures/board_manager. It replaces the identity and the secrets of the board
and the addresses of its network by placeholders before it writes anything, and
writes nothing that still holds one. tests/test_board_contract.py records the double
of the end-to-end test with it."""

import importlib.util
import json
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "capture_board", ROOT / "scripts" / "capture_board.py"
)
capture_board = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture_board)
PLACEHOLDERS = capture_board.PLACEHOLDERS

# What a real board answers with: its ID, its keys, a token of a later version and
# the name and addresses of the board PC in its home network.
BOARD_ID = "5f0c2d8e-3b1a-4c6f-9e2d-7a8b9c0d1e2f"
API_KEY = "a1b2c3d4e5f6-board-api-key"
TLS_KEY = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg\n-----END PRIVATE KEY-----\n"
TLS_CERT = "-----BEGIN CERTIFICATE-----\nMIIC2jCCAcKgAw\n-----END CERTIFICATE-----\n"
TOKEN = "eyJhbGciOiJIUzI1NiJ9.refresh"
HOSTNAME = "living-room-pc"
ADDRESS = "192.168.178.23"
SECRETS = (BOARD_ID, API_KEY, TLS_KEY, TLS_CERT, TOKEN, HOSTNAME, ADDRESS)


def answers():
    return {
        "version.txt": "v2.0.3\n",
        "config.json": {
            "auth": {"board_id": BOARD_ID, "api_key": API_KEY},
            "cam": {"cams": ["/dev/video0"]},
        },
        "system.json": {
            "config": {
                "host": {"port": "3180", "tls_key": TLS_KEY, "tls_cert": TLS_CERT}
            },
            "link": f"wss://api.autodarts.io/boards/{BOARD_ID}",
            "log": f"Listening on {ADDRESS}:3180 and 10.8.0.2, OpenCV 4.12.0.88",
            "cloud": {"refreshToken": TOKEN, "pin": "1234"},
            "legacy": {"api_key": "abc"},
            "note": "the abcde of darts",
            "docs": "192.0.2.10",
        },
        "host.json": {"hostname": HOSTNAME, "ip": ADDRESS, "model": "", "cpu2": None},
    }


FRAMES = [{"type": "state", "data": {"board": BOARD_ID, "from": f"{HOSTNAME}.lan"}}]


def written(content: dict[str, str]) -> dict:
    return {
        name: text if name.endswith(".txt") else json.loads(text)
        for name, text in content.items()
        if name != capture_board.FRAMES
    }


def test_a_recording_says_placeholders_instead_of_the_secrets_of_the_board():
    version, content = capture_board.files(
        answers(), FRAMES, ["/api/state/motion"], ADDRESS, "2026-10-18"
    )

    assert version == "2.0.3"
    files = written(content)
    assert files["version.txt"] == "v2.0.3\n"
    assert files["config.json"]["auth"] == {
        "board_id": PLACEHOLDERS["board_id"],
        "api_key": PLACEHOLDERS["api_key"],
    }
    system = files["system.json"]
    assert system["config"]["host"] == {
        "port": "3180",
        "tls_key": PLACEHOLDERS["tls_key"],
        "tls_cert": PLACEHOLDERS["tls_cert"],
    }
    # Wherever the board names them, and also secrets of keys it doesn't have yet.
    assert system["link"] == "wss://api.autodarts.io/boards/board-1"
    assert system["log"] == (
        "Listening on 198.51.100.7:3180 and 198.51.100.7, OpenCV 4.12.0.88"
    )
    assert system["cloud"] == {"refreshToken": "private-refreshToken", "pin": "1234"}
    # A short secret only at its key, so that it can't change other texts.
    assert system["legacy"] == {"api_key": PLACEHOLDERS["api_key"]}
    assert system["note"] == "the abcde of darts"
    # Addresses for documentation stay, such as those of the placeholders.
    assert system["docs"] == "192.0.2.10"
    assert files["host.json"] == {
        "hostname": PLACEHOLDERS["hostname"],
        "ip": PLACEHOLDERS["ip"],
        "model": "",
        "cpu2": None,
    }
    assert content[capture_board.FRAMES] == (
        '{"type":"state","data":{"board":"board-1","from":"dartboard-pc.lan"}}\n'
    )
    assert files[capture_board.CAPTURE] == {
        "board_manager": "2.0.3",
        "captured": "2026-10-18",
        "source": "scripts/capture_board.py",
        "absent": ["/api/state/motion"],
    }
    for text in content.values():
        assert text.endswith("\n")
        for secret in SECRETS:
            # Neither as it is nor as JSON writes it, such as a key of several lines.
            assert secret not in text
            assert json.dumps(secret)[1:-1] not in text


def test_the_name_of_the_board_pc_it_was_given_is_replaced_too():
    _, content = capture_board.files(
        {"version.txt": "1.0.7", "state.json": {"source": "dartboard.fritz.box"}},
        [],
        [],
        "dartboard.fritz.box",
        None,
    )

    assert json.loads(content["state.json"]) == {"source": "dartboard-pc"}
    assert content["version.txt"] == "1.0.7\n"
    assert content[capture_board.FRAMES] == ""


@pytest.mark.parametrize("host", ["dartboard.local", "192.168.1.50"])
@pytest.mark.parametrize("hostname", ["dartboard", "board-pc", "artboard"])
def test_a_board_pc_named_like_part_of_a_placeholder_is_recorded(host, hostname):
    # "dartboard" is part of the placeholder "dartboard-pc": it must neither be
    # replaced again inside it nor count as left in the recording.
    _, content = capture_board.files(
        {
            "version.txt": "2.0.2",
            "host.json": {"hostname": hostname, "ip": "192.168.1.50"},
            "state.json": {"source": f"reached as {host}, named {hostname}"},
        },
        [{"type": "state", "data": {"from": f"{hostname}.lan"}}],
        [],
        host,
        None,
    )

    assert json.loads(content["host.json"]) == {
        "hostname": PLACEHOLDERS["hostname"],
        "ip": PLACEHOLDERS["ip"],
    }
    placeholder = PLACEHOLDERS["ip" if host[0].isdigit() else "hostname"]
    assert json.loads(content["state.json"]) == {
        "source": f"reached as {placeholder}, named dartboard-pc"
    }
    assert "dartboard-pc-pc" not in "".join(content.values())
    assert content[capture_board.FRAMES] == (
        '{"type":"state","data":{"from":"dartboard-pc.lan"}}\n'
    )


def test_a_secret_is_found_next_to_a_placeholder():
    found = {"dartboard": PLACEHOLDERS["hostname"]}

    assert capture_board.leftovers("dartboard-pc", found) == []
    assert capture_board.leftovers("dartboard-pc and dartboard", found) == [
        PLACEHOLDERS["hostname"]
    ]
    assert capture_board.alternation([]).search("anything") is None


def test_nothing_is_written_that_still_holds_a_secret(monkeypatch):
    monkeypatch.setattr(capture_board, "redact", lambda value, found: value)

    with pytest.raises(SystemExit, match="Nothing written: the recording still holds"):
        capture_board.files(answers(), FRAMES, [], ADDRESS, "2026-10-18")
    # Also a key of several lines, which JSON writes with \n.
    found = {TLS_KEY: PLACEHOLDERS["tls_key"]}
    left = capture_board.leftovers(json.dumps({"tls_key": TLS_KEY}), found)
    assert left == [PLACEHOLDERS["tls_key"]]


def test_a_private_address_is_found_wherever_it_is():
    assert capture_board.leftovers("seen at 10.0.0.5", {}) == ["a private IPv4 address"]
    assert capture_board.leftovers("127.0.0.1 0.0.0.0 198.51.100.7 8.8.8.8", {}) == []
    assert capture_board.leftovers("version 999.1.1.1", {}) == []


@pytest.mark.parametrize(
    ("version", "folder"),
    [("1.0.7\n", "1.0.7"), ("v2.0.2", "2.0.2"), ("2.1.0-beta.1", "2.1.0-beta.1")],
)
def test_a_recording_goes_to_the_folder_of_its_version(version, folder):
    assert capture_board.folder_name(version) == folder


@pytest.mark.parametrize("version", [None, "", "../../etc", "<html>", 2])
def test_a_board_without_a_version_is_not_recorded(version):
    with pytest.raises(SystemExit, match="answers no version"):
        capture_board.folder_name(version)


def test_a_new_recording_replaces_the_files_of_the_one_before(tmp_path):
    old = tmp_path / "2.0.2"
    old.mkdir()
    (old / "system.json").write_text("{}\n", encoding="utf-8")
    (old / "notes.md").write_text("kept\n", encoding="utf-8")

    folder = capture_board.write(tmp_path, "2.0.2", {"state.json": "{}\n"})

    assert folder == old
    assert sorted(path.name for path in folder.iterdir()) == ["notes.md", "state.json"]


def test_the_address_of_the_board_takes_brackets_for_ipv6():
    assert capture_board.base_url("192.0.2.10", 3180) == "http://192.0.2.10:3180"
    assert capture_board.base_url("dartboard.local", 80) == "http://dartboard.local:80"
    assert capture_board.base_url("fe80::1", 3180) == "http://[fe80::1]:3180"


def board(frames, *, close: bool = True) -> web.Application:
    """A Board Manager 1 that knows only the routes of the setup."""
    app = web.Application()

    async def state(request):
        return web.json_response({"x": 1})

    async def version(request):
        return web.Response(text="1.0.7")

    app.router.add_get("/api/state", state)
    app.router.add_get("/api/version", version)

    async def events(request):
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        for frame in frames:
            if isinstance(frame, bytes):
                await socket.send_bytes(frame)
            else:
                await socket.send_str(frame)
        if close:
            await socket.close()
        else:
            await socket.receive()
        return socket

    app.router.add_get("/api/events", events)
    return app


async def record(app, tmp_path, **arguments):
    server = TestServer(app)
    await server.start_server()
    try:
        return await capture_board.capture(
            "127.0.0.1", server.port, out=tmp_path, **arguments
        )
    finally:
        await server.close()


@pytest.mark.usefixtures("socket_enabled")
async def test_a_capture_keeps_the_json_frames_and_lists_the_routes_it_lacks(
    tmp_path, capsys
):
    folder = await record(board(['{"type":"state"}', "no json", b"\x00"]), tmp_path)

    names = sorted(path.name for path in folder.iterdir())
    assert names == ["capture.json", "state.json", "version.txt", "ws-frames.jsonl"]
    assert (folder / "ws-frames.jsonl").read_text() == '{"type":"state"}\n'
    absent = json.loads((folder / "capture.json").read_text())["absent"]
    assert absent == [
        path
        for name, path in capture_board.ROUTES.items()
        if name not in ("state.json", "version.txt")
    ]
    assert "Skipped 1 frames that were no JSON." in capsys.readouterr().err


@pytest.mark.usefixtures("socket_enabled")
async def test_a_capture_records_the_socket_for_the_seconds_it_is_given(tmp_path):
    folder = await record(board(['{"a":1}'], close=False), tmp_path, seconds=0.2)

    assert (folder / "ws-frames.jsonl").read_text() == '{"a":1}\n'


@pytest.mark.usefixtures("socket_enabled")
async def test_a_capture_stops_after_the_frames_it_is_given(tmp_path):
    frames = ['{"a":1}', '{"a":2}', '{"a":3}']

    folder = await record(board(frames, close=False), tmp_path, limit=2)

    assert (folder / "ws-frames.jsonl").read_text() == '{"a":1}\n{"a":2}\n'


def test_the_command_line_records_the_board_it_names(tmp_path, monkeypatch, capsys):
    calls = []

    async def capture(host, port, seconds, out, limit, connected):
        calls.append((host, port, seconds, out, limit))
        connected()
        return out / "2.0.2"

    monkeypatch.setattr(capture_board, "capture", capture)

    status = capture_board.main(
        ["192.0.2.10", "--seconds", "5", "--frames", "40", "--out", str(tmp_path)]
    )

    assert status == 0
    assert calls == [("192.0.2.10", 3180, 5.0, tmp_path, 40)]
    output = capsys.readouterr()
    assert "Recording the socket for 5 s" in output.err
    assert f"Wrote {tmp_path / '2.0.2'}." in output.out


@pytest.mark.parametrize(
    "error", [aiohttp.ClientConnectionError("refused"), TimeoutError(), ValueError()]
)
def test_the_command_line_says_when_the_board_did_not_answer(
    monkeypatch, capsys, error
):
    async def capture(*arguments):
        raise error

    monkeypatch.setattr(capture_board, "capture", capture)

    assert capture_board.main(["192.0.2.10"]) == 1
    assert "The board did not answer as expected" in capsys.readouterr().err
