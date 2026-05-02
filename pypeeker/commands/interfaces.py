import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.universal_list_paginator_python.src.list_paginator import paginate
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_interface_validator_python.src.ast_interface_validator import validate_interface

def cmd_interfaces(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'interfaces' command."""
    target_path = os.path.abspath(args.directory)
    
    if not os.path.exists(target_path):
        return AgentResponse.error(f"{target_path} does not exist.", code="PATH_NOT_FOUND")

    files_to_process = []
    if os.path.isfile(target_path):
        if not target_path.endswith('.py'):
            return AgentResponse.error("Target is a file but not a .py file.", code="INVALID_FILE_TYPE")
        files_to_process.append(target_path)
    else:
        ignore = args.ignore if args.ignore else []
        files_to_process = walk_python_files(target_path, ignore_dirs=ignore)

    all_gaps = []
    total_symbols = 0
    symbols_with_docstrings = 0
    symbols_with_types = 0

    for file in files_to_process:
        file_gaps = validate_interface(file)
        
        # If the file had a syntax error, it returns [{"error": "..."}]
        if file_gaps and "error" in file_gaps[0]:
            continue # Skip files we can't parse
            
        for gap in file_gaps:
            gap["file"] = os.path.relpath(file, target_path) if not os.path.isfile(target_path) else os.path.basename(file)
            gap["absolute_path"] = file
            all_gaps.append(gap)

    # Paginate results
    pagination = paginate(all_gaps, page=args.page, size=args.size)
    
    return AgentResponse.success(
        data=pagination["items"],
        meta={
            "root_directory": target_path if os.path.isdir(target_path) else os.path.dirname(target_path),
            "total_gaps": pagination["total"],
            "pagination": {
                "page": pagination["page"],
                "size": pagination["size"],
                "total_pages": pagination["total_pages"],
                "has_next": pagination["has_next"],
                "has_prev": pagination["has_prev"]
            }
        }
    )
