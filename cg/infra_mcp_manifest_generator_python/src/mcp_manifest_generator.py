import json
import os
from typing import Any, Dict, Optional

class McpManifestGenerator:
    """
    Automates the generation of agent-specific manifests for MCP tools.
    Generates: gemini-extension.json, .claude-plugin/plugin.json, and marketplace.json.
    """

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        command: str,
        args: list[str],
        author: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        context_file: str = "GEMINI.md"
    ):
        self.metadata = {
            "name": name,
            "version": version,
            "description": description,
            "command": command,
            "args": args,
            "author": author or "Unknown",
            "env": env or {},
            "context_file": context_file
        }

    def generate_gemini(self, output_dir: str = "extension"):
        """Generates gemini-extension.json."""
        manifest = {
            "name": self.metadata["name"],
            "version": self.metadata["version"],
            "description": self.metadata["description"],
            "mcpServers": {
                self.metadata["name"]: {
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            },
            "contextFileName": self.metadata["context_file"]
        }
        
        # Ensure pathing for local dev if command is python3 -m
        if self.metadata["command"] == "python3" and "-m" in self.metadata["args"]:
            manifest["mcpServers"][self.metadata["name"]]["env"]["PYTHONPATH"] = "${extensionPath}"

        self._write_json(output_dir, "gemini-extension.json", manifest)

    def generate_claude(self, output_dir: str = ".claude-plugin"):
        """Generates plugin.json for Claude Code."""
        manifest = {
            "name": self.metadata["name"],
            "version": self.metadata["version"],
            "description": self.metadata["description"],
            "author": self.metadata["author"],
            "mcpServers": {
                self.metadata["name"]: {
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            }
        }
        self._write_json(output_dir, "plugin.json", manifest)

    def generate_marketplace(self, output_dir: str = ".agents/plugins"):
        """Generates marketplace.json using official Codex schema."""
        manifest = {
            "name": f"{self.metadata['name']}-marketplace",
            "interface": {
                "displayName": f"{self.metadata['name'].capitalize()} Tools"
            },
            "plugins": [
                {
                    "name": self.metadata["name"],
                    "source": {
                        "source": "local",
                        "path": "../.."
                    },
                    "category": "Development"
                }
            ]
        }
        self._write_json(output_dir, "marketplace.json", manifest)

    def generate_cursor(self, output_dir: str = ".cursor"):
        """Generates mcp.json for Cursor or Roo Code."""
        manifest = {
            "mcpServers": {
                self.metadata["name"]: {
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            }
        }
        self._write_json(output_dir, "mcp.json", manifest)

    def generate_opencode(self, output_path: str = "."):
        """Generates opencode.json."""
        manifest = {
            "mcp": {
                self.metadata["name"]: {
                    "type": "local",
                    "command": [self.metadata["command"]] + self.metadata["args"],
                    "enabled": True,
                    "environment": self.metadata["env"]
                }
            }
        }
        self._write_json(output_path, "opencode.json", manifest)

    def generate_continue(self, output_dir: str = ".continue/mcpServers"):
        """Generates mcp.json for Continue (VS Code / JetBrains)."""
        # Continue supports a directory of individual mcp configs
        manifest = {
            "mcpServers": [
                {
                    "name": self.metadata["name"],
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            ]
        }
        self._write_json(output_dir, f"{self.metadata['name']}.json", manifest)

    def generate_windsurf(self, output_dir: str = ".windsurf"):
        """Generates mcp_config.json for Windsurf (Codeium)."""
        manifest = {
            "mcpServers": {
                self.metadata["name"]: {
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            }
        }
        self._write_json(output_dir, "mcp_config.json", manifest)

    def generate_codex(self, output_dir: str = ".codex-plugin"):
        """Generates plugin.json and .mcp.json for Codex."""
        plugin_manifest = {
            "name": self.metadata["name"],
            "version": self.metadata["version"],
            "description": self.metadata["description"],
            "mcpServers": "./.mcp.json"
        }
        self._write_json(output_dir, "plugin.json", plugin_manifest)
        
        # Claude Code rejects snake_case here — schema requires "mcpServers"
        mcp_config = {
            "mcpServers": {
                self.metadata["name"]: {
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            }
        }
        self._write_json(".", ".mcp.json", mcp_config)

    def generate_claude_desktop_snippet(self, output_path: str = "."):
        """Generates a snippet for Claude Desktop/Aider global config."""
        snippet = {
            "mcpServers": {
                self.metadata["name"]: {
                    "command": self.metadata["command"],
                    "args": self.metadata["args"],
                    "env": self.metadata["env"]
                }
            }
        }
        self._write_json(output_path, "claude_desktop_snippet.json", snippet)

    def generate_all(self):
        """Helper to generate all standard manifests at once."""
        self.generate_gemini()
        self.generate_claude()
        self.generate_marketplace()
        self.generate_cursor()
        self.generate_opencode()
        self.generate_continue()
        self.generate_windsurf()
        self.generate_codex()
        self.generate_claude_desktop_snippet()

    def _write_json(self, directory: str, filename: str, data: Any):
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        path = os.path.join(directory, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
