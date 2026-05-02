import ast

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, target, mode="definition"):
        self.target = target
        self.mode = mode
        self.matches = []
        self.scope_stack = []

    def current_scope(self):
        return ".".join(self.scope_stack)

    def _get_signature(self, node):
        """Extract a one-line signature/header for the node."""
        try:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Mock a node with empty body to unparse just the header
                # Note: unparse on the whole node includes the body, which we don't want.
                # So we manually construct the signature string.
                async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                args_str = ast.unparse(node.args)
                returns_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                return f"{async_prefix}def {node.name}({args_str}){returns_str}"
            elif isinstance(node, ast.ClassDef):
                bases_str = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
                return f"class {node.name}{bases_str}"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                return ast.unparse(node)
            return None
        except Exception:
            return None

    def add_match(self, node, kind, name):
        scope = self.current_scope()
        full_name = f"{scope}.{name}" if scope else name
        match_data = {
            "name": name,
            "full_name": full_name,
            "type": kind,
            "start_line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None)
        }
        
        if self.mode == "definition":
            sig = self._get_signature(node)
            if sig:
                match_data["signature"] = sig
            
            if kind == "class" and isinstance(node, ast.ClassDef):
                try:
                    match_data["bases"] = [ast.unparse(b) for b in node.bases]
                except Exception:
                    match_data["bases"] = []
                
        self.matches.append(match_data)

    def visit_ClassDef(self, node):
        if self.mode == "definition" and node.name == self.target:
            self.add_match(node, "class", node.name)
        
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node):
        if self.mode == "definition" and node.name == self.target:
            self.add_match(node, "function", node.name)
            
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        if self.mode == "definition" and node.name == self.target:
            self.add_match(node, "async_function", node.name)
            
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node):
        if self.mode == "definition":
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == self.target:
                    self.add_match(node, "variable", target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if self.mode == "definition":
            if isinstance(node.target, ast.Name) and node.target.id == self.target:
                self.add_match(node, "variable", node.target.id)
        self.generic_visit(node)
        
    def visit_Name(self, node):
        if self.mode == "usage" and node.id == self.target and isinstance(node.ctx, ast.Load):
            self.add_match(node, "usage", node.id)
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        if self.mode == "usage" and node.attr == self.target and isinstance(node.ctx, ast.Load):
            self.add_match(node, "usage", node.attr)
        self.generic_visit(node)

def locate_symbol(file_path: str, target: str, mode: str = "definition") -> list[dict]:
    """
    Search a Python file's AST for a specific symbol (class, function, or variable).
    Returns a list of match dictionaries containing the type, start_line, and end_line.
    mode can be "definition" or "usage".
    """
    if mode not in ("definition", "usage"):
        return [{"error": f"Invalid mode: {mode}"}]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
    except Exception as e:
        return [{"error": str(e)}]
        
    visitor = SymbolVisitor(target, mode=mode)
    visitor.visit(tree)
    return visitor.matches
