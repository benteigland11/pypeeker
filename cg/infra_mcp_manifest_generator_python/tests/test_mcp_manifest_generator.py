import os
import shutil
import tempfile
import json
from src.mcp_manifest_generator import McpManifestGenerator

def test_generate_all():
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    
    try:
        gen = McpManifestGenerator(
            name="pypeeker",
            version="1.0.0",
            description="Analysis tool",
            command="pypeeker",
            args=["mcp"],
            author="@dev"
        )
        gen.generate_all()
        
        # Check files exist
        assert os.path.exists("extension/gemini-extension.json")
        assert os.path.exists(".claude-plugin/plugin.json")
        assert os.path.exists("marketplace.json")
        
        # Verify content of one
        with open("extension/gemini-extension.json", "r") as f:
            data = json.load(f)
            assert data["name"] == "pypeeker"
            assert data["mcpServers"]["pypeeker"]["command"] == "pypeeker"
            
    finally:
        shutil.rmtree(temp_dir)

def test_pythonpath_injection():
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    try:
        gen = McpManifestGenerator(
            name="pypeeker",
            version="1.0.0",
            description="Analysis tool",
            command="python3",
            args=["-m", "pypeeker.cli", "mcp"]
        )
        gen.generate_gemini("ext")
        with open("ext/gemini-extension.json", "r") as f:
            data = json.load(f)
            assert data["mcpServers"]["pypeeker"]["env"]["PYTHONPATH"] == "${extensionPath}"
    finally:
        shutil.rmtree(temp_dir)
