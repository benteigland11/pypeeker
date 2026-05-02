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

pypeeker turns "read whole files until you find the bug" into a targeted loop:
**map → understand → edit**, with line anchors at every step.

The walkthrough below uses [`psf/requests`](https://github.com/psf/requests) — a
real, well-known library — to answer a real agent question:
*"How does requests handle authentication during redirects?"*

### 1. Map the file — `skeleton`

Strip every function body. Keep imports, signatures, docstrings, and the line
range each symbol occupies.

```bash
$ pypeeker skeleton requests/sessions.py --format stub
```
```python
import os
import time
from .auth import _basic_auth_str
from .cookies import RequestsCookieJar, extract_cookies_to_jar
# ...

class SessionRedirectMixin:  # L107-353
    def get_redirect_target(self, resp):  # L108-126
        """Receives a Response. Returns a redirect URI or ``None``"""
        ...

    def should_strip_auth(self, old_url, new_url):  # L128-158
        """Decide whether Authorization header should be removed when redirecting"""
        ...

    def rebuild_auth(self, prepared_request, response):  # L282-300
        """When being redirected we may want to strip authentication..."""
        ...
```

The two methods we want — `should_strip_auth` and `rebuild_auth` — are now
visible with their exact line ranges.

### 2. Understand the logic — `flow`

Render a function's branching logic as line-anchored pseudocode. No comments,
no whitespace noise, no docstring repetition.

```bash
$ pypeeker flow Session.send requests/sessions.py --format pseudo
```
```
# flow: Session.send  L675-750
L682  kwargs.setdefault('stream', self.stream)
L685  if 'proxies' not in kwargs:
L686      kwargs['proxies'] = resolve_proxies(request, self.proxies, self.trust_env)
L690  if isinstance(request, Request):
L691      raise ValueError('You can only send PreparedRequests.')
L705  r = adapter.send(request, **kwargs)
L712  r = dispatch_hook('response', hooks, r, **kwargs)
L723  if allow_redirects:
L725      gen = self.resolve_redirects(r, request, **kwargs)
L726      history = [resp for resp in gen]
      else:
L728      history = []
L739  if not allow_redirects:
L740      try:
L741          r._next = next(self.resolve_redirects(r, request, yield_requests=True, **kwargs))
L744      except StopIteration:
L750  return r
```

Whole-method bounds in the header (`L675-750`); per-step lines on every node.
The agent can `Read offset=685 limit=2` for a single branch, or replace the
whole method with `offset=675 limit=76`.

### 3. The token math

Same task — find where requests handles redirect auth — measured against
actual agent tool output, including the `Read` tool's line-number prefixes.
Tokens counted with OpenAI's `o200k_base` tokenizer (used by GPT-4o, o1, o3, and GPT-5).

| Workflow                                                                    | Tokens |
|-----------------------------------------------------------------------------|-------:|
| `Read sessions.py` (full file)                                              | 9,063  |
| `skeleton sessions.py` + 2 targeted `Read` calls (L128-158, L282-300)       | 3,218  |
| **`skeleton sessions.py` + 2 `flow` calls on the relevant methods**         | **2,925** |

The combo workflow ends with the agent **better informed** (logic structure
instead of literal code) and able to jump to any line for surgical edits.

For project-scale orientation, mapping the full `requests` package (18 files):

| Operation                                                                   | Tokens |
|-----------------------------------------------------------------------------|-------:|
| `Read` every `.py` file in `requests/`                                      | 59,901 |
| `skeleton requests/`                                                        | 19,508 |

The entire library API surface — every public class, signature, docstring, and
line range — in one call.

### Also included

- **`locate`** — AST-aware symbol search with scope ranges (`path:start-end  signature`). No false positives from substring matches; distinguishes definitions from usages.
- **`circular`** — find import cycles, separates runtime cycles from safe `TYPE_CHECKING` cycles.
- **`missing`** — detect hallucinated or broken internal imports.
- **`impact`** — blast-radius analysis: which globals, attributes, or external calls a function touches.
- **`interfaces`** — flag missing docstrings and type annotations across a project.

All tools default to condensed text/stub output over MCP. Pass `--format json`
on the CLI for structured output suitable for `jq` and downstream tooling.

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
