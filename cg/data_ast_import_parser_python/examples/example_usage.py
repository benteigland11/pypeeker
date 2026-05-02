"""
Example usage of Ast Import Parser.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.ast_import_parser import parse_imports, resolve_import

# Parse this file
file_path = os.path.abspath(__file__)
imports = parse_imports(file_path)
print(f"Found {len(imports)} imports in this file.")

# Try to resolve 'os' (will likely fail since it's stdlib and not in root_dir, which is intended behavior for this widget)
root_dir = os.path.dirname(file_path)
resolved = resolve_import('os', file_path, root_dir, False, 0)
print(f"Resolution of 'os' in {root_dir}: {resolved}")
