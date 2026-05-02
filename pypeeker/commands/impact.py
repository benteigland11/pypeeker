import os
import sys
import ast
import argparse
from collections import deque, Counter
from typing import Any, Dict, List, Optional, Tuple

from cg.universal_agent_response_python.src.agent_response import AgentResponse
from cg.data_ast_impact_analyzer_python.src.ast_impact_analyzer import analyze_impact
from cg.data_ast_import_parser_python.src.ast_import_parser import parse_imports, resolve_import
from cg.data_ast_symbol_locator_python.src.ast_symbol_locator import locate_symbol
from cg.data_file_walker_python.src.file_walker import walk_python_files
from pypeeker.commands.common import require_python_file, resolve_ignore


MAX_DEPTH = 5


# Built-ins with no observable side effects — pure functions or constructors.
# Filtered from the default unresolved view because they add no signal.
_PURE_BUILTINS = frozenset({
    # Type constructors
    "int", "str", "float", "bool", "list", "dict", "tuple", "set", "frozenset",
    "bytes", "bytearray", "complex",
    # Inspection
    "isinstance", "issubclass", "hasattr", "getattr", "callable", "id", "type",
    "vars", "dir", "ascii",
    # Iteration / collection
    "iter", "next", "enumerate", "zip", "range", "map", "filter", "reversed",
    "sorted", "len", "min", "max", "sum", "abs", "round", "pow", "divmod",
    "all", "any", "slice",
    # Misc pure
    "repr", "format", "hash", "hex", "oct", "bin", "chr", "ord",
    "super", "object", "property", "staticmethod", "classmethod",
})

# Built-ins with real side effects — surface these, the agent cares.
_EFFECT_BUILTINS = frozenset({
    "print", "input", "open", "exit", "quit", "breakpoint",
    "exec", "eval", "compile",
    "setattr", "delattr",
    "__import__",
})

# Stdlib module roots; populated lazily for Python 3.10+ where the constant exists.
_STDLIB_MODULES: frozenset = frozenset(getattr(sys, "stdlib_module_names", ()))

# Categories considered "notable" — shown inline by default.
# (`reason` is tracked separately — depth_limit notable calls get a marker.)
_NOTABLE_CATEGORIES = frozenset({"effect_builtin", "stdlib", "resolver_gap", "other"})


def _classify_unresolved(call: str) -> str:
    """Categorize a call by its name shape (independent of why we didn't follow it)."""
    parts = call.split(".")
    head = parts[0] if parts else ""

    # Bare name (no dots)
    if len(parts) == 1:
        if head in _EFFECT_BUILTINS:
            return "effect_builtin"
        if head in _PURE_BUILTINS:
            return "pure_builtin"
        if head and head[0].isupper() and any(
            head.endswith(suffix) for suffix in ("Error", "Exception", "Warning", "Interrupt", "Exit")
        ):
            return "exception"
        return "other"

    # Dotted name
    if head in _STDLIB_MODULES:
        return "stdlib"
    if head in ("self", "cls"):
        # Resolver should have followed this; failing to do so is likely an inheritance gap.
        return "resolver_gap"
    return "dispatch"


def _file_imports_map(file_path: str, project_root: str) -> Dict[str, str]:
    """Map imported names → absolute file paths (project files only).

    Returns: {imported_local_name: absolute_path_to_defining_file}
    For ``from .foo import Bar``, maps "Bar" → path/to/foo.py.
    For ``import x.y``, maps "x.y" → resolved path.
    Skips names whose source resolves outside the project root.
    """
    out: Dict[str, str] = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
    except Exception:
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = ("." * (node.level or 0)) + (node.module or "")
            resolved, reason = resolve_import(mod, file_path, project_root, node.level > 0, node.level or 0)
            if reason != "resolved":
                continue
            for alias in node.names:
                local = alias.asname or alias.name
                out[local] = resolved
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                resolved, reason = resolve_import(alias.name, file_path, project_root, False, 0)
                if reason == "resolved":
                    out[local] = resolved
    return out


def _has_symbol_in_file(file_path: str, symbol_name: str) -> Optional[str]:
    """Return the qualified symbol name if found at top level or as a class method.

    Returns None if not found. Uses analyze_impact's lookup as the source of truth
    for "is this name resolvable inside this file as a function/method?"
    """
    # Try bare name (top-level function)
    res = analyze_impact(file_path, symbol_name)
    if res.get("function") and "error" not in res:
        return symbol_name
    return None


