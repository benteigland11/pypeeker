"""
Example usage of MCP Manifest Generator.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.mcp_manifest_generator import McpManifestGenerator

# Mock metadata
gen = McpManifestGenerator(
    name="test-tool",
    version="1.0.0",
    description="A test tool for agents.",
    command="test-tool",
    args=["mcp"],
    author="@developer"
)

# In a real tool, you would run this in a setup script:
# gen.generate_all()
print("Manifest generator initialized and ready to generate gemini, claude, and marketplace manifests.")
