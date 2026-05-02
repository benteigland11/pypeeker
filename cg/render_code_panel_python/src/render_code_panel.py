"""Render syntax-highlighted code blocks as PNG images.

Public functions:
    render_panel        — render a single code block as PNG bytes
    render_matched_pair — render N panels normalized to a shared code-block width
"""
import io
import subprocess
from typing import Optional, Tuple, List, Dict, Any

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import get_lexer_by_name


# Default colors (Dracula-adjacent neutral dark surface)
_DEFAULT_BG: Tuple[int, int, int] = (24, 25, 33)
_DEFAULT_PANEL_BG: Tuple[int, int, int] = (40, 42, 54)
_DEFAULT_TITLE_COLOR: Tuple[int, int, int] = (248, 248, 242)
_DEFAULT_SUBTITLE_COLOR: Tuple[int, int, int] = (180, 182, 195)


def _resolve_font(font_path: Optional[str], font_size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, falling back to the system default sans-serif."""
    if font_path is None:
        # Use fontconfig to find a system sans-serif font.
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", "sans-serif:bold" if bold else "sans-serif"],
                capture_output=True, text=True, timeout=5,
            )
            font_path = result.stdout.strip() or None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            font_path = None

    if font_path is None:
        return ImageFont.load_default()

    font = ImageFont.truetype(font_path, font_size)
    if bold and hasattr(font, "set_variation_by_axes"):
        try:
            font.set_variation_by_axes([700])
        except Exception:
            pass
    return font


def _discover_monospace_family() -> str:
    """Return a monospace font family name installed on this system.

    Falls back to 'monospace' (a fontconfig alias) if discovery fails.
    Pygments resolves family names via fontconfig at render time.
    """
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{family[0]}", "monospace"],
            capture_output=True, text=True, timeout=5,
        )
        family = result.stdout.strip()
        if family:
            return family
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "monospace"


def _render_code_block(
    code: str,
    language: str,
    theme: str,
    code_font_name: Optional[str],
    code_font_size: int,
) -> Image.Image:
    """Render code to a PIL Image via pygments' ImageFormatter."""
    lexer = get_lexer_by_name(language)
    resolved_font = code_font_name or _discover_monospace_family()
    fmt = ImageFormatter(
        style=theme,
        font_name=resolved_font,
        font_size=code_font_size,
        line_numbers=False,
        line_pad=4,
        image_pad=24,
    )
    png_bytes = highlight(code, lexer, fmt)
    return Image.open(io.BytesIO(png_bytes))


def _measure_text(text: str, font: ImageFont.ImageFont) -> int:
    """Return rendered width in pixels for the given text and font."""
    scratch = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(scratch)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _pad_to_width(img: Image.Image, target_width: int, fill: Tuple[int, int, int]) -> Image.Image:
    """Left-align the image inside a wider canvas; no-op if already wide enough."""
    if img.width >= target_width:
        return img
    out = Image.new("RGB", (target_width, img.height), fill)
    out.paste(img, (0, 0))
    return out


def _compose_panel(
    code_img: Image.Image,
    *,
    title: Optional[str],
    subtitle: Optional[str],
    title_font: ImageFont.ImageFont,
    subtitle_font: ImageFont.ImageFont,
    background: Tuple[int, int, int],
    pad: int,
    caption_height: int,
) -> Image.Image:
    """Assemble a code panel: caption strip on top, code block below."""
    has_caption = bool(title or subtitle)
    caption_block_h = caption_height if has_caption else 0

    # Width must accommodate the caption text; pad code block if narrower.
    title_w = _measure_text(title, title_font) if title else 0
    sub_w = _measure_text(subtitle, subtitle_font) if subtitle else 0
    caption_min_inner = max(title_w, sub_w) + 24 if has_caption else 0
    inner_w = max(code_img.width, caption_min_inner)

    canvas_w = inner_w + pad * 2
    canvas_h = caption_block_h + code_img.height + pad * 2
    canvas = Image.new("RGB", (canvas_w, canvas_h), background)
    draw = ImageDraw.Draw(canvas)

    if title:
        draw.text((pad + 12, pad + 14), title, fill=_DEFAULT_TITLE_COLOR, font=title_font)
    if subtitle:
        sub_y = pad + (50 if title else 14)
        draw.text((pad + 12, sub_y), subtitle, fill=_DEFAULT_SUBTITLE_COLOR, font=subtitle_font)

    canvas.paste(code_img, (pad, pad + caption_block_h))
    return canvas


def render_panel(
    code: str,
    language: str = "python",
    *,
    code_font_name: Optional[str] = None,
    code_font_size: int = 16,
    theme: str = "dracula",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    title_font_path: Optional[str] = None,
    subtitle_font_path: Optional[str] = None,
    title_font_size: int = 28,
    subtitle_font_size: int = 18,
    background: Tuple[int, int, int] = _DEFAULT_BG,
    panel_fill: Tuple[int, int, int] = _DEFAULT_PANEL_BG,
    pad: int = 32,
    caption_height: int = 78,
    min_code_width: Optional[int] = None,
) -> bytes:
    """Render a code block as a captioned PNG.

    :param code: Source text to highlight.
    :param language: Pygments lexer alias (e.g. "python", "json", "javascript").
    :param code_font_name: Monospace font name resolved by pygments.
    :param code_font_size: Code font size in points.
    :param theme: Pygments style name (e.g. "dracula", "monokai", "default").
    :param title: Optional bold caption above the code block.
    :param subtitle: Optional secondary caption line.
    :param title_font_path: TTF path for title; system sans-serif bold if None.
    :param subtitle_font_path: TTF path for subtitle; system sans-serif if None.
    :param background: RGB outer canvas color.
    :param panel_fill: RGB fill used when padding the code block to a wider width.
    :param pad: Outer padding in pixels.
    :param caption_height: Reserved vertical space for caption strip.
    :param min_code_width: If set, pads narrower code blocks to this width before composition.
    :returns: PNG-encoded image bytes.
    """
    code_img = _render_code_block(code, language, theme, code_font_name, code_font_size)

    if min_code_width is not None and code_img.width < min_code_width:
        code_img = _pad_to_width(code_img, min_code_width, panel_fill)

    title_font = _resolve_font(title_font_path, title_font_size, bold=True)
    subtitle_font = _resolve_font(subtitle_font_path, subtitle_font_size, bold=False)

    panel = _compose_panel(
        code_img,
        title=title,
        subtitle=subtitle,
        title_font=title_font,
        subtitle_font=subtitle_font,
        background=background,
        pad=pad,
        caption_height=caption_height,
    )

    out = io.BytesIO()
    panel.save(out, format="PNG")
    return out.getvalue()


def render_matched_pair(
    panels: List[Dict[str, Any]],
    *,
    background: Tuple[int, int, int] = _DEFAULT_BG,
    panel_fill: Tuple[int, int, int] = _DEFAULT_PANEL_BG,
) -> List[bytes]:
    """Render multiple panels normalized to identical code-block width.

    The widest rendered code block sets the floor; narrower ones are padded
    with `panel_fill` so all returned panels visually align as a matched set.

    :param panels: List of dicts; each dict accepts the same kwargs as
                   `render_panel` (except `min_code_width`, which is computed).
    :param background: Shared outer canvas background.
    :param panel_fill: Shared code-block padding fill.
    :returns: List of PNG-encoded image bytes, one per input panel.
    """
    if not panels:
        return []

    # First pass: render each code block so we can find the target width.
    code_imgs = []
    for spec in panels:
        img = _render_code_block(
            spec["code"],
            spec.get("language", "python"),
            spec.get("theme", "dracula"),
            spec.get("code_font_name"),
            spec.get("code_font_size", 16),
        )
        code_imgs.append(img)

    target_w = max(img.width for img in code_imgs)

    # Second pass: pad and compose each panel.
    outputs = []
    for spec, code_img in zip(panels, code_imgs):
        padded = _pad_to_width(code_img, target_w, panel_fill)
        title_font = _resolve_font(
            spec.get("title_font_path"), spec.get("title_font_size", 28), bold=True,
        )
        subtitle_font = _resolve_font(
            spec.get("subtitle_font_path"), spec.get("subtitle_font_size", 18), bold=False,
        )
        panel = _compose_panel(
            padded,
            title=spec.get("title"),
            subtitle=spec.get("subtitle"),
            title_font=title_font,
            subtitle_font=subtitle_font,
            background=background,
            pad=spec.get("pad", 32),
            caption_height=spec.get("caption_height", 78),
        )
        out = io.BytesIO()
        panel.save(out, format="PNG")
        outputs.append(out.getvalue())

    return outputs
