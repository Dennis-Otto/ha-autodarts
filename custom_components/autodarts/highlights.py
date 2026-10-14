"""Highlight photos: the picture of a camera, saved for the highlight gallery.

autodarts.save_highlight saves what a camera sees as a file named by the
moment, the player and what the photo shows, by default in the folder
autodarts/highlights of the media folder, which the media browser shows under
Autodarts. It answers with the file and its address only once the file is
written: a camera that is disabled, unavailable or gives no picture, and a
folder Home Assistant does not allow writing to, fail the action. camera.snapshot
passes over a disabled or unavailable camera and a missing picture without an
error, so whoever relied on it announced photos that were never saved.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from homeassistant.components.camera import async_get_image
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .export import ExportFolderError, export_folder
from .profiles import NAME_LENGTH

# The folder of the highlight photos inside the media directory.
HIGHLIGHTS = Path("autodarts", "highlights")
# What a photo shows at the end of its name, such as 180 or checkout-121.
LABEL_LENGTH = 24
# Characters that file names and addresses do not allow, the separator _, the
# characters of a template, and ~ and .., for which Home Assistant serves no
# file of a media folder, leave the player and the label.
UNSAFE = re.compile(r'[\\/:*?"<>|_{}%#~]|\.{2,}')
# Photos of one second with one name get " (2)", " (3)" and so on, up to this.
COPIES = 100
# The pictures of most cameras are JPEG, which is also the suffix for any other kind.
SUFFIXES = {"image/png": ".png", "image/webp": ".webp"}


def highlight_folder(hass: HomeAssistant) -> tuple[str, Path] | None:
    """The media directory to serve from, and the folder of the photos in it."""
    media = hass.config.media_dirs
    if not media:
        return None
    source = "local" if "local" in media else next(iter(media))
    return source, Path(media[source]) / HIGHLIGHTS


def name_part(text: str, limit: int) -> str:
    """A player or a label as a part of a file name: without the characters
    above or control characters, with single spaces, at most limit long, and
    without a dot at the end, which would make .. with the suffix."""
    printable = "".join(char if char.isprintable() else " " for char in text)
    return " ".join(UNSAFE.sub(" ", printable).split())[:limit].rstrip(". ")


def photo_stem(taken: datetime, player: str, label: str) -> str:
    """2026-09-26_21-05-33_Alex_180, the name the gallery reads."""
    parts = (name_part(player, NAME_LENGTH), name_part(label, LABEL_LENGTH))
    return "_".join([taken.strftime("%Y-%m-%d_%H-%M-%S"), *filter(None, parts)])


def media_url(config: Config, path: Path) -> str:
    """The address of a file of a media folder, from which the media browser and
    the Home Assistant app load it, or "" outside them; runs in the executor."""
    for source, folder in config.media_dirs.items():
        root = Path(folder).resolve()
        if path.is_relative_to(root):
            return quote(f"/media/{source}/{path.relative_to(root).as_posix()}")
    return ""


def _write(
    config: Config, folder: str, stem: str, suffix: str, image: bytes
) -> tuple[Path, str]:
    """Write the photo under a name no file has yet, and find its address;
    runs in the executor."""
    # The rules of the exports: not hidden, and where Home Assistant allows writing.
    target = export_folder(config, folder)
    target.mkdir(parents=True, exist_ok=True)
    for copy in range(1, COPIES + 1):
        path = target / (f"{stem} ({copy}){suffix}" if copy > 1 else stem + suffix)
        try:
            with path.open("xb") as file:
                file.write(image)
        except FileExistsError:
            continue
        except OSError:
            # Part of a photo is no photo, and the gallery would show it broken.
            path.unlink(missing_ok=True)
            raise
        return path, media_url(config, path)
    raise FileExistsError(f"{COPIES} photos named {stem}{suffix} exist already")


def _shown(folder: str) -> str:
    """The folder for a message, with control characters as ?."""
    return "".join(char if char.isprintable() else "?" for char in folder)


async def async_save_highlight(
    hass: HomeAssistant,
    camera: str,
    folder: str | None = None,
    player: str = "",
    label: str = "",
) -> dict[str, Any]:
    """Save the camera's picture as a highlight photo, by default in the gallery,
    and return the file and its address; fails when nothing was saved."""
    state = hass.states.get(camera)
    if state is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="highlight_camera_missing",
            translation_placeholders={"camera": camera},
        )
    if state.state == STATE_UNAVAILABLE:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="highlight_camera_unavailable",
            translation_placeholders={"camera": camera},
        )
    try:
        image = await async_get_image(hass, camera)
    except HomeAssistantError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="highlight_no_picture",
            translation_placeholders={"camera": camera},
        ) from err
    if not folder:
        # Without a media folder, Home Assistant allows writing nowhere near it.
        gallery = highlight_folder(hass)
        folder = str(gallery[1]) if gallery else HIGHLIGHTS.as_posix()
    kind = image.content_type.partition(";")[0].strip().lower()
    try:
        path, url = await hass.async_add_executor_job(
            _write,
            hass.config,
            folder,
            photo_stem(dt_util.now(), player, label),
            SUFFIXES.get(kind, ".jpg"),
            image.content,
        )
    except ExportFolderError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="highlight_folder",
            translation_placeholders={"folder": _shown(folder)},
        ) from err
    except OSError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="highlight_failed",
            translation_placeholders={"error": str(err)},
        ) from err
    return {"photo": str(path), "photo_url": url}
