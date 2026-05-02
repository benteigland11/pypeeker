"""
Example usage of AST Flow Mapper.
"""
import sys, os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.ast_flow_mapper import map_flow

file_path = os.path.abspath(__file__)
flow = map_flow(file_path, "map_flow")
print(json.dumps(flow, indent=2))
