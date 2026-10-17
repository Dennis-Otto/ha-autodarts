---
description: "Why the callers play voice packs in the file names of darts-caller, so existing packs work as they are and a missing file never silences a call."
---

# Give the callers voice packs in the file names of darts-caller

- Status: accepted
- Date: 2026-10-17

## Context

The caller of the scoreboard spoke only with `speechSynthesis` of the browser, which sounds different on every device, robotic on many, and on some browsers sends the text to an online provider. The dart caller and the practice caller speak with a text-to-speech engine of Home Assistant on the speakers of the room. Players of Autodarts know callers with a real voice: darts-caller, the most downloaded tool of the Autodarts scene, plays recorded voice packs, and many players already have packs on their disk. A voice of our own has to work with those packs, cost nothing, keep the calls in the home if the player wants that, and never make a call fall silent because a recording is missing.

## Options

1. **A format of our own,** such as one file per call with a manifest. Free to design, but no existing pack would work, and every pack would have to be made for this integration.
2. **The file names of darts-caller's voice packs:** a folder with `0.mp3` to `180.mp3`, `busted`, `gameshot`, `matchshot`, `you_require`, `yr_2` to `yr_170`, the darts `s1` to `t20`, `bull`, `bullseye`, `outside`, player names, and several files of one key as `gameshot+2.mp3`. Every existing pack works as it is, and the names say what a file says.
3. **Text-to-speech in Home Assistant for the scoreboard, too:** the screen would play the engine's audio for every call. One voice everywhere, but every call waits for the engine, and the scoreboard depends on an engine being set up.

## Decision

Option 2, with packs in `autodarts/voices` of the media folder, the place Home Assistant already serves with its login and shows in the media browser. The scoreboard asks for the files of a pack once with the websocket command `autodarts/voice_pack`, loads them with its login and plays the sounds of a call one after the other through the audio context its tap unlocked; a call the pack lacks, a name without a file and a file that does not load are said by the browser's voice as before. The blueprints find the sound of a call with the action `autodarts.voice_sound` and play it with `media_player.play_media`, or let the engine speak.

For a pack without recordings, `autodarts.generate_voice_pack` records the 417 sounds of a complete pack in the same file names with any text-to-speech engine of Home Assistant, such as Piper for a voice that never leaves the home. It records next to the pack and replaces only a pack it made itself, which it marks with a hidden file, so a pack of darts-caller is never written over.

## Consequences

- Packs of darts-caller work without a change, and a generated pack works in darts-caller, too.
- The calls keep their fallback: a pack can be incomplete, and a missing file never silences a call.
- Calls that darts-caller has no file for, such as the marks of Cricket, stay with the browser's voice or the engine. New calls of the callers should prefer names darts-caller already defines.
- A media player replaces the sound that plays with the next one, so the blueprints play one sound per call; calls of several sounds, such as a name and what the player requires, are the scoreboard's.
