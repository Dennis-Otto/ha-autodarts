"""What a voice assistant says after an action at the board: a visit, a dart, the
next player or a visit taken back, in the language of Home Assistant, in the words
of the scoreboard's caller."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .practice import PracticeGame

# The words of a bed by its multiplier, as the actions name the bed.
BED_WORDS = {"S": "voice_bed_single", "D": "voice_bed_double", "T": "voice_bed_triple"}
OTHER_BEDS = {
    "25": "voice_bed_outer",
    "BULL": "voice_bed_bull",
    "MISS": "voice_bed_miss",
}


async def spoken(hass: HomeAssistant, key: str, **placeholders: str) -> str:
    """A message of the integration in the language of Home Assistant, for a voice
    assistant to say; English where the language lacks it."""
    texts = await async_get_translations(
        hass, hass.config.language, "exceptions", {DOMAIN}
    )
    text = texts.get(f"component.{DOMAIN}.exceptions.{key}.message", key)
    return text.format(**placeholders) if placeholders else text


def _sentence(text: str) -> str:
    """A sentence begins with a capital, also where a name such as "the bot" does."""
    return text[:1].upper() + text[1:]


@dataclass(frozen=True)
class Turn:
    """The player at the board before an action: their seat, what they had left in
    X01 and the legs they had won in the match."""

    seat: int
    left: int | None
    legs: int

    @classmethod
    def of(cls, practice: PracticeGame) -> Turn:
        seat = practice.current
        legs = practice.players[seat].match_legs if seat < len(practice.players) else 0
        return cls(seat, left(practice, seat), legs)


def left(practice: PracticeGame, seat: int) -> int | None:
    """What a player has left in an X01 game, with the darts of the visit on the
    board; None in every other game."""
    if not isinstance(practice.kind, int):
        return None
    scores: list[dict[str, object]] = practice.snapshot()["scores"]
    remaining = scores[seat]["remaining"]
    return remaining if isinstance(remaining, int) else None


async def name(hass: HomeAssistant, practice: PracticeGame, seat: int) -> str:
    """A player's name as the voice says it: the bot, and a player without a name
    by the number of their seat."""
    if seat == practice.bot_seat:
        return await spoken(hass, "voice_bot")
    if seat < len(practice.names) and practice.names[seat]:
        return practice.names[seat]
    return await spoken(hass, "voice_player", number=str(seat + 1))


async def bed(hass: HomeAssistant, key: str) -> str:
    """A bed as the voice says it, such as "Triple 20", "Bull" or "Miss"."""
    if key in OTHER_BEDS:
        return await spoken(hass, OTHER_BEDS[key])
    return await spoken(hass, BED_WORDS[key[0]], number=key[1:])


async def _ended(hass: HomeAssistant, practice: PracticeGame, turn: Turn) -> str | None:
    """The leg or the match the action won for the player, if it did."""
    who = await name(hass, practice, turn.seat)
    if practice.winner is not None:
        return await spoken(hass, "voice_match", name=who)
    if practice.players[turn.seat].match_legs > turn.legs:
        return await spoken(hass, "voice_leg", name=who)
    return None


async def up_next(hass: HomeAssistant, practice: PracticeGame) -> str:
    """Who throws now, and in X01 what they require, as the caller says it."""
    seat = practice.current
    who = await name(hass, practice, seat)
    remaining = left(practice, seat)
    if remaining is None:
        return _sentence(await spoken(hass, "voice_next", name=who))
    return _sentence(
        await spoken(hass, "voice_next_left", name=who, left=str(remaining))
    )


async def passed(hass: HomeAssistant, practice: PracticeGame, turn: Turn) -> str:
    """After the next player was called: the leg or match the visit won, if it did,
    and who throws now."""
    ended = await _ended(hass, practice, turn)
    if ended is None:
        return await up_next(hass, practice)
    if practice.winner is not None:
        return _sentence(ended)
    return f"{_sentence(ended)} {await up_next(hass, practice)}"


async def visit(
    hass: HomeAssistant, practice: PracticeGame, turn: Turn, score: int
) -> str:
    """After a visit entered as its score: what it scored and left, a bust, or the
    leg or match it won, and who throws next."""
    ended = await _ended(hass, practice, turn)
    if ended is not None and practice.winner is not None:
        return ended
    if ended is None:
        who = await name(hass, practice, turn.seat)
        remaining = str(left(practice, turn.seat))
        key = "voice_bust" if score and remaining == str(turn.left) else "voice_visit"
        ended = await spoken(hass, key, score=str(score), name=who, left=remaining)
    said = [_sentence(ended)]
    if practice.current != turn.seat:
        said.append(await up_next(hass, practice))
    return " ".join(said)


async def dart(hass: HomeAssistant, practice: PracticeGame, key: str) -> str:
    """After a dart entered by hand: the bed, and in X01 what is left, a bust or the
    game shot. The leg or match it wins counts once the visit ends, which the next
    player announces."""
    said = await bed(hass, key)
    if not isinstance(practice.kind, int):
        return await spoken(hass, "voice_dart", bed=said)
    snapshot = practice.snapshot()
    if snapshot.get("bust"):
        return await spoken(hass, "voice_dart_bust", bed=said)
    if snapshot.get("won"):
        shot = await spoken(hass, "voice_game_shot")
        return f"{said}. {_sentence(shot)}"
    remaining = str(left(practice, practice.current))
    return await spoken(hass, "voice_dart_left", bed=said, left=remaining)


async def undone(hass: HomeAssistant, practice: PracticeGame, score: int) -> str:
    """After a visit taken back: whose and how many points, to throw anew."""
    who = await name(hass, practice, practice.current)
    return _sentence(await spoken(hass, "voice_undone", score=str(score), name=who))
