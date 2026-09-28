"""Keep the videos of the creator kit in step with the animations they come from."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageSequence

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "creator_media", ROOT / "scripts" / "creator_media.py"
)
media = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media)
KITS = (ROOT / "docs" / "creator-kit.md", ROOT / "docs" / "de" / "creator-kit.md")
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


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="needs ffprobe")
@pytest.mark.parametrize("file", [file for file in FILES if file.endswith(".mp4")])
def test_every_video_is_as_long_as_its_animation(file):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(media.MEDIA / file)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert float(probe.stdout) == pytest.approx(animation_length(file), abs=0.1)
