import ast
import os
import importlib.util

def parse_imports(file_path):
    """
    Parse a Python file and extract all import statements.
    Returns a list of tuples: (module_name, line_number, is_relative, level, is_type_checking)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except (SyntaxError, UnicodeDecodeError):
            return []

    imports = []

    def is_type_checking_guard(node):
        """Check if a node is 'if TYPE_CHECKING:'"""
        if isinstance(node, ast.If):
            # Check for 'if TYPE_CHECKING:'
            if isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING':
                return True
            # Check for 'if typing.TYPE_CHECKING:'
            if isinstance(node.test, ast.Attribute) and node.test.attr == 'TYPE_CHECKING':
                return True
        return False

    def walk_with_context(node, in_type_checking=False):
        # We only consider the 'body' of an 'if TYPE_CHECKING:' block as being in_type_checking.
        # The test itself and the 'orelse' block (else branch) are NOT in_type_checking.
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno, False, 0, in_type_checking))
        elif isinstance(node, ast.ImportFrom):
            level = node.level
            is_relative = level > 0
            if node.module:
                imports.append((node.module, node.lineno, is_relative, level, in_type_checking))
            else:
                for alias in node.names:
                    imports.append((alias.name, node.lineno, is_relative, level, in_type_checking))
        
        if is_type_checking_guard(node):
            # Special handling for 'if TYPE_CHECKING:':
            # walk body with in_type_checking=True
            for child in node.body:
                walk_with_context(child, True)
            # walk orelse (else branch) with current in_type_checking
            for child in node.orelse:
                walk_with_context(child, in_type_checking)
        else:
            for child in ast.iter_child_nodes(node):
                walk_with_context(child, in_type_checking)

    walk_with_context(tree)
    return imports

def resolve_import(import_name, current_file, root_dir, is_relative, level):
    """
    Attempts to resolve an import to a file path within root_dir or local package roots.
    Returns a tuple: (resolved_path, reason)
    """
    current_file_abs = os.path.abspath(current_file)
    current_dir = os.path.dirname(current_file_abs)
    root_dir = os.path.abspath(root_dir)
    
    if is_relative:
        # Handle relative imports
        target_dir = current_dir
        for _ in range(level - 1):
            parent = os.path.dirname(target_dir)
            if parent == target_dir: # Root reached
                break
            target_dir = parent
        
        if len(target_dir) < len(root_dir):
            return None, "out_of_bounds"

        parts = import_name.split('.') if import_name else []
        path = os.path.join(target_dir, *parts)
        return _check_path(path)
    else:
        # Handle absolute imports
        parts = import_name.split('.')
        
        # 1. Try resolving relative to the global root_dir
        global_path = os.path.join(root_dir, *parts)
        path, reason = _check_path(global_path)
        if reason == "resolved":
            return path, reason

        # 2. Try climbing up from current_file to find a local root (monorepo/widget support)
        # Look for markers: widget.json, pyproject.toml, setup.py, .git
        check_dir = current_dir
        while len(check_dir) >= len(root_dir):
            markers = ["widget.json", "pyproject.toml", "setup.py", ".git"]
            if any(os.path.exists(os.path.join(check_dir, m)) for m in markers):
                local_path = os.path.join(check_dir, *parts)
                path, reason = _check_path(local_path)
                if reason == "resolved":
                    return path, reason
            
            parent = os.path.dirname(check_dir)
            if parent == check_dir: break
            check_dir = parent

        # 3. If not in any project root, check if it's a real external module
        try:
            if importlib.util.find_spec(parts[0]) is not None:
                return None, "external"
        except (ImportError, AttributeError, ValueError, TypeError):
            pass
            
        return None, "not_found"

def _check_path(path):
    """Internal helper to check if a path is a .py file or a package."""
    py_path = path + '.py'
    init_path = os.path.join(path, '__init__.py')
    
    if os.path.isfile(py_path):
        return os.path.abspath(py_path), "resolved"
    elif os.path.isdir(path) and os.path.isfile(init_path):
        return os.path.abspath(init_path), "resolved"
    
    return None, "not_found"
