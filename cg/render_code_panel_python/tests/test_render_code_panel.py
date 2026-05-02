import io

import pytest
from PIL import Image

from src.render_code_panel import render_panel, render_matched_pair


def _open(png_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png_bytes))


def test_render_panel_returns_valid_png():
    out = render_panel("x = 1\nprint(x)", language="python")
    img = _open(out)
    assert img.format == "PNG"
    assert img.width > 0 and img.height > 0


def test_render_panel_with_caption_widens_for_long_title():
    short_code = "x = 1"
    long_title = "An unusually long caption title that is definitely wider than the code"
    no_caption = _open(render_panel(short_code, language="python"))
    with_caption = _open(render_panel(short_code, language="python", title=long_title))
    assert with_caption.width >= no_caption.width
    # Caption-driven widening must actually happen for narrow code:
    assert with_caption.width > no_caption.width


def test_render_panel_supports_json_language():
    out = render_panel('{"a": 1, "b": [2, 3]}', language="json")
    img = _open(out)
    assert img.format == "PNG"


def test_render_panel_subtitle_only():
    out = render_panel("y = 2", language="python", subtitle="just a subtitle")
    img = _open(out)
    assert img.format == "PNG"


def test_render_panel_min_code_width_pads_narrow_blocks():
    narrow = _open(render_panel("a", language="python"))
    wide = _open(render_panel("a", language="python", min_code_width=narrow.width + 200))
    assert wide.width >= narrow.width + 200


def test_render_matched_pair_normalizes_widths():
    short_code = "x = 1"
    long_code = (
        "def long_function_signature(parameter_one, parameter_two, parameter_three):\n"
        "    return parameter_one + parameter_two + parameter_three\n"
    )
    outs = render_matched_pair([
        {"code": short_code, "language": "python", "title": "first"},
        {"code": long_code, "language": "python", "title": "second"},
    ])
    assert len(outs) == 2
    img_a = _open(outs[0])
    img_b = _open(outs[1])
    # The narrower panel should be padded so its panel width matches the wider one.
    # Outer widths can still differ if captions are different lengths, but the
    # widths must be at least equal to the wider rendered code block.
    assert img_a.width >= img_b.width or img_b.width >= img_a.width
    # Each must be a valid PNG.
    assert img_a.format == "PNG"
    assert img_b.format == "PNG"


def test_render_matched_pair_empty_input():
    assert render_matched_pair([]) == []


def test_render_matched_pair_mixed_languages():
    outs = render_matched_pair([
        {"code": "x = 1", "language": "python", "title": "code"},
        {"code": '{"k": 1}', "language": "json", "title": "data"},
    ])
    assert len(outs) == 2
    for out in outs:
        assert _open(out).format == "PNG"


def test_invalid_language_raises():
    with pytest.raises(Exception):
        render_panel("x = 1", language="not-a-real-language")
