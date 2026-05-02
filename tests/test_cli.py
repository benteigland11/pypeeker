import subprocess
import json
import sys
from argparse import Namespace

from pypeeker.commands.flow import cmd_flow
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


def test_flow_rejects_non_python_file(tmp_path):
    """Verify flow only accepts Python source files."""
    target = tmp_path / "notes.txt"
    target.write_text("not python", encoding="utf-8")

    result = cmd_flow(Namespace(path=str(target), symbol="main"))

    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_FILE_TYPE"


def test_impact_rejects_non_python_file(tmp_path):
    """Verify impact only accepts Python source files."""
    target = tmp_path / "notes.txt"
    target.write_text("not python", encoding="utf-8")

    result = cmd_impact(Namespace(path=str(target), symbol="main"))

    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_FILE_TYPE"
