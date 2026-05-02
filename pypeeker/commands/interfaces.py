import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_interface_validator_python.src.ast_interface_validator import validate_interface
from pypeeker.commands.common import paginated_success, relative_file, require_python_file

TEST_DIR_NAMES = {"test", "tests"}


def _is_test_file(file_path: str, root_dir: str) -> bool:
    """Return true when a file is under a test directory or named like a test."""
    relative_parts = os.path.relpath(file_path, root_dir).split(os.sep)
    filename = relative_parts[-1]
    return filename.startswith("test_") or any(part in TEST_DIR_NAMES for part in relative_parts[:-1])


def cmd_interfaces(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'interfaces' command."""
    target_path = os.path.abspath(args.directory)
    
    if not os.path.exists(target_path):
        return AgentResponse.error(f"{target_path} does not exist.", code="PATH_NOT_FOUND")

    files_to_process = []
    is_single_file = os.path.isfile(target_path)
    if os.path.isfile(target_path):
        error = require_python_file(target_path)
        if error:
            return error
        files_to_process.append(target_path)
    else:
        ignore = args.ignore if args.ignore else []
        files_to_process = walk_python_files(target_path, ignore_dirs=ignore)

    if getattr(args, "ignore_tests", True):
        root_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        files_to_process = [
            file for file in files_to_process
            if not _is_test_file(file, root_dir)
        ]

    all_gaps = []

    for file in files_to_process:
        file_gaps = validate_interface(file)
        
        # If the file had a syntax error, it returns [{"error": "..."}]
        if file_gaps and "error" in file_gaps[0]:
            continue # Skip files we can't parse
            
        for gap in file_gaps:
            gap["file"] = relative_file(file, target_path, is_single_file)
            gap["absolute_path"] = file
            all_gaps.append(gap)

    return paginated_success(
        all_gaps,
        page=args.page,
        size=args.size,
        meta={
            "root_directory": target_path if os.path.isdir(target_path) else os.path.dirname(target_path),
            "total_gaps": len(all_gaps),
            "ignored_tests": getattr(args, "ignore_tests", True),
        }
    )
