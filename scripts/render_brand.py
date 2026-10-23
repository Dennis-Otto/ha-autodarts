"""Export the bundled Home Assistant brand PNGs from the SVG source of the icon.

Development-only dependencies: resvg-py==0.5.0 and pillow. See docs/branding/README.md.

The images follow the brand image specification of Home Assistant: square icons of
256 and 512 pixels, trimmed to the artwork and transparent. Without a logo of its
own, Home Assistant shows the icon in place of one. The favicon of the website, a
square of 48 pixels, comes from the same icon.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image
from resvg_py import svg_to_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "branding" / "icon.svg"
DESTINATION = ROOT / "custom_components" / "homedarts" / "brand"
# The favicon of the website (theme.favicon in mkdocs.yml): 48 pixels, the size that
# Google shows beside a search result, which browsers scale down for a tab.
FAVICON = ROOT / "docs" / "branding" / "favicon.png"
FAVICON_SIZE = 48
# Render large and scale down, so trimming never cuts into anti-aliased edges.
SUPERSAMPLE = 4096


def render(source: str) -> Image.Image:
    """The SVG as a large transparent image, cropped to its visible pixels."""
    image = Image.open(
        BytesIO(
            svg_to_bytes(svg_string=source, width=SUPERSAMPLE, skip_system_fonts=True)
        )
    ).convert("RGBA")
    box = image.getchannel("A").getbbox()
    return image.crop(box) if box else image


def icon(artwork: Image.Image, size: int) -> Image.Image:
    """A square icon with the artwork filling it along its longer side."""
    scale = size / max(artwork.size)
    fitted = artwork.resize(
        (round(artwork.width * scale), round(artwork.height * scale)), Image.LANCZOS
    )
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(
        fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2)
    )
    return canvas


def main() -> None:
    """Render the transparent icon at both densities and the favicon of the website."""
    DESTINATION.mkdir(parents=True, exist_ok=True)
    symbol = render(SOURCE.read_text(encoding="utf-8"))
    for scale, suffix in ((1, ""), (2, "@2x")):
        icon(symbol, 256 * scale).save(DESTINATION / f"icon{suffix}.png", optimize=True)
    icon(symbol, FAVICON_SIZE).save(FAVICON, optimize=True)


if __name__ == "__main__":
    main()
