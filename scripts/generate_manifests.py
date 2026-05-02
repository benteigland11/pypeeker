import sys
import os

# Add the project root to sys.path so we can import from 'cg'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from cg.infra_mcp_manifest_generator_python.src.mcp_manifest_generator import McpManifestGenerator

def regenerate_manifests():
    gen = McpManifestGenerator(
        name="pypeeker",
        version="1.0.0",
        description="Agent-native Python static analysis toolset. Includes circular import detection, hallucinated import tracking, API skeleton extraction, surgical symbol locating (definitions & usages), and blast-radius impact analysis.",
        command="pypeeker",
        args=["mcp"],
        author="@benteigland11"
    )
    
    print("Generating agent manifests...")
    gen.generate_all()
    for path in [
        "extension/gemini-extension.json",
        ".claude-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        ".cursor/mcp.json",
        "opencode.json",
        ".continue/mcpServers/pypeeker.json",
        ".windsurf/mcp_config.json",
        ".codex-plugin/plugin.json",
        ".mcp.json",
        "claude_desktop_snippet.json",
    ]:
        print(f"✓ {path}")

if __name__ == "__main__":
    regenerate_manifests()
