"""The highlight gallery of the media browser: photos by month, safe by design."""

import os
from datetime import datetime
from pathlib import Path

import pytest
from homeassistant.components import media_source
from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import MediaSourceItem, Unresolvable
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.autodarts.media_source import (
    Highlight,
    async_get_media_source,
    highlight,
    highlight_folder,
)

from .test_local_setup import setup_local
from .test_training import board

PHOTOS = [
    "2026-09-26_21-05-33_Alex_180.jpg",
    "2026-09-26_21-07-10_Alex Bee_checkout-121.JPG",
    "2026-09-02_18-00_140.png",
    "2026-08-31_Sam.webp",
    "2026-08-30.jpeg",
]


@pytest.fixture
def gallery(hass, tmp_path) -> Path:
    """A media folder with the highlight photos and some files that are none."""
    hass.config.media_dirs = {"other": str(tmp_path / "other"), "local": str(tmp_path)}
    folder = tmp_path / "autodarts" / "highlights"
    folder.mkdir(parents=True)
    for name in PHOTOS:
        (folder / name).write_bytes(b"photo")
    (folder / "notes.txt").write_text("no photo")
    (folder / ".hidden.jpg").write_bytes(b"photo")
    (folder / "a folder.jpg").mkdir()
    # A photo saved by other means is sorted by the time it was written.
    other = folder / "kitchen.jpg"
    other.write_bytes(b"photo")
    written = datetime(2026, 7, 4, 12, 0, tzinfo=dt_util.get_default_time_zone())
    os.utime(other, (written.timestamp(), written.timestamp()))
    (tmp_path / "secret.jpg").write_bytes(b"secret")
    # A link that leads nowhere is no photo either.
    try:
        (folder / "broken.jpg").symlink_to(tmp_path / "gone.jpg")
    except OSError:
        pass  # Creating links needs rights Windows does not always grant.
    return folder


def item(hass, identifier: str = "") -> MediaSourceItem:
    return MediaSourceItem(hass, "autodarts", identifier, None)


def test_names_tell_the_moment_the_player_and_the_score(tmp_path):
    def parsed(name: str) -> Highlight | None:
        path = tmp_path / name
        path.write_bytes(b"photo")
        return highlight(path)

    assert parsed("2026-09-26_21-05-33_Alex_180.jpg") == Highlight(
        file="2026-09-26_21-05-33_Alex_180.jpg",
        taken=datetime(2026, 9, 26, 21, 5, 33),
        player="Alex",
        score=180,
    )
    checkout = parsed("2026-09-26_Anna_Lena_checkout-121.jpg")
    assert (checkout.player, checkout.score, checkout.checkout) == (
        "Anna Lena",
        121,
        True,
    )
    assert checkout.taken == datetime(2026, 9, 26)
    assert parsed("2026-09-26_21-05_100.png").taken == datetime(2026, 9, 26, 21, 5)
    alone = parsed("2026-09-26_21-05-33_60.webp")
    assert (alone.player, alone.score) == (None, 60)
    assert parsed("2026-09-26_Kim.jpg").score is None
    # A date that does not exist, or no date at all, falls back to the file time.
    for name in ("2026-13-40_Alex_180.jpg", "180.jpg"):
        fallback = parsed(name)
        assert (fallback.player, fallback.score, fallback.label) == (
            None,
            None,
            name[:-4],
        )
    assert parsed("notes.txt") is None
    assert parsed(".2026-09-26_Alex_180.jpg") is None

    photo = Highlight("x.jpg", datetime(2026, 9, 6), "Alex", 180)
    assert photo.title("de") == "180 · Alex · 06.09."
    assert photo.title("en") == "180 · Alex · Sep 6"
    assert Highlight("x.jpg", datetime(2026, 1, 1), None, 121, True).title("en") == (
        "Checkout 121 · Jan 1"
    )
    assert Highlight("x.jpg", datetime(2026, 12, 24)).title("de") == "24.12."


