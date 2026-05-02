from src.cli_args import create_parser, add_scan_args
import argparse

def test_parser_creation():
    parser = create_parser("Test")
    assert isinstance(parser, argparse.ArgumentParser)

def test_add_scan_args():
    parser = argparse.ArgumentParser()
    add_scan_args(parser)
    args = parser.parse_args(["/tmp", "--ignore", "node_modules", "--output", "json"])
    assert args.directory == "/tmp"
    assert args.ignore == ["node_modules"]
    assert args.output == "json"

def test_parse_args_convenience():
    import sys
    from unittest.mock import patch
    from src.cli_args import parse_args
    with patch.object(sys, 'argv', ["prog", "/tmp"]):
        args = parse_args("Test Desc")
        assert args.directory == "/tmp"
