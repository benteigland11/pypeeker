import sys
import os
import argparse
from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("pypeeker-cli")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

# Add repo root to path if running locally (not installed)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(BASE_DIR) and BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from cg.cg_infra_agent_cli_python.src.agent_cli import AgentCLI
    from pypeeker.commands.circular import cmd_circular
    from pypeeker.commands.missing import cmd_missing
    from pypeeker.commands.skeleton import cmd_skeleton
    from pypeeker.commands.locate import cmd_locate
    from pypeeker.commands.interfaces import cmd_interfaces
    from pypeeker.commands.impact import cmd_impact
except ImportError as e:
    print(f"Error: Could not import project components. {e}", file=sys.stderr)
    sys.exit(1)

def cmd_mcp(args: argparse.Namespace) -> None:
    """
    Handler to launch the MCP server.
    """
    try:
        from pypeeker.mcp import main as run_server
        run_server()
    except ImportError as e:
        if "mcp" in str(e).lower():
             print("Error: MCP dependency not found. Install it with: pip install mcp", file=sys.stderr)
        else:
             print(f"Error launching MCP server: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """
    Main entry point for the pypeeker CLI.
    """
    cli = AgentCLI(
        prog="pypeeker",
        description="Unified Agent-Native Python Analysis CLI.",
        version=__version__,
        epilog=(
            "Environment variables:\n"
            "  PYPEEKER_CLI_NO_VERSION_CHECK=1   "
            "Disable the once-daily PyPI staleness check performed by the MCP server at boot."
        ),
    )
    
    # Common arguments for analysis commands
    analysis_args = [
        {"name": "directory", "help": "Root directory to scan"},
        {"name": "--ignore", "nargs": "*", "help": "Additional directories to ignore (added to defaults like venv, __pycache__, node_modules, etc.)", "default": []},
        {"name": "--include-deps", "action": "store_true", "dest": "include_deps", "help": "Scan everything including venvs, build artifacts, and caches (off by default)"},
        {"name": "--page", "type": int, "default": 1, "help": "Page number"},
        {"name": "--size", "type": int, "default": 20, "help": "Page size"},
    ]

    text_format_arg = {"name": "--format", "choices": ["json", "text"], "default": "text", "help": "Output format: 'text' (default, condensed line-anchored summary) or 'json' (structured)"}
    scan_args = analysis_args + [text_format_arg]

    interface_args = analysis_args + [
        {
            "name": "--include-tests",
            "action": "store_false",
            "dest": "ignore_tests",
            "default": True,
            "help": "Include files inside test directories and test_*.py files",
        },
    ]
    
    # Arguments for path-based commands
    path_args = [
        {"name": "path", "help": "File or directory to scan"},
        {"name": "--ignore", "nargs": "*", "help": "Additional directories to ignore (added to defaults like venv, __pycache__, node_modules, etc.)", "default": []},
        {"name": "--include-deps", "action": "store_true", "dest": "include_deps", "help": "Scan everything including venvs, build artifacts, and caches (off by default)"},
        {"name": "--page", "type": int, "default": 1, "help": "Page number (if path is a dir)"},
        {"name": "--size", "type": int, "default": 20, "help": "Page size (if path is a dir)"},
        {"name": "--format", "choices": ["json", "stub"], "default": "stub", "help": "Output format: 'stub' (default, Python stub text with line ranges) or 'json' (structured AST)"},
    ]
    
    # Arguments for locate
    locate_args = [
        {"name": "symbol", "help": "The symbol name to locate (class, function, variable)"},
        {"name": "path", "help": "File or directory to search within"},
        {"name": "--inherited", "action": "store_true", "help": "If a class, also locate its parent classes"},
        {"name": "--ignore", "nargs": "*", "help": "Additional directories to ignore (added to defaults like venv, __pycache__, node_modules, etc.)", "default": []},
        {"name": "--include-deps", "action": "store_true", "dest": "include_deps", "help": "Scan everything including venvs, build artifacts, and caches (off by default)"},
        {"name": "--page", "type": int, "default": 1, "help": "Page number (if path is a dir)"},
        {"name": "--size", "type": int, "default": 20, "help": "Page size (if path is a dir)"},
        text_format_arg,
    ]
    
    cli.add_commands("Project Scan", [
        {
            "name": "circular",
            "help": "Scan for circular imports in the project",
            "handler": cmd_circular,
            "args": scan_args + [
                {"name": "--summary-only", "action": "store_true", "dest": "summary_only", "help": "Show cycle count and hub list only; skip per-cycle details"},
            ],
        },
        {
            "name": "missing",
            "help": "Scan for unresolved (hallucinated) internal imports",
            "handler": cmd_missing,
            "args": scan_args,
        },
        {
            "name": "interfaces",
            "help": "Scan for documentation and typing gaps in code interfaces",
            "handler": cmd_interfaces,
            "args": interface_args,
        },
    ])

    cli.add_commands("Navigation", [
        {
            "name": "locate",
            "help": "Pinpoint a symbol's definition (and optionally its class ancestry)",
            "handler": cmd_locate,
            "args": locate_args,
        },
    ])

    cli.add_commands("Deep Dive", [
        {
            "name": "skeleton",
            "help": "Extract structural API signature (AST skeleton) of Python files",
            "handler": cmd_skeleton,
            "args": path_args,
        },
        {
            "name": "impact",
            "help": "Both directions of a function: outbound (what it touches) + inbound (who calls it)",
            "handler": cmd_impact,
            "args": [
                {"name": "symbol", "help": "Function name (bare or Class.method)"},
                {"name": "path", "help": "Path to the .py file"},
                {"name": "--inbound", "action": "store_true", "help": "Only show inbound (callers). Default is both directions."},
                {"name": "--outbound", "action": "store_true", "help": "Only show outbound (what this function touches). Default is both directions."},
                {"name": "--depth", "type": int, "default": 1, "help": "Outbound transitive depth (1 = direct only, max 5)"},
                {"name": "--root", "default": None, "help": "Project root for cross-file resolution (defaults to file's directory)"},
                {"name": "--ignore", "nargs": "*", "default": [], "help": "Additional directories to ignore for inbound search"},
                {"name": "--include-deps", "action": "store_true", "dest": "include_deps", "help": "Include venvs/build artifacts in inbound search"},
                {"name": "--format", "choices": ["json", "text"], "default": "text", "help": "Output format"},
                {"name": "--show-all-unresolved", "action": "store_true", "dest": "show_all_unresolved", "help": "Show every unresolved call (default: only notable categories)"},
            ],
        },
    ])

    cli.add_commands("Protocol", [
        {
            "name": "mcp",
            "help": "Launch the Model Context Protocol (MCP) server",
            "handler": cmd_mcp,
            "args": [],
        },
    ])
    
    cli.run()

if __name__ == "__main__":
    main()
