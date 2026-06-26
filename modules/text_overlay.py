"""Generate readable text overlay PNGs (no drawtext/libass required)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    )
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_caption_overlay(
    *,
    title: str,
    body: str,
    width: int = 1920,
    height: int = 1080,
    out_path: Path,
) -> str:
    """Full-frame RGBA PNG: title top, body in lower third."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    title_font = _font(52)
    body_font = _font(36)

    # Lower-third panel
    panel_h = 340
    draw.rectangle((0, height - panel_h, width, height), fill=(8, 6, 12, 210))

    title = (title or "Untitled").strip()[:120]
    body = textwrap.fill((body or "").strip()[:420], width=52)

    draw.text((64, height - panel_h + 28), title, font=title_font, fill=(255, 220, 160, 255))
    draw.multiline_text((64, height - panel_h + 100), body, font=body_font, fill=(245, 245, 245, 255), spacing=8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return str(out_path)