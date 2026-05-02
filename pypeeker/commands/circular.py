import os
import argparse
from collections import Counter
from typing import Any, Dict, List, Tuple
from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_file_walker_python.src.file_walker import walk_python_files
from cg.data_ast_import_parser_python.src.ast_import_parser import parse_imports, resolve_import
from cg.universal_graph_cycles_python.src.graph_cycles import find_cycles
from pypeeker.commands.common import paginated_success, resolve_ignore


def _compute_hubs(cycles: list[dict], min_appearances: int = 2) -> List[Tuple[str, int]]:
    """Return (file, cycle_count) sorted desc for files appearing in >= min_appearances cycles."""
    counter: Counter = Counter()
    for cycle in cycles:
        # Each file in a cycle is counted once per cycle (the cycle "involves" it)
        files_in_cycle = {step["file"] for step in cycle["steps"]}
        counter.update(files_in_cycle)
    return [(f, n) for f, n in counter.most_common() if n >= min_appearances]


def _render_circular_text(cycles: list[dict], hubs: List[Tuple[str, int]], summary_only: bool = False) -> str:
    if not cycles:
        return "# circular imports\n(none)\n"
    lines = ["# circular imports", f"{len(cycles)} cycles found"]

    if hubs:
        lines.append("")
        lines.append("[hubs] files in 2+ cycles:")
        # Pad file names so counts align; cap width to keep things readable
        max_w = min(max(len(f) for f, _ in hubs), 60)
        for f, n in hubs:
            lines.append(f"  {f:<{max_w}}  {n}")

    if summary_only:
        return "\n".join(lines) + "\n"

    for i, cycle in enumerate(cycles, 1):
        kind = "type-only" if cycle["is_type_only"] else "runtime"
        lines.append(f"\n[{i}] {kind} cycle:")
        for step in cycle["steps"]:
            tc = "  [TYPE_CHECKING]" if step.get("is_type_checking") else ""
            lines.append(f"  {step['file']}:{step['line']}  → {step['import']}{tc}")
    return "\n".join(lines) + "\n"


def cmd_circular(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'circular' command."""
    root_dir = os.path.abspath(args.directory)
    fmt = getattr(args, "format", "json") or "json"
    if fmt not in ("json", "text"):
        return AgentResponse.error(f"Unknown format '{fmt}'. Use 'json' or 'text'.", code="BAD_FORMAT")

    if not os.path.isdir(root_dir):
        return AgentResponse.error(f"{root_dir} is not a directory.", code="DIRECTORY_NOT_FOUND")

    # 1. Walk files
    ignore = resolve_ignore(args.ignore, include_deps=getattr(args, "include_deps", False))
    files = walk_python_files(root_dir, ignore_dirs=ignore)
    
    # 2. Parse imports and build graph
    graph = {}
    for file in files:
        try:
            imports = parse_imports(file)
        except (OSError, SyntaxError, UnicodeDecodeError):
            imports = []
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
    
    hubs = _compute_hubs(formatted_cycles)
    hubs_meta = [{"file": f, "cycle_count": n} for f, n in hubs]
    summary_only = bool(getattr(args, "summary_only", False))

    if fmt == "text":
        return AgentResponse.success(
            data={"text": _render_circular_text(formatted_cycles, hubs, summary_only=summary_only)},
            meta={
                "root_directory": root_dir,
                "total_cycles": len(formatted_cycles),
                "cycle_hubs": hubs_meta,
            },
        )

    return paginated_success(
        formatted_cycles,
        page=args.page,
        size=args.size,
        meta={
            "root_directory": root_dir,
            "total_cycles": len(formatted_cycles),
            "cycle_hubs": hubs_meta,
        }
    )
