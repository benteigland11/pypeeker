import os
import argparse
from typing import Any, Dict
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_symbol_locator_python.src.ast_symbol_locator import locate_symbol
from pypeeker.commands.common import paginated_success, relative_file, require_python_file

def _format_match(m: dict) -> str:
    start = m.get("start_line")
    end = m.get("end_line")
    if start and end and end != start:
        loc = f"{m['file']}:{start}-{end}"
    elif start:
        loc = f"{m['file']}:{start}"
    else:
        loc = m["file"]
    sig = m.get("signature") or m.get("name", "")
    return f"{loc}  {sig}"


def _render_locate_text(matches: list[dict], symbol: str) -> str:
    if not matches:
        return f"# locate: {symbol}\n(no matches)\n"
    lines = [f"# locate: {symbol}"]
    for m in matches:
        lines.append(_format_match(m))
        for anc in m.get("ancestors", []) or []:
            lines.append(f"  ↳ {_format_match(anc)}")
    return "\n".join(lines) + "\n"


def cmd_locate(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'locate' command."""
    target_path = os.path.abspath(args.path)
    symbol = args.symbol
    is_single_file = os.path.isfile(target_path)
    fmt = getattr(args, "format", "json") or "json"
    if fmt not in ("json", "text"):
        return AgentResponse.error(f"Unknown format '{fmt}'. Use 'json' or 'text'.", code="BAD_FORMAT")

    if not os.path.exists(target_path):
        return AgentResponse.error(f"{target_path} does not exist.", code="PATH_NOT_FOUND")

    files_to_process = []
    
    if is_single_file:
        error = require_python_file(target_path)
        if error:
            return error
        files_to_process.append(target_path)
    else:
        ignore = args.ignore if args.ignore else []
        files_to_process = walk_python_files(target_path, ignore_dirs=ignore)

    mode = "usage" if getattr(args, "usages", False) else "definition"
    inherited = getattr(args, "inherited", False)
    all_matches = []
    definition_cache = {}
    
    for file in files_to_process:
        matches = locate_symbol(file, symbol, mode=mode)
        
        # If the file had a syntax error, it returns [{"error": "..."}]
        if matches and "error" in matches[0]:
            continue # Skip files we can't parse
            
        for match in matches:
            match["file"] = relative_file(file, target_path, is_single_file)
            match["absolute_path"] = file
            
            # Ancestry resolution
            if inherited and match["type"] == "class" and match.get("bases"):
                ancestors = []
                for base_name in match["bases"]:
                    # Secondary search for each base class name across all files
                    for search_file in files_to_process:
                        cache_key = (search_file, base_name)
                        if cache_key not in definition_cache:
                            definition_cache[cache_key] = locate_symbol(search_file, base_name, mode="definition")
                        base_matches = definition_cache[cache_key]
                        if base_matches and "error" in base_matches[0]:
                            continue
                        for bm in base_matches:
                            if bm["type"] == "class":
                                ancestor = dict(bm)
                                ancestor["file"] = relative_file(search_file, target_path, is_single_file)
                                ancestor["absolute_path"] = search_file
                                ancestors.append(ancestor)
                match["ancestors"] = ancestors
                
            all_matches.append(match)

    if fmt == "text":
        return AgentResponse.success(
            data={"symbol": symbol, "text": _render_locate_text(all_matches, symbol)},
            meta={
                "root_directory": target_path if os.path.isdir(target_path) else os.path.dirname(target_path),
                "total_matches": len(all_matches),
            },
        )

    return paginated_success(
        all_matches,
        page=args.page,
        size=args.size,
        meta={
            "root_directory": target_path if os.path.isdir(target_path) else os.path.dirname(target_path),
            "symbol_searched": symbol,
            "total_matches": len(all_matches),
        }
    )
