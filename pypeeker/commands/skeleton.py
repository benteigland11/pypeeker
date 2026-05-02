import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_skeleton_parser_python.src.ast_skeleton_parser import parse_skeleton
from cg.data_ast_skeleton_parser_python.src.stub_renderer import render_stub
from pypeeker.commands.common import paginated_success, relative_file, require_python_file, resolve_ignore

def cmd_skeleton(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'skeleton' command."""
    target_path = os.path.abspath(args.path)
    fmt = getattr(args, "format", "json") or "json"
    if fmt not in ("json", "stub"):
        return AgentResponse.error(f"Unknown format '{fmt}'. Use 'json' or 'stub'.", code="BAD_FORMAT")

    if not os.path.exists(target_path):
        return AgentResponse.error(f"{target_path} does not exist.", code="PATH_NOT_FOUND")

    files_to_process = []
    is_single_file = False

    if os.path.isfile(target_path):
        error = require_python_file(target_path)
        if error:
            return error
        files_to_process.append(target_path)
        is_single_file = True
    else:
        ignore = resolve_ignore(args.ignore, include_deps=getattr(args, "include_deps", False))
        files_to_process = walk_python_files(target_path, ignore_dirs=ignore)

    skeletons = []
    for file in files_to_process:
        skel = parse_skeleton(file)
        entry = {
            "file": relative_file(file, target_path, is_single_file),
            "absolute_path": file,
        }
        if "error" in skel:
            entry["error"] = skel["error"]
        elif fmt == "stub":
            entry["stub"] = render_stub(skel)
        else:
            entry["skeleton"] = skel
        skeletons.append(entry)

    if is_single_file:
        # Return directly without pagination for single file
        return AgentResponse.success(
            data=skeletons[0],
            meta={"root_directory": os.path.dirname(target_path)}
        )

    return paginated_success(
        skeletons,
        page=args.page,
        size=args.size,
        meta={
            "root_directory": target_path,
            "total_files": len(skeletons),
        }
    )
