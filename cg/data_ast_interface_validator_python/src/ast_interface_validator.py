import ast
import os

def validate_interface(file_path: str) -> list[dict]:
    """
    Validates the API interface of a Python file.
    Checks for missing docstrings, argument type hints, and return type hints.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
    except Exception as e:
        return [{"error": str(e)}]

    gaps = []

    def check_node(node, scope=""):
        name = getattr(node, "name", None)
        if not name:
            return
            
        full_name = f"{scope}.{name}" if scope else name
        node_gaps = []
        
        # 1. Docstring check
        if not ast.get_docstring(node):
            node_gaps.append("missing_docstring")
            
        # 2. Type hints check (for functions)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Argument type hints
            for arg in node.args.args:
                if arg.arg in ("self", "cls"):
                    continue
                if not arg.annotation:
                    node_gaps.append(f"missing_type_hint: {arg.arg}")
            
            if node.args.vararg and not node.args.vararg.annotation:
                node_gaps.append(f"missing_type_hint: *{node.args.vararg.arg}")
            
            for arg in node.args.kwonlyargs:
                if not arg.annotation:
                    node_gaps.append(f"missing_type_hint: {arg.arg}")
                    
            if node.args.kwarg and not node.args.kwarg.annotation:
                node_gaps.append(f"missing_type_hint: **{node.args.kwarg.arg}")
                
            # Return type hint
            if name != "__init__" and not node.returns:
                node_gaps.append("missing_return_type")
        
        if node_gaps:
            gaps.append({
                "symbol": full_name,
                "line": node.lineno,
                "gaps": node_gaps
            })

        # Recurse for classes
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                check_node(child, full_name)

    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            check_node(node)
            
    return gaps
