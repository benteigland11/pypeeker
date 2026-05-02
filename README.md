# pypeeker-cli: Unified Agent-Native Python Analysis CLI

[![Powered by Cartograph](https://img.shields.io/badge/Powered%20by-Cartograph-orange?style=flat-square)](https://github.com/benteigland11/Cartograph)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/benteigland11/pypeeker/actions/workflows/ci.yml/badge.svg)](https://github.com/benteigland11/pypeeker/actions/workflows/ci.yml)

pypeeker-cli is a zero-dependency Python CLI toolset designed for AI agents to analyze codebases with surgical precision. It transforms raw source code into structured, actionable logical maps.

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
*   **interfaces**: Validate code contracts (flags missing docstrings and type hints).

### 2. Navigation (Relationship)
Pinpoint and trace symbols across file boundaries.
*   **locate**: Find a symbol's exact definition bounds (start/end lines) or trace its usages (`--usages`) and ancestry (`--inherited`).

### 3. Deep Dive (Vertical)
Surgical analysis inside a specific file or function.
*   **skeleton**: Extract the API surface of a file (imports, classes, variables, signatures) without function bodies.
*   **flow**: Map the logical control flow (pseudocode) of a function with precise line anchors.
*   **impact**: Analyze the blast radius of a function, distinguishing between internal and external side effects.

---

## Installation

Install pypeeker-cli globally using pip:

```bash
pip install pypeeker-cli
```

*(Note: While in development, you can install locally via pip install .)*

---

## Release Flow

Pypeeker uses Trusted Publishing (OIDC) via GitHub Actions.

1.  **Tag a release**: `git tag -a v1.0.0-cli -m "Release v1.0.0-cli"`
2.  **Push the tag**: `git push origin v1.0.0-cli`
3.  The `pypi-publish.yml` workflow will automatically build and publish the version to PyPI.

---

## Agent Native Integration

pypeeker-cli is built to be a native plugin for AI agents using the Model Context Protocol (MCP).

### Subcommand Usage
```bash
pypeeker mcp
```

### Supported Platforms
*   **Gemini CLI**: `extension/gemini-extension.json`
*   **Claude Code**: `.claude-plugin/plugin.json`
*   **Cursor and Roo Code**: `.cursor/mcp.json` (Auto-detected)
*   **Continue (VS Code / JetBrains)**: `.continue/mcpServers/pypeeker.json`
*   **Windsurf**: `.windsurf/mcp_config.json`

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