async def test_the_gallery_lists_the_months_and_their_photos(hass, gallery):
    source = await async_get_media_source(hass)
    assert source.name == "Autodarts"
    root = await source.async_browse_media(item(hass))
    assert (root.title, root.media_class, root.can_expand, root.can_play) == (
        "Autodarts",
        MediaClass.DIRECTORY,
        True,
        False,
    )
    # The newest month first, its newest photo as the cover.
    assert [(month.identifier, month.title) for month in root.children] == [
        ("2026-09", "September 2026"),
        ("2026-08", "August 2026"),
        ("2026-07", "July 2026"),
    ]
    cover = "/media/local/autodarts/highlights/2026-09-26_21-07-10_Alex%20Bee_checkout-121.JPG"
    assert root.children[0].thumbnail == cover

    september = await source.async_browse_media(item(hass, "2026-09"))
    assert september.title == "September 2026"
    assert [
        (photo.identifier, photo.title, photo.media_content_type)
        for photo in september.children
    ] == [
        (
            "2026-09-26_21-07-10_Alex Bee_checkout-121.JPG",
            "Checkout 121 · Alex Bee · Sep 26",
            "image/jpeg",
        ),
        ("2026-09-26_21-05-33_Alex_180.jpg", "180 · Alex · Sep 26", "image/jpeg"),
        ("2026-09-02_18-00_140.png", "140 · Sep 2", "image/png"),
    ]
    photo = september.children[1]
    assert (photo.media_class, photo.can_play, photo.can_expand) == (
        MediaClass.IMAGE,
        True,
        False,
    )
    assert (
        photo.thumbnail
        == "/media/local/autodarts/highlights/2026-09-26_21-05-33_Alex_180.jpg"
    )
    july = await source.async_browse_media(item(hass, "2026-07"))
    assert [photo.title for photo in july.children] == ["kitchen · Jul 4"]

    hass.config.language = "de"
    august = await source.async_browse_media(item(hass, "2026-08"))
    assert august.title == "August 2026"
    assert [photo.title for photo in august.children] == ["Sam · 31.08.", "30.08."]
    assert (await source.async_browse_media(item(hass))).children[0].title == (
        "September 2026"
    )
    with pytest.raises(BrowseError):
        await source.async_browse_media(item(hass, "../secret"))


async def test_only_photos_of_the_folder_resolve(hass, gallery):
    source = await async_get_media_source(hass)
    photo = await source.async_resolve_media(
        item(hass, "2026-09-26_21-05-33_Alex_180.jpg")
    )
    assert (
        photo.url
        == "/media/local/autodarts/highlights/2026-09-26_21-05-33_Alex_180.jpg"
    )
    assert photo.mime_type == "image/jpeg"
    assert photo.path == gallery / "2026-09-26_21-05-33_Alex_180.jpg"
    webp = await source.async_resolve_media(item(hass, "2026-08-31_Sam.webp"))
    assert webp.mime_type == "image/webp"

    link = gallery / "link.jpg"
    try:
        link.symlink_to(gallery.parents[1] / "secret.jpg")
    except OSError:
        link = None  # Creating links needs rights Windows does not always grant.
    for identifier in (
        "../../secret.jpg",
        "..",
        "autodarts/highlights/2026-08-30.jpeg",
        "2026-09",
        "notes.txt",
        ".hidden.jpg",
        "missing.jpg",
        "a folder.jpg",
        *(["link.jpg"] if link else []),
    ):
        with pytest.raises(Unresolvable):
            await source.async_resolve_media(item(hass, identifier))
    if link:
        listed = await source.async_browse_media(item(hass, "2026-09"))
        assert "link.jpg" not in [photo.identifier for photo in listed.children]


async def test_without_a_folder_the_gallery_is_empty(hass, tmp_path):
    source = await async_get_media_source(hass)
    hass.config.media_dirs = {"media": str(tmp_path)}
    assert highlight_folder(hass) == ("media", tmp_path / "autodarts" / "highlights")
    assert (await source.async_browse_media(item(hass))).children == []
    hass.config.media_dirs = {}
    assert highlight_folder(hass) is None
    assert (await source.async_browse_media(item(hass))).children == []
    with pytest.raises(Unresolvable):
        await source.async_resolve_media(item(hass, "2026-09-26_Alex_180.jpg"))


async def test_the_media_browser_finds_the_gallery_of_the_integration(
    hass, aioclient_mock, gallery
):
    await setup_local(hass, aioclient_mock, state=board())
    assert await async_setup_component(hass, "media_source", {})
    root = await media_source.async_browse_media(hass, "media-source://")
    assert "Autodarts" in [child.title for child in root.children]
    months = await media_source.async_browse_media(hass, "media-source://autodarts")
    assert months.children[0].title == "September 2026"
    resolved = await media_source.async_resolve_media(
        hass, "media-source://autodarts/2026-08-30.jpeg", None
    )
    assert resolved.url == "/media/local/autodarts/highlights/2026-08-30.jpeg"
