import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_ast_flow_mapper_python.src.ast_flow_mapper import map_flow
from cg.data_ast_flow_mapper_python.src.flow_renderer import render_flow
from pypeeker.commands.common import require_python_file

def cmd_flow(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'flow' command."""
    file_path = os.path.abspath(args.path)
    symbol = args.symbol
    fmt = getattr(args, "format", "json") or "json"
    if fmt not in ("json", "pseudo"):
        return AgentResponse.error(f"Unknown format '{fmt}'. Use 'json' or 'pseudo'.", code="BAD_FORMAT")

    if not os.path.exists(file_path):
        return AgentResponse.error(f"{file_path} does not exist.", code="PATH_NOT_FOUND")

    if not os.path.isfile(file_path):
        return AgentResponse.error("Target must be a file, not a directory.", code="INVALID_TARGET")

    error = require_python_file(file_path)
    if error:
        return error

    result = map_flow(file_path, symbol)

    if "error" in result:
        return AgentResponse.error(result["error"], code="FLOW_MAPPING_FAILED")

    if fmt == "pseudo":
        return AgentResponse.success(data={
            "function": result["function"],
            "pseudo": render_flow(result),
        })

    return AgentResponse.success(data=result)
