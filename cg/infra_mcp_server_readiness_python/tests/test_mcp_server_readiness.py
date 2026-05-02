import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mcp_server_readiness import (
    _is_newer,
    check_for_update,
    get_package_version,
    run_cli_in_process,
)


def test_get_package_version_returns_string_for_installed_package():
    result = get_package_version("pip")
    assert isinstance(result, str)
    assert result != "unknown"


def test_get_package_version_returns_unknown_for_missing_package():
    assert get_package_version("definitely-not-a-real-package-xyz-9999") == "unknown"


def test_run_cli_returns_error_envelope_for_missing_module():
    response = run_cli_in_process("definitely_not_a_module_xyz_9999", "noop")
    assert response["status"] == "error"
    assert response["data"]["exit_code"] != 0


def test_is_newer_basic():
    assert _is_newer("1.5.1", "1.5.0") is True
    assert _is_newer("2.0.0", "1.9.9") is True
    assert _is_newer("1.5.0", "1.5.0") is False
    assert _is_newer("1.4.0", "1.5.0") is False


def test_is_newer_handles_unparseable():
    assert _is_newer("garbage", "1.0.0") is False
    assert _is_newer("1.0.0", "garbage") is False


def test_check_for_update_skipped_when_unknown():
    assert check_for_update("any-pkg", "unknown") is None


def test_check_for_update_honors_env_optout(monkeypatch):
    monkeypatch.setenv("PIP_NO_VERSION_CHECK", "1")
    assert check_for_update("pip", "0.0.1") is None


def test_check_for_update_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    cache_dir = tmp_path / "mcp_server_readiness"
    cache_dir.mkdir()
    import json
    cache_file = cache_dir / "fake-pkg.json"
    cache_file.write_text(json.dumps({"checked_at": time.time(), "latest": "9.9.9"}))
    result = check_for_update("fake-pkg", "1.0.0")
    assert result == "9.9.9"


def test_check_for_update_cache_returns_none_when_not_newer(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    cache_dir = tmp_path / "mcp_server_readiness"
    cache_dir.mkdir()
    import json
    cache_file = cache_dir / "fake-pkg.json"
    cache_file.write_text(json.dumps({"checked_at": time.time(), "latest": "1.0.0"}))
    assert check_for_update("fake-pkg", "1.0.0") is None
