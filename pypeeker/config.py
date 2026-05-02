"""Project-level config loader for pypeeker.

Reads `[tool.pypeeker]` from the nearest `pyproject.toml` walking up from a
target directory. Falls back to `.pypeeker.toml` at the same location.
"""
import os
from typing import Any, Dict, List, Optional

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:  # Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


_CONFIG_FILENAMES = ("pyproject.toml", ".pypeeker.toml")
_cache: Dict[str, "ProjectConfig"] = {}


class ProjectConfig:
    """Resolved per-project configuration."""

    def __init__(self, ignore: Optional[List[str]] = None, source: Optional[str] = None):
        self.ignore: List[str] = list(ignore or [])
        self.source: Optional[str] = source

    def __repr__(self) -> str:
        return f"ProjectConfig(ignore={self.ignore!r}, source={self.source!r})"


def _read_pyproject_section(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return data.get("tool", {}).get("pypeeker") if path.endswith("pyproject.toml") else data.get("pypeeker") or data


def _walk_up_for_config(start: str) -> Optional[str]:
    cur = os.path.abspath(start)
    while True:
        for fname in _CONFIG_FILENAMES:
            candidate = os.path.join(cur, fname)
            if os.path.isfile(candidate):
                section = _read_pyproject_section(candidate)
                if section:
                    return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def load_project_config(target_path: str) -> ProjectConfig:
    """Load config for the project containing `target_path`. Cached per resolved root."""
    start = target_path if os.path.isdir(target_path) else os.path.dirname(os.path.abspath(target_path))
    cache_key = os.path.abspath(start)
    if cache_key in _cache:
        return _cache[cache_key]

    config_path = _walk_up_for_config(start)
    if config_path is None:
        cfg = ProjectConfig()
        _cache[cache_key] = cfg
        return cfg

    section = _read_pyproject_section(config_path) or {}
    ignore = section.get("ignore", [])
    if not isinstance(ignore, list):
        ignore = []
    cfg = ProjectConfig(ignore=[str(d) for d in ignore], source=config_path)
    _cache[cache_key] = cfg
    return cfg


def clear_cache() -> None:
    """Useful for tests."""
    _cache.clear()
