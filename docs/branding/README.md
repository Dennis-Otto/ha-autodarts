---
description: "The Autodarts icon and logo of the integration: their sources, the PNG exports for Home Assistant, the colors of the website and how to render them anew."
---

# Brand assets

The bundled artwork identifies Autodarts in Home Assistant. It comes from the official Autodarts website, retrieved on 2026-09-18:

- `icon.svg`: <https://autodarts.com/favicon.svg>
- `logo.svg`: <https://autodarts.com/brand/autodarts-logo-colored.svg>

The SVG sources are preserved unchanged. PNG exports live in `custom_components/autodarts/brand/` and follow the [Home Assistant brand image specification](https://github.com/home-assistant/brands#image-specification): transparent, trimmed to the artwork and compressed.

- `icon.png` (256 × 256) and `icon@2x.png` (512 × 512): the symbol fills the square along its longer side. Both themes share them through Home Assistant's dark-icon fallback.
- `logo.png` (540 × 128) and `logo@2x.png` (1079 × 256), with dark lettering for light themes; the shortest side is 128 and 256 pixels.
- `dark_logo.png` and `dark_logo@2x.png`, the original white lettering for dark themes, at the same sizes.

The documentation website shows the symbol too: `icon.svg` as the logo in its header, and `favicon.png` (48 × 48), which the same script renders, as the icon of its browser tabs and search results. Its colors come from the symbol and the social preview of the repository, in `docs/stylesheets/brand.css`:

| Use | Light | Dark |
| --- | --- | --- |
| Header, tabs and preview cards of shared links | Navy `#0a1624` with white text | Navy `#0a1624` with white text |
| Links | Teal `#0f766e` (5.5:1 on white) | Teal `#4fd1c5` (8.5:1 on the dark page) |
| A link or button under the pointer | Dark teal `#115e59` | Light teal `#81e6d9` |

Every color of a text keeps a contrast of at least 4.5:1 to its background; `tests/test_website_brand.py` computes each pair and fails for one that falls short. The footer of every page says that the website is an unofficial community project, not affiliated with Autodarts.

The colored symbol and all paths are unchanged; only the light-theme wordmark's white fill is replaced with dark slate. PNG rendering needs no fonts, network access or runtime integration dependency. The script renders each SVG at 4096 pixels, trims the transparent border and scales the result down, so edges stay sharp.

To regenerate from the repository root using a separate development environment:

```sh
python3 -m venv /tmp/autodarts-brand-renderer-venv
/tmp/autodarts-brand-renderer-venv/bin/pip install resvg-py==0.5.0 pillow==12.0.0
/tmp/autodarts-brand-renderer-venv/bin/python scripts/render_brand.py
```

Then compress the images, for example with `pngquant --quality 85-98 --ext .png --force custom_components/autodarts/brand/*.png docs/branding/favicon.png`.

Home Assistant [supports local custom-integration brand assets from 2026.3](https://developers.home-assistant.io/docs/core/integration/brand_images/). The folder is included in HACS and manual installations. No manifest `icon` property or cloud authorization is needed.

Autodarts and Winmau names and artwork belong to their respective owners and are excluded from this project's MIT license. Their use identifies the supported product and does not imply affiliation or endorsement.
