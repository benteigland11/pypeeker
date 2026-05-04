import subprocess
import json
import sys
from argparse import Namespace

from pypeeker.commands.impact import cmd_impact
from pypeeker.commands.interfaces import cmd_interfaces


def test_cli_help():
    """Verify pypeeker --help exits with 0."""
    result = subprocess.run([sys.executable, "-m", "pypeeker.cli", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Project Scan" in result.stdout
    assert "--include-tests" in subprocess.run(
        [sys.executable, "-m", "pypeeker.cli", "interfaces", "-h"],
        capture_output=True,
        text=True,
    ).stdout


def test_cli_circular_json():
    """Verify circular --format json returns the structured list payload."""
    result = subprocess.run([sys.executable, "-m", "pypeeker.cli", "circular", ".", "--format", "json"], capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "success"
    assert isinstance(data["data"], list)


def test_cli_circular_default_text():
    """Verify circular defaults to the condensed text payload."""
    result = subprocess.run([sys.executable, "-m", "pypeeker.cli", "circular", "."], capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "success"
    assert "text" in data["data"]
    assert data["data"]["text"].startswith("# circular imports")


def test_interfaces_ignores_tests_by_default(tmp_path):
    """Verify interface scanning excludes test-only gaps by default."""
    src_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    src_dir.mkdir()
    tests_dir.mkdir()
    (src_dir / "module.py").write_text("def public(value):\n    return value\n", encoding="utf-8")
    (tests_dir / "test_module.py").write_text("def test_public():\n    assert True\n", encoding="utf-8")

    args = Namespace(directory=str(tmp_path), ignore=[], ignore_tests=True, page=1, size=20)
    result = cmd_interfaces(args)

    assert result["status"] == "success"
    assert result["meta"]["total_gaps"] == 1
    assert result["meta"]["ignored_tests"] is True
    assert result["data"][0]["file"] == "pkg/module.py"


def test_interfaces_can_include_tests(tmp_path):
    """Verify interface scanning can opt into test-file gaps."""
    src_dir = tmp_path / "pkg"
    tests_dir = tmp_path / "tests"
    src_dir.mkdir()
    tests_dir.mkdir()
    (src_dir / "module.py").write_text("def public(value):\n    return value\n", encoding="utf-8")
    (tests_dir / "test_module.py").write_text("def test_public():\n    assert True\n", encoding="utf-8")

    args = Namespace(directory=str(tmp_path), ignore=[], ignore_tests=False, page=1, size=20)
    result = cmd_interfaces(args)

    assert result["status"] == "success"
    assert result["meta"]["total_gaps"] == 2
    assert result["meta"]["ignored_tests"] is False
    assert {item["file"] for item in result["data"]} == {"pkg/module.py", "tests/test_module.py"}


def test_resolve_ignore_merges_user_with_defaults():
    """User-provided ignores are added to defaults, not replacing them."""
    from pypeeker.commands.common import resolve_ignore, DEFAULT_IGNORE_DIRS

    merged = set(resolve_ignore(["custom_dir"], include_deps=False))
    assert "custom_dir" in merged
    assert "venv" in merged  # default still present
    assert "__pycache__" in merged  # default still present
    assert merged >= DEFAULT_IGNORE_DIRS  # all defaults preserved


def test_resolve_ignore_include_deps_drops_defaults():
    """include_deps=True bypasses the default skip list."""
    from pypeeker.commands.common import resolve_ignore

    minimal = set(resolve_ignore(["custom_dir"], include_deps=True))
    assert minimal == {"custom_dir"}


def test_resolve_ignore_handles_none_user_input():
    """A None user-ignore yields just the defaults."""
    from pypeeker.commands.common import resolve_ignore, DEFAULT_IGNORE_DIRS

    assert set(resolve_ignore(None, include_deps=False)) == DEFAULT_IGNORE_DIRS
    assert resolve_ignore(None, include_deps=True) == []


def test_circular_skips_venv_by_default(tmp_path):
    """A venv full of cycles should be invisible to default scans."""
    from pypeeker.commands.circular import cmd_circular

    # Create a real cycle in the project root
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a\n", encoding="utf-8")
    # Create a cycle inside a venv (should be ignored)
    venv = tmp_path / "venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "x.py").write_text("import y\n", encoding="utf-8")
    (venv / "y.py").write_text("import x\n", encoding="utf-8")

    args = Namespace(directory=str(tmp_path), ignore=[], page=1, size=20, format="json", summary_only=False, include_deps=False)
    result = cmd_circular(args)

    assert result["meta"]["total_cycles"] == 1  # only the project-level cycle


def test_circular_surfaces_cycle_hubs(tmp_path):
    """Circular scan ranks files by the number of cycles they appear in."""
    from pypeeker.commands.circular import cmd_circular

    # Two cycles, both passing through hub.py:
    #   hub.py -> a.py -> hub.py
    #   hub.py -> b.py -> hub.py
    (tmp_path / "hub.py").write_text("import a\nimport b\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import hub\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import hub\n", encoding="utf-8")

    args = Namespace(directory=str(tmp_path), ignore=[], page=1, size=20, format="json", summary_only=False)
    result = cmd_circular(args)

    assert result["status"] == "success"
    assert result["meta"]["total_cycles"] == 2
    hubs = result["meta"]["cycle_hubs"]
    assert hubs[0]["file"] == "hub.py"
    assert hubs[0]["cycle_count"] == 2


def test_circular_summary_only_suppresses_cycle_bodies(tmp_path):
    """summary_only mode returns the count + hubs without per-cycle detail."""
    from pypeeker.commands.circular import cmd_circular

    (tmp_path / "hub.py").write_text("import a\nimport b\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import hub\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import hub\n", encoding="utf-8")

    args = Namespace(directory=str(tmp_path), ignore=[], page=1, size=20, format="text", summary_only=True)
    result = cmd_circular(args)

    text = result["data"]["text"]
    assert "[hubs]" in text
    assert "hub.py" in text
    assert "[1] runtime cycle:" not in text  # cycle bodies suppressed


def test_impact_depth_propagates_writes_through_call_graph(tmp_path):
    """At depth>=2, transitive_external.writes aggregates writes from called functions."""
    from pypeeker.commands.impact import cmd_impact

    (tmp_path / "mod.py").write_text(
        "class Service:\n"
        "    def entry(self):\n"
        "        self.helper()\n"
        "    def helper(self):\n"
        "        self.shared_state = 1\n",
        encoding="utf-8",
    )

    # Depth=1: only direct writes from entry (none — helper does the writing)
    direct = cmd_impact(Namespace(path=str(tmp_path / "mod.py"), symbol="Service.entry", depth=1, root=str(tmp_path), format="json", outbound=True))
    assert direct["data"]["outbound"]["external"]["writes"] == []

    # Depth=2: should surface helper's write transitively
    transitive = cmd_impact(Namespace(path=str(tmp_path / "mod.py"), symbol="Service.entry", depth=2, root=str(tmp_path), format="json", outbound=True))
    writes = transitive["data"]["outbound"]["transitive_external"]["writes"]
    assert any(w["name"] == "self.shared_state" for w in writes)
    assert any(w["in_symbol"] == "Service.helper" for w in writes)


def test_impact_depth_marks_unresolved_calls(tmp_path):
    """Dynamic dispatch and built-ins should be reported as unresolved, not silently followed."""
    from pypeeker.commands.impact import cmd_impact

    (tmp_path / "mod.py").write_text(
        "class Service:\n"
        "    def entry(self, obj):\n"
        "        obj.method()\n"
        "        len([1, 2, 3])\n",
        encoding="utf-8",
    )

    result = cmd_impact(Namespace(path=str(tmp_path / "mod.py"), symbol="Service.entry", depth=2, root=str(tmp_path), format="json", outbound=True))
    unresolved_calls = {u["call"] for u in result["data"]["outbound"]["unresolved"]}
    assert "obj.method" in unresolved_calls
    assert "len" in unresolved_calls


def test_impact_depth_is_cycle_safe(tmp_path):
    """A → B → A should not infinite-loop."""
    from pypeeker.commands.impact import cmd_impact

    (tmp_path / "mod.py").write_text(
        "def a():\n"
        "    b()\n"
        "def b():\n"
        "    a()\n",
        encoding="utf-8",
    )

    # Should complete without timeout/recursion error
    result = cmd_impact(Namespace(path=str(tmp_path / "mod.py"), symbol="a", depth=5, root=str(tmp_path), format="json", outbound=True))
    visited_symbols = {v["symbol"] for v in result["data"]["outbound"]["visited"]}
    assert visited_symbols == {"a", "b"}  # each visited exactly once


def test_impact_disambiguates_methods_by_class(tmp_path):
    """Verify impact accepts qualified Class.method names so same-named methods resolve correctly."""
    target = tmp_path / "mod.py"
    target.write_text(
        "class A:\n"
        "    def run(self):\n"
        "        self.a_only = True\n"
        "class B:\n"
        "    def run(self):\n"
        "        self.b_only = True\n",
        encoding="utf-8",
    )

    a = cmd_impact(Namespace(path=str(target), symbol="A.run", outbound=True))
    b = cmd_impact(Namespace(path=str(target), symbol="B.run", outbound=True))

    assert a["status"] == "success"
    assert b["status"] == "success"
    assert "self.a_only" in a["data"]["outbound"]["external"]["writes"]
    assert "self.b_only" not in a["data"]["outbound"]["external"]["writes"]
    assert "self.b_only" in b["data"]["outbound"]["external"]["writes"]
    assert "self.a_only" not in b["data"]["outbound"]["external"]["writes"]


def test_impact_inbound_filters_out_unrelated_same_name(tmp_path):
    """Verify inbound only returns callers that actually import the defining file.

    Regression: prior behavior did pure-name matching across the project, so a
    symbol like `resolve` would falsely match every unrelated file that defined
    its own `resolve()`. The fix gates inbound hits on the importing file
    actually pulling in the defining module.
    """
    target = tmp_path / "binary_resolver.py"
    target.write_text(
        "def resolve(name):\n"
        "    return name\n",
        encoding="utf-8",
    )
    # Real caller — imports from the defining module.
    real = tmp_path / "real_caller.py"
    real.write_text(
        "from binary_resolver import resolve\n"
        "def go():\n"
        "    return resolve('nim')\n",
        encoding="utf-8",
    )
    # Fake caller — has a function called `resolve` but doesn't import the target.
    fake = tmp_path / "fake_caller.py"
    fake.write_text(
        "def resolve(x):\n"
        "    return x + 1\n"
        "def use():\n"
        "    return resolve(42)\n",
        encoding="utf-8",
    )

    result = cmd_impact(Namespace(
        path=str(target), symbol="resolve",
        inbound=True, root=str(tmp_path), format="json",
    ))

    assert result["status"] == "success"
    files = {hit["file"] for hit in result["data"]["inbound"]}
    assert "real_caller.py" in files
    assert "fake_caller.py" not in files


def test_impact_inbound_keeps_same_file_callers(tmp_path):
    """Verify inbound keeps callers in the same file as the defining symbol
    (no import needed when symbol is in local scope)."""
    target = tmp_path / "mod.py"
    target.write_text(
        "def helper():\n"
        "    return 1\n"
        "def caller():\n"
        "    return helper()\n",
        encoding="utf-8",
    )

    result = cmd_impact(Namespace(
        path=str(target), symbol="helper",
        inbound=True, root=str(tmp_path), format="json",
    ))

    assert result["status"] == "success"
    files = {hit["file"] for hit in result["data"]["inbound"]}
    assert "mod.py" in files


def test_impact_inbound_accepts_sibling_package_reexport(tmp_path):
    """Verify inbound accepts callers that import via a sibling __init__.py
    in the same package directory (covers `from pkg import name` re-exports)."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from .core import resolve\n",
        encoding="utf-8",
    )
    target = pkg / "core.py"
    target.write_text(
        "def resolve(name):\n"
        "    return name\n",
        encoding="utf-8",
    )
    caller = tmp_path / "caller.py"
    caller.write_text(
        "from pkg import resolve\n"
        "def go():\n"
        "    return resolve('x')\n",
        encoding="utf-8",
    )

    result = cmd_impact(Namespace(
        path=str(target), symbol="resolve",
        inbound=True, root=str(tmp_path), format="json",
    ))

    assert result["status"] == "success"
    files = {hit["file"] for hit in result["data"]["inbound"]}
    assert "caller.py" in files


def test_impact_inbound_resolves_aliased_imports(tmp_path):
    """Verify inbound finds callers that import the symbol under a local alias
    (`from m import resolve as _resolve_bin`)."""
    target = tmp_path / "binary_resolver.py"
    target.write_text(
        "def resolve(name):\n"
        "    return name\n",
        encoding="utf-8",
    )
    aliased = tmp_path / "aliased_caller.py"
    aliased.write_text(
        "from binary_resolver import resolve as _resolve_bin\n"
        "def go():\n"
        "    return _resolve_bin('nim')\n",
        encoding="utf-8",
    )

    result = cmd_impact(Namespace(
        path=str(target), symbol="resolve",
        inbound=True, root=str(tmp_path), format="json",
    ))

    assert result["status"] == "success"
    files = {hit["file"] for hit in result["data"]["inbound"]}
    assert "aliased_caller.py" in files


def test_impact_rejects_non_python_file(tmp_path):
    """Verify impact only accepts Python source files."""
    target = tmp_path / "notes.txt"
    target.write_text("not python", encoding="utf-8")

    result = cmd_impact(Namespace(path=str(target), symbol="main"))

    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_FILE_TYPE"
