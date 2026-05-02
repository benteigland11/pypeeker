import os
import tempfile
from src.ast_symbol_locator import locate_symbol

def test_locate_symbol_with_signature():
    code = """
TARGET = 10

class TARGET(Base):
    def TARGET(self, x: int = 1):
        pass

async def TARGET():
    pass

class Other:
    TARGET: int = 5
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        matches = locate_symbol(path, "TARGET")
        assert len(matches) == 5
        
        # 1. Global var
        assert "signature" in matches[0]
        assert matches[0]["signature"] == "TARGET = 10"
        
        # 2. Class
        assert matches[1]["signature"] == "class TARGET(Base)"
        assert matches[1]["bases"] == ["Base"]
        
        # 3. Method
        assert matches[2]["signature"] == "def TARGET(self, x: int=1)"
        
        # 4. Async Function
        assert matches[3]["signature"] == "async def TARGET()"
        
        # 5. Class Var
        assert matches[4]["signature"] == "TARGET: int = 5"
        
    finally:
        os.remove(path)

def test_locate_usages():
    code = """
TARGET = 10
def use_target():
    print(TARGET)
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        matches = locate_symbol(path, "TARGET", mode="usage")
        assert len(matches) == 1
        # Usages should NOT include signatures (noise)
        assert "signature" not in matches[0]
    finally:
        os.remove(path)

def test_parse_error():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("invalid syntax @@@")
        path = f.name
    try:
        matches = locate_symbol(path, "TARGET")
        assert len(matches) == 1
        assert "error" in matches[0]
    finally:
        os.remove(path)