def _has_method_in_class(file_path: str, class_name: str, method_name: str) -> Optional[str]:
    """Return Class.method qualified name if the method exists in the class."""
    qualified = f"{class_name}.{method_name}"
    res = analyze_impact(file_path, qualified)
    if res.get("function") and "error" not in res:
        return qualified
    return None


def _resolve_call(
    call_name: str,
    source_file: str,
    source_class: Optional[str],
    project_root: str,
    file_imports: Dict[str, str],
) -> Optional[Tuple[str, str]]:
    """Resolve a call to (file_path, qualified_symbol) or None if unresolvable.

    Static-resolution heuristics only:
    - self.X / cls.X        → look in source_class within source_file
    - X (bare)              → top-level in source_file, or an imported name
    - Module.X / Imported.X → resolve Module via imports, find X in that file
    Anything else returns None (caller should mark as unresolved).
    """
    if not call_name or "(" in call_name:  # paranoia: drop call sites that snuck in
        return None

    parts = call_name.split(".")

    # Case 1: self.X or cls.X — look within current class
    if len(parts) >= 2 and parts[0] in ("self", "cls") and source_class:
        method = parts[1]
        qualified = _has_method_in_class(source_file, source_class, method)
        if qualified:
            return (source_file, qualified)
        return None

    # Case 2: bare name (single segment, no dots)
    if len(parts) == 1:
        bare = parts[0]
        # Top-level in current file?
        local = _has_symbol_in_file(source_file, bare)
        if local:
            return (source_file, local)
        # Imported from another project file?
        if bare in file_imports:
            target_file = file_imports[bare]
            if _is_under_root(target_file, project_root):
                resolved = _has_symbol_in_file(target_file, bare)
                if resolved:
                    return (target_file, resolved)
        return None

    # Case 3: Module.X or AliasOrClass.X
    if len(parts) >= 2:
        head, tail = parts[0], parts[1]
        # Class defined in current file: Class.method
        cls_lookup = _has_method_in_class(source_file, head, tail)
        if cls_lookup:
            return (source_file, cls_lookup)
        # Imported binding: head is an imported module/class
        if head in file_imports:
            target_file = file_imports[head]
            if _is_under_root(target_file, project_root):
                # Try as Class.method in that file
                cls_lookup = _has_method_in_class(target_file, head, tail)
                if cls_lookup:
                    return (target_file, cls_lookup)
                # Try as bare top-level function tail in that file
                top_level = _has_symbol_in_file(target_file, tail)
                if top_level:
                    return (target_file, top_level)
        return None

    return None


