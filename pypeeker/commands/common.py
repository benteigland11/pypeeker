import os
from typing import Any, Dict

from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.universal_list_paginator_python.src.list_paginator import paginate


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
