import os
import tempfile
from src.ast_impact_analyzer import analyze_impact

def test_analyze_impact_granular():
    code = """
global_var = 1
def my_func(arg1):
    global global_var
    local_var = 2
    self.state = 3
    print(global_var)
    print(arg1)
    def nested():
        nonlocal local_var
        local_var = 4
    nested()
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        res = analyze_impact(path, "my_func")
        assert "error" not in res
        
        # External
        ext = res["external"]
        assert "print" in ext["calls"]
        assert "global_var" in ext["reads"]
        assert "global_var" in res["external"]["globals"]
        assert "self.state" in ext["writes"]
        
        # Internal
        intl = res["internal"]
        assert "nested" in intl["calls"]
        assert "arg1" in intl["reads"]
        assert "local_var" in intl["writes"]
        
    finally:
        os.remove(path)

def test_not_found():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("def a(): pass")
        path = f.name
    try:
        res = analyze_impact(path, "ghost")
        assert "error" in res
    finally:
        os.remove(path)