def _is_under_root(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
    except ValueError:
        return False


def _propagate_impact(
    symbol: str,
    file_path: str,
    project_root: str,
    max_depth: int,
) -> Dict[str, Any]:
    """BFS the call graph, return aggregated transitive surface.

    Walks outward from (symbol, file_path) up to max_depth levels.
    Resolves callees statically; unresolvable calls are reported, not followed.
    """
    visited: set = set()
    queue: deque = deque([(symbol, file_path, 0)])

    visited_nodes: List[Dict[str, Any]] = []
    transitive_calls: set = set()
    transitive_writes: List[Dict[str, Any]] = []
    transitive_globals: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []

    imports_cache: Dict[str, Dict[str, str]] = {}

    while queue:
        sym, path, depth = queue.popleft()
        key = (path, sym)
        if key in visited:
            continue
        visited.add(key)

        result = analyze_impact(path, sym)
        if "error" in result:
            continue

        rel_path = os.path.relpath(path, project_root)
        visited_nodes.append({
            "depth": depth,
            "symbol": sym,
            "path": rel_path,
            "external_call_count": len(result["external"]["calls"]),
            "external_write_count": len(result["external"]["writes"]),
        })

        transitive_calls.update(result["external"]["calls"])
        for w in result["external"]["writes"]:
            transitive_writes.append({"name": w, "in_symbol": sym, "in_path": rel_path, "at_depth": depth})
        for g in result["external"]["globals"]:
            transitive_globals.append({"name": g, "in_symbol": sym, "in_path": rel_path, "at_depth": depth})

        if depth >= max_depth:
            # Past the limit: surface the calls but don't recurse
            for call in result["external"]["calls"]:
                unresolved.append({
                    "call": call, "in_symbol": sym, "in_path": rel_path,
                    "at_depth": depth, "reason": "depth_limit",
                    "category": _classify_unresolved(call),
                })
            continue

        if path not in imports_cache:
            imports_cache[path] = _file_imports_map(path, project_root)
        file_imports = imports_cache[path]

        source_class = sym.rsplit(".", 1)[0] if "." in sym else None

        for call in result["external"]["calls"]:
            resolved = _resolve_call(call, path, source_class, project_root, file_imports)
            if resolved is not None:
                queue.append((resolved[1], resolved[0], depth + 1))
            else:
                unresolved.append({
                    "call": call, "in_symbol": sym, "in_path": rel_path,
                    "at_depth": depth, "reason": "unresolved",
                    "category": _classify_unresolved(call),
                })

    return {
        "function": symbol,
        "depth": max_depth,
        "transitive_external": {
            "calls": sorted(transitive_calls),
            "writes": transitive_writes,
            "globals": transitive_globals,
        },
        "visited": visited_nodes,
        "unresolved": unresolved,
    }


def _render_propagation_text(data: Dict[str, Any], show_all_unresolved: bool = False) -> str:
    """Aggregated transitive-surface text view for depth>1 impact results."""
    lines: List[str] = [
        f"# impact: {data['function']}  (depth {data['depth']})",
        "",
    ]

    writes = data["transitive_external"]["writes"]
    globals_ = data["transitive_external"]["globals"]
    calls = data["transitive_external"]["calls"]
    visited = data["visited"]
    unresolved = data["unresolved"]

    lines.append(f"transitive surface across {len(visited)} reached symbols:")
    lines.append(f"  external calls:   {len(calls)} unique")
    lines.append(f"  external writes:  {len(writes)}" + ("       <- danger zone for refactors" if writes else ""))
    for w in writes:
        lines.append(f"    {w['name']:<40}  in {w['in_symbol']} (depth {w['at_depth']})")
    lines.append(f"  globals modified: {len(globals_)}")
    for g in globals_:
        lines.append(f"    {g['name']:<40}  in {g['in_symbol']} (depth {g['at_depth']})")

    lines.append("")
    lines.append(f"reached symbols:")
    for v in visited:
        lines.append(f"  depth {v['depth']}  {v['symbol']:<55}  {v['path']}")

    if unresolved:
        # Dedupe by (call, in_symbol) for readability
        seen = set()
        uniq = []
        for u in unresolved:
            key = (u["call"], u["in_symbol"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(u)

        notable = [u for u in uniq if u.get("category") in _NOTABLE_CATEGORIES] if not show_all_unresolved else uniq
        suppressed = [u for u in uniq if u not in notable]

        if notable:
            lines.append("")
            lines.append(f"unresolved (notable, {len(notable)}):")
            for u in notable[:50]:
                cat = u.get("category", "other")
                marker = " *" if u.get("reason") == "depth_limit" else ""
                tag = f"[{cat}{marker}]"
                lines.append(f"  {u['call']:<45}  in {u['in_symbol']} (depth {u['at_depth']}) {tag}")
            if len(notable) > 50:
                lines.append(f"  ... and {len(notable) - 50} more")
            if any(u.get("reason") == "depth_limit" for u in notable):
                lines.append("  * = at depth limit; would be followed if --depth were higher")

        if suppressed and not show_all_unresolved:
            cats = Counter(u.get("category", "other") for u in suppressed)
            summary = ", ".join(f"{n} {cat.replace('_', ' ')}" for cat, n in cats.most_common())
            lines.append("")
            lines.append(f"unresolved (filtered, {len(suppressed)}): {summary}")
            lines.append("  pass --show-all-unresolved to see them")

    return "\n".join(lines) + "\n"


def _find_inbound_callers(
    symbol: str,
    project_root: str,
    ignore_dirs: List[str],
) -> List[Dict[str, Any]]:
    """Walk the project for places that reference the symbol.

    Static name match — for `Class.method`, searches for the rightmost name
    component (the method) across all project files. False positives are
    possible (any name collision); the agent can filter.
    """
    search_name = symbol.rsplit(".", 1)[-1]
    matches: List[Dict[str, Any]] = []
    for f in walk_python_files(project_root, ignore_dirs=ignore_dirs):
        result = locate_symbol(f, search_name, mode="usage")
        if result and "error" in result[0]:
            continue
        for m in result:
            m["file"] = os.path.relpath(f, project_root)
            m["absolute_path"] = f
            matches.append(m)
    return matches


def cmd_impact(args: argparse.Namespace) -> Dict[str, Any]:
    """Handler for the 'impact' command."""
    file_path = os.path.abspath(args.path)
    symbol = args.symbol
    depth = max(1, min(int(getattr(args, "depth", 1) or 1), MAX_DEPTH))
    root = getattr(args, "root", None)
    fmt = getattr(args, "format", "json") or "json"
    if fmt not in ("json", "text"):
        return AgentResponse.error(f"Unknown format '{fmt}'. Use 'json' or 'text'.", code="BAD_FORMAT")

    # Direction flags: --inbound / --outbound. Neither = both. Both = both.
    inbound_flag = bool(getattr(args, "inbound", False))
    outbound_flag = bool(getattr(args, "outbound", False))
    do_inbound = inbound_flag or not outbound_flag
    do_outbound = outbound_flag or not inbound_flag

    if not os.path.exists(file_path):
        return AgentResponse.error(f"{file_path} does not exist.", code="PATH_NOT_FOUND")

    if not os.path.isfile(file_path):
        return AgentResponse.error("Target must be a file, not a directory.", code="INVALID_TARGET")

    error = require_python_file(file_path)
    if error:
        return error

    project_root = os.path.abspath(root) if root else os.path.dirname(file_path)
    if not os.path.isdir(project_root):
        return AgentResponse.error(f"Project root '{project_root}' is not a directory.", code="INVALID_ROOT")

    out: Dict[str, Any] = {"function": symbol}

    # --- Outbound (what this function reaches into) ---
    if do_outbound:
        if depth == 1:
            outbound = analyze_impact(file_path, symbol)
            if "error" in outbound:
                return AgentResponse.error(outbound["error"], code="IMPACT_ANALYSIS_FAILED")
            out["outbound"] = outbound
        else:
            initial = analyze_impact(file_path, symbol)
            if "error" in initial:
                return AgentResponse.error(initial["error"], code="IMPACT_ANALYSIS_FAILED")
            out["outbound"] = _propagate_impact(symbol, file_path, project_root, depth)

    # --- Inbound (who calls this function) ---
    if do_inbound:
        ignore = resolve_ignore(
            getattr(args, "ignore", []) or [],
            include_deps=getattr(args, "include_deps", False),
            project_root=project_root,
        )
        out["inbound"] = _find_inbound_callers(symbol, project_root, ignore)

    if fmt == "text":
        show_all = bool(getattr(args, "show_all_unresolved", False))
        text = _render_combined_text(out, depth, show_all_unresolved=show_all)
        return AgentResponse.success(
            data={"text": text, **out},
            meta={"project_root": project_root},
        )

    return AgentResponse.success(data=out, meta={"project_root": project_root})


def _render_combined_text(out: Dict[str, Any], depth: int, show_all_unresolved: bool = False) -> str:
    """Render a combined inbound/outbound view as text."""
    lines: List[str] = [f"# impact: {out['function']}", ""]

    if "outbound" in out:
        lines.append("## outbound (what this function reaches into)")
        lines.append("")
        outbound = out["outbound"]
        if depth == 1:
            calls = outbound.get("external", {}).get("calls", [])
            writes = outbound.get("external", {}).get("writes", [])
            globals_ = outbound.get("external", {}).get("globals", [])
            lines.append(f"  external calls:   {len(calls)}")
            for c in calls:
                lines.append(f"    {c}")
            lines.append(f"  external writes:  {len(writes)}" + ("       <- side effects" if writes else ""))
            for w in writes:
                lines.append(f"    {w}")
            lines.append(f"  globals modified: {len(globals_)}")
            for g in globals_:
                lines.append(f"    {g}")
        else:
            # depth>1 propagation result already has its own renderer
            lines.append(_render_propagation_text(outbound, show_all_unresolved=show_all_unresolved))
        lines.append("")

    if "inbound" in out:
        inbound = out["inbound"]
        lines.append(f"## inbound (who calls this) — {len(inbound)} match(es)")
        lines.append("")
        if not inbound:
            lines.append("  (no callers found in project)")
        else:
            for m in inbound[:50]:
                start = m.get("start_line", "?")
                lines.append(f"  {m['file']}:{start}")
            if len(inbound) > 50:
                lines.append(f"  ... and {len(inbound) - 50} more")
        lines.append("")

    return "\n".join(lines) + "\n"
