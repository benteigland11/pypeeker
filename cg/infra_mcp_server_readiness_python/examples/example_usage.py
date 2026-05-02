"""Example usage of MCP Server Readiness primitives.

Demonstrates the building blocks without any network calls (PyPI check is
disabled here so the example runs offline and exits cleanly):
  1. get_package_version reads installed package metadata.
  2. run_cli_in_process invokes a sibling CLI module via sys.executable.
  3. make_server constructs a FastMCP with serverInfo.version populated.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mcp_server_readiness import get_package_version, make_server, run_cli_in_process


def demo_version_lookup() -> None:
    print(f"pip version (installed):       {get_package_version('pip')}")
    print(f"missing package version:       {get_package_version('not-real-xyz')}")


def demo_cli_runner() -> None:
    response = run_cli_in_process("definitely_not_a_module_xyz", "any-command")
    print(f"missing-module run status:     {response['status']}")
    print(f"missing-module exit_code:      {response['data']['exit_code']}")


def demo_server_factory() -> None:
    # check_pypi=False keeps the example offline-safe; production usage
    # leaves it on so agents see a notice when an update is available.
    server = make_server(
        name="example-mcp",
        pkg_name="pip",
        instructions="Demo server. Replace pkg_name with your own package.",
        check_pypi=False,
    )
    print(f"server type:                   {type(server).__name__}")
    print(f"server name:                   {server.name}")
    print(f"server version:                {server._mcp_server.version}")


if __name__ == "__main__":
    demo_version_lookup()
    demo_cli_runner()
    demo_server_factory()
