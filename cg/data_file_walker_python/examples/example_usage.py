"""
Example usage of File Walker.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.file_walker import walk_python_files

# Walk the directory containing this example
example_dir = os.path.dirname(os.path.abspath(__file__))
files = walk_python_files(example_dir)
print(f"Found {len(files)} python files in {example_dir}")
