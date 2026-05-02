import os
import tempfile
from src.ast_skeleton_parser import parse_skeleton

def test_parse_skeleton():
    code = """
import os
from sys import path

GLOBAL_VAR = 10
TYPED_VAR: str = "hello"

@app.route("/")
@cache
def hello(name: str, count=1) -> str:
    \"\"\"Say hello.\"\"\"
    return name * count

@dataclass
class Greeter(object):
    \"\"\"Greeter class.\"\"\"
    CLASS_VAR = 5
    
    @classmethod
    async def greet(cls, *args, **kwargs):
        pass
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        skel = parse_skeleton(path)
        assert "error" not in skel
        
        imports = skel["imports"]
        assert len(imports) == 2
        assert "import os" in imports[0]
        
        variables = skel["variables"]
        assert len(variables) == 2
        assert variables[0]["name"] == "GLOBAL_VAR"
        assert variables[0]["value"] == "10"
        assert variables[1]["name"] == "TYPED_VAR"
        assert variables[1]["type"] == "str"
        assert variables[1]["value"] == "'hello'"
        
        functions = skel["functions"]
        assert len(functions) == 1
        fn = functions[0]
        assert fn["name"] == "hello"
        assert fn["docstring"] == "Say hello."
        assert fn["returns"] == "str"
        assert fn["decorators"] == ["app.route('/')", 'cache']
        assert len(fn["args"]) == 2
        assert fn["args"][0]["name"] == "name"
        assert fn["args"][0]["type"] == "str"
        assert fn["args"][1]["name"] == "count"
        assert fn["args"][1]["default"] == "1"
        
        classes = skel["classes"]
        assert len(classes) == 1
        cls = classes[0]
        assert cls["name"] == "Greeter"
        assert cls["docstring"] == "Greeter class."
        assert cls["bases"] == ["object"]
        assert cls["decorators"] == ["dataclass"]
        
        cls_vars = cls["variables"]
        assert len(cls_vars) == 1
        assert cls_vars[0]["name"] == "CLASS_VAR"
        assert cls_vars[0]["value"] == "5"
        
        methods = cls["methods"]
        assert len(methods) == 1
        m = methods[0]
        assert m["name"] == "greet"
        assert m["is_async"] is True
        assert m["decorators"] == ["classmethod"]
        assert len(m["args"]) == 3 # cls, *args, **kwargs
        
    finally:
        os.remove(path)

def test_parse_error():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("invalid syntax @@@")
        path = f.name
    try:
        skel = parse_skeleton(path)
        assert "error" in skel
    finally:
        os.remove(path)

def test_ast_unparse_exceptions():
    from unittest.mock import patch
    code = """
import os
VAR = 1
@dec
def hello(name: str = "a", *args: int, kw: str = "b", **kwargs: dict) -> str:
    pass
@dec2
class A(object):
    CVAR = 2
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        with patch("ast.unparse", side_effect=Exception("mocked")):
            skel = parse_skeleton(path)
            # Should gracefully handle the exceptions
            assert "error" not in skel
            
            # imports will be empty because unparse failed
            assert len(skel["imports"]) == 0
            
            # variables empty values
            assert len(skel["variables"]) == 1
            assert "value" not in skel["variables"][0]
            
            # functions will lack types and returns
            fn = skel["functions"][0]
            assert fn["returns"] is None
            assert len(fn["decorators"]) == 0
            for arg in fn["args"]:
                assert "type" not in arg
                assert "default" not in arg
                
            # class bases will be empty
            cls = skel["classes"][0]
            assert len(cls["bases"]) == 0
            assert len(cls["decorators"]) == 0
            assert len(cls["variables"]) == 1
            assert "value" not in cls["variables"][0]
    finally:
        os.remove(path)
