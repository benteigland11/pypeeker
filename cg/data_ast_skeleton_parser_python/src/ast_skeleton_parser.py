import ast

def extract_arguments(args: ast.arguments) -> list[dict]:
    extracted = []
    
    def arg_to_dict(a: ast.arg, default_node=None):
        info = {"name": a.arg}
        if a.annotation:
            try:
                info["type"] = ast.unparse(a.annotation)
            except Exception:
                pass
        if default_node:
            try:
                info["default"] = ast.unparse(default_node)
            except Exception:
                pass
        return info
        
    # Zip args from right with defaults
    defs = args.defaults
    offset = len(args.args) - len(defs)
    
    for i, a in enumerate(args.args):
        default = defs[i - offset] if i >= offset else None
        extracted.append(arg_to_dict(a, default))
        
    if args.vararg:
        vararg_info = {"name": f"*{args.vararg.arg}"}
        if args.vararg.annotation:
            try:
                vararg_info["type"] = ast.unparse(args.vararg.annotation)
            except Exception:
                pass
        extracted.append(vararg_info)
        
    # kwonlyargs
    kw_defs = args.kw_defaults
    for i, a in enumerate(args.kwonlyargs):
        default = kw_defs[i] if kw_defs[i] else None
        extracted.append(arg_to_dict(a, default))
        
    if args.kwarg:
        kwarg_info = {"name": f"**{args.kwarg.arg}"}
        if args.kwarg.annotation:
            try:
                kwarg_info["type"] = ast.unparse(args.kwarg.annotation)
            except Exception:
                pass
        extracted.append(kwarg_info)
        
    return extracted

def extract_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    decorators = []
    for d in node.decorator_list:
        try:
            decorators.append(ast.unparse(d))
        except Exception:
            pass
    return decorators

def extract_variables(body: list[ast.stmt]) -> list[dict]:
    variables = []
    for node in body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_info = {"name": target.id}
                    if node.value:
                        try:
                            var_info["value"] = ast.unparse(node.value)
                        except Exception:
                            pass
                    variables.append(var_info)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                var_info = {"name": node.target.id}
                try:
                    var_info["type"] = ast.unparse(node.annotation)
                except Exception:
                    pass
                if node.value:
                    try:
                        var_info["value"] = ast.unparse(node.value)
                    except Exception:
                        pass
                variables.append(var_info)
    return variables

def extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    returns = None
    if node.returns:
        try:
            returns = ast.unparse(node.returns)
        except Exception:
            pass

    return {
        "name": node.name,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "docstring": ast.get_docstring(node),
        "decorators": extract_decorators(node),
        "args": extract_arguments(node.args),
        "returns": returns
    }

def extract_class(node: ast.ClassDef) -> dict:
    methods = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(extract_function(child))
            
    bases = []
    for b in node.bases:
        try:
            bases.append(ast.unparse(b))
        except Exception:
            pass
            
    variables = extract_variables(node.body)
    
    return {
        "name": node.name,
        "docstring": ast.get_docstring(node),
        "decorators": extract_decorators(node),
        "bases": bases,
        "variables": variables,
        "methods": methods
    }

def parse_skeleton(file_path: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
    except Exception as e:
        return {"error": str(e)}
        
    imports = []
    classes = []
    functions = []
    
    for node in tree.body:
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            try:
                # `ast.unparse` will cleanly recreate the import string
                imports.append(ast.unparse(node))
            except Exception:
                pass
        elif isinstance(node, ast.ClassDef):
            classes.append(extract_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(extract_function(node))
            
    variables = extract_variables(tree.body)
            
    return {
        "imports": imports,
        "variables": variables,
        "classes": classes,
        "functions": functions
    }
