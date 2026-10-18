"""Draw what the score display blueprint shows on a pixel display, for the guide.

    python scripts/render_score_display.py

writes docs/images/score-display.svg: a display of 32 by 8 pixels, as an AWTRIX 3
or a PixelIt has, for each screen of a game, in the default colors of the blueprint
and in a font of 3 by 5 pixels like theirs. tests/test_blueprints.py checks that the
picture is the one this script draws, in the colors the blueprint has.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICTURE = ROOT / "docs" / "images" / "score-display.svg"
COLUMNS, ROWS = 32, 8
# The size of a pixel and of its cell, the frame of a display and the gap between
# two, which keeps every display on the grid of the dark pixels.
PIXEL, CELL, BORDER, GAP = 10, 12, 12, 24
# The text stands on the rows 1 to 5, as on the displays.
TOP = 1
OFF = "#1d1f24"
CASE = "#0b0c0e"
# Each screen of a game: its text, and the setting of the blueprint whose default
# color it has.
SCREENS = (
    ("501", "score_color", (255, 255, 255)),
    ("40 D20", "checkout_color", (0, 200, 80)),
    ("180!", "visit_color", (255, 190, 0)),
    ("BUST", "bust_color", (255, 0, 0)),
    ("LEA WINS", "match_color", (255, 190, 0)),
)
FONT = {
    "0": ("XXX", "X.X", "X.X", "X.X", "XXX"),
    "1": (".X.", "XX.", ".X.", ".X.", "XXX"),
    "2": ("XXX", "..X", "XXX", "X..", "XXX"),
    "3": ("XXX", "..X", ".XX", "..X", "XXX"),
    "4": ("X.X", "X.X", "XXX", "..X", "..X"),
    "5": ("XXX", "X..", "XXX", "..X", "XXX"),
    "6": ("XXX", "X..", "XXX", "X.X", "XXX"),
    "7": ("XXX", "..X", "..X", ".X.", ".X."),
    "8": ("XXX", "X.X", "XXX", "X.X", "XXX"),
    "9": ("XXX", "X.X", "XXX", "..X", "XXX"),
    "!": ("X", "X", "X", ".", "X"),
    " ": (".", ".", ".", ".", "."),
    "A": (".X.", "X.X", "XXX", "X.X", "X.X"),
    "B": ("XX.", "X.X", "XX.", "X.X", "XX."),
    "D": ("XX.", "X.X", "X.X", "X.X", "XX."),
    "E": ("XXX", "X..", "XX.", "X..", "XXX"),
    "I": ("X", "X", "X", "X", "X"),
    "L": ("X..", "X..", "X..", "X..", "XXX"),
    "N": ("X.X", "XXX", "XXX", "X.X", "X.X"),
    "S": (".XX", "X..", ".X.", "..X", "XX."),
    "T": ("XXX", ".X.", ".X.", ".X.", ".X."),
    "U": ("X.X", "X.X", "X.X", "X.X", "XXX"),
    "W": ("X.X", "X.X", "XXX", "XXX", "X.X"),
}


def lit(text: str) -> set[tuple[int, int]]:
    """The pixels a text lights, as (column, row), centered as the displays do."""
    glyphs = [FONT[character] for character in text]
    width = sum(len(glyph[0]) for glyph in glyphs) + len(glyphs) - 1
    if width > COLUMNS:
        message = f"{text!r} is {width} pixels wide and would scroll"
        raise ValueError(message)
    column = (COLUMNS - width) // 2
    pixels = set()
    for glyph in glyphs:
        for row, line in enumerate(glyph):
            pixels.update(
                (column + offset, TOP + row)
                for offset, dot in enumerate(line)
                if dot == "X"
            )
        column += len(glyph[0]) + 1
    return pixels


def display(top: int, text: str, color: tuple[int, int, int]) -> list[str]:
    """One display at the given height: its case with the dark pixels, and the
    pixels its text lights."""
    fill = "#{:02x}{:02x}{:02x}".format(*color)
    width = COLUMNS * CELL + 2 * BORDER
    height = ROWS * CELL + 2 * BORDER
    parts = [
        f'<rect x="0" y="{top}" width="{width}" height="{height}" rx="10" fill="{CASE}"/>',
        f'<rect x="{BORDER}" y="{top + BORDER}" width="{COLUMNS * CELL}" '
        f'height="{ROWS * CELL}" fill="url(#off)"/>',
    ]
    inset = (CELL - PIXEL) // 2
    for column, row in sorted(lit(text)):
        x = BORDER + column * CELL + inset
        y = top + BORDER + row * CELL + inset
        parts.append(
            f'<rect x="{x}" y="{y}" width="{PIXEL}" height="{PIXEL}" rx="2" fill="{fill}"/>'
        )
    return parts


def render() -> str:
    """The picture as SVG, the same on every run."""
    width = COLUMNS * CELL + 2 * BORDER
    height = ROWS * CELL + 2 * BORDER
    total = len(SCREENS) * height + (len(SCREENS) - 1) * GAP
    title = "A pixel display at the board: " + ", ".join(text for text, _, _ in SCREENS)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total}" '
        f'viewBox="0 0 {width} {total}" role="img">',
        f"<title>{title}</title>",
        # A pixel that is off, repeated over every display.
        f'<defs><pattern id="off" width="{CELL}" height="{CELL}" '
        f'patternUnits="userSpaceOnUse" x="{BORDER}" y="{BORDER}">'
        f'<rect x="{(CELL - PIXEL) // 2}" y="{(CELL - PIXEL) // 2}" width="{PIXEL}" '
        f'height="{PIXEL}" rx="2" fill="{OFF}"/></pattern></defs>',
    ]
    for index, (text, _, color) in enumerate(SCREENS):
        parts.extend(display(index * (height + GAP), text, color))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    PICTURE.write_text(render(), encoding="utf-8", newline="\n")
    print(f"drew {PICTURE.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
