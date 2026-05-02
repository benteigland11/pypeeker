import ast
from typing import Any, List, Optional

class FlowVisitor(ast.NodeVisitor):
    def __init__(self, target_name: str):
        self.target_name = target_name
        self.flow_tree = []
        self._found = False
        self._class_stack = []
        self.lineno = None
        self.end_lineno = None

    def visit_ClassDef(self, node: ast.ClassDef):
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self._matches_target(node.name):
            self._found = True
            self.flow_tree = self.map_body(node.body)
            self.lineno = node.lineno
            self.end_lineno = getattr(node, "end_lineno", node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if self._matches_target(node.name):
            self._found = True
            self.flow_tree = self.map_body(node.body)
            self.lineno = node.lineno
            self.end_lineno = getattr(node, "end_lineno", node.lineno)
        self.generic_visit(node)

    def _matches_target(self, function_name: str) -> bool:
        full_name = ".".join([*self._class_stack, function_name])
        return self.target_name in {function_name, full_name}

    def map_body(self, body: List[ast.stmt]) -> List[dict]:
        nodes = []
        for stmt in body:
            mapped = self.map_node(stmt)
            if mapped:
                nodes.append(mapped)
        return nodes

    def map_node(self, node: ast.AST) -> Optional[dict]:
        base_info = {
            "line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None),
        }
        
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
                "body": self.map_body(node.body),
                "orelse": self.map_body(node.orelse) if node.orelse else []
            }
        elif isinstance(node, (ast.While)):
            return {
                **base_info,
                "type": "while",
                "test": ast.unparse(node.test),
                "body": self.map_body(node.body),
                "orelse": self.map_body(node.orelse) if node.orelse else []
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
                        "end_line": getattr(h, "end_lineno", None),
                        "body": self.map_body(h.body)
                    } for h in node.handlers
                ],
                "orelse": self.map_body(node.orelse) if node.orelse else [],
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
                        "end_line": getattr(c.pattern, "end_lineno", None),
                        "body": self.map_body(c.body)
                    } for c in node.cases
                ]
            }
        elif isinstance(node, (ast.Return)):
            return {**base_info, "type": "return", "value": ast.unparse(node.value) if node.value else None}
        elif isinstance(node, (ast.Raise)):
            return {**base_info, "type": "raise", "exc": ast.unparse(node.exc) if node.exc else None}
        elif isinstance(node, ast.Delete):
            return {**base_info, "type": "delete", "targets": [ast.unparse(target) for target in node.targets]}
        elif isinstance(node, ast.Assert):
            return {
                **base_info,
                "type": "assert",
                "test": ast.unparse(node.test),
                "msg": ast.unparse(node.msg) if node.msg else None,
            }
        elif isinstance(node, ast.Break):
            return {**base_info, "type": "break"}
        elif isinstance(node, ast.Continue):
            return {**base_info, "type": "continue"}
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            return {**base_info, "type": "yield", "value": ast.unparse(node.value) if node.value else None}
        elif isinstance(node, ast.Expr):
            inner = node.value
            if isinstance(inner, ast.Call):
                return {**base_info, "type": "call", "value": ast.unparse(inner)}
            if isinstance(inner, (ast.Yield, ast.YieldFrom)):
                return {**base_info, "type": "yield", "value": ast.unparse(inner.value) if inner.value else None}
            if isinstance(inner, (ast.Attribute, ast.Subscript, ast.Name, ast.Await)):
                return {**base_info, "type": "access", "value": ast.unparse(inner)}
        elif isinstance(node, ast.Assign):
            return {
                **base_info,
                "type": "assign",
                "target": ", ".join(ast.unparse(target) for target in node.targets),
                "value": ast.unparse(node.value),
            }
        elif isinstance(node, ast.AnnAssign):
            return {
                **base_info,
                "type": "assign",
                "target": ast.unparse(node.target),
                "value": ast.unparse(node.value) if node.value else None,
            }
        elif isinstance(node, ast.AugAssign):
            return {
                **base_info,
                "type": "assign",
                "target": ast.unparse(node.target),
                "value": f"{ast.unparse(node.target)} {type(node.op).__name__}= {ast.unparse(node.value)}",
            }
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
        
    return {
        "function": function_name,
        "lineno": visitor.lineno,
        "end_lineno": visitor.end_lineno,
        "flow": visitor.flow_tree,
    }
