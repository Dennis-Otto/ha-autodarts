"""Voice packs for the caller: recorded or rendered calls instead of a robotic voice.

A voice pack is a folder of autodarts/voices in the media folder, for example
/media/autodarts/voices/russ-bray/, whose sounds are named after what they say,
as darts-caller names the files of its voice packs: 180.mp3, busted.wav,
gameshot.mp3, matchshot.mp3, yr_40.mp3, t20.mp3 or alex.mp3 for a player. A key
with several files, such as gameshot.mp3 and gameshot+2.mp3, plays one of them
at random. So a voice pack of darts-caller works as it is.

The scoreboard card asks for every sound of a pack with the websocket command
autodarts/voice_pack, the caller blueprints for the sound of one call with
autodarts.voice_sound. autodarts.generate_voice_pack records a complete pack
with a text-to-speech engine of Home Assistant, such as Piper for a voice that
never leaves the house.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import shutil
from pathlib import Path, PurePath
from typing import Any
from urllib.parse import quote

from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .export import ExportFolderError, export_folder
from .highlights import media_folder

# The folder of the voice packs inside the media directory.
VOICES = Path("autodarts", "voices")
# The sounds a browser and a media player play; darts-caller reads mp3 and wav.
AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
PACK_LENGTH = 64
# A folder name of letters, digits, spaces, dots, dashes and underscores, that
# starts and ends with a letter or a digit. Home Assistant serves no file of a
# media folder whose path holds .., so a pack name has none either.
PACK_NAME = re.compile(r"(?!.*\.\.)\w(?:[\w .-]{0,62}\w)?")
# The files of a pack that are looked at, so a wrong folder cannot keep Home
# Assistant busy; a pack of darts-caller with player names has a few thousand.
MAX_SOUNDS = 10_000
# A generated pack has this file, so the generator replaces only its own packs.
MARK = ".autodarts-voice-pack"
GENERATING: HassKey[asyncio.Lock] = HassKey(f"{DOMAIN}_voice_pack")
# The languages of the integration; the words of a generated pack are in one of them.
LANGUAGES = ("en", "de", "es", "fr", "nl")
# What a voice assistant answers when no sound of a pack fits.
NO_SOUND = {"key": "", "media_content_id": "", "media_content_type": ""}


class RecordedPackError(Exception):
    """A pack of that name exists and was not generated."""


def valid_pack(pack: str) -> bool:
    """A plain folder name, nothing that leads elsewhere."""
    return PACK_NAME.fullmatch(pack) is not None


def voice_folder(hass: HomeAssistant) -> tuple[str, Path] | None:
    """The media directory to serve from, and the folder of the voice packs in it."""
    return media_folder(hass, VOICES)


def sound_key(name: str) -> str | None:
    """The key of a sound as darts-caller reads it from the file name: 180 of
    180.mp3, gameshot of Gameshot+2.wav; None for a file that is no sound, is
    hidden, or that Home Assistant does not serve."""
    path = PurePath(name)
    if (
        name.startswith(".")
        or path.suffix.lower() not in AUDIO_TYPES
        or "~" in name
        or ".." in name
    ):
        return None
    return path.stem.split("+", 1)[0].strip().lower() or None


def _sounds(folder: Path) -> dict[str, list[str]] | None:
    """Every sound of a pack by its key, as paths in the pack in the order of
    their names, also in folders of the pack; None when there is no such pack.
    Runs in the executor."""
    if not folder.is_dir():
        return None
    root = folder.resolve()
    sounds: dict[str, list[str]] = {}
    seen = 0
    for top, folders, files in os.walk(root):
        # Hidden folders stay out, and links to folders are not followed.
        folders[:] = sorted(name for name in folders if sound_folder(name))
        for name in sorted(files):
            path = Path(top, name)
            key = sound_key(name)
            # A link out of the pack does not count.
            if key is None or not path.resolve().is_relative_to(root):
                continue
            sounds.setdefault(key, []).append(path.relative_to(root).as_posix())
            seen += 1
            if seen >= MAX_SOUNDS:
                return sounds
    return sounds


def sound_folder(name: str) -> bool:
    """A folder of a pack whose files Home Assistant serves."""
    return not name.startswith(".") and "~" not in name


async def _pack(hass: HomeAssistant, pack: str) -> tuple[str, dict[str, list[str]]]:
    """The media directory and every sound of a pack; no sounds without the pack."""
    found = voice_folder(hass)
    if found is None or not valid_pack(pack):
        return "", {}
    source, voices = found
    sounds = await hass.async_add_executor_job(_sounds, voices / pack)
    return source, sounds or {}


def _place(source: str, pack: str, file: str) -> str:
    """Where a sound of a pack is in a media directory, as the media browser names it."""
    return f"{source}/{VOICES.as_posix()}/{pack}/{file}"


async def async_voice_pack(hass: HomeAssistant, pack: str) -> dict[str, list[str]]:
    """Every sound of a pack by its key, with the addresses of Home Assistant's
    media view, which load with the login of the scoreboard; none without the
    pack."""
    source, sounds = await _pack(hass, pack)
    return {
        key: [quote(f"/media/{_place(source, pack, file)}") for file in files]
        for key, files in sounds.items()
    }


async def async_voice_sound(
    hass: HomeAssistant, pack: str, keys: list[str]
) -> dict[str, Any]:
    """The sound of the first key the pack has, as media for a media player, one
    of its files at random; empty values when the pack has none of the keys."""
    if not valid_pack(pack):
        raise _pack_name(pack)
    source, sounds = await _pack(hass, pack)
    for key in keys:
        files = sounds.get(key.strip().lower())
        if files:
            # Variety on stage, not security.
            file = random.choice(files)
            return {
                "key": key,
                "media_content_id": f"media-source://media_source/{_place(source, pack, file)}",
                "media_content_type": AUDIO_TYPES[PurePath(file).suffix.lower()],
            }
    return dict(NO_SOUND)


def _pack_name(pack: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="voice_pack_name",
        translation_placeholders={"pack": _shown(pack)},
    )


def _shown(text: str) -> str:
    """A text for a message, with control characters as ?."""
    return "".join(char if char.isprintable() else "?" for char in text)


def pack_words(say: dict[str, str]) -> dict[str, str]:
    """The words of every sound a generated pack has, by its key, in the words
    of the caller: the scores, a bust, the game shot and the match, what a
    player requires, and every dart, as darts-caller names them."""
    words = {"0": say["voice_pack_no_score"]}
    words.update({str(score): str(score) for score in range(1, 181)})
    words["busted"] = say["voice_pack_bust"]
    words["gameshot"] = say["voice_pack_leg"]
    words["matchshot"] = say["voice_pack_match"]
    words["you_require"] = say["voice_pack_require"]
    words.update(
        {
            f"yr_{left}": say["voice_pack_require_score"].format(remaining=left)
            for left in range(2, 171)
        }
    )
    for number in range(1, 21):
        words[f"s{number}"] = str(number)
        words[f"d{number}"] = say["voice_bed_double"].format(number=number)
        words[f"t{number}"] = say["voice_bed_triple"].format(number=number)
    words["bull"] = say["voice_bed_outer"]
    words["bullseye"] = say["voice_bed_bull"]
    words["outside"] = say["voice_bed_miss"]
    return words


async def _say(hass: HomeAssistant, language: str) -> dict[str, str]:
    """The caller's words in the language of the voice, such as German for
    de-CH, or English for a language the integration does not speak."""
    words = re.split(r"[-_]", language, maxsplit=1)[0].lower()
    texts = await async_get_translations(
        hass, words if words in LANGUAGES else "en", "exceptions", {DOMAIN}
    )
    prefix = f"component.{DOMAIN}.exceptions."
    return {
        key.removeprefix(prefix).removesuffix(".message"): text
        for key, text in texts.items()
        if key.startswith(prefix)
    }


def _prepare(config: Config, target: Path) -> Path:
    """An empty folder next to the pack to record into, so a pack that fails
    halfway leaves the one before as it was; runs in the executor."""
    # The rules of the exports: not hidden, and where Home Assistant allows writing.
    voices = export_folder(config, str(target.parent))
    voices.mkdir(parents=True, exist_ok=True)
    pack = voices / target.name
    if (
        pack.exists()
        and not (pack / MARK).is_file()
        and (not pack.is_dir() or any(pack.iterdir()))
    ):
        raise RecordedPackError(pack)
    staging = voices / f".{target.name}.new"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    return staging


def _finish(staging: Path, pack: str, mark: str) -> Path:
    """Put the recorded pack in place of the one before; runs in the executor."""
    (staging / MARK).write_text(mark, encoding="utf-8")
    target = staging.parent / pack
    old = staging.parent / f".{pack}.old"
    shutil.rmtree(old, ignore_errors=True)
    if target.exists():
        target.rename(old)
    staging.rename(target)
    shutil.rmtree(old, ignore_errors=True)
    return target


async def async_generate_voice_pack(
    hass: HomeAssistant,
    engine: str,
    language: str,
    pack: str,
    voice: str | None = None,
) -> dict[str, Any]:
    """Record every sound of a voice pack with a text-to-speech engine, in the
    folder of the voice packs, and return the pack, its folder and the number
    of its sounds. One pack at a time; a pack of that name that was not
    generated, such as one of darts-caller, stays as it is."""
    if not valid_pack(pack):
        raise _pack_name(pack)
    if hass.states.get(engine) is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="voice_pack_engine_missing",
            translation_placeholders={"engine": engine},
        )
    lock = hass.data.setdefault(GENERATING, asyncio.Lock())
    if lock.locked():
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="voice_pack_busy"
        )
    async with lock:
        return await _generate(hass, engine, language, pack, voice)


async def _generate(
    hass: HomeAssistant, engine: str, language: str, pack: str, voice: str | None
) -> dict[str, Any]:
    # Text-to-speech brings its own requirements, which Home Assistant installs
    # with it, so it is loaded once there is an engine to speak.
    from homeassistant.components import tts

    found = voice_folder(hass)
    if found is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="voice_pack_no_media"
        )
    words = pack_words(await _say(hass, language))
    options = {"voice": voice} if voice else None
    try:
        media = {
            key: tts.generate_media_source_id(
                hass, text, engine, language, options, cache=False
            )
            for key, text in words.items()
        }
    except HomeAssistantError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="voice_pack_engine",
            translation_placeholders={
                "engine": engine,
                "language": _shown(language),
                "error": str(err),
            },
        ) from err
    target = found[1] / pack
    try:
        staging = await hass.async_add_executor_job(_prepare, hass.config, target)
    except ExportFolderError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="voice_pack_folder",
            translation_placeholders={"folder": str(found[1])},
        ) from err
    except RecordedPackError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="voice_pack_recorded",
            translation_placeholders={"pack": pack},
        ) from err
    try:
        for key, source in media.items():
            extension, audio = await tts.async_get_media_source_audio(hass, source)
            suffix = f".{extension.lower()}"
            if suffix not in AUDIO_TYPES:
                raise HomeAssistantError(f"{engine} speaks {extension}, not mp3")
            await hass.async_add_executor_job(
                (staging / f"{key}{suffix}").write_bytes, audio
            )
        mark = json.dumps({"engine": engine, "language": language, "voice": voice})
        folder = await hass.async_add_executor_job(_finish, staging, pack, mark)
    except (HomeAssistantError, OSError, ValueError) as err:
        await hass.async_add_executor_job(shutil.rmtree, staging, True)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="voice_pack_failed",
            translation_placeholders={"pack": pack, "error": str(err)},
        ) from err
    return {"pack": pack, "folder": str(folder), "sounds": len(media)}
