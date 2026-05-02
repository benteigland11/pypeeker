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
        description="Agent-native Python static analysis toolset. Includes circular import detection, hallucinated import tracking, API skeleton extraction, surgical symbol locating (definitions & usages), and logic flow mapping.",
        command="pypeeker",
        args=["mcp"],
        author="@benteigland11"
    )
    
    print("Generating agent manifests...")
    gen.generate_all()
    print("✓ extension/gemini-extension.json")
    print("✓ .claude-plugin/plugin.json")
    print("✓ marketplace.json")

if __name__ == "__main__":
    regenerate_manifests()
