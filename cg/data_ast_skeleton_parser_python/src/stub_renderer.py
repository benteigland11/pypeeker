def _format_arg(arg: dict) -> str:
    s = arg["name"]
    if "type" in arg:
        s += f": {arg['type']}"
    if "default" in arg:
        s += f" = {arg['default']}" if "type" in arg else f"={arg['default']}"
    return s


def _format_signature(fn: dict) -> str:
    args = ", ".join(_format_arg(a) for a in fn.get("args", []))
    prefix = "async def" if fn.get("is_async") else "def"
    sig = f"{prefix} {fn['name']}({args})"
    if fn.get("returns"):
        sig += f" -> {fn['returns']}"
    return sig + ":"


def _line_tag(node: dict) -> str:
    start = node.get("lineno")
    end = node.get("end_lineno")
    if start is None:
        return ""
    if end and end != start:
        return f"  # L{start}-{end}"
    return f"  # L{start}"


def _render_docstring(doc: str | None, indent: str) -> list[str]:
    if not doc:
        return []
    if "\n" in doc:
        lines = [f'{indent}"""']
        for line in doc.split("\n"):
            lines.append(f"{indent}{line}" if line else indent.rstrip())
        lines.append(f'{indent}"""')
        return lines
    return [f'{indent}"""{doc}"""']


def _render_function(fn: dict, indent: str = "") -> list[str]:
    lines = []
    for dec in fn.get("decorators", []):
        lines.append(f"{indent}@{dec}")
    lines.append(f"{indent}{_format_signature(fn)}{_line_tag(fn)}")
    body_indent = indent + "    "
    doc_lines = _render_docstring(fn.get("docstring"), body_indent)
    lines.extend(doc_lines)
    lines.append(f"{body_indent}...")
    return lines


def _render_variable(var: dict, indent: str = "") -> str:
    s = f"{indent}{var['name']}"
    if "type" in var:
        s += f": {var['type']}"
    if "value" in var:
        s += f" = {var['value']}"
    return s


def _render_class(cls: dict) -> list[str]:
    lines = []
    for dec in cls.get("decorators", []):
        lines.append(f"@{dec}")
    bases = cls.get("bases", [])
    header = f"class {cls['name']}"
    if bases:
        header += f"({', '.join(bases)})"
    header += ":"
    lines.append(f"{header}{_line_tag(cls)}")

    body_indent = "    "
    body: list[str] = []
    body.extend(_render_docstring(cls.get("docstring"), body_indent))
    for var in cls.get("variables", []):
        body.append(_render_variable(var, body_indent))
    for method in cls.get("methods", []):
        if body and not body[-1].strip() == "":
            body.append("")
        body.extend(_render_function(method, body_indent))

    if not body:
        body.append(f"{body_indent}...")
    lines.extend(body)
    return lines


def render_stub(skeleton: dict) -> str:
    """Render a skeleton dict as Python stub text (PEP 484 .pyi style)."""
    sections: list[list[str]] = []

    imports = skeleton.get("imports", [])
    if imports:
        sections.append(list(imports))

    variables = skeleton.get("variables", [])
    if variables:
        sections.append([_render_variable(v) for v in variables])

    for cls in skeleton.get("classes", []):
        sections.append(_render_class(cls))

    for fn in skeleton.get("functions", []):
        sections.append(_render_function(fn))

    return "\n\n".join("\n".join(s) for s in sections) + "\n"
