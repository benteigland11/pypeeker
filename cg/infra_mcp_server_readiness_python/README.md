# MCP Server Readiness

Future-proofs any FastMCP-based server that ships as a single PyPI package alongside a CLI.

## What it gives you

1. **`run_cli_in_process(pkg_name, command, args)`** — a CLI escape-hatch runner
   that uses `sys.executable -m <pkg_name>.cli` instead of relying on `$PATH`.
   The MCP server can never end up calling a different version of the CLI than
   the one it's installed alongside.
2. **`make_server(name, pkg_name, instructions)`** — a `FastMCP` constructor
   that reads the installed package version via `importlib.metadata` and sets
   it on the underlying `Server.version` so MCP's initialize handshake
   advertises it via `serverInfo` (zero token cost). It also queries PyPI
   once per session (cached 24h on disk, 2s timeout, fail-quiet) and prepends
   a single-line update notice to `instructions` **only when the installed
   version is stale**. Up-to-date sessions see no version chatter at all.
3. **`check_for_update(pkg_name, current_version)`** — the PyPI check
   exposed standalone if you want to surface staleness elsewhere.
4. **`get_package_version(pkg_name)`** — the underlying lookup helper.

Opt out of the PyPI check entirely by setting `<PKG>_NO_VERSION_CHECK=1`
(uppercased, dashes-to-underscores) or by passing `check_pypi=False` to
`make_server`.

## Drop-in template for a new MCP server

Copy this into your project as `<your_pkg>/mcp.py`. Replace `your_pkg` with the
actual package name (must match the `name=` in your `setup.py` / `pyproject.toml`),
and replace the tool stubs with your real handlers.

```python
import os
import sys
from typing import Any, Dict, Optional

# Make local source importable before installation (handy during development).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(BASE_DIR) and BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from cg.infra_mcp_server_readiness_python.src.mcp_server_readiness import (
    make_server,
    run_cli_in_process,
)

_INSTRUCTIONS = """\
Short, agent-actionable info only. Document config keys the agent needs to know
(e.g. "pyproject.toml [tool.your_pkg] ignore = [...] adds to default skip list").
Avoid marketing copy — the agent does not need to be sold the product.
"""

mcp = make_server(name="your-pkg", pkg_name="your_pkg", instructions=_INSTRUCTIONS)


@mcp.tool()
def example(arg: str) -> Dict[str, Any]:
    """One-line description. Required params first, optional params with defaults."""
    return {"status": "success", "data": {"echo": arg}}


@mcp.tool()
def cli(command: str, args: Optional[list[str]] = None) -> Dict[str, Any]:
    """Escape hatch: run an arbitrary `your-pkg <command> <args>` for power flags
    not exposed by the typed tools above."""
    return run_cli_in_process("your_pkg", command, args)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

In `setup.py` / `pyproject.toml`, register two console scripts:

```python
entry_points={
    "console_scripts": [
        "your-pkg=your_pkg.cli:main",
        "your-pkg-mcp=your_pkg.mcp:main",
    ],
},
install_requires=["mcp>=0.1.0"],
```

That's it. Agents see `your_pkg <version>` in their initial tool listing,
`serverInfo.version` is populated for any client that surfaces it, and the CLI
escape hatch always runs the matching version.

## Stable-API + distribution policy

Treat this as a checklist when releasing:

- **MCP tool names and required params are stable API.** Add optional params
  freely; never rename or remove without a major version bump. This is what
  lets a marketplace manifest pin `your-pkg>=1.5` and stay valid forever.
- **Marketplaces get launchers, not bundles.** When listing on Claude
  plugin store, DXT, Gemini extensions, Cursor, etc., the entry point should
  be `uvx your-pkg` or `pip install your-pkg>=X` — never a frozen wheel
  snapshot. PyPI stays the single source of truth; marketplace listings only
  need re-cutting if the launch contract itself changes.
- **One PyPI package = one version = atomic upgrades.** Keep MCP server and
  CLI in the same wheel so `pip install -U your-pkg` updates both in lockstep.
- **Server `instructions` are one-time, per session.** Never dump
  per-call diagnostics into tool response `meta` that could live in
  `instructions` instead — every byte in `meta` is paid on every call.

## When NOT to use this

- Servers without a CLI escape hatch don't need `run_cli_in_process`.
- Servers that aren't packaged as PyPI wheels (e.g., bundled DXT-only
  distributions) can't use `importlib.metadata` reliably and should pass
  the version string explicitly.
