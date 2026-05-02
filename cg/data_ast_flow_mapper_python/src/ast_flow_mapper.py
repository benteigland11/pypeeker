import ast
from typing import Any, List, Optional

class FlowVisitor(ast.NodeVisitor):
    def __init__(self, target_name: str):
        self.target_name = target_name
        self.flow_tree = []
        self._found = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == self.target_name:
            self._found = True
            self.flow_tree = self.map_body(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if node.name == self.target_name:
            self._found = True
            self.flow_tree = self.map_body(node.body)
        self.generic_visit(node)

    def map_body(self, body: List[ast.stmt]) -> List[dict]:
        nodes = []
        for stmt in body:
            mapped = self.map_node(stmt)
            if mapped:
                nodes.append(mapped)
        return nodes

    def map_node(self, node: ast.AST) -> Optional[dict]:
        base_info = {"line": getattr(node, "lineno", None)}
        
        if isinstance(node, ast.If):
            return {
                **base_info,
                "type": "if",
                "test": ast.unparse(node.test),
                "body": self.map_body(node.body),
                "orelse": self.map_body(node.orelse) if node.orelse else []
            }
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            return {
                **base_info,
                "type": "for",
                "target": ast.unparse(node.target),
                "iter": ast.unparse(node.iter),
                "body": self.map_body(node.body)
            }
        elif isinstance(node, (ast.While)):
            return {
                **base_info,
                "type": "while",
                "test": ast.unparse(node.test),
                "body": self.map_body(node.body)
            }
        elif isinstance(node, ast.Try):
            return {
                **base_info,
                "type": "try",
                "body": self.map_body(node.body),
                "handlers": [
                    {
                        "type": "except",
                        "name": ast.unparse(h.type) if h.type else "Exception",
                        "line": getattr(h, "lineno", None),
                        "body": self.map_body(h.body)
                    } for h in node.handlers
                ],
                "finalbody": self.map_body(node.finalbody) if node.finalbody else []
            }
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            return {
                **base_info,
                "type": "with",
                "items": [ast.unparse(item) for item in node.items],
                "body": self.map_body(node.body)
            }
        elif isinstance(node, ast.Match):
            return {
                **base_info,
                "type": "match",
                "subject": ast.unparse(node.subject),
                "cases": [
                    {
                        "type": "case",
                        "pattern": ast.unparse(c.pattern),
                        "guard": ast.unparse(c.guard) if c.guard else None,
                        "line": getattr(c.pattern, "lineno", None),
                        "body": self.map_body(c.body)
                    } for c in node.cases
                ]
            }
        elif isinstance(node, (ast.Return)):
            return {**base_info, "type": "return", "value": ast.unparse(node.value) if node.value else None}
        elif isinstance(node, (ast.Raise)):
            return {**base_info, "type": "raise", "exc": ast.unparse(node.exc) if node.exc else None}
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            return {**base_info, "type": "yield", "value": ast.unparse(node.value) if node.value else None}
        elif isinstance(node, ast.Expr):
            inner = node.value
            if isinstance(inner, ast.Call):
                return {**base_info, "type": "call", "value": ast.unparse(inner)}
            if isinstance(inner, (ast.Yield, ast.YieldFrom)):
                return {**base_info, "type": "yield", "value": ast.unparse(inner.value) if inner.value else None}
        elif isinstance(node, ast.Call):
             return {**base_info, "type": "call", "value": ast.unparse(node)}
        
        return None

def map_flow(file_path: str, function_name: str) -> dict:
    """
    Extract the logical control flow of a specific function in a Python file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
    except Exception as e:
        return {"error": str(e)}

    visitor = FlowVisitor(function_name)
    visitor.visit(tree)
    
    if not visitor._found:
        return {"error": f"Function '{function_name}' not found in {file_path}"}
        
    return {"function": function_name, "flow": visitor.flow_tree}
