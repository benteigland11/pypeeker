import os
import tempfile
import ast
from src.ast_flow_mapper import map_flow

def test_map_flow_enhanced():
    code = """
def complex_flow(x):
    with open("f.txt") as f:
        match x:
            case 1 if x > 0:
                return "one"
            case _:
                raise ValueError()
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
        
    try:
        res = map_flow(path, "complex_flow")
        assert "error" not in res
        flow = res["flow"]
        
        # 1. With block
        assert flow[0]["type"] == "with"
        assert flow[0]["line"] == 3
        
        # 2. Match block
        match_node = flow[0]["body"][0]
        assert match_node["type"] == "match"
        assert match_node["line"] == 4
        
        # 3. Case block
        case1 = match_node["cases"][0]
        assert case1["line"] == 5
        assert case1["body"][0]["type"] == "return"
        assert case1["body"][0]["line"] == 6
        
    finally:
        os.remove(path)

def test_flow_variations():
    code = """
async def variations():
    while True:
        yield 1
        yield from [2]
    for i in x:
        pass
    try:
        pass
    finally:
        pass
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        res = map_flow(path, "variations")
        flow = res["flow"]
        assert flow[0]["type"] == "while"
        assert flow[0]["body"][0]["type"] == "yield"
        assert flow[0]["body"][1]["type"] == "yield"
        assert flow[1]["type"] == "for"
        assert flow[2]["type"] == "try"
    finally:
        os.remove(path)

def test_not_found():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("def a(): pass")
        path = f.name
    try:
        res = map_flow(path, "ghost")
        assert "error" in res
    finally:
        os.remove(path)
