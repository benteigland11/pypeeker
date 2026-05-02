"""
Example usage of Ast Skeleton Parser.
"""
import sys, os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.ast_skeleton_parser import parse_skeleton

file_path = os.path.abspath(__file__)
skel = parse_skeleton(file_path)
print(json.dumps(skel, indent=2))
