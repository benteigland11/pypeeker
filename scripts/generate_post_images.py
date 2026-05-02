"""Regenerate the README/social-share images for pypeeker using the
render-code-panel-python widget.

Outputs:
    post_1_code.png   — Session.request source (Read view)
    post_2_impact.png — pypeeker impact Session.request output
"""
import json
import os
import subprocess
import sys

# Make the repo root importable so we can pull from cg/ widgets directly.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from cg.render_code_panel_python.src.render_code_panel import render_matched_pair


# Hand-condensed view of psf/requests Session.request — keeps the narrative
# (signature → docstring elision → real body) without rendering 92 lines.
SESSION_REQUEST_VIEW = '''def request(
    self, method, url, params=None, data=None, headers=None,
    cookies=None, files=None, auth=None, timeout=None,
    allow_redirects=True, proxies=None, hooks=None,
    stream=None, verify=None, cert=None, json=None,
):
    """Constructs a Request, prepares it and sends it..."""

    # Create the Request.
    req = Request(
        method=method.upper(), url=url, headers=headers,
        files=files, data=data or {}, json=json,
        params=params or {}, auth=auth, cookies=cookies, hooks=hooks,
    )
    prep = self.prepare_request(req)

    proxies = proxies or {}
    settings = self.merge_environment_settings(
        prep.url, proxies, stream, verify, cert
    )

    # Send the request.
    send_kwargs = {"timeout": timeout, "allow_redirects": allow_redirects}
    send_kwargs.update(settings)
    resp = self.send(prep, **send_kwargs)

    return resp'''


def _impact_payload(symbol: str, target_path: str) -> str:
    """Run `pypeeker impact` and return a compact pretty-printed payload."""
    raw = subprocess.run(
        ["pypeeker", "impact", symbol, target_path],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(raw)["data"]
    compact = {
        "external": {
            "calls":   data["external"]["calls"],
            "writes":  data["external"]["writes"],
            "globals": data["external"]["globals"],
        },
        "internal": {
            "writes": data["internal"]["writes"],
        },
    }
    return json.dumps(compact, indent=2)


def main() -> None:
    target = "/tmp/requests/src/requests/sessions.py"
    if not os.path.exists(target):
        print(f"Error: {target} not found.", file=sys.stderr)
        print("Clone psf/requests to /tmp/requests first:", file=sys.stderr)
        print("  git clone --depth 1 https://github.com/psf/requests.git /tmp/requests", file=sys.stderr)
        sys.exit(1)

    impact_text = _impact_payload("Session.request", target)

    pngs = render_matched_pair([
        {
            "code": SESSION_REQUEST_VIEW,
            "language": "python",
            "title": "sessions.py from psf/requests",
        },
        {
            "code": impact_text,
            "language": "json",
            "title": "pypeeker impact",
        },
    ])

    for path, png in zip(["post_1_code.png", "post_2_impact.png"], pngs):
        out_path = os.path.join(ROOT, path)
        with open(out_path, "wb") as f:
            f.write(png)
        size_kb = len(png) // 1024
        print(f"✓ {path} ({size_kb} KB)")


if __name__ == "__main__":
    main()
