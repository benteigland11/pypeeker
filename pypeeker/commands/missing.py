import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_import_parser_python.src.ast_import_parser import parse_imports, resolve_import
from pypeeker.commands.common import paginated_success, resolve_ignore


def _render_missing_text(items: list[dict]) -> str:
    if not items:
        return "# missing imports\n(none)\n"
    lines = ["# missing imports"]
    for it in items:
        tc = "  [TYPE_CHECKING]" if it.get("is_type_checking") else ""
        lines.append(f"{it['file']}:{it['line']}  {it['import']}{tc}")
    return "\n".join(lines) + "\n"


def cmd_missing(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'missing' command."""
    root_dir = os.path.abspath(args.directory)
    fmt = getattr(args, "format", "json") or "json"
    if fmt not in ("json", "text"):
        return AgentResponse.error(f"Unknown format '{fmt}'. Use 'json' or 'text'.", code="BAD_FORMAT")

    if not os.path.isdir(root_dir):
        return AgentResponse.error(f"{root_dir} is not a directory.", code="DIRECTORY_NOT_FOUND")

    # 1. Walk files
    ignore = resolve_ignore(args.ignore, include_deps=getattr(args, "include_deps", False))
    files = walk_python_files(root_dir, ignore_dirs=ignore)
    
    # 2. Parse imports and find 'not_found' ones
    missing_imports = []
    for file in files:
        try:
            imports = parse_imports(file)
        except (OSError, SyntaxError, UnicodeDecodeError):
            imports = []
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
    
    if fmt == "text":
        return AgentResponse.success(
            data={"text": _render_missing_text(missing_imports)},
            meta={"root_directory": root_dir, "total_missing": len(missing_imports)},
        )

    return paginated_success(
        missing_imports,
        page=args.page,
        size=args.size,
        meta={
            "root_directory": root_dir,
            "total_missing": len(missing_imports),
        }
    )
