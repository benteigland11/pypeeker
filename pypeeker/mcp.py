import os
import sys
from typing import Any, Dict

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

# Initialize FastMCP server
mcp = FastMCP("pypeeker-cli")

class Args:
    """Mock args object to pass to CLI handlers."""
    def __init__(self, **kwargs: Any):
        """
        Initialize the Args object with keyword arguments.
        """
        self.__dict__.update(kwargs)
        if 'ignore' not in kwargs: self.ignore = []
        if 'page' not in kwargs: self.page = 1
        if 'size' not in kwargs: self.size = 20

_INCLUDE_DEPS_DOC = (
    ":param include_deps: If True, scan everything including venvs (venv, .venv), "
    "build artifacts (dist, build), caches (__pycache__, .mypy_cache), and node_modules. "
    "Defaults to False — these directories are skipped by default since they almost "
    "never contain code the user wants to analyze."
)


@mcp.tool()
def circular(directory: str, ignore: list[str] = None, page: int = 1, size: int = 20, format: str = "text", summary_only: bool = False, include_deps: bool = False) -> Dict[str, Any]:
    """
    Find circular import chains (dependency loops) in a Python project.

    Identifies files that import each other, which can cause runtime crashes.
    Distinguishes between actual execution cycles and safe TYPE_CHECKING cycles.

    Output always includes a 'cycle_hubs' summary in meta — files appearing in
    2+ cycles, ranked by appearance count. Use this to find the gravitational
    center of an import-tangle problem.

    :param directory: Root directory to scan recursively.
    :param ignore: Additional directories to skip (added to defaults).
    :param page: Results page number for large projects (default 1).
    :param size: Number of cycles per page (default 20).
    :param format: 'text' (default) renders a condensed cycle list with file:line anchors. 'json' returns structured cycle data.
    :param summary_only: If true, skip per-cycle details and return only the cycle count and hub summary. Useful for first-pass triage.
    """ + "\n    " + _INCLUDE_DEPS_DOC
    args = Args(directory=directory, ignore=ignore, page=page, size=size, format=format, summary_only=summary_only, include_deps=include_deps)
    return cmd_circular(args)

@mcp.tool()
def missing(directory: str, ignore: list[str] = None, page: int = 1, size: int = 20, format: str = "text", include_deps: bool = False) -> Dict[str, Any]:
    """
    Detect missing or hallucinated internal imports in a Python project.

    Checks every import statement to see if the target file actually exists in the project.
    Intelligently ignores standard library and properly installed external packages.

    :param directory: Root directory to scan recursively.
    :param ignore: Additional directories to skip (added to defaults).
    :param page: Results page number (default 1).
    :param size: Number of missing imports per page (default 20).
    :param format: 'text' (default) renders a condensed file:line list. 'json' returns structured data.
    """ + "\n    " + _INCLUDE_DEPS_DOC
    args = Args(directory=directory, ignore=ignore, page=page, size=size, format=format, include_deps=include_deps)
    return cmd_missing(args)

@mcp.tool()
def skeleton(path: str, ignore: list[str] = None, page: int = 1, size: int = 20, format: str = "stub", include_deps: bool = False) -> Dict[str, Any]:
    """
    Extract the structural API surface (AST skeleton) of Python files.

    Provides imports, class definitions, function signatures, variables, and docstrings.
    Completely strips out function/method bodies to save token context for the agent.

    :param path: File path or directory to scan.
    :param ignore: Additional directories to skip if path is a directory (added to defaults).
    :param page: Results page number for directory scans.
    :param size: Number of file skeletons per page (default 20).
    :param format: 'stub' (default) renders Python stub text with line ranges (# L42-78) for targeted reads. 'json' returns structured AST data.
    """ + "\n    " + _INCLUDE_DEPS_DOC
    args = Args(path=path, ignore=ignore, page=page, size=size, format=format, include_deps=include_deps)
    return cmd_skeleton(args)

@mcp.tool()
def locate(symbol: str, path: str, usages: bool = False, inherited: bool = False, ignore: list[str] = None, page: int = 1, size: int = 20, format: str = "text", include_deps: bool = False) -> Dict[str, Any]:
    """
    Surgically pinpoint a symbol's definition or its usages across a project.

    Returns exact start and end line numbers and the one-line signature/header.
    Use this to find where a class/function is defined or everywhere it is called.

    :param symbol: Exact name of the class, function, or variable to find.
    :param path: File or directory to search within.
    :param usages: If true, find everywhere the symbol is invoked/used instead of defined.
    :param inherited: If true and symbol is a class, also locate its parent (base) classes.
    :param ignore: Additional directories to skip (added to defaults).
    :param page: Results page number (default 1).
    :param size: Number of matches per page (default 20).
    :param format: 'text' (default) renders 'path:start-end  signature' per match. 'json' returns structured data.
    """ + "\n    " + _INCLUDE_DEPS_DOC
    args = Args(symbol=symbol, path=path, usages=usages, inherited=inherited, ignore=ignore, page=page, size=size, format=format, include_deps=include_deps)
    return cmd_locate(args)

@mcp.tool()
def interfaces(directory: str, ignore: list[str] = None, ignore_tests: bool = True, page: int = 1, size: int = 20, include_deps: bool = False) -> Dict[str, Any]:
    """
    Identify documentation and typing gaps in a project's code interfaces.

    Acts as a contract validator, flagging missing docstrings, argument types, and return types.
    High-signal for understanding where a codebase is underspecified or brittle.

    :param directory: Root directory to scan recursively.
    :param ignore: Additional directories to skip (added to defaults).
    :param ignore_tests: Exclude files inside test directories and test_*.py files (default true).
    :param page: Results page number (default 1).
    :param size: Number of interface gaps per page (default 20).
    """ + "\n    " + _INCLUDE_DEPS_DOC
    args = Args(directory=directory, ignore=ignore, ignore_tests=ignore_tests, page=page, size=size, include_deps=include_deps)
    return cmd_interfaces(args)

@mcp.tool()
def impact(symbol: str, path: str) -> Dict[str, Any]:
    """
    Analyze the side effects and dependencies (blast radius) of a function.
    
    Distinguishes between internal (local variables) and external (global state, 
    class attributes, cross-module calls) impact.
    
    :param symbol: Name of the function or method to analyze.
    :param path: Path to the .py file containing the function.
    """
    args = Args(symbol=symbol, path=path)
    return cmd_impact(args)

def main() -> None:
    """
    Launch the FastMCP server.
    """
    mcp.run()

if __name__ == "__main__":
    main()
