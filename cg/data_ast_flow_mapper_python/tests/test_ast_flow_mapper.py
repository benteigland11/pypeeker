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
        assert flow[0]["end_line"] == 8
        
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

def test_flow_maps_meaningful_assignments():
    code = """
def send_request(method, url, settings):
    req = Request(method=method.upper(), url=url)
    prep = self.prepare_request(req)
    send_kwargs = {"timeout": None}
    send_kwargs.update(settings)
    resp = self.send(prep, **send_kwargs)
    return resp
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        res = map_flow(path, "send_request")
        flow = res["flow"]
        assert [step["type"] for step in flow] == [
            "assign",
            "assign",
            "assign",
            "call",
            "assign",
            "return",
        ]
        assert flow[0]["target"] == "req"
        assert flow[0]["value"] == "Request(method=method.upper(), url=url)"
        assert flow[4]["target"] == "resp"
        assert flow[4]["value"] == "self.send(prep, **send_kwargs)"
    finally:
        os.remove(path)

def test_flow_maps_state_and_loop_edges():
    code = '''
def stateful(items):
    "docstring should not be emitted"
    current = None
    for item in items:
        if item.skip:
            continue
        current = item
        item.content
        del item.temp
        break
    else:
        current = "missing"
    try:
        assert current is not None, "missing"
    except AssertionError:
        raise
    else:
        current.ready
    finally:
        cleanup()
    return current
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        res = map_flow(path, "stateful")
        flow = res["flow"]

        assert flow[0] == {"line": 4, "end_line": 4, "type": "assign", "target": "current", "value": "None"}
        loop = flow[1]
        assert loop["type"] == "for"
        assert loop["orelse"][0]["value"] == "'missing'"
        assert loop["body"][0]["body"][0]["type"] == "continue"
        assert loop["body"][1]["target"] == "current"
        assert loop["body"][2] == {"line": 9, "end_line": 9, "type": "access", "value": "item.content"}
        assert loop["body"][3] == {"line": 10, "end_line": 10, "type": "delete", "targets": ["item.temp"]}
        assert loop["body"][4]["type"] == "break"

        try_node = flow[2]
        assert try_node["type"] == "try"
        assert try_node["body"][0]["type"] == "assert"
        assert try_node["orelse"][0] == {"line": 19, "end_line": 19, "type": "access", "value": "current.ready"}
        assert try_node["finalbody"][0]["type"] == "call"
    finally:
        os.remove(path)

def test_flow_supports_qualified_method_names():
    code = """
def request():
    return "module"

class Session:
    def request(self):
        prep = self.prepare()
        return prep
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        res = map_flow(path, "Session.request")
        assert res["function"] == "Session.request"
        assert res["flow"][0]["target"] == "prep"
        assert res["flow"][0]["line"] == 7
        assert res["flow"][1]["value"] == "prep"
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
