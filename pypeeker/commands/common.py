import os
from typing import Any, Dict, Iterable, List, Optional

from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.universal_list_paginator_python.src.list_paginator import paginate


# Common Python project clutter that almost no one wants in an AST scan.
# Includes virtualenvs, build outputs, caches, VCS, and JS dep dirs.
DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset({
    # Virtualenvs
    "venv", ".venv", "env", "ENV", "virtualenv",
    # Caches
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".cache",
    # VCS
    ".git", ".hg", ".svn",
    # Build/dist artifacts
    "dist", "build", "site-packages",
    # JS/Node ecosystems (sometimes co-located in Python projects)
    "node_modules",
})


def resolve_ignore(user_ignore: Optional[Iterable[str]], include_deps: bool = False) -> List[str]:
    """Merge user-provided ignores with sensible Python defaults.

    :param user_ignore: Directories the caller explicitly wants skipped.
    :param include_deps: If True, skip the default skip list (scan everything,
                         including venvs, caches, build artifacts).
    :returns: Final list of directory names to skip during file walking.
    """
    user_set = set(user_ignore) if user_ignore else set()
    if include_deps:
        return sorted(user_set)
    return sorted(user_set | DEFAULT_IGNORE_DIRS)


def pagination_meta(pagination: Dict[str, Any]) -> Dict[str, Any]:
    """Return the standard pagination metadata block."""
    return {
        "page": pagination["page"],
        "size": pagination["size"],
        "total_pages": pagination["total_pages"],
        "has_next": pagination["has_next"],
        "has_prev": pagination["has_prev"],
    }


def paginated_success(items: list[Any], *, page: int, size: int, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Paginate a result list and return the standard success response."""
    pagination = paginate(items, page=page, size=size)
    response_meta = dict(meta)
    response_meta["pagination"] = pagination_meta(pagination)
    return AgentResponse.success(data=pagination["items"], meta=response_meta)


def relative_file(file_path: str, target_path: str, is_single_file: bool) -> str:
    """Return a stable display path for command responses."""
    return os.path.basename(file_path) if is_single_file else os.path.relpath(file_path, target_path)


def require_python_file(file_path: str) -> Dict[str, Any] | None:
    """Return an error response when a target is not a .py file."""
    if not file_path.endswith(".py"):
        return AgentResponse.error("Target is a file but not a .py file.", code="INVALID_FILE_TYPE")
    return None
