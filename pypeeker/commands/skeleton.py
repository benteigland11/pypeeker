import os
import argparse
from typing import Any, Dict
from universal_agent_response_python.src.agent_response import AgentResponse
from universal_list_paginator_python.src.list_paginator import paginate
from data_file_walker_python.src.file_walker import walk_python_files
from data_ast_skeleton_parser_python.src.ast_skeleton_parser import parse_skeleton

def cmd_skeleton(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'skeleton' command."""
    target_path = os.path.abspath(args.path)
    
    if not os.path.exists(target_path):
        return AgentResponse.error(f"{target_path} does not exist.", code="PATH_NOT_FOUND")

    files_to_process = []
    is_single_file = False
    
    if os.path.isfile(target_path):
        if not target_path.endswith('.py'):
            return AgentResponse.error("Target is a file but not a .py file.", code="INVALID_FILE_TYPE")
        files_to_process.append(target_path)
        is_single_file = True
    else:
        ignore = args.ignore if args.ignore else []
        files_to_process = walk_python_files(target_path, ignore_dirs=ignore)

    skeletons = []
    for file in files_to_process:
        skel = parse_skeleton(file)
        if "error" in skel:
            skeletons.append({
                "file": os.path.relpath(file, target_path) if not is_single_file else os.path.basename(file),
                "absolute_path": file,
                "error": skel["error"]
            })
        else:
            skeletons.append({
                "file": os.path.relpath(file, target_path) if not is_single_file else os.path.basename(file),
                "absolute_path": file,
                "skeleton": skel
            })

    if is_single_file:
        # Return directly without pagination for single file
        return AgentResponse.success(
            data=skeletons[0],
            meta={"root_directory": os.path.dirname(target_path)}
        )

    # Paginate for directories
    pagination = paginate(skeletons, page=args.page, size=args.size)
    
    return AgentResponse.success(
        data=pagination["items"],
        meta={
            "root_directory": target_path,
            "total_files": pagination["total"],
            "pagination": {
                "page": pagination["page"],
                "size": pagination["size"],
                "total_pages": pagination["total_pages"],
                "has_next": pagination["has_next"],
                "has_prev": pagination["has_prev"]
            }
        }
    )
