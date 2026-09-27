"""Synthetic pictures for the demo and the E2E run: highlight photos and avatars.

Every picture is drawn here, so documentation screenshots never show a real person.
"""

from __future__ import annotations

import io
import math

from PIL import Image, ImageDraw, ImageFont

# The numbers clockwise from the top, as on every dartboard.
ORDER = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]
# Radii of the beds in millimetres.
RINGS = [
    (170, "double"),
    (160, "single"),
    (107, "treble"),
    (97, "single"),
]
DARK, LIGHT = (27, 27, 27), (241, 228, 195)
RED, GREEN = (212, 47, 47), (29, 145, 80)


def _bed(name: str) -> tuple[float, float]:
    """Angle in degrees clockwise from the top and radius in millimetres of a bed."""
    if name in ("BULL", "25"):
        return 0.0, 3 if name == "BULL" else 12
    number = int(name[1:])
    radius = {"S": 130, "D": 165, "T": 102}[name[0]]
    return ORDER.index(number) * 18.0, radius


def board_photo(darts: list[str], width: int = 640, height: int = 480) -> bytes:
    """A dartboard on a dark wall with darts in the named beds, as a JPEG."""
    image = Image.new("RGB", (width, height), (32, 34, 38))
    draw = ImageDraw.Draw(image)
    cx, cy = width / 2, height / 2
    scale = (min(width, height) / 2 - 12) / 225

    def circle(radius: float, fill) -> None:
        r = radius * scale
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)

    circle(225, (16, 16, 16))
    for radius, kind in RINGS:
        for index in range(20):
            start = -90 + index * 18 - 9
            even = index % 2 == 0
            if kind == "single":
                color = DARK if even else LIGHT
            else:
                color = RED if even else GREEN
            r = radius * scale
            draw.pieslice(
                (cx - r, cy - r, cx + r, cy + r), start, start + 18, fill=color
            )
    circle(17, GREEN)
    circle(7, RED)
    font = ImageFont.load_default(size=max(12, round(16 * scale * 1.2)))
    for index, number in enumerate(ORDER):
        angle = math.radians(index * 18)
        x = cx + 197 * scale * math.sin(angle)
        y = cy - 197 * scale * math.cos(angle)
        draw.text((x, y), str(number), fill=(245, 245, 245), font=font, anchor="mm")
    for offset, name in enumerate(darts):
        angle, radius = _bed(name)
        # Darts of one visit sit a little apart in their bed.
        angle = math.radians(angle + (offset - 1) * 3)
        x = cx + radius * scale * math.sin(angle)
        y = cy - radius * scale * math.cos(angle)
        draw.line((x, y, x + 34, y - 46), fill=(60, 60, 64), width=5)
        draw.polygon(
            [(x + 30, y - 40), (x + 52, y - 50), (x + 40, y - 62)], fill=(0, 229, 255)
        )
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 214, 10))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=82)
    return buffer.getvalue()


def avatar(initial: str, color: tuple[int, int, int], size: int = 256) -> bytes:
    """A round-looking avatar with an initial, as a PNG."""
    image = Image.new("RGB", (size, size), color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=size // 2)
    draw.text(
        (size / 2, size / 2), initial, fill=(255, 255, 255), font=font, anchor="mm"
    )
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()
