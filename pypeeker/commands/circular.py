import os
import argparse
from typing import Any, Dict
from universal_agent_response_python.src.agent_response import AgentResponse
from universal_list_paginator_python.src.list_paginator import paginate
from data_file_walker_python.src.file_walker import walk_python_files
from data_ast_import_parser_python.src.ast_import_parser import parse_imports, resolve_import
from universal_graph_cycles_python.src.graph_cycles import find_cycles

def cmd_circular(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'circular' command."""
    root_dir = os.path.abspath(args.directory)
    
    if not os.path.isdir(root_dir):
        return AgentResponse.error(f"{root_dir} is not a directory.", code="DIRECTORY_NOT_FOUND")

    # 1. Walk files
    ignore = args.ignore if args.ignore else []
    files = walk_python_files(root_dir, ignore_dirs=ignore)
    
    # 2. Parse imports and build graph
    graph = {}
    for file in files:
        imports = parse_imports(file)
        neighbors = []
        for mod_name, line, is_rel, level, is_tc in imports:
            resolved, reason = resolve_import(mod_name, file, root_dir, is_rel, level)
            if reason == "resolved" and resolved != file:
                neighbors.append((resolved, {"line": line, "module": mod_name, "is_type_checking": is_tc}))
        graph[file] = neighbors
    
    # 3. Find cycles
    cycles_raw = find_cycles(graph)
    
    # 4. Format cycles
    formatted_cycles = []
    for cycle in cycles_raw:
        steps = []
        is_type_only_cycle = True
        for node, meta in cycle:
            if not meta.get("is_type_checking", False):
                is_type_only_cycle = False
            steps.append({
                "file": os.path.relpath(node, root_dir),
                "line": meta["line"],
                "import": meta["module"],
                "is_type_checking": meta.get("is_type_checking", False),
                "absolute_path": node
            })
        formatted_cycles.append({
            "steps": steps,
            "is_type_only": is_type_only_cycle
        })
    
    # 5. Paginating
    pagination = paginate(formatted_cycles, page=args.page, size=args.size)
    
    return AgentResponse.success(
        data=pagination["items"],
        meta={
            "root_directory": root_dir,
            "total_cycles": pagination["total"],
            "pagination": {
                "page": pagination["page"],
                "size": pagination["size"],
                "total_pages": pagination["total_pages"],
                "has_next": pagination["has_next"],
                "has_prev": pagination["has_prev"]
            }
        }
    )
