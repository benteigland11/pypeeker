"""MCP Server Readiness: future-proofing primitives for FastMCP-based servers.

  - run_cli_in_process: invoke a sibling CLI via `sys.executable -m <pkg>.cli`,
    eliminating PATH-resolution mismatches between the MCP host env and the CLI binary.
  - make_server: construct a FastMCP with serverInfo.version populated from the
    installed package's metadata. Optionally checks PyPI once per session for a
    newer release; if found, prepends a one-line update notice to instructions.
    No per-tool-call overhead, no network call when up-to-date the response is
    cached for 24h on disk, and the entire check is skipped when the env var
    `<PKG>_NO_VERSION_CHECK=1` is set.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, List, Optional, Tuple

_CACHE_TTL_SECONDS = 24 * 60 * 60
_PYPI_TIMEOUT = 2.0


def get_package_version(pkg_name: str) -> str:
    """Return the installed version string for pkg_name, or 'unknown' if not installed."""
    try:
        return version(pkg_name)
    except PackageNotFoundError:
        return "unknown"


def run_cli_in_process(
    pkg_name: str,
    command: str,
    args: Optional[List[str]] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Run `python -m <pkg_name>.cli <command> <args>` and return a standard envelope.

    Uses sys.executable so the CLI always runs in the same interpreter/env as the
    MCP server, regardless of what `<pkg_name>` console-script happens to be on $PATH.
    """
    full_cmd = [sys.executable, "-m", f"{pkg_name}.cli", command] + (args or [])
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": {
                "message": f"{pkg_name} command timed out ({timeout}s)",
                "code": "TIMEOUT",
            },
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": {
                "message": f"Python module {pkg_name}.cli not importable",
                "code": "NOT_INSTALLED",
            },
        }
    return {
        "status": "success" if result.returncode == 0 else "error",
        "data": {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        },
    }


def _cache_path(pkg_name: str) -> str:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "mcp_server_readiness", f"{pkg_name}.json")


def _read_cache(path: str) -> Optional[Tuple[float, str]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return float(data["checked_at"]), str(data["latest"])
    except (OSError, ValueError, KeyError):
        return None


def _write_cache(path: str, latest: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"checked_at": time.time(), "latest": latest}, fh)
    except OSError:
        pass


def _fetch_latest_from_pypi(pkg_name: str, timeout: float) -> Optional[str]:
    url = f"https://pypi.org/pypi/{pkg_name}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
        return str(payload["info"]["version"])
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError):
        return None


def _is_newer(latest: str, current: str) -> bool:
    """Compare PEP 440-ish version strings by tuple of ints. Conservative: any
    parse failure → assume not newer (avoid false positives)."""
    def parse(v: str) -> Optional[Tuple[int, ...]]:
        parts = [p for p in v.split(".") if p.isdigit()]
        if not parts:
            return None
        return tuple(int(p) for p in parts)

    a, b = parse(latest), parse(current)
    if a is None or b is None:
        return False
    return a > b


def check_for_update(
    pkg_name: str,
    current_version: str,
    cache_ttl_seconds: int = _CACHE_TTL_SECONDS,
    timeout: float = _PYPI_TIMEOUT,
) -> Optional[str]:
    """Return latest version string if PyPI has a newer release, else None.

    Cached on disk for cache_ttl_seconds. Fail-quiet: any network error, parse
    error, or env-var opt-out returns None. Honors `<PKG>_NO_VERSION_CHECK=1`
    (pkg name uppercased, dashes-to-underscores).
    """
    if current_version == "unknown":
        return None

    env_key = f"{pkg_name.upper().replace('-', '_')}_NO_VERSION_CHECK"
    if os.environ.get(env_key) == "1":
        return None

    path = _cache_path(pkg_name)
    cached = _read_cache(path)
    if cached and (time.time() - cached[0]) < cache_ttl_seconds:
        latest = cached[1]
    else:
        latest = _fetch_latest_from_pypi(pkg_name, timeout)
        if latest is None:
            return None
        _write_cache(path, latest)

    return latest if _is_newer(latest, current_version) else None


def make_server(
    name: str,
    pkg_name: str,
    instructions: str = "",
    check_pypi: bool = True,
) -> Any:
    """Construct a FastMCP server with serverInfo.version populated from pkg metadata.

    Version is read once at server boot via importlib.metadata and set on the
    underlying Server.version so the MCP initialize handshake advertises it via
    serverInfo. This costs zero tokens.

    If check_pypi is True (default), PyPI is queried (cached 24h) for the latest
    release and a one-line update notice is prepended to instructions only when
    the installed version is stale. When up-to-date, instructions are unmodified.
    """
    from mcp.server.fastmcp import FastMCP

    pkg_version = get_package_version(pkg_name)
    final_instructions = instructions

    if check_pypi:
        newer = check_for_update(pkg_name, pkg_version)
        if newer is not None:
            notice = (
                f"[{pkg_name} {pkg_version} -> {newer} available; "
                f"`pip install -U {pkg_name}`]"
            )
            final_instructions = (
                f"{notice}\n\n{instructions}" if instructions else notice
            )

    server = FastMCP(name, instructions=final_instructions or None)
    server._mcp_server.version = pkg_version
    return server
