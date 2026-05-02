"""Demonstrate render_code_panel: a single panel and a matched pair.

Writes example outputs to a temp directory and prints their sizes.
No network calls; runs and exits cleanly.
"""
import io
import os
import tempfile

from PIL import Image

from src.render_code_panel import render_panel, render_matched_pair


SAMPLE_PYTHON = '''def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def greet(name):
    return f"Hello, {name}!"
'''

SAMPLE_JSON = '''{
  "items": [
    {"id": 1, "label": "alpha"},
    {"id": 2, "label": "beta"}
  ],
  "total": 2
}
'''


def _save(png_bytes: bytes, path: str) -> tuple[int, int]:
    img = Image.open(io.BytesIO(png_bytes))
    img.save(path)
    return img.size


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # Single panel
        single_png = render_panel(
            SAMPLE_PYTHON,
            language="python",
            title="example.py",
            subtitle="two helper functions",
        )
        single_path = os.path.join(tmp, "single.png")
        size = _save(single_png, single_path)
        print(f"single.png: {size[0]}x{size[1]}")

        # Matched pair: code + data, normalized to the same code-block width
        pair = render_matched_pair([
            {
                "code": SAMPLE_PYTHON,
                "language": "python",
                "title": "code",
                "subtitle": "python source",
            },
            {
                "code": SAMPLE_JSON,
                "language": "json",
                "title": "data",
                "subtitle": "json payload",
            },
        ])
        for i, png in enumerate(pair, start=1):
            path = os.path.join(tmp, f"pair_{i}.png")
            size = _save(png, path)
            print(f"pair_{i}.png: {size[0]}x{size[1]}")


main()
