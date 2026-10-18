"""Keep the videos of the creator kit in step with the animations they come from."""

import importlib.util
import struct
from pathlib import Path

import pytest
from PIL import Image, ImageSequence

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "creator_media", ROOT / "scripts" / "creator_media.py"
)
media = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media)
KITS = (ROOT / "docs" / "creator-kit.md", ROOT / "docs" / "creator-kit.de.md")
FILES = sorted(
    f"{name}-{language}.{kind}"
    for name in media.ANIMATIONS
    for language in media.LANGUAGES
    for kind in ("mp4", "gif")
)


def animation_length(file: str) -> float:
    """Seconds of the WebP animation a video or GIF was made from."""
    name, language = file.rsplit(".", 1)[0].rsplit("-", 1)
    source = media.IMAGES / language / f"{name}.webp"
    return sum(duration for _, duration in media.frames(source)) / 1000


def test_the_schedule_keeps_the_length_of_the_animation():
    durations = [1400, 250, 650, 17, 2800]
    counts = media.schedule(durations)
    assert sum(counts) == round(sum(durations) * media.FPS / 1000)
    assert all(count >= 0 for count in counts)
    # 30 frames of 100 ms: three video frames each, without drifting.
    assert media.schedule([100] * 30) == [3] * 30
    # Frames of 50 ms alternate between one and two video frames at 30 per second.
    assert sum(media.schedule([50] * 10)) == 15


def test_frames_keep_their_durations_and_lose_transparency(tmp_path):
    source = tmp_path / "animation.webp"
    first = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    second = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
    first.save(
        source,
        save_all=True,
        append_images=[second],
        duration=[200, 500],
        loop=0,
        lossless=True,
    )
    frames = list(media.frames(source))
    assert [duration for _, duration in frames] == [200, 500]
    assert frames[0][0].mode == "RGB"
    assert frames[0][0].getpixel((0, 0)) == media.BACKGROUND
    assert frames[1][0].getpixel((0, 0)) == (255, 0, 0)


def test_every_video_exists_and_nothing_else():
    assert sorted(path.name for path in media.MEDIA.iterdir()) == FILES


@pytest.mark.parametrize(
    "kit", KITS, ids=lambda path: path.relative_to(ROOT).as_posix()
)
def test_both_creator_kits_link_every_video(kit):
    text = kit.read_text(encoding="utf-8")
    assert [file for file in FILES if f"media/{file}" not in text] == []


@pytest.mark.parametrize("file", [file for file in FILES if file.endswith(".gif")])
def test_every_gif_is_as_long_as_its_animation(file):
    with Image.open(media.MEDIA / file) as gif:
        length = sum(
            frame.info.get("duration", 0) for frame in ImageSequence.Iterator(gif)
        )
    assert length / 1000 == pytest.approx(animation_length(file), abs=0.1)


@pytest.mark.parametrize("file", [file for file in FILES if file.endswith(".mp4")])
def test_every_video_is_as_long_as_its_animation(file):
    length = media.mp4_duration(media.MEDIA / file)
    assert length == pytest.approx(animation_length(file), abs=0.1)


def box(kind: bytes, content: bytes, *, large: bool = False) -> bytes:
    """An MP4 box: its size, its type and its content, with a 64-bit size if large."""
    if large:
        return struct.pack(">I4sQ", 1, kind, 16 + len(content)) + content
    return struct.pack(">I4s", 8 + len(content), kind) + content


def movie_header(timescale: int, duration: int, version: int = 0) -> bytes:
    """The box mvhd of a movie, as ffmpeg writes it, up to the duration."""
    if version:
        times = struct.pack(">QQIQ", 0, 0, timescale, duration)
    else:
        times = struct.pack(">IIII", 0, 0, timescale, duration)
    # The version, the flags, the times and the rest of the header: rate, volume, …
    return box(b"mvhd", bytes([version, 0, 0, 0]) + times + bytes(80))


def test_the_duration_comes_from_the_header_of_the_movie(tmp_path):
    video = tmp_path / "video.mp4"
    # ftyp, free and the media first, as without +faststart; then the movie.
    track = box(b"trak", box(b"tkhd", bytes(84)))
    video.write_bytes(
        box(b"ftyp", b"isom" + bytes(4))
        + box(b"free", b"")
        + box(b"mdat", bytes(64), large=True)
        + box(b"moov", track + movie_header(1000, 4250))
    )
    assert media.mp4_duration(video) == 4.25


def test_a_long_movie_has_a_header_of_version_one(tmp_path):
    video = tmp_path / "video.mp4"
    # Ten hours at 90 kHz no longer fit in 32 bits.
    video.write_bytes(box(b"moov", movie_header(90_000, 36_000 * 90_000, version=1)))
    assert media.mp4_duration(video) == 36_000


def test_a_last_box_of_size_zero_reaches_to_the_end_of_the_file(tmp_path):
    video = tmp_path / "video.mp4"
    movie = box(b"moov", movie_header(600, 1500))
    video.write_bytes(box(b"ftyp", b"isom") + bytes(4) + movie[4:])
    assert media.mp4_duration(video) == 2.5


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(box(b"ftyp", b"isom"), id="no movie"),
        pytest.param(box(b"moov", box(b"trak", b"")), id="no header"),
        pytest.param(struct.pack(">I4s", 4, b"moov") + bytes(8), id="broken size"),
        pytest.param(struct.pack(">I4s", 1, b"moov") + bytes(4), id="cut-off size"),
        pytest.param(box(b"moov", box(b"mvhd", bytes(16))), id="short header"),
        pytest.param(
            box(b"moov", box(b"mvhd", bytes([1, 0, 0, 0]) + bytes(20))),
            id="short header of version one",
        ),
        pytest.param(box(b"moov", movie_header(0, 100)), id="no timescale"),
        pytest.param(b"", id="empty"),
    ],
)
def test_a_file_without_a_movie_header_is_no_video(tmp_path, content):
    video = tmp_path / "video.mp4"
    video.write_bytes(content)
    with pytest.raises(ValueError, match="not an MP4 video"):
        media.mp4_duration(video)
