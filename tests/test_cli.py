import subprocess
import json

def test_cli_help():
    """Verify pypeeker --help exits with 0."""
    result = subprocess.run(["pypeeker", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Project Scan" in result.stdout

def test_cli_circular_json():
    """Verify circular command returns valid JSON."""
    # Run against the current directory
    result = subprocess.run(["pypeeker", "circular", "."], capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
