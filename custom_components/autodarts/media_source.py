"""Highlight photos of the board in the media browser of Home Assistant.

The highlight photo blueprint saves its pictures in the folder
autodarts/highlights of the media directory, for example
/media/autodarts/highlights/2026-09-26_21-05-33_Alex_180.jpg. The media
browser lists them by month, newest first, with titles like
"180 · Alex · 26.09.". Only plain file names of that folder resolve, so no
identifier can reach anything outside it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.util import raise_if_invalid_filename

from .const import DOMAIN

# The folder of the highlight photos inside the media directory.
HIGHLIGHTS = Path("autodarts", "highlights")
PHOTO_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
# 2026-09-26_21-05-33_Alex_180 or 2026-09-26_Alex_checkout-121: the day, then
# optionally the time, the player and the score.
PHOTO_NAME = re.compile(
    r"^(?P<day>\d{4}-\d{2}-\d{2})"
    r"(?:_(?P<time>\d{2}-\d{2}(?:-\d{2})?))?"
    r"(?:_(?P<player>.+?))??"
    r"(?:_(?P<checkout>checkout-)?(?P<score>\d{1,3}))?$"
)
MONTH = re.compile(r"^\d{4}-\d{2}$")
MONTHS = {
    "en": (
        "January February March April May June July August September October"
        " November December"
    ).split(),
    "de": (
        "Januar Februar März April Mai Juni Juli August September Oktober"
        " November Dezember"
    ).split(),
    "es": (
        "Enero Febrero Marzo Abril Mayo Junio Julio Agosto Septiembre Octubre"
        " Noviembre Diciembre"
    ).split(),
    "fr": (
        "Janvier Février Mars Avril Mai Juin Juillet Août Septembre Octobre"
        " Novembre Décembre"
    ).split(),
    "nl": (
        "Januari Februari Maart April Mei Juni Juli Augustus September Oktober"
        " November December"
    ).split(),
}
# "September 2026", in Spanish "Septiembre de 2026".
MONTH_TITLES = {"es": "{month} de {year}"}
SHORT_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
# Day and month as the language writes them: 26.09., 26/09 or 26-09.
SHORT_DATES = {
    "de": "{day:02d}.{month:02d}.",
    "es": "{day:02d}/{month:02d}",
    "fr": "{day:02d}/{month:02d}",
    "nl": "{day:02d}-{month:02d}",
}


@dataclass(frozen=True)
class Highlight:
    """One photo and what its name tells about it."""

    file: str
    taken: datetime
    player: str | None = None
    score: int | None = None
    checkout: bool = False
    # The name of a photo that does not follow the convention.
    label: str | None = None

    @property
    def month(self) -> str:
        return self.taken.strftime("%Y-%m")

    def title(self, language: str) -> str:
        """180 · Alex · 26.09. or Checkout 121 · Sep 26."""
        parts = [self.label] if self.label else []
        if self.score is not None:
            parts.append(f"Checkout {self.score}" if self.checkout else str(self.score))
        if self.player:
            parts.append(self.player)
        parts.append(_short_date(self.taken.date(), language))
        return " · ".join(parts)


def _language(hass: HomeAssistant) -> str:
    """The language of Home Assistant, such as "es" for "es-419"; others read English."""
    language = str(hass.config.language).split("-")[0].lower()
    return language if language in MONTHS else "en"


def _short_date(day: date, language: str) -> str:
    if language in SHORT_DATES:
        return SHORT_DATES[language].format(day=day.day, month=day.month)
    return f"{SHORT_MONTHS[day.month - 1]} {day.day}"


def _month_title(month: str, language: str) -> str:
    year, number = month.split("-")
    name = MONTHS[language][int(number) - 1]
    return MONTH_TITLES.get(language, "{month} {year}").format(month=name, year=year)


def _inside(folder: Path, path: Path) -> bool:
    """A file of the folder itself; a link out of it does not count."""
    return path.is_file() and path.resolve().parent == folder.resolve()


def highlight(path: Path) -> Highlight | None:
    """What a file of the folder shows, or None when it is no photo."""
    if path.name.startswith(".") or path.suffix.lower() not in PHOTO_TYPES:
        return None
    match = PHOTO_NAME.match(path.stem)
    if match:
        clock = (match["time"] or "00-00-00").split("-") + ["00"]
        try:
            taken = datetime.fromisoformat(
                f"{match['day']}T{clock[0]}:{clock[1]}:{clock[2]}"
            )
        except ValueError:
            match = None
    if match is None:
        # Photos saved by other means are sorted by the time they were written.
        written = dt_util.as_local(dt_util.utc_from_timestamp(path.stat().st_mtime))
        return Highlight(
            file=path.name, taken=written.replace(tzinfo=None), label=path.stem
        )
    return Highlight(
        file=path.name,
        taken=taken,
        player=match["player"].replace("_", " ").strip() or None
        if match["player"]
        else None,
        score=int(match["score"]) if match["score"] else None,
        checkout=bool(match["checkout"]),
    )


def highlight_folder(hass: HomeAssistant) -> tuple[str, Path] | None:
    """The media directory to serve from, and the folder of the photos in it."""
    media = hass.config.media_dirs
    if not media:
        return None
    source = "local" if "local" in media else next(iter(media))
    return source, Path(media[source]) / HIGHLIGHTS


async def async_get_media_source(hass: HomeAssistant) -> HighlightSource:
    return HighlightSource(hass)


class HighlightSource(MediaSource):
    """The highlight photos of the board, by month."""

    name: str = "Autodarts"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _scan(self) -> list[Highlight]:
        """Every photo of the folder, newest first."""
        found = highlight_folder(self.hass)
        if found is None or not found[1].is_dir():
            return []
        folder = found[1]
        photos = [
            photo
            for path in folder.iterdir()
            if _inside(folder, path) and (photo := highlight(path)) is not None
        ]
        return sorted(photos, key=lambda photo: (photo.taken, photo.file), reverse=True)

    def _url(self, source: str, file: str) -> str:
        """The address of Home Assistant's media view for a photo."""
        return quote(f"/media/{source}/{HIGHLIGHTS.as_posix()}/{file}")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        photos = await self.hass.async_add_executor_job(self._scan)
        found = highlight_folder(self.hass)
        source = found[0] if found else ""
        language = _language(self.hass)
        if not item.identifier:
            covers: dict[str, Highlight] = {}
            for photo in photos:
                # The newest photo of a month is its cover.
                covers.setdefault(photo.month, photo)
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=None,
                media_class=MediaClass.DIRECTORY,
                media_content_type="",
                title=self.name,
                can_play=False,
                can_expand=True,
                children_media_class=MediaClass.DIRECTORY,
                children=[
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=month,
                        media_class=MediaClass.DIRECTORY,
                        media_content_type="",
                        title=_month_title(month, language),
                        thumbnail=self._url(source, cover.file),
                        can_play=False,
                        can_expand=True,
                        children_media_class=MediaClass.IMAGE,
                    )
                    for month, cover in covers.items()
                ],
            )
        if not MONTH.match(item.identifier):
            raise BrowseError(f"Unknown highlight month: {item.identifier}")
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=item.identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=_month_title(item.identifier, language),
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.IMAGE,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=photo.file,
                    media_class=MediaClass.IMAGE,
                    media_content_type=PHOTO_TYPES[Path(photo.file).suffix.lower()],
                    title=photo.title(language),
                    thumbnail=self._url(source, photo.file),
                    can_play=True,
                    can_expand=False,
                )
                for photo in photos
                if photo.month == item.identifier
            ],
        )

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """A photo by its plain file name; nothing outside the folder resolves."""
        name = item.identifier
        suffix = Path(name).suffix.lower()
        found = highlight_folder(self.hass)
        try:
            raise_if_invalid_filename(name)
        except ValueError as err:
            raise Unresolvable(f"Invalid highlight: {name}") from err
        if found is None or name.startswith(".") or suffix not in PHOTO_TYPES:
            raise Unresolvable(f"Invalid highlight: {name}")
        source, folder = found
        path = folder / name
        if not await self.hass.async_add_executor_job(_inside, folder, path):
            raise Unresolvable(f"Unknown highlight: {name}")
        return PlayMedia(self._url(source, name), PHOTO_TYPES[suffix], path=path)
