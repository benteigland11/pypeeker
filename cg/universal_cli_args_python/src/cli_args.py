import argparse

def create_parser(description):
    """Creates a basic argument parser."""
    return argparse.ArgumentParser(description=description)

def add_scan_args(parser):
    """Adds standard directory scanning arguments."""
    parser.add_argument("directory", help="The root directory to scan")
    parser.add_argument("--ignore", nargs="*", help="Directories to ignore", default=[])
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")
    return parser

def parse_args(description):
    """Convenience function to create and parse standard args."""
    parser = create_parser(description)
    add_scan_args(parser)
    return parser.parse_args()
