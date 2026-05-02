import os
import argparse
from typing import Any, Dict, List
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.universal_list_paginator_python.src.list_paginator import paginate
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_symbol_locator_python.src.ast_symbol_locator import locate_symbol

def cmd_locate(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'locate' command."""
    target_path = os.path.abspath(args.path)
    symbol = args.symbol
    
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

    mode = "usage" if getattr(args, "usages", False) else "definition"
    inherited = getattr(args, "inherited", False)
    all_matches = []
    
    for file in files_to_process:
        matches = locate_symbol(file, symbol, mode=mode)
        
        # If the file had a syntax error, it returns [{"error": "..."}]
        if matches and "error" in matches[0]:
            continue # Skip files we can't parse
            
        for match in matches:
            match["file"] = os.path.relpath(file, target_path) if not os.path.isfile(target_path) else os.path.basename(file)
            match["absolute_path"] = file
            
            # Ancestry resolution
            if inherited and match["type"] == "class" and match.get("bases"):
                ancestors = []
                for base_name in match["bases"]:
                    # Secondary search for each base class name across all files
                    for search_file in files_to_process:
                        base_matches = locate_symbol(search_file, base_name, mode="definition")
                        if base_matches and "error" in base_matches[0]:
                            continue
                        for bm in base_matches:
                            if bm["type"] == "class":
                                bm["file"] = os.path.relpath(search_file, target_path) if not os.path.isfile(target_path) else os.path.basename(search_file)
                                bm["absolute_path"] = search_file
                                ancestors.append(bm)
                match["ancestors"] = ancestors
                
            all_matches.append(match)

    # Paginate results
    pagination = paginate(all_matches, page=args.page, size=args.size)
    
    return AgentResponse.success(
        data=pagination["items"],
        meta={
            "root_directory": target_path if os.path.isdir(target_path) else os.path.dirname(target_path),
            "symbol_searched": symbol,
            "total_matches": pagination["total"],
            "pagination": {
                "page": pagination["page"],
                "size": pagination["size"],
                "total_pages": pagination["total_pages"],
                "has_next": pagination["has_next"],
                "has_prev": pagination["has_prev"]
            }
        }
    )
