# pypeeker-cli: Unified Agent-Native Python Analysis CLI

[![Powered by Cartograph](https://img.shields.io/badge/Powered%20by-Cartograph-orange?style=flat-square)](https://github.com/benteigland11/Cartograph)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/benteigland11/pypeeker/actions/workflows/ci.yml/badge.svg)](https://github.com/benteigland11/pypeeker/actions/workflows/ci.yml)

pypeeker-cli is a mcp-dependency only Python CLI toolset designed for AI agents to analyze codebases with surgical precision. It transforms raw source code into structured, actionable logical maps.

---

## Cartograph Showcase

pypeeker-cli is a premier showcase for [Cartograph](https://github.com/benteigland11/Cartograph), a platform for reusable engineering. 

Every core feature in pypeeker-cli, from AST parsing to graph cycle detection, is implemented as a standalone, validated Cartograph widget. This architecture ensures that pypeeker-cli is not just a tool, but a modular assembly of hardened building blocks that can be easily extended or repurposed.

---

## Analysis Surface Area

pypeeker-cli categorizes its tools by Analysis Surface Area, allowing agents to choose the right depth for their task:

### 1. Project Scan (Horizontal)
Broad audits of the entire project tree to find relationships and hazards.
*   **circular**: Find import dependency loops (identifies runtime crashes vs safe TYPE_CHECKING cycles).
*   **missing**: Detect hallucinated or missing internal imports using Dynamic Root Discovery.
*   **interfaces**: Validate code contracts (flags missing docstrings and type hints; tests are ignored by default, use `--include-tests` to opt in).

### 2. Navigation (Relationship)
Pinpoint and trace symbols across file boundaries.
*   **locate**: Find a symbol's exact definition bounds (start/end lines) or trace its usages (`--usages`) and ancestry (`--inherited`).

### 3. Deep Dive (Vertical)
Surgical analysis inside a specific file or function.
*   **skeleton**: Extract the API surface of a file (imports, classes, variables, signatures) without function bodies.
*   **flow**: Map the logical control flow (pseudocode) of a function with precise line anchors.
*   **impact**: Analyze the blast radius of a function, distinguishing between internal and external side effects.

---

## Tool Showcase

pypeeker transforms dense Python source into structured, machine-first intelligence.

### API Skeleton extraction
Compress a 500-line file into a surgical map of its signatures and docstrings.

```json
{
  "file": "cli.py",
  "skeleton": {
    "imports": ["import sys", "import os", "import argparse"],
    "functions": [
      {
        "name": "main",
        "docstring": "Main entry point for the pypeeker CLI.",
        "args": [{"name": "args", "type": "argparse.Namespace"}],
        "returns": "None"
      }
    ]
  }
}
```

### Logical Flow mapping
View the branching logic and external calls of a function without reading the implementation boilerplate.

```json
{
  "function": "main",
  "flow": [
    { "line": 77, "type": "call", "value": "cli.add_commands('Project Scan', [...])" },
    { "line": 143, "type": "call", "value": "cli.run()" }
  ]
}
```

### Granular Impact analysis
Identify exactly which class attributes or globals a function modifies before refactoring.

```json
{
  "function": "save",
  "external": {
    "writes": ["self.updated_at", "self.status"],
    "calls": ["db.commit", "logging.info"]
  }
}
```

---

## Installation

Install the pypeeker-cli core primitive globally using pip:

```bash
pip install pypeeker-cli
```

This provides the `pypeeker` command on your system path.

---

## Agent Native Integration

pypeeker-cli is designed to be consumed by AI agents via the Model Context Protocol (MCP). After installing the CLI, you can integrate it into your agent of choice.

### Integration Methods

#### Gemini CLI
Install as a native extension:
```bash
gemini extensions install https://github.com/benteigland11/pypeeker
```

#### Claude Code
Add as a persistent MCP server:
```bash
claude mcp add pypeeker-cli -- pypeeker mcp
```

#### Codex
Add as a global MCP server:
```bash
codex mcp add pypeeker-cli -- pypeeker mcp
```

#### Cursor and Roo Code
Pypeeker is pre-configured for automatic detection via `.cursor/mcp.json`.

#### Continue
The server is pre-configured via `.continue/mcpServers/pypeeker.json`.

#### Windsurf
The server is pre-configured via `.windsurf/mcp_config.json`.

#### Claude Desktop and Aider
Copy the JSON from `claude_desktop_snippet.json` into your global `claude_desktop_config.json`.

---

## Reusable Core

Built using the following Cartograph Widgets (found in `cg/`):
- `cg-infra-agent-cli-python`: Machine-first declarative CLI framework.
- `data-ast-import-parser-python`: Root-aware static import analysis.
- `data-ast-skeleton-parser-python`: API signature extraction.
- `data-ast-symbol-locator-python`: Surgical symbol pinpointing and ancestry.
- `data-ast-interface-validator-python`: API gap detection.
- `data-ast-flow-mapper-python`: Logical pseudocode generation.
- `data-ast-impact-analyzer-python`: Side-effect and dependency mapping.
- `infra-mcp-manifest-generator-python`: Automated distribution scaffolding.
- `universal-agent-response-python`: Standardized JSON schema.
- `universal-list-paginator-python`: Result set pagination.

---

## License

Licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.
