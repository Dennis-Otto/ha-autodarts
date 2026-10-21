---
description: "The icon of HomeDarts for Autodarts: its source, the PNG exports for Home Assistant, the colors of the website and how to render them anew."
---

# Brand assets

HomeDarts has an icon of its own: a house with a dartboard and a dart in its bull, darts at home. It is part of the project and under its MIT license. Autodarts asked on 2026-10-21 that the project no longer shows its logo, so neither the integration nor the website carries it.

- `icon.svg`: the source, a square of 512 × 512. The navy of the house, `#1d3a57`, is light enough to stand out on a dark background too, so one icon serves both themes.

PNG exports live in `custom_components/homedarts/brand/` and follow the [Home Assistant brand image specification](https://github.com/home-assistant/brands#image-specification): transparent, trimmed to the artwork and compressed.

- `icon.png` (256 × 256) and `icon@2x.png` (512 × 512): the artwork fills the square along its longer side. Both themes share them through Home Assistant's dark-icon fallback, and without a logo of its own Home Assistant shows the icon in place of one.

The documentation website shows the icon too: `icon.svg` as the logo in its header, and `favicon.png` (48 × 48), which the same script renders, as the icon of its browser tabs and search results. Its colors come from the icon and the social preview of the repository, in `docs/stylesheets/brand.css`:

| Use | Light | Dark |
| --- | --- | --- |
| Header, tabs and preview cards of shared links | Navy `#0a1624` with white text | Navy `#0a1624` with white text |
| Links | Teal `#0f766e` (5.5:1 on white) | Teal `#4fd1c5` (8.5:1 on the dark page) |
| A link or button under the pointer | Dark teal `#115e59` | Light teal `#81e6d9` |

Every color of a text keeps a contrast of at least 4.5:1 to its background; `tests/test_website_brand.py` computes each pair and fails for one that falls short, and checks that the brand folder holds the icon and nothing else. The footer of every page says that the website is an unofficial community project, not affiliated with Autodarts.

PNG rendering needs no fonts, network access or runtime integration dependency. The script renders the SVG at 4096 pixels, trims the transparent border and scales the result down, so edges stay sharp.

To regenerate from the repository root using a separate development environment:

```sh
python3 -m venv /tmp/brand-renderer-venv
/tmp/brand-renderer-venv/bin/pip install resvg-py==0.5.0 pillow==12.0.0
/tmp/brand-renderer-venv/bin/python scripts/render_brand.py
```

Then compress the images, for example with `pngquant --quality 85-98 --ext .png --force custom_components/homedarts/brand/*.png docs/branding/favicon.png`.

Home Assistant [supports local custom-integration brand assets from 2026.3](https://developers.home-assistant.io/docs/core/integration/brand_images/). The folder is included in HACS and manual installations. No manifest `icon` property or cloud authorization is needed.
