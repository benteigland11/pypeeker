import os
import sys
import subprocess
from typing import Any, Dict, Literal, Optional

# Add repo root to path so we can import local packages before installation.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(BASE_DIR) and BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from mcp.server.fastmcp import FastMCP
from pypeeker.commands.circular import cmd_circular
from pypeeker.commands.missing import cmd_missing
from pypeeker.commands.skeleton import cmd_skeleton
from pypeeker.commands.locate import cmd_locate
from pypeeker.commands.interfaces import cmd_interfaces
from pypeeker.commands.impact import cmd_impact

mcp = FastMCP("pypeeker-cli")


class _Args:
    """Mock args object to pass to CLI handlers."""
    def __init__(self, **kwargs: Any):
        self.__dict__.update(kwargs)
        self.ignore = kwargs.get("ignore", [])
        self.page = kwargs.get("page", 1)
        self.size = kwargs.get("size", 20)


@mcp.tool()
def audit(
    directory: str,
    kind: Literal["cycles", "missing-imports", "interfaces"],
    summary_only: bool = False,
    ignore_tests: bool = True,
    page: int = 1,
    size: int = 20,
    format: str = "text",
) -> Dict[str, Any]:
    """Project-wide audits. kind='cycles' finds import cycles (with hub ranking); 'missing-imports' finds broken/hallucinated import paths; 'interfaces' flags missing docstrings & type hints. summary_only is for cycles only; ignore_tests is for interfaces only."""
    if kind == "cycles":
        return cmd_circular(_Args(directory=directory, page=page, size=size, format=format, summary_only=summary_only))
    if kind == "missing-imports":
        return cmd_missing(_Args(directory=directory, page=page, size=size, format=format))
    if kind == "interfaces":
        return cmd_interfaces(_Args(directory=directory, ignore_tests=ignore_tests, page=page, size=size))
    return {"status": "error", "error": {"message": f"Unknown audit kind: {kind}", "code": "BAD_KIND"}}


@mcp.tool()
def peek(
    path: str,
    mode: Literal["skeleton", "locate", "usages", "ancestry", "impact"],
    symbol: Optional[str] = None,
    depth: int = 1,
    root: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    format: str = "text",
    show_all_unresolved: bool = False,
) -> Dict[str, Any]:
    """File or symbol inspection. mode='skeleton' returns a file/package API surface (symbol unused). 'locate'/'usages'/'ancestry' find a symbol's definition / usages / class parents (symbol required). 'impact' analyzes a function's side effects (symbol required); set depth>1 + root for transitive blast-radius across files."""
    if mode == "skeleton":
        # skeleton uses 'stub' as its text format; translate uniform 'text' input.
        skel_format = "stub" if format == "text" else format
        return cmd_skeleton(_Args(path=path, page=page, size=size, format=skel_format))
    if mode in ("locate", "usages", "ancestry"):
        if not symbol:
            return {"status": "error", "error": {"message": f"mode='{mode}' requires symbol", "code": "MISSING_SYMBOL"}}
        return cmd_locate(_Args(
            symbol=symbol, path=path,
            usages=(mode == "usages"),
            inherited=(mode == "ancestry"),
            page=page, size=size, format=format,
        ))
    if mode == "impact":
        if not symbol:
            return {"status": "error", "error": {"message": "mode='impact' requires symbol", "code": "MISSING_SYMBOL"}}
        return cmd_impact(_Args(
            symbol=symbol, path=path, depth=depth, root=root,
            format=format, show_all_unresolved=show_all_unresolved,
        ))
    return {"status": "error", "error": {"message": f"Unknown peek mode: {mode}", "code": "BAD_MODE"}}


@mcp.tool()
def cli(command: str, args: Optional[list[str]] = None) -> Dict[str, Any]:
    """Escape hatch: run an arbitrary `pypeeker <command> <args>` and return its raw stdout. For power flags not exposed by audit/peek (e.g. --include-deps, --ignore custom_dir, --format json on tools that default to text)."""
    full_cmd = ["pypeeker", command] + (args or [])
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": {"message": "pypeeker command timed out (120s)", "code": "TIMEOUT"}}
    except FileNotFoundError:
        return {"status": "error", "error": {"message": "pypeeker binary not on PATH", "code": "NOT_INSTALLED"}}
    return {
        "status": "success" if result.returncode == 0 else "error",
        "data": {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode},
    }


def main() -> None:
    """Launch the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
