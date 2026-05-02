"""
Example usage of Ast Symbol Locator.
"""
import sys, os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.ast_symbol_locator import locate_symbol

file_path = os.path.abspath(__file__)
matches = locate_symbol(file_path, "sys")
print(json.dumps(matches, indent=2))
