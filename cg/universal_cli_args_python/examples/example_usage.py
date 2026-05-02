"""
Example usage of Cli Args.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.cli_args import create_parser, add_scan_args

parser = create_parser("Example Parser")
add_scan_args(parser)
print("CLI Parser created and arguments added successfully.")
