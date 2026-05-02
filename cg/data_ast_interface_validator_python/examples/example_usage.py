"""
Example usage of AST Interface Validator.
"""
import sys, os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.ast_interface_validator import validate_interface

file_path = os.path.abspath(__file__)
gaps = validate_interface(file_path)
print(json.dumps(gaps, indent=2))
