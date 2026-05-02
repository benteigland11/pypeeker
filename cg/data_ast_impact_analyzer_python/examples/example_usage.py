"""
Example usage of AST Impact Analyzer.
"""
import sys, os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.ast_impact_analyzer import analyze_impact

file_path = os.path.abspath(__file__)
impact = analyze_impact(file_path, "analyze_impact")
print(json.dumps(impact, indent=2))
