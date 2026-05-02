import os
import tempfile
from src.ast_interface_validator import validate_interface

def test_validate_interface():
    code = """
class Good:
    \"\"\"This is a good class.\"\"\"
    def __init__(self, x: int):
        pass
    def method(self, y: str) -> bool:
        \"\"\"Good method.\"\"\"
        return True

def bad_func(a, b=1):
    return a + b
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        gaps = validate_interface(path)
        # 2 gaps: Good.__init__ (missing docstring), bad_func (everything missing)
        assert len(gaps) == 2
        
        init_gap = next(gap for gap in gaps if gap["symbol"] == "Good.__init__")
        assert "missing_docstring" in init_gap["gaps"]
        
        bad_gap = next(gap for gap in gaps if gap["symbol"] == "bad_func")
        assert bad_gap["symbol"] == "bad_func"
        assert "missing_docstring" in bad_gap["gaps"]
        assert "missing_type_hint: a" in bad_gap["gaps"]
        assert "missing_type_hint: b" in bad_gap["gaps"]
        assert "missing_return_type" in bad_gap["gaps"]
    finally:
        os.remove(path)

def test_parse_error():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("invalid syntax @@@")
        path = f.name
    try:
        gaps = validate_interface(path)
        assert len(gaps) == 1
        assert "error" in gaps[0]
    finally:
        os.remove(path)
