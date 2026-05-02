import ast

class ImpactVisitor(ast.NodeVisitor):
    def __init__(self, target_name):
        self.target_name = target_name
        self.found = False
        self.impact = {
            "external_calls": [],
            "internal_calls": [],
            "external_reads": [],
            "internal_reads": [],
            "external_writes": [],
            "internal_writes": [],
            "globals": []
        }
        self._in_target = False
        self._locals = set()
        self._defined_internally = set()
        self._class_stack = []

    def _matches_target(self, function_name: str) -> bool:
        full_name = ".".join([*self._class_stack, function_name])
        return self.target_name in {function_name, full_name}

    def visit_ClassDef(self, node):
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node):
        if self._matches_target(node.name):
            self.found = True
            self._in_target = True
            # Add arguments to locals
            for arg in node.args.args:
                self._locals.add(arg.arg)
            for arg in node.args.kwonlyargs:
                self._locals.add(arg.arg)
            if node.args.vararg:
                self._locals.add(node.args.vararg.arg)
            if node.args.kwarg:
                self._locals.add(node.args.kwarg.arg)

            self.generic_visit(node)
            self._in_target = False
        else:
            if self._in_target:
                self._defined_internally.add(node.name)
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Global(self, node):
        if self._in_target:
            self.impact["globals"].extend(node.names)
        self.generic_visit(node)

    def visit_Call(self, node):
        if self._in_target:
            try:
                name = ast.unparse(node.func)
                if name in self._defined_internally or name in self._locals:
                    self.impact["internal_calls"].append(name)
                    self.impact["internal_reads"].append(name)
                else:
                    self.impact["external_calls"].append(name)
                    self.impact["external_reads"].append(name)
            except Exception:
                pass
        self.generic_visit(node)

    def visit_Name(self, node):
        if self._in_target:
            if isinstance(node.ctx, ast.Store):
                self._locals.add(node.id)
                self.impact["internal_writes"].append(node.id)
            elif isinstance(node.ctx, ast.Load):
                if node.id in self._locals or node.id in self._defined_internally:
                    self.impact["internal_reads"].append(node.id)
                else:
                    self.impact["external_reads"].append(node.id)
        # No generic_visit(node) needed for Name

    def visit_Attribute(self, node):
        if self._in_target:
            try:
                attr_str = ast.unparse(node)
                # If it starts with 'self.' or 'cls.', it's an external class-state impact
                root = attr_str.split('.')[0]
                is_external = root == "self" or root == "cls" or root not in self._locals
                
                if isinstance(node.ctx, ast.Store):
                    if is_external:
                        self.impact["external_writes"].append(attr_str)
                    else:
                        self.impact["internal_writes"].append(attr_str)
                elif isinstance(node.ctx, ast.Load):
                    if is_external:
                        self.impact["external_reads"].append(attr_str)
                    else:
                        self.impact["internal_reads"].append(attr_str)
            except Exception:
                pass
        self.generic_visit(node)

def analyze_impact(file_path: str, function_name: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
    except Exception as e:
        return {"error": str(e)}

    visitor = ImpactVisitor(function_name)
    visitor.visit(tree)
    
    if not visitor.found:
        return {"error": f"Function '{function_name}' not found"}

    def unique(lst):
        return sorted(list(set(lst)))

    return {
        "function": function_name,
        "external": {
            "calls": unique(visitor.impact["external_calls"]),
            "reads": unique(visitor.impact["external_reads"]),
            "writes": unique(visitor.impact["external_writes"]),
            "globals": unique(visitor.impact["globals"])
        },
        "internal": {
            "calls": unique(visitor.impact["internal_calls"]),
            "reads": unique(visitor.impact["internal_reads"]),
            "writes": unique(visitor.impact["internal_writes"])
        }
    }
