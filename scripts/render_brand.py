"""Export bundled Home Assistant brand PNGs from the official SVG sources.

Development-only dependencies: resvg-py==0.5.0 and pillow. See docs/branding/README.md.

The images follow the brand image specification of Home Assistant: square icons of
256 and 512 pixels, and logos whose shortest side is 128 or 256 pixels, all trimmed
to the artwork and transparent. The favicon of the website, a square of 48 pixels,
comes from the same symbol.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image
from resvg_py import svg_to_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "docs" / "branding"
DESTINATION = ROOT / "custom_components" / "autodarts" / "brand"
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


def logo(artwork: Image.Image, shortest: int) -> Image.Image:
    """The trimmed wordmark with its shortest side at the given size."""
    scale = shortest / min(artwork.size)
    return artwork.resize(
        (round(artwork.width * scale), round(artwork.height * scale)), Image.LANCZOS
    )


def main() -> None:
    """Render transparent icons and theme-specific wordmarks at both densities, and
    the favicon of the website."""
    DESTINATION.mkdir(parents=True, exist_ok=True)
    symbol = render((SOURCES / "icon.svg").read_text(encoding="utf-8"))
    dark_source = (SOURCES / "logo.svg").read_text(encoding="utf-8")
    light_source = dark_source.replace('fill="white"', 'fill="#0f172a"')
    wordmarks = {"logo": render(light_source), "dark_logo": render(dark_source)}
    for scale, suffix in ((1, ""), (2, "@2x")):
        icon(symbol, 256 * scale).save(DESTINATION / f"icon{suffix}.png", optimize=True)
        for name, artwork in wordmarks.items():
            logo(artwork, 128 * scale).save(
                DESTINATION / f"{name}{suffix}.png", optimize=True
            )
    icon(symbol, FAVICON_SIZE).save(FAVICON, optimize=True)


if __name__ == "__main__":
    main()
