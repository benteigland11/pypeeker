import os
import argparse
from typing import Any, Dict
from universal_agent_response_python.src.agent_response import AgentResponse
from universal_list_paginator_python.src.list_paginator import paginate
from data_file_walker_python.src.file_walker import walk_python_files
from data_ast_import_parser_python.src.ast_import_parser import parse_imports, resolve_import

def cmd_missing(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'missing' command."""
    root_dir = os.path.abspath(args.directory)
    
    if not os.path.isdir(root_dir):
        return AgentResponse.error(f"{root_dir} is not a directory.", code="DIRECTORY_NOT_FOUND")

    # 1. Walk files
    ignore = args.ignore if args.ignore else []
    files = walk_python_files(root_dir, ignore_dirs=ignore)
    
    # 2. Parse imports and find 'not_found' ones
    missing_imports = []
    for file in files:
        imports = parse_imports(file)
        for mod_name, line, is_rel, level, is_tc in imports:
            _, reason = resolve_import(mod_name, file, root_dir, is_rel, level)
            if reason == "not_found":
                missing_imports.append({
                    "file": os.path.relpath(file, root_dir),
                    "line": line,
                    "import": mod_name,
                    "is_type_checking": is_tc,
                    "absolute_path": file
                })
    
    # 3. Paginating
    pagination = paginate(missing_imports, page=args.page, size=args.size)
    
    return AgentResponse.success(
        data=pagination["items"],
        meta={
            "root_directory": root_dir,
            "total_missing": pagination["total"],
            "pagination": {
                "page": pagination["page"],
                "size": pagination["size"],
                "total_pages": pagination["total_pages"],
                "has_next": pagination["has_next"],
                "has_prev": pagination["has_prev"]
            }
        }
    )
