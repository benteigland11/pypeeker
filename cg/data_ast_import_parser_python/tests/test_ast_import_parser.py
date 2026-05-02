from src.ast_import_parser import parse_imports, resolve_import
import os
import tempfile
import shutil

def test_parse_imports():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("import os\nfrom sys import path\nfrom . import local")
        path = f.name
    try:
        imports = parse_imports(path)
        # (module, line, is_rel, level, is_tc)
        assert any(i[0] == "os" and not i[2] and not i[4] for i in imports)
        assert any(i[0] == "sys" and not i[2] and not i[4] for i in imports)
        assert any(i[0] == "local" and i[2] and not i[4] for i in imports)
    finally:
        os.remove(path)

def test_parse_imports_error():
    # Syntax error
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("invalid syntax @@@")
        path = f.name
    try:
        assert parse_imports(path) == []
    finally:
        os.remove(path)

def test_parse_imports_tc():
    # Test both TYPE_CHECKING and typing.TYPE_CHECKING
    code = """
import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import b
if typing.TYPE_CHECKING:
    import c
else:
    import d
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        imports = parse_imports(path)
        assert any(i[0] == "b" and i[4] for i in imports)
        assert any(i[0] == "c" and i[4] for i in imports)
        assert any(i[0] == "d" and not i[4] for i in imports)
    finally:
        os.remove(path)

def test_resolve_import_granularity():
    root = tempfile.mkdtemp()
    try:
        a_py = os.path.join(root, "a.py")
        b_py = os.path.join(root, "b.py")
        open(b_py, "w").close()
        
        # 1. Resolved
        path, reason = resolve_import("b", a_py, root, False, 0)
        assert reason == "resolved"
        assert path == os.path.abspath(b_py)
        
        # 2. External (not in root_dir)
        path, reason = resolve_import("os", a_py, root, False, 0)
        assert reason == "external"
        assert path is None
        
        # 3. Not Found (prefix exists in root_dir, but specific module doesn't)
        os.mkdir(os.path.join(root, "pkg"))
        path, reason = resolve_import("pkg.missing", a_py, root, False, 0)
        assert reason == "not_found"
        
        # 4. Out of bounds
        path, reason = resolve_import("foo", a_py, root, True, 5)
        assert reason == "out_of_bounds"
    finally:
        shutil.rmtree(root)
