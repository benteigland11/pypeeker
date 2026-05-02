import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_ast_impact_analyzer_python.src.ast_impact_analyzer import analyze_impact

def cmd_impact(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'impact' command."""
    file_path = os.path.abspath(args.path)
    symbol = args.symbol
    
    if not os.path.exists(file_path):
        return AgentResponse.error(f"{file_path} does not exist.", code="PATH_NOT_FOUND")
    
    if not os.path.isfile(file_path):
        return AgentResponse.error("Target must be a file, not a directory.", code="INVALID_TARGET")

    result = analyze_impact(file_path, symbol)
    
    if "error" in result:
        return AgentResponse.error(result["error"], code="IMPACT_ANALYSIS_FAILED")
        
    return AgentResponse.success(data=result)
