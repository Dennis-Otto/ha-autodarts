---
description: "The Autodarts icon and logo that the integration brings: where they come from, the PNG exports for Home Assistant and how to render them anew."
---

# Brand assets

The bundled artwork identifies Autodarts in Home Assistant. It comes from the official Autodarts website, retrieved on 2026-09-18:

- `icon.svg`: <https://autodarts.com/favicon.svg>
- `logo.svg`: <https://autodarts.com/brand/autodarts-logo-colored.svg>

The SVG sources are preserved unchanged. PNG exports live in `custom_components/autodarts/brand/` and follow the [Home Assistant brand image specification](https://github.com/home-assistant/brands#image-specification): transparent, trimmed to the artwork and compressed.

- `icon.png` (256 × 256) and `icon@2x.png` (512 × 512): the symbol fills the square along its longer side. Both themes share them through Home Assistant's dark-icon fallback.
- `logo.png` (540 × 128) and `logo@2x.png` (1079 × 256), with dark lettering for light themes; the shortest side is 128 and 256 pixels.
- `dark_logo.png` and `dark_logo@2x.png`, the original white lettering for dark themes, at the same sizes.

The colored symbol and all paths are unchanged; only the light-theme wordmark's white fill is replaced with dark slate. PNG rendering needs no fonts, network access or runtime integration dependency. The script renders each SVG at 4096 pixels, trims the transparent border and scales the result down, so edges stay sharp.

To regenerate from the repository root using a separate development environment:

```sh
python3 -m venv /tmp/autodarts-brand-renderer-venv
/tmp/autodarts-brand-renderer-venv/bin/pip install resvg-py==0.5.0 pillow==12.0.0
/tmp/autodarts-brand-renderer-venv/bin/python scripts/render_brand.py
```

Then compress the images, for example with `pngquant --quality 85-98 --ext .png --force custom_components/autodarts/brand/*.png`.

Home Assistant [supports local custom-integration brand assets from 2026.3](https://developers.home-assistant.io/docs/core/integration/brand_images/). The folder is included in HACS and manual installations. No manifest `icon` property or cloud authorization is needed.

Autodarts and Winmau names and artwork belong to their respective owners and are excluded from this project's MIT license. Their use identifies the supported product and does not imply affiliation or endorsement.
