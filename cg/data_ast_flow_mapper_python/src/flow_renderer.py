def _tag(node: dict) -> str:
    line = node.get("line")
    return f"L{line:<4}" if line else "     "


def _render_block(nodes: list, indent: str, lines: list[str]) -> None:
    for n in nodes:
        _render_node(n, indent, lines)


def _render_node(node: dict, indent: str, lines: list[str]) -> None:
    t = node["type"]
    tag = _tag(node)

    if t == "if":
        lines.append(f"{tag} {indent}if {node['test']}:")
        _render_block(node["body"], indent + "    ", lines)
        if node.get("orelse"):
            lines.append(f"      {indent}else:")
            _render_block(node["orelse"], indent + "    ", lines)
    elif t == "for":
        lines.append(f"{tag} {indent}for {node['target']} in {node['iter']}:")
        _render_block(node["body"], indent + "    ", lines)
        if node.get("orelse"):
            lines.append(f"      {indent}else:")
            _render_block(node["orelse"], indent + "    ", lines)
    elif t == "while":
        lines.append(f"{tag} {indent}while {node['test']}:")
        _render_block(node["body"], indent + "    ", lines)
        if node.get("orelse"):
            lines.append(f"      {indent}else:")
            _render_block(node["orelse"], indent + "    ", lines)
    elif t == "try":
        lines.append(f"{tag} {indent}try:")
        _render_block(node["body"], indent + "    ", lines)
        for h in node.get("handlers", []):
            htag = f"L{h.get('line'):<4}" if h.get("line") else "     "
            lines.append(f"{htag} {indent}except {h.get('name', 'Exception')}:")
            _render_block(h.get("body", []), indent + "    ", lines)
        if node.get("orelse"):
            lines.append(f"      {indent}else:")
            _render_block(node["orelse"], indent + "    ", lines)
        if node.get("finalbody"):
            lines.append(f"      {indent}finally:")
            _render_block(node["finalbody"], indent + "    ", lines)
    elif t == "with":
        items = ", ".join(node.get("items", []))
        lines.append(f"{tag} {indent}with {items}:")
        _render_block(node["body"], indent + "    ", lines)
    elif t == "match":
        lines.append(f"{tag} {indent}match {node['subject']}:")
        for c in node.get("cases", []):
            ctag = f"L{c.get('line'):<4}" if c.get("line") else "     "
            guard = f" if {c['guard']}" if c.get("guard") else ""
            lines.append(f"{ctag} {indent}    case {c['pattern']}{guard}:")
            _render_block(c.get("body", []), indent + "        ", lines)
    elif t == "return":
        val = node.get("value")
        lines.append(f"{tag} {indent}return{(' ' + val) if val else ''}")
    elif t == "raise":
        exc = node.get("exc")
        lines.append(f"{tag} {indent}raise{(' ' + exc) if exc else ''}")
    elif t == "yield":
        val = node.get("value")
        lines.append(f"{tag} {indent}yield{(' ' + val) if val else ''}")
    elif t == "assign":
        val = node.get("value")
        if val is None:
            lines.append(f"{tag} {indent}{node['target']}")
        else:
            lines.append(f"{tag} {indent}{node['target']} = {val}")
    elif t == "call":
        lines.append(f"{tag} {indent}{node['value']}")
    elif t == "access":
        lines.append(f"{tag} {indent}{node['value']}")
    elif t == "delete":
        lines.append(f"{tag} {indent}del {', '.join(node.get('targets', []))}")
    elif t == "assert":
        msg = f", {node['msg']}" if node.get("msg") else ""
        lines.append(f"{tag} {indent}assert {node['test']}{msg}")
    elif t == "break":
        lines.append(f"{tag} {indent}break")
    elif t == "continue":
        lines.append(f"{tag} {indent}continue")


def render_flow(flow: dict) -> str:
    """Render a flow tree as compact pseudocode with line anchors."""
    name = flow.get("function", "?")
    start, end = flow.get("lineno"), flow.get("end_lineno")
    header = f"# flow: {name}"
    if start and end:
        header += f"  L{start}-{end}"
    lines: list[str] = [header]
    _render_block(flow.get("flow", []), "", lines)
    return "\n".join(lines) + "\n"
